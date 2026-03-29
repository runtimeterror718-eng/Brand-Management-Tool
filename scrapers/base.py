"""
Shared scraper infrastructure: retry, exponential backoff, rate limiting, proxy rotation.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Any

from config.constants import (
    RATE_LIMITS,
    SCRAPER_BACKOFF_BASE,
    SCRAPER_MAX_RETRIES,
    SCRAPER_PROXY_ROTATION_AFTER,
    SCRAPER_REQUEST_TIMEOUT,
)
from config.settings import PROXY_URL
from search.filters import SearchParams

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket rate limiter per platform."""

    def __init__(self, rpm: int):
        self._interval = 60.0 / max(rpm, 1)
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            wait = self._interval - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()


class ProxyRotator:
    """Rotates proxy after N requests. Supports residential proxy URLs with session IDs."""

    def __init__(self, base_url: str, rotate_after: int = SCRAPER_PROXY_ROTATION_AFTER):
        self._base_url = base_url
        self._rotate_after = rotate_after
        self._request_count = 0
        self._session_id = self._new_session()

    @staticmethod
    def _new_session() -> str:
        return f"sess-{random.randint(100000, 999999)}"

    def get_proxy(self) -> str | None:
        if not self._base_url:
            return None
        self._request_count += 1
        if self._request_count >= self._rotate_after:
            self._session_id = self._new_session()
            self._request_count = 0
        # Append session to proxy URL for sticky-session rotation
        sep = "&" if "?" in self._base_url else "?"
        return f"{self._base_url}{sep}session={self._session_id}"

    def reset(self):
        self._request_count = 0
        self._session_id = self._new_session()


class BaseScraper(ABC):
    """Abstract base for all platform scrapers."""

    platform: str = ""

    def __init__(self):
        rpm = RATE_LIMITS.get(self.platform, 30)
        self.rate_limiter = RateLimiter(rpm)
        self.proxy = ProxyRotator(PROXY_URL)
        self.timeout = SCRAPER_REQUEST_TIMEOUT
        self.max_retries = SCRAPER_MAX_RETRIES
        self.backoff_base = SCRAPER_BACKOFF_BASE

    @abstractmethod
    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        """Search the platform for mentions matching params."""

    @abstractmethod
    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        """Scrape comments from a specific post/video."""

    async def _retry(self, coro_fn, *args, **kwargs):
        """Execute an async function with exponential backoff retry."""
        for attempt in range(1, self.max_retries + 1):
            try:
                await self.rate_limiter.acquire()
                return await coro_fn(*args, **kwargs)
            except Exception as exc:
                if attempt == self.max_retries:
                    logger.error(
                        "[%s] Failed after %d attempts: %s",
                        self.platform, self.max_retries, exc,
                    )
                    raise
                wait = self.backoff_base ** attempt + random.uniform(0, 1)
                logger.warning(
                    "[%s] Attempt %d failed (%s), retrying in %.1fs",
                    self.platform, attempt, exc, wait,
                )
                await asyncio.sleep(wait)
