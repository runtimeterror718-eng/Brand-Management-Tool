"""
Aggregates severity across brand / platform / time.
"""

from __future__ import annotations

import logging
from typing import Any

from severity.scorer import compute_severity
from severity.rules import should_alert, get_alert_channel
from storage import queries as db

logger = logging.getLogger(__name__)


def score_mentions(
    mentions: list[dict[str, Any]], brand: dict[str, Any]
) -> list[dict[str, Any]]:
    """Score all mentions and persist results. Returns scored list."""
    scored = []

    for mention in mentions:
        result = compute_severity(mention, brand)

        # Persist severity score
        try:
            db.insert_severity_score({
                "mention_id": mention.get("id", ""),
                "brand_id": brand.get("id", ""),
                "severity_level": result["severity_level"],
                "severity_score": result["severity_score"],
                "sentiment_component": result["sentiment_component"],
                "engagement_component": result["engagement_component"],
                "velocity_component": result["velocity_component"],
                "keyword_component": result["keyword_component"],
            })
        except Exception:
            logger.exception("Failed to persist severity score")

        mention["severity"] = result
        scored.append(mention)

    return scored


def aggregate_severity(brand_id: str) -> dict[str, Any]:
    """Aggregate current severity stats for a brand."""
    scores = db.get_severity_scores(brand_id, limit=500)

    if not scores:
        return {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "avg_score": 0}

    levels = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    total_score = 0.0

    for s in scores:
        level = s.get("severity_level", "low")
        levels[level] = levels.get(level, 0) + 1
        total_score += s.get("severity_score", 0)

    return {
        "total": len(scores),
        **levels,
        "avg_score": round(total_score / len(scores), 4),
    }


def get_critical_mentions(brand_id: str, limit: int = 50) -> list[dict]:
    """Get the most critical mentions for immediate attention."""
    return db.get_severity_scores(brand_id, level="critical", limit=limit)
