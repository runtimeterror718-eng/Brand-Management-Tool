from __future__ import annotations

from copy import deepcopy

from storage import queries


class _Resp:
    def __init__(self, data):
        self.data = data


class _FakeVideosTable:
    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.last_on_conflict = None

    def upsert(self, row: dict, on_conflict: str | None = None):
        self.last_on_conflict = on_conflict
        existing = self.rows.get(row["video_id"], {})
        merged = {**existing, **row}
        self.rows[row["video_id"]] = merged
        return _Exec(_Resp([merged]))


class _Exec:
    def __init__(self, response: _Resp):
        self._response = response

    def execute(self):
        return self._response


class _FakeClient:
    def __init__(self):
        self.videos = _FakeVideosTable()

    def table(self, name: str):
        if name != "youtube_videos":
            raise AssertionError(f"Unexpected table requested: {name}")
        return self.videos


def test_upsert_youtube_video_is_idempotent(monkeypatch):
    fake_client = _FakeClient()
    monkeypatch.setattr(queries, "get_service_client", lambda: fake_client)

    row1 = {
        "video_id": "abc123",
        "video_title": "first",
        "video_views": 10,
    }
    row2 = {
        "video_id": "abc123",
        "video_title": "updated",
        "video_views": 20,
    }

    out1 = queries.upsert_youtube_video(row1)
    out2 = queries.upsert_youtube_video(row2)

    assert fake_client.videos.last_on_conflict == "video_id"
    assert len(fake_client.videos.rows) == 1
    assert fake_client.videos.rows["abc123"]["video_title"] == "updated"
    assert out1["video_id"] == "abc123"
    assert out2["video_views"] == 20


def test_merge_analysis_artifacts_keeps_existing_keys(monkeypatch):
    existing = {
        "video_id": "abc123",
        "analysis_artifacts": {
            "title_triage": {
                "custom_id": "cid-1",
                "status": "submitted",
            },
            "legacy_stage": {"ok": True},
        },
    }
    writes: dict[str, dict] = {}

    monkeypatch.setattr(queries, "get_youtube_video_by_video_id", lambda video_id: existing)
    monkeypatch.setattr(
        queries,
        "update_youtube_video_by_video_id",
        lambda video_id, updates: writes.setdefault(video_id, updates),
    )

    queries.merge_youtube_video_analysis_artifacts(
        "abc123",
        {
            "title_triage": {
                "status": "completed",
                "output_file_id": "out-1",
            },
            "new_stage": {"value": 1},
        },
    )

    merged = writes["abc123"]["analysis_artifacts"]
    assert merged["title_triage"]["custom_id"] == "cid-1"
    assert merged["title_triage"]["status"] == "completed"
    assert merged["title_triage"]["output_file_id"] == "out-1"
    assert merged["legacy_stage"]["ok"] is True
    assert merged["new_stage"]["value"] == 1


class _FakeCommentsTable:
    def __init__(self, rows: list[dict]):
        self.rows = deepcopy(rows)
        self.inserted: list[dict] = []
        self.updates: list[tuple[str, dict]] = []
        self._pending_update: dict | None = None

    def insert(self, rows: list[dict]):
        self.inserted.extend(deepcopy(rows))
        return _Exec(_Resp(rows))

    def update(self, payload: dict):
        self._pending_update = deepcopy(payload)
        return self

    def eq(self, field: str, value: str):
        if field != "id":
            raise AssertionError(f"Unexpected eq field for comments update: {field}")
        pending = deepcopy(self._pending_update or {})
        self.updates.append((value, pending))
        updated = []
        for row in self.rows:
            if str(row.get("id")) == str(value):
                row.update(pending)
                updated.append(deepcopy(row))
        return _Exec(_Resp(updated))


class _FakeCommentsClient:
    def __init__(self, rows: list[dict]):
        self.comments = _FakeCommentsTable(rows)

    def table(self, name: str):
        if name != "youtube_comments":
            raise AssertionError(f"Unexpected table requested: {name}")
        return self.comments


def test_insert_youtube_comments_batch_hydrates_missing_comment_id(monkeypatch):
    existing = [
        {
            "id": "row-1",
            "video_id": "vid-1",
            "comment_id": None,
            "comment_author": "Alice",
            "comment_text": "same text",
            "comment_date": "2026-03-31T10:00:00+00:00",
        }
    ]
    incoming = [
        {
            "video_id": "vid-1",
            "comment_id": "c-123",
            "parent_comment_id": None,
            "thread_comment_id": "c-123",
            "is_reply": False,
            "comment_author": "alice",
            "comment_text": "same text",
            "comment_replies": 0,
            "comment_likes": 2,
            "comment_date": "2026-03-31T10:00:00+00:00",
            "scraped_at": "2026-04-01T12:00:00+00:00",
            "raw_payload": {"x": 1},
        }
    ]
    fake_client = _FakeCommentsClient(existing)

    monkeypatch.setattr(queries, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(queries, "get_youtube_comments", lambda video_id, limit=5000: deepcopy(existing))

    out = queries.insert_youtube_comments_batch(incoming)

    assert out == []
    assert fake_client.comments.inserted == []
    assert len(fake_client.comments.updates) == 1
    updated_row = fake_client.comments.rows[0]
    assert updated_row["comment_id"] == "c-123"
    assert updated_row["thread_comment_id"] == "c-123"
    assert updated_row["comment_likes"] == 2


def test_insert_youtube_comments_batch_does_not_overwrite_existing_comment_id(monkeypatch):
    existing = [
        {
            "id": "row-1",
            "video_id": "vid-1",
            "comment_id": "c-123",
            "comment_author": "Alice",
            "comment_text": "same text",
            "comment_date": "2026-03-31T10:00:00+00:00",
        }
    ]
    incoming = [
        {
            "video_id": "vid-1",
            "comment_id": "c-123",
            "comment_author": "alice",
            "comment_text": "same text",
            "comment_date": "2026-03-31T10:00:00+00:00",
        }
    ]
    fake_client = _FakeCommentsClient(existing)

    monkeypatch.setattr(queries, "get_service_client", lambda: fake_client)
    monkeypatch.setattr(queries, "get_youtube_comments", lambda video_id, limit=5000: deepcopy(existing))

    out = queries.insert_youtube_comments_batch(incoming)

    assert out == []
    assert fake_client.comments.inserted == []
    assert fake_client.comments.updates == []
