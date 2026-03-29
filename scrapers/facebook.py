"""
Facebook scraper — Meta Graph API or Playwright fallback.

Owner: Esha (TBD)
"""

from __future__ import annotations

import logging
from typing import Any

from scrapers.base import BaseScraper
from search.engine import register_searcher
from search.filters import SearchParams

logger = logging.getLogger(__name__)


class FacebookScraper(BaseScraper):
    platform = "facebook"

    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        # TODO: Implement Facebook search via Graph API or Playwright
        logger.info("Facebook scraper not yet implemented")
        return []

    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        # TODO: Implement
        return []


_scraper = FacebookScraper()
register_searcher("facebook", _scraper.search)
