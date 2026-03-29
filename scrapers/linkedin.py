"""
LinkedIn scraper — Proxycurl API recommended.

Owner: Esha (TBD)
Risk: LinkedIn sends legal letters for direct scraping.
"""

from __future__ import annotations

import logging
from typing import Any

from scrapers.base import BaseScraper
from search.engine import register_searcher
from search.filters import SearchParams

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    platform = "linkedin"

    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        # TODO: Implement LinkedIn search via Proxycurl API
        logger.info("LinkedIn scraper not yet implemented")
        return []

    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        # TODO: Implement
        return []


_scraper = LinkedInScraper()
register_searcher("linkedin", _scraper.search)
