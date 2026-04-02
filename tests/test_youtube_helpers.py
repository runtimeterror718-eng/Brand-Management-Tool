from __future__ import annotations

from scrapers.youtube import (
    build_discovery_query_buckets,
    build_query_buckets,
    dedupe_query_terms,
    is_blacklisted_channel,
    map_video_to_mention,
    map_video_to_raw_video_row,
    normalize_final_analysis,
    normalize_title_triage,
)


def _sample_candidate() -> dict:
    return {
        "video_id": "vid123",
        "channel_id": "chan123",
        "source_url": "https://www.youtube.com/watch?v=vid123",
        "search_hits": [{"query": "physics wallah", "bucket": "primary"}],
        "video": {
            "id": "vid123",
            "snippet": {
                "title": "PW review by student",
                "description": "detailed review",
                "publishedAt": "2026-03-31T10:00:00Z",
                "channelTitle": "Unofficial Channel",
                "defaultLanguage": "en",
            },
            "statistics": {
                "viewCount": "1200",
                "likeCount": "45",
                "commentCount": "18",
            },
            "contentDetails": {"duration": "PT12M30S"},
        },
        "channel": {
            "id": "chan123",
            "snippet": {"title": "Unofficial Channel", "customUrl": "@unofficialpw"},
            "statistics": {"subscriberCount": "9000"},
        },
    }


def test_blacklist_filtering_by_id_and_handle() -> None:
    assert is_blacklisted_channel("UCiGyWN6DEbnj2alu7iapuKQ", None)
    assert is_blacklisted_channel(None, "@vidyapeethpw")
    assert not is_blacklisted_channel("random-channel", "@independent_creator")


def test_keyword_normalization_and_query_bucketing() -> None:
    cleaned = dedupe_query_terms(["  PW APP  ", "pw app", "arjuna", "physics wallah"])
    assert cleaned == ["pw app", "physics wallah"]

    buckets = build_discovery_query_buckets(extra_terms=["PW app", "pw app"], include_secondary=False)
    assert "pw app" in buckets["primary"]
    assert buckets["secondary"] == []
    assert any(term.startswith("arjuna ") for term in buckets["expanded"])

    chunked = build_query_buckets({"primary": ["a", "b", "c"]}, bucket_size=2)
    assert chunked == {"primary": [["a", "b"], ["c"]]}


def test_video_mapping_to_raw_row_payload() -> None:
    row = map_video_to_raw_video_row(_sample_candidate(), brand_id="brand-1")
    assert row["brand_id"] == "brand-1"
    assert row["video_id"] == "vid123"
    assert row["video_duration"] == 750
    assert row["video_views"] == 1200
    assert row["video_likes"] == 45
    assert row["video_comment_count"] == 18
    assert row["source_url"].endswith("vid123")


def test_video_mapping_to_normalized_mention() -> None:
    triage = {
        "label": "negative",
        "is_pr_risk": True,
        "confidence": 0.91,
        "issue_type": "refund",
        "reason": "complaint wording",
    }
    mention = map_video_to_mention("brand-1", _sample_candidate(), triage)
    assert mention["platform"] == "youtube"
    assert mention["platform_ref_id"] == "vid123"
    assert mention["content_type"] == "video"
    assert mention["source_url"].endswith("vid123")
    assert mention["author_handle"] == "unofficialpw"
    assert mention["sentiment_label"] == "negative"
    assert mention["sentiment_score"] < 0


def test_triage_and_final_parser_normalization() -> None:
    triage = normalize_title_triage({"label": "bad_value", "confidence": 9})
    assert triage["label"] == "uncertain"
    assert triage["confidence"] == 1.0

    final_out = normalize_final_analysis(
        {
            "final_sentiment": "NEGATIVE",
            "severity": "critical",
            "key_claims": ["claim1"],
            "top_negative_themes": ["fees"],
            "processing_status": "complete",
        },
        triage,
    )
    assert final_out["final_sentiment"] == "negative"
    assert final_out["severity"] == "critical"
    assert final_out["key_claims"] == ["claim1"]
    assert final_out["top_negative_themes"] == ["fees"]
