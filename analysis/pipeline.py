"""
Orchestrates the full 3-tier analysis flow:
  Tier 1: Clean (free)  →  Tier 2: Understand (pennies)  →  Tier 3: Explain (LLM ~$0.08)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from analysis.cleaner import clean_batch
from analysis.sentiment import analyze_batch as sentiment_batch
from analysis.clustering import cluster_mentions
from analysis.insights import generate_insights
from storage import queries as db

logger = logging.getLogger(__name__)


async def run_analysis(
    brand_id: str,
    brand_name: str,
    mentions: list[dict[str, Any]],
    languages: list[str] | None = None,
) -> dict[str, Any]:
    """
    Run the full 3-tier analysis pipeline on a list of mentions.

    Returns the complete analysis report including themes, risks, opportunities.
    """
    import asyncio

    if not mentions:
        return {"error": "No mentions to analyze"}

    # --- Tier 1: Clean ---
    logger.info("Tier 1: Cleaning %d mentions...", len(mentions))
    cleaned = clean_batch(mentions, allowed_languages=languages)

    if not cleaned:
        return {"error": "All mentions filtered during cleaning"}

    texts = [m.get("content_text", "") for m in cleaned]

    # --- Tier 2: Understand ---
    logger.info("Tier 2: Sentiment + clustering on %d mentions...", len(cleaned))

    # Sentiment analysis
    sentiments = await asyncio.get_event_loop().run_in_executor(
        None, sentiment_batch, texts
    )

    # Attach sentiment to mentions and compute weighted scores
    for mention, sent in zip(cleaned, sentiments):
        mention["sentiment_score"] = sent["score"]
        mention["sentiment_label"] = sent["label"]
        # Weight sentiment by engagement (Rule #9)
        engagement = mention.get("engagement_score", 0) or 1
        mention["weighted_sentiment"] = sent["score"] * (1 + (engagement / 1000))

    # Update mentions in DB with sentiment
    for mention in cleaned:
        if mention.get("id"):
            try:
                db.update_mention(mention["id"], {
                    "sentiment_score": mention["sentiment_score"],
                    "sentiment_label": mention["sentiment_label"],
                })
            except Exception:
                pass

    # Clustering
    cluster_result = await asyncio.get_event_loop().run_in_executor(
        None, cluster_mentions, texts
    )

    # Attach cluster labels
    for mention, label in zip(cleaned, cluster_result["labels"]):
        mention["cluster_id"] = label
        if mention.get("id"):
            try:
                db.update_mention(mention["id"], {"cluster_id": label})
            except Exception:
                pass

    # Compute stats
    scores = [s["score"] for s in sentiments]
    positive = sum(1 for s in sentiments if s["label"] == "positive")
    negative = sum(1 for s in sentiments if s["label"] == "negative")
    total = len(sentiments)

    sentiment_stats = {
        "avg": sum(scores) / total if total else 0,
        "positive_pct": (positive / total * 100) if total else 0,
        "negative_pct": (negative / total * 100) if total else 0,
    }

    # Platform breakdown
    platform_breakdown: dict[str, int] = {}
    for m in cleaned:
        p = m.get("platform", "unknown")
        platform_breakdown[p] = platform_breakdown.get(p, 0) + 1

    # --- Tier 3: Explain ---
    logger.info("Tier 3: Generating LLM insights...")
    report = await asyncio.get_event_loop().run_in_executor(
        None,
        generate_insights,
        brand_name,
        cluster_result["cluster_summaries"],
        sentiment_stats,
        len(cleaned),
        platform_breakdown,
    )

    # Persist analysis run
    analysis_data = {
        "brand_id": brand_id,
        "total_mentions": len(cleaned),
        "overall_sentiment": sentiment_stats["avg"],
        "cluster_count": cluster_result["n_clusters"],
        "themes": report.get("themes", []),
        "risks": report.get("risks", []),
        "opportunities": report.get("opportunities", []),
        "severity_summary": report.get("severity_overview", {}),
        "llm_cost_usd": report.get("_llm_cost_usd", 0),
    }
    try:
        db.insert_analysis_run(analysis_data)
    except Exception:
        logger.exception("Failed to persist analysis run")

    return {
        "brand_id": brand_id,
        "brand_name": brand_name,
        "mention_count": len(cleaned),
        "sentiment_stats": sentiment_stats,
        "cluster_count": cluster_result["n_clusters"],
        "cluster_summaries": cluster_result["cluster_summaries"],
        "report": report,
        "platform_breakdown": platform_breakdown,
    }
