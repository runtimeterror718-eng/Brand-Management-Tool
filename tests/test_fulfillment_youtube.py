from __future__ import annotations

from search.fulfillment import build_youtube_fulfillment_from_triage


def test_fulfillment_flags_for_negative_label() -> None:
    outcome = build_youtube_fulfillment_from_triage("negative", confidence=0.9, is_pr_risk=True)
    assert outcome["passed"] is True
    assert outcome["queued_for_scraping"] is True
    assert outcome["queued_for_transcription"] is True
    assert outcome["score"] == 0.9


def test_fulfillment_flags_for_uncertain_label() -> None:
    outcome = build_youtube_fulfillment_from_triage("uncertain", confidence=0.2, is_pr_risk=False)
    assert outcome["passed"] is True
    assert outcome["queued_for_scraping"] is True
    assert outcome["queued_for_transcription"] is True
    assert outcome["score"] >= 0.5


def test_fulfillment_flags_for_positive_label() -> None:
    outcome = build_youtube_fulfillment_from_triage("positive", confidence=0.8, is_pr_risk=False)
    assert outcome["passed"] is False
    assert outcome["queued_for_scraping"] is False
    assert outcome["queued_for_transcription"] is False
    assert 0 <= outcome["score"] <= 0.2
