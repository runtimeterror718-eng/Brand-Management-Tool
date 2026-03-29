"""
Tier 2: Sentiment analysis using XLM-RoBERTa (multilingual).
NOT VADER. NOT TextBlob.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline

        logger.info("Loading XLM-RoBERTa sentiment model...")
        _pipeline = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual",
            top_k=None,
            truncation=True,
            max_length=512,
        )
    return _pipeline


def _label_to_score(outputs: list[dict]) -> tuple[float, str]:
    """Convert model output to a score [-1, 1] and label."""
    score_map = {}
    for item in outputs:
        label = item["label"].lower()
        score_map[label] = item["score"]

    positive = score_map.get("positive", 0)
    negative = score_map.get("negative", 0)
    neutral = score_map.get("neutral", 0)

    # Composite score: [-1, 1]
    composite = positive - negative

    if positive > negative and positive > neutral:
        label = "positive"
    elif negative > positive and negative > neutral:
        label = "negative"
    else:
        label = "neutral"

    return round(composite, 4), label


def analyze_sentiment(text: str) -> dict[str, Any]:
    """Analyze sentiment for a single text."""
    if not text or not text.strip():
        return {"score": 0.0, "label": "neutral", "raw": []}

    pipe = _get_pipeline()
    outputs = pipe(text[:512])[0]
    score, label = _label_to_score(outputs)

    return {"score": score, "label": label, "raw": outputs}


def analyze_batch(texts: list[str], batch_size: int = 32) -> list[dict[str, Any]]:
    """Analyze sentiment for a batch of texts."""
    if not texts:
        return []

    pipe = _get_pipeline()
    results = []

    # Process in chunks
    for i in range(0, len(texts), batch_size):
        chunk = [t[:512] if t else "" for t in texts[i : i + batch_size]]
        outputs = pipe(chunk)
        for output in outputs:
            score, label = _label_to_score(output)
            results.append({"score": score, "label": label, "raw": output})

    return results
