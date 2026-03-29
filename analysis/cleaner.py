"""
Tier 1: Clean — dedup, spam removal, language detection, normalization.
Removes ~35% noise. FREE.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from storage.dedup import is_duplicate

logger = logging.getLogger(__name__)

# Lazy-loaded fastText model for language detection
_lang_model = None


def _get_lang_model():
    global _lang_model
    if _lang_model is None:
        import fasttext

        _lang_model = fasttext.load_model("lid.176.ftz")
    return _lang_model


def detect_language(text: str) -> str:
    """Detect language using fastText. Returns ISO 639-1 code."""
    try:
        model = _get_lang_model()
        predictions = model.predict(text.replace("\n", " ")[:500])
        label = predictions[0][0].replace("__label__", "")
        return label
    except Exception:
        return "en"


def normalize_text(text: str) -> str:
    """Basic text normalization."""
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove zero-width characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    # Normalize unicode quotes
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return text


def is_spam(text: str) -> bool:
    """Simple spam detection heuristics."""
    if not text or len(text.strip()) < 5:
        return True
    lower = text.lower()
    spam_signals = [
        lower.count("http") > 3,
        lower.count("subscribe") > 2,
        lower.count("follow me") > 1,
        len(set(text.split())) < 3 and len(text.split()) > 5,  # repetitive
        any(
            phrase in lower
            for phrase in [
                "check my profile",
                "dm for collab",
                "free followers",
                "earn money fast",
                "click the link",
            ]
        ),
    ]
    return sum(spam_signals) >= 2


def clean_batch(
    mentions: list[dict[str, Any]],
    allowed_languages: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Run Tier 1 cleaning on a batch of mentions.

    Steps: normalize → spam filter → language detect → dedup.
    Returns only clean mentions.
    """
    if allowed_languages is None:
        allowed_languages = ["en", "hi"]

    cleaned = []
    stats = {"total": len(mentions), "spam": 0, "lang_filtered": 0, "dedup": 0}

    for mention in mentions:
        text = mention.get("content_text", "")

        # Normalize
        text = normalize_text(text)
        mention["content_text"] = text

        # Spam filter
        if is_spam(text):
            stats["spam"] += 1
            continue

        # Language detection
        lang = detect_language(text)
        mention["language"] = lang
        if lang not in allowed_languages:
            stats["lang_filtered"] += 1
            continue

        # Dedup
        if is_duplicate(text, mention.get("id")):
            stats["dedup"] += 1
            continue

        cleaned.append(mention)

    logger.info(
        "Tier 1 cleaning: %d → %d (spam=%d, lang=%d, dedup=%d)",
        stats["total"],
        len(cleaned),
        stats["spam"],
        stats["lang_filtered"],
        stats["dedup"],
    )
    return cleaned
