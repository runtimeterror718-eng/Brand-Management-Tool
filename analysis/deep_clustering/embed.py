"""
Stage 3: Composite Embedding — text (70%) + metadata features (30%).
Uses multilingual MiniLM for Hinglish/Hindi support.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sklearn.preprocessing import StandardScaler

from analysis.deep_clustering.ingest import NormalizedMention

logger = logging.getLogger(__name__)

_model = None

INTENT_CATS = ["complaint", "praise", "question", "comparison", "suggestion",
               "experience_sharing", "news_reaction", "humor_sarcasm", "unknown"]
EMOTION_CATS = ["anger", "frustration", "disappointment", "satisfaction", "excitement",
                "confusion", "indifference", "sarcasm", "trust", "fear"]
SPECIFICITY_CATS = ["general_brand", "specific_product", "specific_person",
                    "specific_event", "specific_feature"]
URGENCY_CATS = ["low", "medium", "high", "crisis"]
SEGMENT_CATS = ["current_student", "prospective_student", "parent", "ex_student",
                "competitor_employee", "general_public", "educator", "investor"]
PLATFORM_CATS = ["reddit", "youtube", "instagram", "telegram", "twitter", "facebook"]


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading multilingual MiniLM for deep clustering...")
        _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _model


def create_composite_embeddings(
    mentions: list[NormalizedMention],
    enrichments: list[dict[str, Any]],
    text_weight: float = 0.70,
    metadata_weight: float = 0.30,
) -> np.ndarray:
    """
    Composite embedding = weighted(text) + weighted(metadata features).
    Metadata ensures a complaint about pricing clusters separately from a question about pricing.
    """
    model = _get_model()

    # --- Text embeddings ---
    texts = [m.content[:512] for m in mentions]
    logger.info("Embedding %d texts...", len(texts))
    text_embeddings = model.encode(texts, batch_size=128, normalize_embeddings=True, show_progress_bar=True)

    # --- Metadata feature vectors ---
    metadata_vectors = []
    for e, m in zip(enrichments, mentions):
        features: list[float] = []

        # One-hot categoricals
        for val, cats in [
            (e.get("intent", "unknown"), INTENT_CATS),
            (e.get("emotion", "indifference"), EMOTION_CATS),
            (e.get("specificity", "general_brand"), SPECIFICITY_CATS),
            (e.get("urgency", "low"), URGENCY_CATS),
            (e.get("user_segment", "general_public"), SEGMENT_CATS),
            (m.platform, PLATFORM_CATS),
        ]:
            features.extend(1.0 if val == c else 0.0 for c in cats)

        # Binary features
        features.append(1.0 if e.get("competitor_mentioned") else 0.0)
        features.append(1.0 if e.get("is_actionable") else 0.0)
        features.append(1.0 if e.get("complaint_category") else 0.0)

        # Numeric features
        features.append(float(m.engagement_score))

        metadata_vectors.append(features)

    metadata_array = np.array(metadata_vectors, dtype=np.float64)

    # Normalize
    scaler = StandardScaler()
    metadata_normalized = scaler.fit_transform(metadata_array)

    # Unit-norm both
    text_norms = np.linalg.norm(text_embeddings, axis=1, keepdims=True)
    text_unit = text_embeddings / np.maximum(text_norms, 1e-10)

    meta_norms = np.linalg.norm(metadata_normalized, axis=1, keepdims=True)
    meta_unit = metadata_normalized / np.maximum(meta_norms, 1e-10)

    composite = np.hstack([text_unit * text_weight, meta_unit * metadata_weight])

    logger.info("Composite embedding: %d dims (text: %d, metadata: %d)",
                composite.shape[1], text_embeddings.shape[1], metadata_array.shape[1])
    return composite


def create_composite_embeddings_with_text(
    mentions: list[NormalizedMention],
    enrichments: list[dict[str, Any]],
    text_weight: float = 0.70,
    metadata_weight: float = 0.30,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Same as create_composite_embeddings but also returns the raw text embeddings (384d)
    for storage in pgvector.
    Returns (composite_embeddings, text_only_embeddings).
    """
    model = _get_model()

    texts = [m.content[:512] for m in mentions]
    logger.info("Embedding %d texts (with text-only return)...", len(texts))
    text_embeddings = model.encode(texts, batch_size=128, normalize_embeddings=True, show_progress_bar=True)

    metadata_vectors = []
    for e, m in zip(enrichments, mentions):
        features: list[float] = []
        for val, cats in [
            (e.get("intent", "unknown"), INTENT_CATS),
            (e.get("emotion", "indifference"), EMOTION_CATS),
            (e.get("specificity", "general_brand"), SPECIFICITY_CATS),
            (e.get("urgency", "low"), URGENCY_CATS),
            (e.get("user_segment", "general_public"), SEGMENT_CATS),
            (m.platform, PLATFORM_CATS),
        ]:
            features.extend(1.0 if val == c else 0.0 for c in cats)
        features.append(1.0 if e.get("competitor_mentioned") else 0.0)
        features.append(1.0 if e.get("is_actionable") else 0.0)
        features.append(1.0 if e.get("complaint_category") else 0.0)
        features.append(float(m.engagement_score))
        metadata_vectors.append(features)

    metadata_array = np.array(metadata_vectors, dtype=np.float64)
    scaler = StandardScaler()
    metadata_normalized = scaler.fit_transform(metadata_array)

    text_norms = np.linalg.norm(text_embeddings, axis=1, keepdims=True)
    text_unit = text_embeddings / np.maximum(text_norms, 1e-10)
    meta_norms = np.linalg.norm(metadata_normalized, axis=1, keepdims=True)
    meta_unit = metadata_normalized / np.maximum(meta_norms, 1e-10)

    composite = np.hstack([text_unit * text_weight, meta_unit * metadata_weight])

    return composite, text_embeddings
