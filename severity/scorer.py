"""
Computes severity score per mention — the core severity formula from the spec.
"""

from __future__ import annotations

import logging
from math import log
from typing import Any

from severity.keywords import load_crisis_keywords, count_keyword_hits
from severity.rules import classify_severity
from storage.queries import get_hourly_mention_rate, get_avg_hourly_rate
from config.constants import SEVERITY_WEIGHTS, VELOCITY_SPIKE_DIVISOR

logger = logging.getLogger(__name__)


def compute_severity(mention: dict[str, Any], brand: dict[str, Any]) -> dict[str, Any]:
    """
    Compute severity score for a single mention.

    Components:
      - Sentiment (0–0.30): very negative = higher
      - Engagement (0–0.25): high engagement + negative = worse
      - Velocity (0–0.25): sudden spike = crisis signal
      - Keywords (0–0.20): crisis keyword matches

    Returns dict with severity_score, severity_level, and all components.
    """
    # --- Sentiment component (0–0.30) ---
    sentiment_score = mention.get("sentiment_score", 0) or 0
    sent = abs(min(sentiment_score, 0))
    sentiment_component = min(sent * 0.3, SEVERITY_WEIGHTS["sentiment_max"])

    # --- Engagement component (0–0.25) ---
    engagement = mention.get("engagement_score", 0) or 0
    eng = log(1 + engagement)
    engagement_component = min(eng / 20, SEVERITY_WEIGHTS["engagement_max"])

    # --- Velocity component (0–0.25) ---
    brand_id = brand.get("id", "")
    try:
        current_rate = get_hourly_mention_rate(brand_id, last_hours=2)
        baseline_rate = get_avg_hourly_rate(brand_id, last_days=7)
        velocity_ratio = current_rate / max(baseline_rate, 1)
        velocity_component = (
            min((velocity_ratio - 1) / VELOCITY_SPIKE_DIVISOR, SEVERITY_WEIGHTS["velocity_max"])
            if velocity_ratio > 1
            else 0.0
        )
    except Exception:
        velocity_component = 0.0

    # --- Keyword component (0–0.20) ---
    content = mention.get("content_text", "")
    crisis_keywords = load_crisis_keywords(brand)
    keyword_hits = count_keyword_hits(content, crisis_keywords)
    keyword_component = min(keyword_hits * 0.05, SEVERITY_WEIGHTS["keyword_max"])

    # --- Final score ---
    score = min(
        sentiment_component + engagement_component + velocity_component + keyword_component,
        1.0,
    )
    level = classify_severity(score)

    return {
        "severity_score": round(score, 4),
        "severity_level": level,
        "sentiment_component": round(sentiment_component, 4),
        "engagement_component": round(engagement_component, 4),
        "velocity_component": round(velocity_component, 4),
        "keyword_component": round(keyword_component, 4),
    }
