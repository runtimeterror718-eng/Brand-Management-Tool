from __future__ import annotations

from scrapers import youtube as yt


class _FakeCommentClient(yt.YouTubeDataAPIClient):
    def __init__(self):
        super().__init__(api_key="dummy")
        self.calls: list[tuple[str, dict]] = []

    def _get_sync(self, endpoint: str, params: dict):
        self.calls.append((endpoint, params))
        if endpoint == "/commentThreads":
            return {
                "items": [
                    {
                        "snippet": {
                            "totalReplyCount": 2,
                            "topLevelComment": {
                                "id": "c1",
                                "snippet": {
                                    "authorDisplayName": "top",
                                    "textDisplay": "top text",
                                    "likeCount": 4,
                                    "publishedAt": "2026-03-30T10:00:00Z",
                                },
                            },
                        },
                        "replies": {
                            "comments": [
                                {
                                    "id": "r1",
                                    "snippet": {
                                        "authorDisplayName": "r1",
                                        "textDisplay": "reply one",
                                        "likeCount": 1,
                                        "publishedAt": "2026-03-30T10:10:00Z",
                                    },
                                }
                            ]
                        },
                    }
                ]
            }
        if endpoint == "/comments":
            return {
                "items": [
                    {
                        "id": "r2",
                        "snippet": {
                            "authorDisplayName": "r2",
                            "textDisplay": "reply two",
                            "likeCount": 0,
                            "publishedAt": "2026-03-30T10:20:00Z",
                        },
                    }
                ]
            }
        raise AssertionError(f"Unexpected endpoint {endpoint}")


def test_fetch_comments_with_replies_sync_includes_replies() -> None:
    client = _FakeCommentClient()

    rows = client.fetch_comments_with_replies_sync("vid-1", max_results=10)

    ids = [row.get("comment_id") for row in rows]
    assert ids == ["c1", "r1", "r2"]
    assert rows[0]["is_reply"] is False
    assert rows[1]["is_reply"] is True
    assert rows[1]["parent_comment_id"] == "c1"
    assert rows[2]["thread_comment_id"] == "c1"


def test_layer2_sync_fetch_writes_transcript_and_comments(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    candidate = {
        "video_id": "vid-1",
        "source_url": "https://www.youtube.com/watch?v=vid-1",
        "mention": {"id": "mention-1"},
        "queued_for_transcription": True,
        "queued_for_scraping": True,
    }

    transcript_writes: list[dict] = []
    comment_writes: list[list[dict]] = []
    artifact_writes: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        yt,
        "_collect_layer2_candidates_for_brand",
        lambda brand_id, scan_limit=2000, include_completed=False: [candidate],
    )
    monkeypatch.setattr(
        yt,
        "get_apify_transcripts_batch",
        lambda urls: (
            {
                "vid-1": {
                    "text": "apify transcript",
                    "language": "en",
                    "segments": [],
                    "duration": 12,
                    "source_metadata": {"provider": "apify_actor"},
                }
            },
            {"status": "ok", "requested_urls": 1},
        ),
    )

    class _FakeClient:
        def __init__(self, api_key: str):
            self.api_key = api_key

        def fetch_comments_with_replies_sync(self, video_id: str, max_results: int):
            return [
                {
                    "video_id": video_id,
                    "comment_id": "c1",
                    "parent_comment_id": None,
                    "thread_comment_id": "c1",
                    "is_reply": False,
                    "comment_author": "u",
                    "comment_text": "t",
                    "comment_replies": 1,
                    "comment_likes": 0,
                    "comment_date": "2026-03-30T10:00:00+00:00",
                    "scraped_at": "2026-03-30T10:00:00+00:00",
                    "raw_payload": {},
                }
            ]

    monkeypatch.setattr(yt, "YOUTUBE_API_KEY", "dummy")
    monkeypatch.setattr(yt, "YouTubeDataAPIClient", _FakeClient)
    monkeypatch.setattr(
        yt.db,
        "upsert_youtube_video_transcript",
        lambda video_id, row: transcript_writes.append({"video_id": video_id, **row}) or row,
    )
    monkeypatch.setattr(yt.db, "insert_youtube_comments_batch", lambda rows: comment_writes.append(rows) or rows)
    monkeypatch.setattr(yt.db, "merge_youtube_video_analysis_artifacts", lambda video_id, patch: artifact_writes.append((video_id, patch)) or {"video_id": video_id})

    summary = yt.run_youtube_layer2_fetch_sync_for_brand(
        brand=brand,
        page_size=50,
        page_offset=0,
        comments_max_per_video_override=20,
    )

    assert summary["status"] == "ok"
    assert summary["processed_count"] == 1
    assert summary["transcript_success"] == 1
    assert summary["comments_success"] == 1
    assert summary["comments_fetched_total"] == 1
    assert transcript_writes and transcript_writes[0]["source_type"] == "apify_youtube_actor"
    assert comment_writes and len(comment_writes[0]) == 1
    assert any(v_id == "vid-1" for v_id, _ in artifact_writes)


def test_collect_layer2_candidates_skips_completed_by_default(monkeypatch) -> None:
    row = {
        "video_id": "vid-1",
        "source_url": "https://www.youtube.com/watch?v=vid-1",
        "analysis_artifacts": {"layers": {"layer_2": {"status": "completed"}}},
    }
    monkeypatch.setattr(yt, "_get_brand_video_rows", lambda brand_id, limit=800: [row])
    monkeypatch.setattr(yt.db, "get_mention_by_platform_ref", lambda brand_id, platform, ref: {"id": "mention-1"})
    monkeypatch.setattr(
        yt.db,
        "get_latest_fulfillment_result_for_mention",
        lambda mention_id: {"queued_for_scraping": True, "queued_for_transcription": True},
    )

    skipped = yt._collect_layer2_candidates_for_brand("brand-1", include_completed=False)
    included = yt._collect_layer2_candidates_for_brand("brand-1", include_completed=True)

    assert skipped == []
    assert len(included) == 1
    assert included[0]["video_id"] == "vid-1"


def test_layer2_sync_fetch_uses_fallback_transcript_when_apify_empty(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    candidate = {
        "video_id": "vid-1",
        "source_url": "https://www.youtube.com/watch?v=vid-1",
        "mention": {"id": "mention-1"},
        "queued_for_transcription": True,
        "queued_for_scraping": False,
    }
    transcript_writes: list[dict] = []

    monkeypatch.setattr(yt, "_collect_layer2_candidates_for_brand", lambda brand_id, scan_limit=2000, include_completed=False: [candidate])
    monkeypatch.setattr(yt, "get_apify_transcripts_batch", lambda urls: ({}, {"status": "missing_api_key"}))

    async def _fallback(video_id: str, source_url: str, **kwargs):
        return {
            "text": "fallback transcript",
            "language": "en",
            "segments": [],
            "duration": 20,
            "source_type": "youtube_captions",
            "source_metadata": {"provider": "youtube_transcript_api_captions"},
            "attempt_order": ["youtube_captions", "external_provider", "whisper_fallback"],
        }

    monkeypatch.setattr(yt, "get_transcript_with_fallback", _fallback)
    monkeypatch.setattr(
        yt.db,
        "upsert_youtube_video_transcript",
        lambda video_id, row: transcript_writes.append({"video_id": video_id, **row}) or row,
    )
    monkeypatch.setattr(yt.db, "merge_youtube_video_analysis_artifacts", lambda video_id, patch: {"video_id": video_id, "analysis_artifacts": patch})

    summary = yt.run_youtube_layer2_fetch_sync_for_brand(
        brand=brand,
        page_size=50,
        page_offset=0,
        use_fallback_transcript=True,
    )

    assert summary["status"] == "ok"
    assert summary["transcript_success"] == 1
    assert summary["transcript_failed"] == 0
    assert transcript_writes
    assert transcript_writes[0]["source_type"] == "youtube_captions"


def test_layer2_sync_fetch_skips_apify_when_transcript_exists(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    candidate = {
        "video_id": "vid-1",
        "source_url": "https://www.youtube.com/watch?v=vid-1",
        "mention": {"id": "mention-1"},
        "queued_for_transcription": True,
        "queued_for_scraping": False,
        "has_transcript_text": True,
        "existing_transcript_source_type": "apify_youtube_actor",
    }
    apify_calls: list[list[str]] = []
    transcript_writes: list[dict] = []

    monkeypatch.setattr(
        yt,
        "_collect_layer2_candidates_for_brand",
        lambda brand_id, scan_limit=2000, include_completed=False: [candidate],
    )
    monkeypatch.setattr(
        yt,
        "get_apify_transcripts_batch",
        lambda urls: apify_calls.append(list(urls)) or ({}, {"status": "noop", "requested_urls": len(urls)}),
    )
    monkeypatch.setattr(
        yt.db,
        "upsert_youtube_video_transcript",
        lambda video_id, row: transcript_writes.append({"video_id": video_id, **row}) or row,
    )
    monkeypatch.setattr(
        yt.db,
        "merge_youtube_video_analysis_artifacts",
        lambda video_id, patch: {"video_id": video_id, "analysis_artifacts": patch},
    )

    summary = yt.run_youtube_layer2_fetch_sync_for_brand(
        brand=brand,
        page_size=50,
        page_offset=0,
    )

    assert summary["status"] == "ok"
    assert summary["processed_count"] == 1
    assert summary["transcript_requested_count"] == 0
    assert summary["transcript_skipped_existing_count"] == 1
    assert summary["transcript_success"] == 1
    assert apify_calls == [[]]
    assert transcript_writes == []
