"""
Step 2: Fulfillment Criteria — scores and filters search results.

Only results passing fulfillment get queued for transcription/scraping.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from config.constants import (
    CONTENT_TYPES_REQUIRING_TRANSCRIPTION,
    FULFILLMENT_PASS_THRESHOLD,
)
from storage.dedup import is_duplicate


def check_fulfillment(
    search_params: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate a single search result against fulfillment criteria.

    Parameters
    ----------
    search_params : dict
        The original search parameters (keywords, min_likes, after_date, languages, …).
    result : dict
        A raw search result with keys like content_text, engagement_score,
        published_at, language, content_type, comments_count.

    Returns
    -------
    dict with passed, score, criteria_met, queued_for_transcription, queued_for_scraping.
    """
    content_text = (result.get("content_text") or "").lower()
    engagement = result.get("engagement_score", 0)
    published_at = result.get("published_at")
    language = result.get("language", "en")
    content_type = result.get("content_type", "text")
    comments_count = result.get("comments_count", 0)

    # Parse after_date
    after_date = search_params.get("after_date")
    if isinstance(after_date, str):
        after_date = datetime.fromisoformat(after_date)
    if after_date is None:
        after_date = datetime.min

    # Parse published_at
    if isinstance(published_at, str):
        published_at = datetime.fromisoformat(published_at)
    if published_at is None:
        published_at = datetime.utcnow()

    criteria = {
        "min_engagement": engagement >= search_params.get("min_likes", 0),
        "recency": published_at >= after_date,
        "language_match": language in search_params.get("languages", ["en", "hi"]),
        "keyword_match": any(
            kw.lower() in content_text
            for kw in search_params.get("keywords", [])
        ),
        "not_duplicate": not is_duplicate(content_text, result.get("id")),
    }

    score = sum(criteria.values()) / len(criteria) if criteria else 0.0
    passed = score >= FULFILLMENT_PASS_THRESHOLD

    return {
        "passed": passed,
        "score": round(score, 3),
        "criteria_met": criteria,
        "queued_for_transcription": passed
        and content_type in CONTENT_TYPES_REQUIRING_TRANSCRIPTION,
        "queued_for_scraping": passed and comments_count > 0,
    }


def evaluate_batch(
    search_params: dict[str, Any],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Evaluate a batch of results. Returns only those that passed."""
    evaluated = []
    for result in results:
        outcome = check_fulfillment(search_params, result)
        outcome["result"] = result
        if outcome["passed"]:
            evaluated.append(outcome)
    return evaluated


def build_youtube_fulfillment_from_triage(
    triage_label: str,
    confidence: float,
    is_pr_risk: bool,
) -> dict[str, Any]:
    """
    Convert YouTube title triage output into fulfillment flags.

    For YouTube unofficial flow, "passed" means the mention should proceed
    to deeper investigation and enrichment.
    """
    label = (triage_label or "uncertain").strip().lower()
    conf = max(0.0, min(1.0, float(confidence or 0.0)))

    is_flagged = label in {"negative", "uncertain"} or bool(is_pr_risk)
    if label == "negative":
        score = conf
    elif label == "uncertain":
        score = max(conf, 0.5)
    else:
        score = max(0.0, 1.0 - conf)

    criteria_met = {
        "triage_label": label,
        "is_pr_risk": bool(is_pr_risk),
        "confidence_ge_0_5": conf >= 0.5,
        "requires_deep_enrichment": is_flagged,
    }
    return {
        "passed": is_flagged,
        "score": round(score, 3),
        "criteria_met": criteria_met,
        "queued_for_scraping": is_flagged,
        "queued_for_transcription": is_flagged,
    }
