"""
Tier 2: Embeddings → HDBSCAN clustering → cluster summaries.
NOT K-means.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading MiniLM embedding model...")
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embed_model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Generate embeddings for a list of texts."""
    model = _get_embed_model()
    return model.encode(texts, show_progress_bar=False, normalize_embeddings=True)


def cluster_mentions(
    texts: list[str],
    min_cluster_size: int = 5,
    min_samples: int = 3,
) -> dict[str, Any]:
    """
    Cluster texts using HDBSCAN.

    Returns dict with 'labels', 'n_clusters', 'cluster_summaries'.
    """
    import hdbscan

    if len(texts) < min_cluster_size:
        return {
            "labels": [-1] * len(texts),
            "n_clusters": 0,
            "cluster_summaries": [],
        }

    embeddings = embed_texts(texts)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(embeddings)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)

    # Build cluster summaries
    summaries = []
    for cid in range(n_clusters):
        mask = labels == cid
        cluster_indices = np.where(mask)[0]
        cluster_embeddings = embeddings[mask]

        # Find medoid (most central point)
        centroid = cluster_embeddings.mean(axis=0)
        distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
        medoid_idx = cluster_indices[np.argmin(distances)]

        # Top-5 representatives (closest to centroid)
        top_5_local = np.argsort(distances)[:5]
        rep_indices = cluster_indices[top_5_local]

        summaries.append({
            "cluster_id": cid,
            "size": int(mask.sum()),
            "medoid_index": int(medoid_idx),
            "medoid_text": texts[medoid_idx],
            "representative_indices": rep_indices.tolist(),
            "representative_texts": [texts[i] for i in rep_indices],
        })

    logger.info("Clustered %d texts into %d clusters", len(texts), n_clusters)

    return {
        "labels": labels.tolist(),
        "n_clusters": n_clusters,
        "cluster_summaries": summaries,
    }
