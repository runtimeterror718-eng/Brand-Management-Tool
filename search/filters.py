"""
Parse and validate search parameters from user input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from config.constants import FULFILLMENT_DEFAULT_LANGUAGES, PLATFORMS


@dataclass
class SearchParams:
    """Validated search parameters for multi-platform search."""

    keywords: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=lambda: list(PLATFORMS))
    min_likes: int = 0
    min_shares: int = 0
    min_comments: int = 0
    after_date: datetime | None = None
    before_date: datetime | None = None
    languages: list[str] = field(
        default_factory=lambda: list(FULFILLMENT_DEFAULT_LANGUAGES)
    )
    brand_id: str | None = None
    max_results_per_platform: int = 100

    def __post_init__(self):
        # Normalize hashtags
        self.hashtags = [
            h if h.startswith("#") else f"#{h}" for h in self.hashtags
        ]
        # Validate platforms
        self.platforms = [p for p in self.platforms if p in PLATFORMS]
        if not self.platforms:
            self.platforms = list(PLATFORMS)


def build_search_params(raw: dict) -> SearchParams:
    """Build a SearchParams from a raw dict (e.g. from API request)."""
    after = raw.get("after_date")
    before = raw.get("before_date")

    return SearchParams(
        keywords=raw.get("keywords", []),
        hashtags=raw.get("hashtags", []),
        platforms=raw.get("platforms", list(PLATFORMS)),
        min_likes=int(raw.get("min_likes", 0)),
        min_shares=int(raw.get("min_shares", 0)),
        min_comments=int(raw.get("min_comments", 0)),
        after_date=datetime.fromisoformat(after) if isinstance(after, str) else after,
        before_date=datetime.fromisoformat(before) if isinstance(before, str) else before,
        languages=raw.get("languages", list(FULFILLMENT_DEFAULT_LANGUAGES)),
        brand_id=raw.get("brand_id"),
        max_results_per_platform=int(raw.get("max_results_per_platform", 100)),
    )
