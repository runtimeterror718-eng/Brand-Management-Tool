from __future__ import annotations

from copy import deepcopy

from storage import queries


class _Resp:
    def __init__(self, data):
        self.data = data


class _Exec:
    def __init__(self, response: _Resp):
        self._response = response

    def execute(self):
        return self._response


class _FakeTelegramMessagesTable:
    def __init__(self):
        self.rows: list[dict] = []
        self.last_on_conflict = None

    def upsert(self, payload, on_conflict: str | None = None):
        self.last_on_conflict = on_conflict
        if isinstance(payload, list):
            self.rows.extend(deepcopy(payload))
            return _Exec(_Resp(deepcopy(payload)))
        self.rows.append(deepcopy(payload))
        return _Exec(_Resp([deepcopy(payload)]))


class _FakeTelegramChannelsTable:
    def __init__(self):
        self.updated: list[tuple[str, dict]] = []
        self.inserted: list[dict] = []
        self._pending_update: dict | None = None

    def update(self, payload: dict):
        self._pending_update = deepcopy(payload)
        return self

    def eq(self, field: str, value: str):
        if field != "id":
            raise AssertionError(f"Unexpected eq field: {field}")
        payload = deepcopy(self._pending_update or {})
        self.updated.append((value, payload))
        return _Exec(_Resp([{"id": value, **payload}]))

    def insert(self, payload: dict):
        self.inserted.append(deepcopy(payload))
        return _Exec(_Resp([deepcopy(payload)]))


class _FakeClient:
    def __init__(self):
        self.messages = _FakeTelegramMessagesTable()
        self.channels = _FakeTelegramChannelsTable()

    def table(self, name: str):
        if name == "telegram_messages":
            return self.messages
        if name == "telegram_channels":
            return self.channels
        raise AssertionError(f"Unexpected table requested: {name}")


def test_upsert_telegram_message_uses_compound_conflict(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(queries, "get_service_client", lambda: fake_client)

    out = queries.upsert_telegram_message(
        {
            "brand_id": "brand-1",
            "channel_id": "  chan-1  ",
            "message_id": "  msg-1  ",
            "message_text": "hello",
        }
    )

    assert fake_client.messages.last_on_conflict == "brand_id,channel_username,message_id"
    assert out["channel_id"] == "chan-1"
    assert out["message_id"] == "msg-1"


def test_upsert_telegram_channel_updates_existing_row(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(queries, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(
        queries,
        "get_telegram_channel",
        lambda brand_id, channel_id: {"id": "row-1", "brand_id": brand_id, "channel_id": channel_id},
    )

    out = queries.upsert_telegram_channel(
        {
            "brand_id": "brand-1",
            "channel_id": "chan-1",
            "classification_label": "likely_official",
            "should_monitor": True,
        }
    )

    assert not fake_client.channels.inserted
    assert len(fake_client.channels.updated) == 1
    row_id, payload = fake_client.channels.updated[0]
    assert row_id == "row-1"
    assert payload["classification_label"] == "likely_official"
    assert payload["should_monitor"] is True
    assert out["id"] == "row-1"


def test_upsert_telegram_channels_batch_calls_single_upsert(monkeypatch):
    calls: list[str] = []

    def _fake_upsert(row: dict) -> dict:
        calls.append(str(row.get("channel_id")))
        return {"channel_id": row.get("channel_id")}

    monkeypatch.setattr(queries, "upsert_telegram_channel", _fake_upsert)

    out = queries.upsert_telegram_channels_batch(
        [
            {"channel_id": "chan-1"},
            {"channel_id": "chan-2"},
        ]
    )

    assert calls == ["chan-1", "chan-2"]
    assert out == [{"channel_id": "chan-1"}, {"channel_id": "chan-2"}]


class _FakeTelegramChannelsListTable:
    def __init__(self, rows: list[dict]):
        self._rows = deepcopy(rows)
        self._filters_eq: list[tuple[str, str]] = []
        self._filters_gte: list[tuple[str, str]] = []
        self._limit = None

    def select(self, _cols: str):
        return self

    def order(self, _field: str, desc: bool = False):
        return self

    def limit(self, value: int):
        self._limit = value
        return self

    def eq(self, field: str, value: str):
        self._filters_eq.append((field, str(value)))
        return self

    def gte(self, field: str, value: str):
        self._filters_gte.append((field, str(value)))
        return self

    def execute(self):
        rows = deepcopy(self._rows)
        for field, value in self._filters_eq:
            rows = [row for row in rows if str(row.get(field) or "") == value]
        for field, value in self._filters_gte:
            rows = [row for row in rows if str(row.get(field) or "") >= value]
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Resp(rows)


class _FakeListClient:
    def __init__(self, rows: list[dict]):
        self.channels = _FakeTelegramChannelsListTable(rows)

    def table(self, name: str):
        if name != "telegram_channels":
            raise AssertionError(f"Unexpected table requested: {name}")
        return self.channels


def test_list_telegram_channels_for_fulfilment_filters_only_unclassified_and_targets(monkeypatch):
    rows = [
        {
            "id": "row-1",
            "brand_id": "brand-1",
            "channel_id": "1001",
            "channel_username": "pw_one",
            "classification_label": None,
            "llm_classification_response": None,
            "should_monitor": None,
            "is_fake": None,
        },
        {
            "id": "row-2",
            "brand_id": "brand-1",
            "channel_id": "1002",
            "channel_username": "pw_two",
            "classification_label": "fan_unofficial",
            "llm_classification_response": {"status": "completed"},
            "should_monitor": True,
            "is_fake": False,
        },
        {
            "id": "row-3",
            "brand_id": "brand-1",
            "channel_id": "1003",
            "channel_username": "pw_three",
            "classification_label": "official",
            "llm_classification_response": {"status": "completed"},
            "should_monitor": False,
            "is_fake": False,
            "fake_score_10": None,
        },
    ]

    monkeypatch.setattr(queries, "get_service_client", lambda: _FakeListClient(rows))

    out = queries.list_telegram_channels_for_fulfilment(
        brand_id="brand-1",
        only_unclassified=True,
        limit=10,
        target_channel_ids=["1001", "1003"],
        target_channel_usernames=[],
    )

    assert [row["id"] for row in out] == ["row-1", "row-3"]


def test_list_telegram_channels_for_message_fetch_filters_monitored_and_targets(monkeypatch):
    rows = [
        {
            "id": "row-1",
            "brand_id": "brand-1",
            "channel_id": "1001",
            "channel_username": "pw_one",
            "should_monitor": True,
        },
        {
            "id": "row-2",
            "brand_id": "brand-1",
            "channel_id": "1002",
            "channel_username": "pw_two",
            "should_monitor": True,
        },
        {
            "id": "row-3",
            "brand_id": "brand-1",
            "channel_id": "1003",
            "channel_username": "pw_three",
            "should_monitor": False,
        },
    ]

    monkeypatch.setattr(queries, "get_service_client", lambda: _FakeListClient(rows))

    out = queries.list_telegram_channels_for_message_fetch(
        brand_id="brand-1",
        limit=10,
        target_channel_ids=["1001"],
        target_channel_usernames=["@pw_two"],
    )

    assert [row["id"] for row in out] == ["row-1", "row-2"]
