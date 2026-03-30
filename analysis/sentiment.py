"""
Tier 2: Sentiment analysis using XLM-RoBERTa (multilingual).
Augmented with Hinglish lexicon for Indian social media.
NOT VADER. NOT TextBlob.
"""

from __future__ import annotations

import logging
from typing import Any

from config.hinglish_lexicon import compute_hinglish_sentiment, is_hinglish

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
    """Analyze sentiment for a single text. Augments with Hinglish lexicon when detected."""
    if not text or not text.strip():
        return {"score": 0.0, "label": "neutral", "raw": [], "hinglish_terms": []}

    pipe = _get_pipeline()
    outputs = pipe(text[:512])[0]
    score, label = _label_to_score(outputs)

    # Augment with Hinglish lexicon for Indian social media content
    hinglish_terms = []
    if is_hinglish(text):
        hl_score, hinglish_terms = compute_hinglish_sentiment(text)
        if hinglish_terms:
            # Blend: 60% XLM-RoBERTa + 40% lexicon (lexicon catches slang the model misses)
            score = round(score * 0.6 + hl_score * 0.4, 4)
            # Re-derive label from blended score
            if score > 0.1:
                label = "positive"
            elif score < -0.1:
                label = "negative"
            else:
                label = "neutral"

    return {"score": score, "label": label, "raw": outputs, "hinglish_terms": hinglish_terms}


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
        for j, output in enumerate(outputs):
            score, label = _label_to_score(output)
            text = chunk[j]
            hinglish_terms = []
            if is_hinglish(text):
                hl_score, hinglish_terms = compute_hinglish_sentiment(text)
                if hinglish_terms:
                    score = round(score * 0.6 + hl_score * 0.4, 4)
                    if score > 0.1:
                        label = "positive"
                    elif score < -0.1:
                        label = "negative"
                    else:
                        label = "neutral"
            results.append({"score": score, "label": label, "raw": output, "hinglish_terms": hinglish_terms})

    return results
