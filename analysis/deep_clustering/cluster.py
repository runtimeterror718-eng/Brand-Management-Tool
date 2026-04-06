"""
Stage 4: Multi-Level HDBSCAN Clustering.
  Level 1 (Themes): coarse, min_cluster_size adaptive ~5% of data
  Level 2 (Topics): medium, within each L1 theme
  Level 3 (Sub-topics): fine, within each L2 topic, leaf method
"""

from __future__ import annotations

import logging

import hdbscan
import numpy as np
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)


def multi_level_cluster(embeddings: np.ndarray) -> dict:
    """
    Three-level hierarchical clustering.
    Returns structure with mention indices at each level.
    """
    n = len(embeddings)
    logger.info("Multi-level clustering on %d mentions...", n)

    # Dimensionality reduction
    if embeddings.shape[1] > 50:
        pca = PCA(n_components=50)
        reduced = pca.fit_transform(embeddings)
        logger.info("PCA: %d → 50 dims (%.1f%% variance retained)",
                     embeddings.shape[1], pca.explained_variance_ratio_.sum() * 100)
    else:
        reduced = embeddings

    results = {
        "level_1": {},
        "level_2": {},
        "level_3": {},
        "mention_assignments": {},
    }

    # ======================== LEVEL 1: Themes ========================
    # Adaptive min_cluster_size: smaller for <2K data, larger for big datasets
    if n < 500:
        l1_min = max(8, n // 30)
        l1_samples = 3
    elif n < 2000:
        l1_min = max(10, n // 40)
        l1_samples = 3
    else:
        l1_min = max(20, n // 20)
        l1_samples = 5
    logger.info("L1: min_cluster_size=%d, min_samples=%d (n=%d)", l1_min, l1_samples, n)

    l1_clusterer = hdbscan.HDBSCAN(
        min_cluster_size=l1_min, min_samples=l1_samples,
        metric="euclidean", cluster_selection_method="eom",
        prediction_data=True,
    )
    l1_labels = l1_clusterer.fit_predict(reduced)
    l1_labels = _recycle_noise(l1_labels, reduced, l1_clusterer, threshold=0.2)

    l1_ids = sorted(set(l1_labels) - {-1})
    l1_noise = int((l1_labels == -1).sum())
    logger.info("L1: %d themes, %d noise (%.0f%%)", len(l1_ids), l1_noise, l1_noise / n * 100)

    for cid in l1_ids:
        mask = l1_labels == cid
        results["level_1"][cid] = {
            "mention_indices": np.where(mask)[0].tolist(),
            "count": int(mask.sum()),
        }

    # Handle L1 noise as its own theme
    l1_noise_idx = np.where(l1_labels == -1)[0].tolist()
    if l1_noise_idx:
        noise_theme_id = max(l1_ids) + 1 if l1_ids else 0
        results["level_1"][noise_theme_id] = {
            "mention_indices": l1_noise_idx,
            "count": len(l1_noise_idx),
            "is_misc": True,
        }

    # ======================== LEVEL 2: Topics ========================
    l2_global = 0
    for l1_id, l1_data in results["level_1"].items():
        indices = l1_data["mention_indices"]

        if len(indices) < 15 or l1_data.get("is_misc"):
            results["level_2"][l2_global] = {
                "parent_theme": l1_id, "mention_indices": indices,
                "count": len(indices), "is_misc": l1_data.get("is_misc", False),
            }
            l2_global += 1
            continue

        l2_emb = reduced[indices]
        l2_min = max(8, len(indices) // 10)

        l2c = hdbscan.HDBSCAN(
            min_cluster_size=l2_min, min_samples=3,
            metric="euclidean", cluster_selection_method="eom",
            prediction_data=True,
        )
        l2_labels = l2c.fit_predict(l2_emb)
        l2_labels = _recycle_noise(l2_labels, l2_emb, l2c, threshold=0.25)

        for lid in sorted(set(l2_labels) - {-1}):
            local_idx = np.array(indices)[l2_labels == lid].tolist()
            results["level_2"][l2_global] = {
                "parent_theme": l1_id, "mention_indices": local_idx,
                "count": len(local_idx),
            }
            l2_global += 1

        # L2 noise
        l2_noise = np.array(indices)[l2_labels == -1].tolist()
        if l2_noise:
            results["level_2"][l2_global] = {
                "parent_theme": l1_id, "mention_indices": l2_noise,
                "count": len(l2_noise), "is_misc": True,
            }
            l2_global += 1

    logger.info("L2: %d topics", len(results["level_2"]))

    # ======================== LEVEL 3: Sub-topics ========================
    l3_global = 0
    for l2_id, l2_data in results["level_2"].items():
        indices = l2_data["mention_indices"]

        if len(indices) < 8 or l2_data.get("is_misc"):
            results["level_3"][l3_global] = {
                "parent_topic": l2_id, "parent_theme": l2_data["parent_theme"],
                "mention_indices": indices, "count": len(indices),
                "is_misc": l2_data.get("is_misc", False),
            }
            l3_global += 1
            continue

        l3_emb = reduced[indices]
        l3_min = max(4, len(indices) // 8)

        l3c = hdbscan.HDBSCAN(
            min_cluster_size=l3_min, min_samples=2,
            metric="euclidean", cluster_selection_method="leaf",
            prediction_data=True,
        )
        l3_labels = l3c.fit_predict(l3_emb)

        for lid in sorted(set(l3_labels) - {-1}):
            local_idx = np.array(indices)[l3_labels == lid].tolist()
            results["level_3"][l3_global] = {
                "parent_topic": l2_id, "parent_theme": l2_data["parent_theme"],
                "mention_indices": local_idx, "count": len(local_idx),
            }
            l3_global += 1

        l3_noise = np.array(indices)[l3_labels == -1].tolist()
        if l3_noise:
            results["level_3"][l3_global] = {
                "parent_topic": l2_id, "parent_theme": l2_data["parent_theme"],
                "mention_indices": l3_noise, "count": len(l3_noise),
                "is_misc": True,
            }
            l3_global += 1

    logger.info("L3: %d sub-topics", len(results["level_3"]))

    # Build mention assignments
    for l3_id, l3_data in results["level_3"].items():
        for idx in l3_data["mention_indices"]:
            results["mention_assignments"][idx] = {
                "theme_id": l3_data["parent_theme"],
                "topic_id": l3_data["parent_topic"],
                "subtopic_id": l3_id,
            }

    return results


def _recycle_noise(labels, embeddings, clusterer, threshold=0.25):
    noise_mask = labels == -1
    if noise_mask.sum() == 0:
        return labels
    refined = labels.copy()
    try:
        soft_labels, strengths = hdbscan.approximate_predict(clusterer, embeddings[noise_mask])
        noise_indices = np.where(noise_mask)[0]
        for i, (sl, st) in enumerate(zip(soft_labels, strengths)):
            if st > threshold:
                refined[noise_indices[i]] = sl
    except Exception:
        pass
    return refined
