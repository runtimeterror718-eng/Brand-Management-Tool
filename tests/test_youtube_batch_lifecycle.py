from __future__ import annotations

from copy import deepcopy

from scrapers import youtube as yt


def _video_row(custom_id: str = "title_triage:vid-1") -> dict:
    return {
        "video_id": "vid-1",
        "channel_id": "chan-1",
        "video_title": "PW refund issue",
        "video_description": "complaint",
        "video_date": "2026-03-30T08:00:00Z",
        "video_views": 120,
        "video_likes": 6,
        "video_comment_count": 3,
        "source_url": "https://www.youtube.com/watch?v=vid-1",
        "title_triage_custom_id": custom_id,
        "analysis_artifacts": {
            "title_triage": {
                "custom_id": custom_id,
                "provider_batch_id": "batch-1",
                "status": "completed",
            }
        },
        "raw_data": {
            "video": {
                "id": "vid-1",
                "snippet": {
                    "title": "PW refund issue",
                    "description": "complaint",
                    "publishedAt": "2026-03-30T08:00:00Z",
                    "channelTitle": "Independent",
                },
                "statistics": {
                    "viewCount": "120",
                    "likeCount": "6",
                    "commentCount": "3",
                },
                "contentDetails": {"duration": "PT4M10S"},
            },
            "channel": {
                "id": "chan-1",
                "snippet": {"title": "Independent", "customUrl": "@indiepw"},
            },
            "search_hits": [{"query": "physics wallah", "bucket": "primary"}],
        },
    }


def test_deterministic_custom_id_generation() -> None:
    analyzer = yt.AzureYouTubeAnalyzer()
    one = analyzer.custom_id("title_triage", "brand-1", "vid-1")
    two = analyzer.custom_id("title_triage", "brand-1", "vid-1")
    three = analyzer.custom_id("title_triage", "brand-1", "vid-2")

    assert one == two
    assert one != three
    assert one.startswith("title_triage:")
    assert one.endswith("video:vid-1")


def test_batch_result_and_error_parsing(tmp_path) -> None:
    analyzer = yt.AzureYouTubeAnalyzer()
    output_path = tmp_path / "out.jsonl"
    error_path = tmp_path / "err.jsonl"

    output_path.write_text(
        "\n".join(
            [
                '{"custom_id":"cid-1","response":{"status_code":200,"request_id":"req-1","body":{"id":"resp-1","choices":[{"message":{"content":"{\\"label\\":\\"negative\\",\\"confidence\\":0.9,\\"is_pr_risk\\":true,\\"issue_type\\":\\"refund\\",\\"reason\\":\\"complaint\\"}"}}]}}}',
                '{"custom_id":"cid-2","response":{"status_code":200,"request_id":"req-2","body":{"id":"resp-2","choices":[{"message":{"content":"{\\"label\\":\\"positive\\",\\"confidence\\":0.8,\\"is_pr_risk\\":false,\\"issue_type\\":\\"general\\",\\"reason\\":\\"ok\\"}"}}]}}}',
            ]
        ),
        encoding="utf-8",
    )
    error_path.write_text(
        '{"custom_id":"cid-3","error":{"message":"rate_limit","code":"429"}}\n',
        encoding="utf-8",
    )

    parsed, parsed_meta = analyzer.parse_batch_output_records(output_path)
    errors = analyzer.parse_batch_error_records(error_path)

    assert parsed["cid-1"]["label"] == "negative"
    assert parsed["cid-2"]["label"] == "positive"
    assert parsed_meta["cid-1"]["correlation_id"] == "req-1"
    assert errors["cid-3"]["message"] == "rate_limit"


def test_ingest_maps_batch_outputs_to_video_rows(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    custom_id = "title_triage:vid-1"
    state = {"vid-1": _video_row(custom_id=custom_id)}
    video_updates: list[tuple[str, dict]] = []
    fulfillment_updates: list[dict] = []

    class _FakeAnalyzer:
        def fetch_batch_outputs(self, batch_meta: dict):
            return {
                "results_by_custom_id": {
                    custom_id: {
                        "label": "negative",
                        "confidence": 0.91,
                        "is_pr_risk": True,
                        "issue_type": "refund",
                        "reason": "complaint",
                    }
                },
                "result_meta_by_custom_id": {
                    custom_id: {"correlation_id": "req-result-1", "status_code": 200}
                },
                "errors_by_custom_id": {},
                "batch_output_path": "/tmp/file-out.jsonl",
                "batch_error_path": None,
            }

    monkeypatch.setattr(yt, "AzureYouTubeAnalyzer", _FakeAnalyzer)
    monkeypatch.setattr(yt.db, "get_youtube_videos_for_brand", lambda brand_id, limit=1000: list(state.values()))
    monkeypatch.setattr(yt.db, "get_youtube_video_by_video_id", lambda video_id: deepcopy(state.get(video_id)))

    def _update_video(video_id: str, updates: dict):
        row = state.setdefault(video_id, {"video_id": video_id})
        row.update(deepcopy(updates))
        video_updates.append((video_id, updates))
        return row

    monkeypatch.setattr(yt.db, "update_youtube_video_by_video_id", _update_video)
    monkeypatch.setattr(yt.db, "merge_youtube_video_analysis_artifacts", lambda video_id, patch: _update_video(video_id, {"analysis_artifacts": yt._deep_merge_dicts(state[video_id].get("analysis_artifacts", {}), patch)}))

    monkeypatch.setattr(yt.db, "get_mention_by_platform_ref", lambda brand_id, platform, platform_ref_id: {"id": "mention-1", "raw_data": {}})
    monkeypatch.setattr(yt.db, "upsert_mention_by_platform_ref", lambda payload: {"id": "mention-1", "raw_data": payload.get("raw_data", {})})
    monkeypatch.setattr(yt.db, "get_latest_fulfillment_result_for_mention", lambda mention_id: None)
    monkeypatch.setattr(yt.db, "upsert_fulfillment_result_for_mention", lambda row: fulfillment_updates.append(row) or row)

    summary = yt.ingest_youtube_title_triage_results_for_brand(
        brand=brand,
        batch_meta={
            "provider_batch_id": "batch-1",
            "status": "completed",
            "output_file_id": "out-1",
            "error_file_id": None,
            "mode": "batch",
        },
        target_custom_ids=[custom_id],
    )

    assert summary["videos_updated_with_triage_results"] == 1
    assert summary["flagged_video_ids"] == ["vid-1"]
    assert any(update[1].get("title_triage_label") == "negative" for update in video_updates)
    assert state["vid-1"]["analysis_artifacts"]["title_triage"]["correlation_id"] == "req-result-1"
    assert fulfillment_updates


def test_sync_title_triage_ingestion_processes_chunks_of_10(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW", "keywords": ["physics wallah"]}

    def _candidate(ix: int) -> dict:
        video_id = f"vid-{ix}"
        return {
            "video_id": video_id,
            "channel_id": f"chan-{ix}",
            "source_url": f"https://www.youtube.com/watch?v={video_id}",
            "search_hits": [{"query": "physics wallah", "bucket": "primary"}],
            "video": {
                "id": video_id,
                "snippet": {
                    "title": f"title {ix}",
                    "description": "desc",
                    "publishedAt": "2026-03-30T08:00:00Z",
                    "channelTitle": "Independent",
                },
                "statistics": {"viewCount": "10", "likeCount": "1", "commentCount": "0"},
                "contentDetails": {"duration": "PT1M"},
            },
            "channel": {
                "id": f"chan-{ix}",
                "snippet": {"title": "Independent", "customUrl": f"@indie{ix}"},
                "statistics": {"subscriberCount": "100"},
            },
        }

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            pass

    class _FakeAnalyzer:
        call_count = 0

        def custom_id(self, stage: str, brand_id: str, video_id: str) -> str:
            return f"{stage}:{video_id}"

        def direct_call_with_meta(self, stage: str, payload: dict):
            _FakeAnalyzer.call_count += 1
            return (
                {
                    "label": "negative",
                    "confidence": 0.8,
                    "is_pr_risk": True,
                    "issue_type": "refund",
                    "reason": "complaint",
                },
                {"status": "completed", "mode": "direct", "correlation_id": f"req-{_FakeAnalyzer.call_count}"},
            )

    monkeypatch.setattr(yt, "YOUTUBE_API_KEY", "dummy")
    monkeypatch.setattr(yt, "YouTubeDataAPIClient", _FakeClient)
    monkeypatch.setattr(yt, "AzureYouTubeAnalyzer", _FakeAnalyzer)

    async def _fake_discover(client, query_buckets, max_results_per_keyword, published_after_days, query_chunk_size):
        return [_candidate(i) for i in range(12)]

    monkeypatch.setattr(yt, "discover_unofficial_video_candidates", _fake_discover)

    monkeypatch.setattr(yt.db, "find_youtube_channel", lambda channel_id, brand_id=None: None)
    monkeypatch.setattr(yt.db, "upsert_youtube_channel", lambda row: row)
    monkeypatch.setattr(yt.db, "get_youtube_video_by_video_id", lambda video_id: None)
    monkeypatch.setattr(yt.db, "upsert_youtube_video", lambda row: row)
    monkeypatch.setattr(yt.db, "update_youtube_video_by_video_id", lambda video_id, updates: {"video_id": video_id, **updates})
    monkeypatch.setattr(yt.db, "merge_youtube_video_analysis_artifacts", lambda video_id, patch: {"video_id": video_id, "analysis_artifacts": patch})
    monkeypatch.setattr(yt.db, "get_mention_by_platform_ref", lambda brand_id, platform, platform_ref_id: None)
    monkeypatch.setattr(yt.db, "upsert_mention_by_platform_ref", lambda payload: {"id": f"mention-{payload.get('platform_ref_id')}", "raw_data": payload.get("raw_data", {})})
    monkeypatch.setattr(yt.db, "get_latest_fulfillment_result_for_mention", lambda mention_id: None)
    monkeypatch.setattr(yt.db, "upsert_fulfillment_result_for_mention", lambda row: row)

    import asyncio

    summary = asyncio.run(
        yt.run_youtube_title_triage_sync_ingestion_for_brand(
            brand=brand,
            include_secondary=False,
            query_buckets_override={"primary": ["physics wallah"]},
            max_results_per_keyword_override=2,
            published_after_days_override=7,
            triage_batch_size=10,
        )
    )

    assert summary["status"] == "ok"
    assert summary["discovered"] == 12
    assert summary["titles_triaged"] == 12
    assert summary["triage_batch_size"] == 10
    assert summary["triage_chunks_processed"] == 2
    assert summary["enrichment_triggered"] is False
    assert _FakeAnalyzer.call_count == 12
