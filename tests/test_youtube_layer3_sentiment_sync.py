from __future__ import annotations

from scrapers import youtube as yt


def test_normalize_transcript_sentiment_triage_applies_pr_heuristic() -> None:
    out = yt.normalize_transcript_sentiment_triage(
        {
            "pr_sentiment": "negative",
            "is_pr_risk": False,
            "severity": "high",
            "issue_type": "student_wellbeing",
            "target_entity": "students",
            "transcript_summary": "summary",
            "key_claims": ["claim-1"],
            "brand_harm_evidence": [],
            "protective_context": ["context-1"],
            "recommended_action": "monitor",
            "reason": "non brand discussion",
        }
    )
    assert out["pr_sentiment"] == "neutral"
    assert out["is_pr_risk"] is False
    assert out["severity"] == "high"


def test_parse_comment_sentiment_results_matches_exact_ids() -> None:
    payload = {
        "results": [
            {"Comment ID": "AbC123", "Sentiment": "positive"},
            {"Comment ID": "xyz987", "Sentiment": "NEGATIVE"},
        ]
    }
    mapped = yt.parse_comment_sentiment_results(payload, ["AbC123", "xyz987", "missing"])
    assert mapped["AbC123"] == "positive"
    assert mapped["xyz987"] == "negative"
    assert mapped["missing"] == "neutral"


def test_transcript_sentiment_sync_updates_video(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    row = {
        "video_id": "vid-1",
        "video_title": "Title",
        "transcript_text": "Transcript text",
    }
    video_updates: list[tuple[str, dict]] = []

    class _FakeAnalyzer:
        @property
        def is_configured(self):
            return True

        def custom_id(self, stage: str, brand_id: str, video_id: str) -> str:
            return f"{stage}:{video_id}"

        def direct_call_with_meta(self, stage: str, payload: dict):
            return (
                {
                    "pr_sentiment": "negative",
                    "is_pr_risk": True,
                    "severity": "high",
                    "issue_type": "brand_attack",
                    "target_entity": "brand",
                    "transcript_summary": "summary",
                    "key_claims": ["claim"],
                    "brand_harm_evidence": ["evidence"],
                    "protective_context": [],
                    "recommended_action": "escalate",
                    "reason": "complaint language",
                },
                {"mode": "direct", "status": "completed", "correlation_id": "req-1"},
            )

    monkeypatch.setattr(yt, "AzureYouTubeAnalyzer", _FakeAnalyzer)
    monkeypatch.setattr(yt, "_get_layer3_eligible_video_rows", lambda brand_id, scan_limit=5000: [row])
    monkeypatch.setattr(
        yt.db,
        "update_youtube_video_by_video_id",
        lambda video_id, updates: video_updates.append((video_id, updates)) or {"video_id": video_id, **updates},
    )
    monkeypatch.setattr(yt.db, "merge_youtube_video_analysis_artifacts", lambda video_id, patch: {"video_id": video_id, "analysis_artifacts": patch})

    summary = yt.run_youtube_transcript_sentiment_sync_for_brand(brand)

    assert summary["status"] == "ok"
    assert summary["processed"] == 1
    assert summary["updated"] == 1
    assert video_updates
    latest = video_updates[-1][1]
    assert latest["transcript_pr_sentiment"] == "negative"
    assert latest["transcript_pr_is_risk"] is True
    assert latest["transcript_pr_severity"] == "high"
    assert latest["transcript_pr_issue_type"] == "brand_attack"
    assert latest["transcript_pr_target_entity"] == "brand"


def test_comment_sentiment_sync_batches_20(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    row = {"video_id": "vid-1", "video_title": "Title"}
    update_batches: list[int] = []

    class _FakeAnalyzer:
        @property
        def is_configured(self):
            return True

        def custom_id(self, stage: str, brand_id: str, video_id: str) -> str:
            return f"{stage}:{video_id}"

        def direct_call_with_meta(self, stage: str, payload: dict):
            results = []
            for item in payload.get("comments", []):
                results.append({"Comment ID": item.get("Comment ID"), "Sentiment": "neutral"})
            return {"results": results}, {"mode": "direct", "status": "completed", "correlation_id": "req-1"}

    comments = [
        {
            "comment_id": f"c{i}",
            "comment_text": f"text {i}",
            "is_reply": False,
        }
        for i in range(1, 26)
    ]

    monkeypatch.setattr(yt, "AzureYouTubeAnalyzer", _FakeAnalyzer)
    monkeypatch.setattr(yt, "_get_layer3_eligible_video_rows", lambda brand_id, scan_limit=5000: [row])
    monkeypatch.setattr(yt.db, "get_youtube_comments", lambda video_id, limit=2000: comments)
    monkeypatch.setattr(
        yt.db,
        "update_youtube_comment_sentiments",
        lambda updates: update_batches.append(len(updates)) or len(updates),
    )
    monkeypatch.setattr(yt.db, "merge_youtube_video_analysis_artifacts", lambda video_id, patch: {"video_id": video_id, "analysis_artifacts": patch})

    summary = yt.run_youtube_comment_sentiment_sync_for_brand(
        brand,
        comment_batch_size=20,
    )

    assert summary["status"] == "ok"
    assert summary["videos_processed"] == 1
    assert summary["batches_processed"] == 2
    assert summary["comments_classified"] == 25
    assert summary["comments_updated"] == 25
    assert update_batches == [20, 5]
