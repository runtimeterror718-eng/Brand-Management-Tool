from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from scrapers import telegram as tg


class _FakeMessage:
    def __init__(self, message_id: int, date: datetime):
        self.id = message_id
        self.date = date
        self.message = f"message {message_id}"
        self.text = self.message
        self.media = None
        self.sender = None
        self.sender_id = None
        self.views = 0
        self.forwards = 0
        self.reply_to = None
        self.reactions = None
        self.web_preview = None
        self.pinned = False
        self.voice = None
        self.video = None
        self.photo = None
        self.document = None
        self.sticker = None
        self.poll = None

    def to_dict(self):
        return {"id": self.id, "message": self.message}


class _FakeClient:
    def __init__(self, messages: list[_FakeMessage]):
        self._messages = messages

    async def download_media(self, _message, file=None):
        if file is bytes:
            return b"\x01\x02"
        return None

    async def iter_messages(self, _entity, limit=None):
        count = 0
        for message in self._messages:
            if limit is not None and count >= limit:
                break
            count += 1
            yield message


def test_channel_message_fetch_window_switches_historical_to_daily(monkeypatch) -> None:
    now = datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(tg, "_now_utc", lambda: now)

    historical = tg._channel_message_fetch_window(
        channel_row={"historical_data": False},
        historical_months=6,
        daily_lookback_days=1,
    )
    daily = tg._channel_message_fetch_window(
        channel_row={"historical_data": True},
        historical_months=6,
        daily_lookback_days=1,
    )

    assert historical["mode"] == "historical_6m"
    assert historical["since"] == now - timedelta(days=182)
    assert daily["mode"] == "daily_incremental"
    assert daily["since"] == now - timedelta(days=1)


def test_extract_message_media_payload_encodes_base64() -> None:
    scraper = tg.TelegramScraper()
    client = _FakeClient(messages=[])

    class _Attr:
        file_name = "lecture.jpg"

    class _Document:
        mime_type = "image/jpeg"
        attributes = [_Attr()]

    class _MediaMessage(_FakeMessage):
        def __init__(self):
            super().__init__(message_id=1, date=datetime.now(timezone.utc))
            self.media = object()
            self.document = _Document()

    payload = asyncio.run(
        scraper._extract_message_media_payload(
            client=client,
            message=_MediaMessage(),
            max_media_bytes=64,
        )
    )

    assert payload["media_base64"] == "AQI="
    assert payload["media_mime_type"] == "image/jpeg"
    assert payload["media_file_name"] == "lecture.jpg"
    assert payload["media_file_size_bytes"] == 2
    assert payload["media_metadata_patch"]["media_download_status"] == "ok"


def test_safe_tl_object_dict_serializes_nested_datetimes() -> None:
    class _Obj:
        def to_dict(self):
            return {
                "outer_ts": datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc),
                "nested": {
                    "inner_ts": datetime(2026, 4, 2, 10, 30, tzinfo=timezone.utc),
                },
            }

    out = tg._safe_tl_object_dict(_Obj())
    assert out["outer_ts"] == "2026-04-02T10:00:00+00:00"
    assert out["nested"]["inner_ts"] == "2026-04-02T10:30:00+00:00"


def test_extract_message_media_payload_skips_large_known_size_before_download() -> None:
    scraper = tg.TelegramScraper()

    class _Client:
        async def download_media(self, *_args, **_kwargs):
            raise AssertionError("download_media should not be called for oversized media")

    class _Attr:
        file_name = "huge.bin"

    class _Document:
        mime_type = "application/octet-stream"
        size = 50_000_000
        attributes = [_Attr()]

    class _MediaMessage(_FakeMessage):
        def __init__(self):
            super().__init__(message_id=2, date=datetime.now(timezone.utc))
            self.media = object()
            self.document = _Document()
            self.file = type("FileMeta", (), {"size": 50_000_000})()

    payload = asyncio.run(
        scraper._extract_message_media_payload(
            client=_Client(),
            message=_MediaMessage(),
            max_media_bytes=1024,
        )
    )

    assert payload["media_file_size_bytes"] == 50_000_000
    assert payload["media_metadata_patch"]["media_download_status"] == "skipped_size_limit"
    assert payload["media_metadata_patch"]["max_media_bytes"] == 1024


def test_extract_message_media_payload_skips_when_disabled() -> None:
    scraper = tg.TelegramScraper()

    class _Client:
        async def download_media(self, *_args, **_kwargs):
            raise AssertionError("download_media should not run when disabled")

    class _MediaMessage(_FakeMessage):
        def __init__(self):
            super().__init__(message_id=3, date=datetime.now(timezone.utc))
            self.media = object()

    payload = asyncio.run(
        scraper._extract_message_media_payload(
            client=_Client(),
            message=_MediaMessage(),
            max_media_bytes=0,
        )
    )
    assert payload["media_metadata_patch"]["media_download_status"] == "skipped_disabled"


def test_fetch_messages_for_channel_window_batches_by_ten_and_sleeps(monkeypatch) -> None:
    now = datetime(2026, 4, 2, 12, 0, tzinfo=timezone.utc)
    channel_row = {
        "id": "row-1",
        "channel_id": "100100",
        "channel_username": "pw_official",
        "channel_title": "Physics Wallah Official",
        "discovery_keyword": "physics wallah",
        "discovery_source": "keyword_search",
    }
    messages = [_FakeMessage(idx + 1, now - timedelta(minutes=idx)) for idx in range(11)]
    scraper = tg.TelegramScraper()
    client = _FakeClient(messages=messages)

    async def _fake_resolve(_row):
        return type("Entity", (), {"username": "pw_official"})()

    async def _fake_get_client():
        return client

    upsert_sizes: list[int] = []
    sleep_calls: list[int] = []
    cursor_updates: list[dict] = []

    def _fake_upsert_batch(rows: list[dict]):
        upsert_sizes.append(len(rows))
        return rows

    def _fake_update(_row_id: str, updates: dict):
        cursor_updates.append(dict(updates))
        return updates

    async def _fake_sleep(seconds: int):
        sleep_calls.append(int(seconds))

    monkeypatch.setattr(scraper, "_resolve_channel_entity", _fake_resolve)
    monkeypatch.setattr(scraper, "_get_client", _fake_get_client)
    monkeypatch.setattr(tg.db, "upsert_telegram_messages_batch", _fake_upsert_batch)
    monkeypatch.setattr(tg.db, "update_telegram_channel", _fake_update)
    monkeypatch.setattr(tg.random, "randint", lambda _a, _b: 2)
    monkeypatch.setattr(tg.asyncio, "sleep", _fake_sleep)

    result = asyncio.run(
        scraper.fetch_messages_for_channel_window(
            channel_row=channel_row,
            brand_id="brand-1",
            since=now - timedelta(days=1),
            batch_size=10,
            batch_sleep_min_seconds=1,
            batch_sleep_max_seconds=3,
            max_media_bytes=256,
        )
    )

    assert result["status"] == "completed"
    assert result["messages_upserted"] == 11
    assert result["batches_processed"] == 2
    assert upsert_sizes == [10, 1]
    assert sleep_calls == [2]
    assert cursor_updates[-1]["last_message_id"] == "11"


def test_run_message_fetch_pipeline_for_brand_sets_historical_flag_and_summary(monkeypatch) -> None:
    scraper = tg.TelegramScraper()
    channels = [
        {"id": "row-a", "channel_id": "1001", "channel_username": "alpha", "historical_data": False},
        {"id": "row-b", "channel_id": "1002", "channel_username": "beta", "historical_data": False},
        {"id": "row-c", "channel_id": "1003", "channel_username": "gamma", "historical_data": True},
    ]

    fetch_calls: list[tuple[str, int]] = []
    channel_updates: list[tuple[str, dict]] = []
    sleep_calls: list[int] = []

    async def _fake_fetch(
        self,
        channel_row,
        brand_id,
        since,
        batch_size,
        batch_sleep_min_seconds,
        batch_sleep_max_seconds,
        max_media_bytes,
    ):
        fetch_calls.append((str(channel_row.get("id")), int(max_media_bytes)))
        return {
            "status": "completed",
            "channel_id": channel_row.get("channel_id"),
            "channel_username": channel_row.get("channel_username"),
            "messages_scanned": 12,
            "messages_upserted": 4,
            "batches_processed": 1,
            "window_since": tg._to_iso(since),
            "batch_size": batch_size,
        }

    def _fake_update(row_id: str, updates: dict):
        channel_updates.append((row_id, dict(updates)))
        return {"id": row_id, **updates}

    async def _fake_sleep(seconds: int):
        sleep_calls.append(int(seconds))

    monkeypatch.setattr(tg.db, "list_telegram_channels_for_message_fetch", lambda **_kwargs: list(channels))
    monkeypatch.setattr(tg.TelegramScraper, "fetch_messages_for_channel_window", _fake_fetch)
    monkeypatch.setattr(tg.db, "update_telegram_channel", _fake_update)
    monkeypatch.setattr(tg.asyncio, "sleep", _fake_sleep)

    summary = asyncio.run(
        scraper.run_message_fetch_pipeline_for_brand(
            brand={"id": "brand-1", "name": "PW"},
            limit_channels=10,
            batch_size=10,
            historical_months=6,
            daily_lookback_days=1,
            between_channels_sleep_seconds=5,
            max_media_bytes=4096,
        )
    )

    assert fetch_calls == [("row-a", 0), ("row-b", 0), ("row-c", 4096)]
    assert summary["channels_considered"] == 3
    assert summary["historical_channels"] == 2
    assert summary["daily_channels"] == 1
    assert summary["channels_completed"] == 3
    assert summary["messages_upserted"] == 12
    assert sleep_calls == [5]
    assert [row_id for row_id, _ in channel_updates] == ["row-a", "row-b"]
    assert all(updates.get("historical_data") is True for _, updates in channel_updates)
