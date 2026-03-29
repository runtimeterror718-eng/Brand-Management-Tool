"""
Week-over-week trends, velocity spikes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from storage import queries as db

logger = logging.getLogger(__name__)


def get_weekly_trends(brand_id: str, weeks: int = 4) -> list[dict[str, Any]]:
    """Compute week-over-week trends for a brand."""
    trends = []
    now = datetime.utcnow()

    for w in range(weeks):
        week_end = now - timedelta(weeks=w)
        week_start = week_end - timedelta(weeks=1)

        mentions = db.get_mentions(brand_id, since=week_start, limit=2000)
        # Filter to the specific week
        week_mentions = [
            m for m in mentions
            if m.get("scraped_at") and m["scraped_at"] <= week_end.isoformat()
        ]

        sentiments = [m.get("sentiment_score", 0) or 0 for m in week_mentions]
        avg_sent = sum(sentiments) / len(sentiments) if sentiments else 0

        # Platform breakdown
        platforms: dict[str, int] = {}
        for m in week_mentions:
            p = m.get("platform", "unknown")
            platforms[p] = platforms.get(p, 0) + 1

        trends.append({
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "mention_count": len(week_mentions),
            "avg_sentiment": round(avg_sent, 4),
            "platforms": platforms,
        })

    return list(reversed(trends))  # chronological order


def detect_velocity_spike(brand_id: str, threshold: float = 3.0) -> dict[str, Any] | None:
    """
    Detect if there's a velocity spike (current rate >> baseline).

    Returns spike info if detected, None otherwise.
    """
    current_rate = db.get_hourly_mention_rate(brand_id, last_hours=2)
    baseline_rate = db.get_avg_hourly_rate(brand_id, last_days=7)

    if baseline_rate == 0:
        return None

    ratio = current_rate / baseline_rate
    if ratio >= threshold:
        return {
            "spike_detected": True,
            "current_rate": round(current_rate, 2),
            "baseline_rate": round(baseline_rate, 2),
            "ratio": round(ratio, 2),
            "severity": "critical" if ratio >= 10 else "high" if ratio >= 5 else "medium",
        }

    return None
