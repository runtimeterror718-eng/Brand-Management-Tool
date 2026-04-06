"""
Stage 7: Full Pipeline Orchestrator — runs all stages and stores to Supabase.

Usage:
    python -m analysis.deep_clustering.pipeline --brand-id <uuid>
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from typing import Any

from config.supabase_client import get_service_client
from analysis.deep_clustering.ingest import ingest_all, NormalizedMention
from analysis.deep_clustering.enrich import enrich_mentions
from analysis.deep_clustering.embed import create_composite_embeddings_with_text
from analysis.deep_clustering.cluster import multi_level_cluster
from analysis.deep_clustering.label import label_all_clusters

logger = logging.getLogger(__name__)


def run_deep_clustering(brand_id: str) -> dict[str, Any]:
    """
    Full 7-stage deep clustering pipeline.
    Returns summary stats.
    """
    start = datetime.utcnow()
    client = get_service_client()

    # Stage 1: Ingest & Normalize
    logger.info("=" * 60)
    logger.info("STAGE 1: Ingest & Normalize")
    logger.info("=" * 60)
    mentions = ingest_all(brand_id)
    if len(mentions) < 10:
        return {"error": "Not enough data to cluster", "mention_count": len(mentions)}

    # Stage 2: LLM Pre-Enrichment
    logger.info("=" * 60)
    logger.info("STAGE 2: LLM Pre-Enrichment (%d mentions)", len(mentions))
    logger.info("=" * 60)
    enrichments = enrich_mentions(mentions)

    # Stage 3: Composite Embedding
    logger.info("=" * 60)
    logger.info("STAGE 3: Composite Embedding")
    logger.info("=" * 60)
    embeddings, text_embeddings = create_composite_embeddings_with_text(mentions, enrichments)

    # Stage 3b: Store embeddings in pgvector
    logger.info("=" * 60)
    logger.info("STAGE 3b: Store Embeddings in pgvector")
    logger.info("=" * 60)
    _store_embeddings(brand_id, mentions, enrichments, text_embeddings, client)

    # Stage 4: Multi-Level Clustering
    logger.info("=" * 60)
    logger.info("STAGE 4: Multi-Level HDBSCAN")
    logger.info("=" * 60)
    cluster_results = multi_level_cluster(embeddings)

    # Stage 5 & 6: LLM Labeling + Dynamics
    logger.info("=" * 60)
    logger.info("STAGE 5-6: LLM Labeling & Dynamics")
    logger.info("=" * 60)
    labeled = label_all_clusters(cluster_results, mentions, enrichments)

    # Stage 7: Store to Supabase
    logger.info("=" * 60)
    logger.info("STAGE 7: Store to Supabase")
    logger.info("=" * 60)
    _store_results(brand_id, labeled, mentions, enrichments, client)

    elapsed = (datetime.utcnow() - start).total_seconds()
    summary = {
        "brand_id": brand_id,
        "total_mentions": len(mentions),
        "themes": len(labeled["level_1"]),
        "topics": len(labeled["level_2"]),
        "subtopics": len(labeled["level_3"]),
        "elapsed_seconds": round(elapsed, 1),
        "timestamp": datetime.utcnow().isoformat(),
    }
    logger.info("Pipeline complete in %.1fs: %s", elapsed, json.dumps(summary, indent=2))
    return summary


def _store_embeddings(
    brand_id: str,
    mentions: list[NormalizedMention],
    enrichments: list[dict],
    text_embeddings,  # numpy array (N, 384)
    client,
):
    """Store text embeddings in mention_embeddings table for RAG + similarity search."""
    import numpy as np

    # Clear old embeddings for this brand
    try:
        client.table("mention_embeddings").delete().eq("brand_id", brand_id).execute()
    except Exception:
        pass

    stored = 0
    batch = []

    for i, (m, e) in enumerate(zip(mentions, enrichments)):
        vec = text_embeddings[i].tolist()

        batch.append({
            "brand_id": brand_id,
            "mention_id": m.id if m.original_table in ("mentions",) else None,
            "content_text": m.content[:500],
            "platform": m.platform,
            "cluster_id": None,  # will be updated after clustering
            "sentiment_label": e.get("emotion"),
            "sentiment_score": None,
            "embedding": vec,
        })

        if len(batch) >= 50:
            try:
                client.table("mention_embeddings").insert(batch).execute()
                stored += len(batch)
            except Exception:
                logger.exception("Failed to store embedding batch at %d", i)
            batch = []

    if batch:
        try:
            client.table("mention_embeddings").insert(batch).execute()
            stored += len(batch)
        except Exception:
            logger.exception("Failed to store final embedding batch")

    logger.info("Stored %d embeddings in pgvector (384d text vectors)", stored)


def _jsonable(obj):
    """Convert numpy types to Python native for JSON serialization."""
    import numpy as np
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def _store_results(
    brand_id: str,
    labeled: dict,
    mentions: list[NormalizedMention],
    enrichments: list[dict],
    client,
):
    """Store all results to Supabase tables."""

    # Clear old data for this brand
    for table in ["topic_subtopics", "topic_topics", "topic_themes", "mention_enrichments"]:
        try:
            client.table(table).delete().eq("brand_id", brand_id).execute()
        except Exception:
            pass

    # --- Store themes (L1) ---
    for cid, data in labeled["level_1"].items():
        try:
            client.table("topic_themes").upsert(_jsonable({
                "brand_id": brand_id,
                "theme_id": cid,
                "name": data["name"],
                "description": data.get("description", ""),
                "mention_count": data["count"],
                "avg_sentiment": data.get("avg_sentiment"),
                "velocity": data.get("velocity", 0),
                "lifecycle": data.get("lifecycle", "unknown"),
                "actionability_score": data.get("actionability_score", 0),
                "platform_distribution": data.get("platforms", {}),
                "platform_sentiments": data.get("platform_sentiments", {}),
                "platform_divergence": data.get("platform_divergence", 0),
                "intent_distribution": data.get("intent_distribution", {}),
                "emotion_distribution": data.get("emotion_distribution", {}),
                "user_segment_distribution": data.get("user_segment_distribution", {}),
                "complaint_categories": data.get("complaint_categories", {}),
                "representative_texts": [mentions[i].content[:200] for i in data["mention_indices"][:7]],
                "first_seen": data.get("first_seen"),
                "last_seen": data.get("last_seen"),
            }), on_conflict="brand_id,theme_id").execute()
        except Exception:
            logger.exception("Failed to store theme %d", cid)

    # --- Store topics (L2) ---
    for cid, data in labeled["level_2"].items():
        try:
            client.table("topic_topics").upsert(_jsonable({
                "brand_id": brand_id,
                "topic_id": cid,
                "parent_theme_id": data["parent_theme"],
                "name": data["name"],
                "description": data.get("description", ""),
                "mention_count": data["count"],
                "avg_sentiment": data.get("avg_sentiment"),
                "velocity": data.get("velocity", 0),
                "lifecycle": data.get("lifecycle", "unknown"),
                "actionability_score": data.get("actionability_score", 0),
                "platform_distribution": data.get("platforms", {}),
                "platform_sentiments": data.get("platform_sentiments", {}),
                "platform_divergence": data.get("platform_divergence", 0),
                "intent_distribution": data.get("intent_distribution", {}),
                "emotion_distribution": data.get("emotion_distribution", {}),
                "user_segment_distribution": data.get("user_segment_distribution", {}),
                "complaint_categories": data.get("complaint_categories", {}),
                "representative_texts": [mentions[i].content[:200] for i in data["mention_indices"][:5]],
                "first_seen": data.get("first_seen"),
                "last_seen": data.get("last_seen"),
            }), on_conflict="brand_id,topic_id").execute()
        except Exception:
            logger.exception("Failed to store topic %d", cid)

    # --- Store sub-topics (L3) ---
    for cid, data in labeled["level_3"].items():
        try:
            client.table("topic_subtopics").upsert(_jsonable({
                "brand_id": brand_id,
                "subtopic_id": cid,
                "parent_topic_id": data["parent_topic"],
                "parent_theme_id": data["parent_theme"],
                "name": data["name"],
                "description": data.get("description", ""),
                "mention_count": data["count"],
                "avg_sentiment": data.get("avg_sentiment"),
                "velocity": data.get("velocity", 0),
                "lifecycle": data.get("lifecycle", "unknown"),
                "actionability_score": data.get("actionability_score", 0),
                "platform_distribution": data.get("platforms", {}),
                "representative_texts": [mentions[i].content[:150] for i in data["mention_indices"][:5]],
                "is_misc": data.get("is_misc", False),
                "first_seen": data.get("first_seen"),
                "last_seen": data.get("last_seen"),
            }), on_conflict="brand_id,subtopic_id").execute()
        except Exception:
            logger.exception("Failed to store subtopic %d", cid)

    # --- Store per-mention enrichments ---
    assignments = labeled.get("level_3", {})
    # Build reverse lookup: mention_index → (theme, topic, subtopic)
    idx_to_assignment = {}
    for l3_id, l3_data in assignments.items():
        for idx in l3_data["mention_indices"]:
            idx_to_assignment[idx] = {
                "theme_id": l3_data["parent_theme"],
                "topic_id": l3_data["parent_topic"],
                "subtopic_id": l3_id,
            }

    batch = []
    for i, (m, e) in enumerate(zip(mentions, enrichments)):
        assignment = idx_to_assignment.get(i, {})
        batch.append({
            "mention_id": m.id if m.original_table == "mentions" else None,
            "brand_id": brand_id,
            "intent": e.get("intent"),
            "emotion": e.get("emotion"),
            "specificity": e.get("specificity"),
            "product_mentioned": e.get("product_mentioned"),
            "person_mentioned": e.get("person_mentioned"),
            "competitor_mentioned": e.get("competitor_mentioned"),
            "complaint_category": e.get("complaint_category"),
            "user_segment": e.get("user_segment"),
            "urgency": e.get("urgency"),
            "is_actionable": e.get("is_actionable", False),
            "action_type": e.get("action_type"),
            "theme_id": assignment.get("theme_id"),
            "topic_id": assignment.get("topic_id"),
            "subtopic_id": assignment.get("subtopic_id"),
        })

        if len(batch) >= 100:
            try:
                client.table("mention_enrichments").insert(_jsonable(batch)).execute()
            except Exception:
                logger.exception("Failed to store enrichment batch")
            batch = []

    if batch:
        try:
            client.table("mention_enrichments").insert(_jsonable(batch)).execute()
        except Exception:
            logger.exception("Failed to store final enrichment batch")

    logger.info("Stored: %d themes, %d topics, %d sub-topics, %d enrichments",
                len(labeled["level_1"]), len(labeled["level_2"]),
                len(labeled["level_3"]), len(mentions))


# ---- CLI ----

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Deep topic clustering pipeline")
    parser.add_argument("--brand-id", required=True, help="Brand UUID")
    args = parser.parse_args()

    result = run_deep_clustering(args.brand_id)

    print(f"\n{'=' * 60}")
    print("DEEP CLUSTERING RESULTS")
    print(f"{'=' * 60}")
    print(f"  Mentions analyzed: {result.get('total_mentions', 0)}")
    print(f"  Level 1 Themes:    {result.get('themes', 0)}")
    print(f"  Level 2 Topics:    {result.get('topics', 0)}")
    print(f"  Level 3 Sub-topics:{result.get('subtopics', 0)}")
    print(f"  Time:              {result.get('elapsed_seconds', 0)}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
