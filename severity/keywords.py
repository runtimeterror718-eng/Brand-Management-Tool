"""
Brand-risk keyword lists — crisis words, competitor names, Hinglish slang.
"""

from __future__ import annotations

from typing import Any

from config.hinglish_lexicon import get_crisis_terms

# Default English crisis keywords
DEFAULT_CRISIS_KEYWORDS = [
    "scam", "fraud", "lawsuit", "scandal", "boycott", "recall", "data breach",
    "leak", "hack", "fired", "resignation", "investigation", "penalty", "fine",
    "controversy", "complaint", "warning", "ban", "illegal", "toxic", "unsafe",
    "death", "injury", "lawsuit", "class action", "SEC", "FTC", "FDA",
    "whistleblower", "cover-up", "corruption", "bankrupt", "layoff", "layoffs",
]

# Hinglish crisis terms (severity >= 0.6)
HINGLISH_CRISIS_KEYWORDS = get_crisis_terms()


def load_crisis_keywords(brand: dict[str, Any]) -> list[str]:
    """
    Load crisis keywords for a brand.
    Combines: English defaults + Hinglish crisis terms + competitor names.
    """
    keywords = list(DEFAULT_CRISIS_KEYWORDS)
    keywords.extend(HINGLISH_CRISIS_KEYWORDS)

    # Add competitor names as risk keywords
    competitors = brand.get("competitors", [])
    keywords.extend([c.lower() for c in competitors])

    return keywords


def count_keyword_hits(text: str, keywords: list[str]) -> int:
    """Count how many crisis keywords appear in the text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)
