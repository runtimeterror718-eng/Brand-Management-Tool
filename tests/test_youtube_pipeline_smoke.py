from __future__ import annotations

import asyncio
from copy import deepcopy

from scrapers import youtube as yt


def _candidate() -> dict:
    return {
        "video_id": "vid-smoke-1",
        "channel_id": "chan-smoke-1",
        "source_url": "https://www.youtube.com/watch?v=vid-smoke-1",
        "search_hits": [{"query": "physics wallah", "bucket": "primary"}],
        "video": {
            "id": "vid-smoke-1",
            "snippet": {
                "title": "PW problem video",
                "description": "complaint details",
                "publishedAt": "2026-03-30T08:00:00Z",
                "channelTitle": "Independent Channel",
                "defaultLanguage": "en",
            },
            "statistics": {"viewCount": "100", "likeCount": "5", "commentCount": "2"},
            "contentDetails": {"duration": "PT4M10S"},
        },
        "channel": {
            "id": "chan-smoke-1",
            "snippet": {"title": "Independent Channel", "customUrl": "@indie_pw"},
            "statistics": {"subscriberCount": "1000"},
        },
    }


class _FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    async def fetch_comments(self, video_id: str, max_results: int):
        return [
            {
                "video_id": video_id,
                "comment_author": "u1",
                "comment_text": "bad experience",
                "comment_replies": 0,
                "comment_likes": 1,
                "comment_date": yt._to_iso(yt._now_utc()),
                "scraped_at": yt._to_iso(yt._now_utc()),
            }
        ]


class _FakeAnalyzer:
    def __init__(self):
        self.batch_enabled = True

    def custom_id(self, stage: str, brand_id: str, video_id: str) -> str:
        return f"{stage}:{video_id}"

    def submit_batch_stage(self, stage: str, brand_id: str, payloads_by_custom_id: dict):
        return (
            {},
            {
                "stage": stage,
                "mode": "batch",
                "status": "submitted",
                "provider_batch_id": "batch-1",
                "input_file_id": "file-in-1",
                "output_file_id": None,
                "error_file_id": None,
                "batch_input_path": "/tmp/in.jsonl",
                "batch_output_path": None,
                "batch_error_path": None,
                "submitted_at": yt._to_iso(yt._now_utc()),
                "correlation_id": "req-submit-1",
                "error": None,
                "results_meta_by_custom_id": {},
            },
        )

    def poll_batch_stage(self, batch_id: str):
        return {
            "provider_batch_id": batch_id,
            "status": "completed",
            "input_file_id": "file-in-1",
            "output_file_id": "file-out-1",
            "error_file_id": None,
            "submitted_at": yt._to_iso(yt._now_utc()),
            "polled_at": yt._to_iso(yt._now_utc()),
            "completed_at": yt._to_iso(yt._now_utc()),
            "correlation_id": "req-poll-1",
            "error": None,
        }

    def fetch_batch_outputs(self, batch_meta: dict):
        return {
            "results_by_custom_id": {
                "title_triage:vid-smoke-1": {
                    "label": "negative",
                    "is_pr_risk": True,
                    "confidence": 0.85,
                    "issue_type": "refund",
                    "reason": "title indicates complaint",
                }
            },
            "result_meta_by_custom_id": {
                "title_triage:vid-smoke-1": {
                    "correlation_id": "req-result-1",
                    "status_code": 200,
                    "provider_response_id": "resp-1",
                }
            },
            "errors_by_custom_id": {},
            "batch_output_path": "/tmp/out.jsonl",
            "batch_error_path": None,
        }

    def run_stage(self, stage: str, brand_id: str, payloads_by_custom_id: dict):
        custom_id = next(iter(payloads_by_custom_id.keys()))
        if stage == "transcript_analysis":
            return ({custom_id: {"sentiment": "negative", "issue_type": "refund"}}, {"mode": "direct"})
        if stage == "comment_analysis":
            return (
                {custom_id: {"sentiment": "negative", "top_negative_themes": ["refund"]}},
                {"mode": "direct"},
            )
        return (
            {
                custom_id: {
                    "title_sentiment": "negative",
                    "final_sentiment": "negative",
                    "is_pr_risk": True,
                    "severity": "high",
                    "issue_type": "refund",
                    "target_entity": "physics wallah",
                    "key_claims": ["refund not received"],
                    "top_negative_themes": ["refund"],
                    "comment_sentiment_summary": "mostly negative",
                    "transcript_summary": "complaint summary",
                    "recommended_action": "investigate",
                    "analysis_version": "test-v1",
                    "processing_status": "complete",
                }
            },
            {"mode": "direct"},
        )


def test_mocked_end_to_end_unofficial_pipeline(monkeypatch):
    brand = {"id": "brand-1", "name": "PW", "keywords": ["physics wallah"]}

    writes = {
        "channels": [],
        "videos": {},
        "video_updates": [],
        "mentions": {},
        "fulfillment": [],
        "transcriptions": [],
        "comments": [],
        "mention_updates": [],
    }

    monkeypatch.setattr(yt, "YOUTUBE_API_KEY", "dummy")
    monkeypatch.setattr(yt, "YouTubeDataAPIClient", _FakeClient)
    monkeypatch.setattr(yt, "AzureYouTubeAnalyzer", _FakeAnalyzer)

    async def fake_discover(client, query_buckets, max_results_per_keyword, published_after_days, query_chunk_size):
        return [_candidate()]

    async def fake_transcript(video_id: str, source_url: str, **kwargs):
        return {
            "text": "this is transcript",
            "language": "en",
            "segments": [],
            "duration": 20,
            "source_type": "youtube_captions",
            "attempt_order": ["youtube_captions", "external_provider", "whisper_fallback"],
            "source_metadata": {"provider": "captions"},
        }

    monkeypatch.setattr(yt, "discover_unofficial_video_candidates", fake_discover)
    monkeypatch.setattr(yt, "get_transcript_with_fallback", fake_transcript)

    monkeypatch.setattr(yt.db, "find_youtube_channel", lambda channel_id, brand_id=None: None)
    monkeypatch.setattr(yt.db, "upsert_youtube_channel", lambda row: writes["channels"].append(deepcopy(row)) or row)

    def _upsert_video(row):
        existing = writes["videos"].get(row["video_id"], {})
        merged = yt._deep_merge_dicts(existing, deepcopy(row))
        writes["videos"][row["video_id"]] = merged
        return merged

    def _update_video(video_id, updates):
        row = writes["videos"].setdefault(video_id, {"video_id": video_id, "analysis_artifacts": {}})
        row.update(deepcopy(updates))
        writes["video_updates"].append((video_id, deepcopy(updates)))
        return row

    monkeypatch.setattr(yt.db, "upsert_youtube_video", _upsert_video)
    monkeypatch.setattr(yt.db, "get_youtube_video_by_video_id", lambda video_id: deepcopy(writes["videos"].get(video_id)))
    monkeypatch.setattr(yt.db, "get_youtube_videos_for_brand", lambda brand_id, limit=800: list(deepcopy(writes["videos"]).values()))
    monkeypatch.setattr(yt.db, "update_youtube_video_by_video_id", _update_video)
    monkeypatch.setattr(
        yt.db,
        "merge_youtube_video_analysis_artifacts",
        lambda video_id, patch: _update_video(
            video_id,
            {
                "analysis_artifacts": yt._deep_merge_dicts(
                    writes["videos"].get(video_id, {}).get("analysis_artifacts", {}),
                    patch,
                )
            },
        ),
    )

    def _get_mention(brand_id, platform, platform_ref_id):
        return deepcopy(writes["mentions"].get(platform_ref_id))

    def _upsert_mention(payload):
        video_id = payload.get("platform_ref_id")
        mention = writes["mentions"].get(video_id, {"id": f"mention-{video_id}"})
        mention.update({"raw_data": deepcopy(payload.get("raw_data", {})), **deepcopy(payload)})
        writes["mentions"][video_id] = mention
        return deepcopy(mention)

    monkeypatch.setattr(yt.db, "get_mention_by_platform_ref", _get_mention)
    monkeypatch.setattr(yt.db, "upsert_mention_by_platform_ref", _upsert_mention)
    monkeypatch.setattr(yt.db, "get_latest_fulfillment_result_for_mention", lambda mention_id: None)
    monkeypatch.setattr(yt.db, "upsert_fulfillment_result_for_mention", lambda row: writes["fulfillment"].append(deepcopy(row)) or row)
    monkeypatch.setattr(
        yt.db,
        "upsert_youtube_video_transcript",
        lambda video_id, row: writes["transcriptions"].append({"video_id": video_id, **deepcopy(row)}) or row,
    )
    monkeypatch.setattr(yt.db, "insert_youtube_comments_batch", lambda rows: writes["comments"].extend(deepcopy(rows)) or rows)
    monkeypatch.setattr(yt.db, "update_mention", lambda mention_id, row: writes["mention_updates"].append((mention_id, deepcopy(row))) or row)

    summary = asyncio.run(yt.run_unofficial_youtube_pipeline_for_brand(brand))

    assert summary["status"] == "ok"
    assert summary["discovered"] == 1
    assert summary["flagged"] == 1
    assert summary["videos_updated_with_batch_metadata"] >= 1
    assert summary["videos_updated_with_triage_results"] == 1
    assert summary["enriched"] == 1
    assert summary["comments_fetched_total"] == 1
    assert summary["final_analysis_saved_count"] == 1

    assert len(writes["channels"]) == 1
    assert len(writes["videos"]) == 1
    assert len(writes["mentions"]) == 1
    assert len(writes["fulfillment"]) >= 2  # pending + ingested
    assert len(writes["transcriptions"]) == 1
    assert len(writes["comments"]) == 1
    assert len(writes["mention_updates"]) == 1
