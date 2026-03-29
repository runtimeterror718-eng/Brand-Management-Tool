"""
Brand health score — sentiment + volume + engagement aggregate.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from storage import queries as db

logger = logging.getLogger(__name__)


def compute_health_score(brand_id: str, days: int = 7) -> dict[str, Any]:
    """
    Compute brand health score combining:
      - Sentiment score (40%): average sentiment across mentions
      - Volume score (30%): mention volume trend
      - Engagement score (30%): average engagement normalized

    Returns score 0-100 and component breakdown.
    """
    since = datetime.utcnow() - timedelta(days=days)
    mentions = db.get_mentions(brand_id, since=since, limit=1000)

    if not mentions:
        return {
            "health_score": 50,
            "sentiment_score": 0,
            "volume_score": 0,
            "engagement_score": 0,
            "mention_count": 0,
            "period_days": days,
        }

    # Sentiment component (40%) — map [-1, 1] to [0, 100]
    sentiments = [m.get("sentiment_score", 0) or 0 for m in mentions]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
    sentiment_score = (avg_sentiment + 1) * 50  # [-1,1] → [0,100]

    # Volume component (30%) — compare to previous period
    prev_since = since - timedelta(days=days)
    prev_count = db.get_mention_count_since(brand_id, prev_since)
    current_count = len(mentions)

    if prev_count > 0:
        volume_change = (current_count - prev_count) / prev_count
        volume_score = min(max(50 + volume_change * 25, 0), 100)
    else:
        volume_score = 50 if current_count > 0 else 0

    # Engagement component (30%)
    engagements = [m.get("engagement_score", 0) or 0 for m in mentions]
    avg_engagement = sum(engagements) / len(engagements) if engagements else 0
    engagement_score = min(avg_engagement / 100, 100)  # normalize

    # Weighted total
    health = (
        sentiment_score * 0.4
        + volume_score * 0.3
        + engagement_score * 0.3
    )

    return {
        "health_score": round(health, 1),
        "sentiment_score": round(sentiment_score, 1),
        "volume_score": round(volume_score, 1),
        "engagement_score": round(engagement_score, 1),
        "mention_count": current_count,
        "avg_sentiment": round(avg_sentiment, 4),
        "period_days": days,
    }
