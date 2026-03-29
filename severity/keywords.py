"""
Brand-risk keyword lists — crisis words, competitor names, etc.
"""

from __future__ import annotations

from typing import Any

# Default crisis keywords (augmented per-brand)
DEFAULT_CRISIS_KEYWORDS = [
    "scam", "fraud", "lawsuit", "scandal", "boycott", "recall", "data breach",
    "leak", "hack", "fired", "resignation", "investigation", "penalty", "fine",
    "controversy", "complaint", "warning", "ban", "illegal", "toxic", "unsafe",
    "death", "injury", "lawsuit", "class action", "SEC", "FTC", "FDA",
    "whistleblower", "cover-up", "corruption", "bankrupt", "layoff", "layoffs",
]


def load_crisis_keywords(brand: dict[str, Any]) -> list[str]:
    """
    Load crisis keywords for a brand.
    Combines default crisis words + competitor names.
    """
    keywords = list(DEFAULT_CRISIS_KEYWORDS)

    # Add competitor names as risk keywords
    competitors = brand.get("competitors", [])
    keywords.extend([c.lower() for c in competitors])

    return keywords


def count_keyword_hits(text: str, keywords: list[str]) -> int:
    """Count how many crisis keywords appear in the text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw in text_lower)
