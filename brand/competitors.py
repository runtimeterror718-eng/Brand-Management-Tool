"""
Competitor mention tracking — compare brand vs competitors.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from storage import queries as db

logger = logging.getLogger(__name__)


def get_competitor_comparison(
    brand_id: str, days: int = 7
) -> dict[str, Any]:
    """
    Compare brand mentions/sentiment against competitor mentions.
    """
    brand = db.get_brand(brand_id)
    if not brand:
        return {"error": "Brand not found"}

    since = datetime.utcnow() - timedelta(days=days)
    brand_mentions = db.get_mentions(brand_id, since=since)

    brand_sentiments = [m.get("sentiment_score", 0) or 0 for m in brand_mentions]
    brand_avg = sum(brand_sentiments) / len(brand_sentiments) if brand_sentiments else 0

    comparison = {
        "brand": {
            "name": brand["name"],
            "mention_count": len(brand_mentions),
            "avg_sentiment": round(brand_avg, 4),
        },
        "competitors": [],
        "period_days": days,
    }

    # Track competitor mentions across all monitored brands
    for competitor_name in brand.get("competitors", []):
        # Search for competitor mentions in the brand's mention data
        comp_mentions = [
            m for m in brand_mentions
            if competitor_name.lower() in (m.get("content_text", "") or "").lower()
        ]
        comp_sentiments = [m.get("sentiment_score", 0) or 0 for m in comp_mentions]
        comp_avg = sum(comp_sentiments) / len(comp_sentiments) if comp_sentiments else 0

        comparison["competitors"].append({
            "name": competitor_name,
            "mention_count": len(comp_mentions),
            "avg_sentiment": round(comp_avg, 4),
        })

    return comparison
