"""
X / Twitter scraper — twikit.

Owner: Abhishek
Auth: Username/password → cookies | Proxy: Datacenter (guest) / Residential (auth)
"""

from __future__ import annotations

import logging
from typing import Any

from scrapers.base import BaseScraper
from search.engine import register_searcher
from search.filters import SearchParams
from config.settings import TWITTER_USERNAME, TWITTER_PASSWORD

logger = logging.getLogger(__name__)


class TwitterScraper(BaseScraper):
    platform = "twitter"

    def __init__(self):
        super().__init__()
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from twikit import Client

            self._client = Client("en-US")
            await self._client.login(
                auth_info_1=TWITTER_USERNAME,
                password=TWITTER_PASSWORD,
            )
        return self._client

    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        """Search X/Twitter for tweets matching keywords."""
        client = await self._get_client()
        query = " ".join(params.keywords + params.hashtags)
        results = []

        try:
            tweets = await self._retry(client.search_tweet, query, "Latest")
            for tweet in tweets:
                results.append({
                    "content_text": tweet.text or "",
                    "content_type": "text",
                    "author_handle": tweet.user.screen_name if tweet.user else "",
                    "author_name": tweet.user.name if tweet.user else "",
                    "engagement_score": (tweet.favorite_count or 0) + (tweet.retweet_count or 0),
                    "likes": tweet.favorite_count or 0,
                    "shares": tweet.retweet_count or 0,
                    "comments_count": tweet.reply_count or 0,
                    "source_url": f"https://x.com/{tweet.user.screen_name}/status/{tweet.id}"
                    if tweet.user
                    else "",
                    "published_at": tweet.created_at,
                    "language": tweet.lang or "en",
                    "raw_data": {"tweet_id": tweet.id},
                })
                if len(results) >= params.max_results_per_platform:
                    break
        except Exception:
            logger.exception("Twitter search failed")

        return results

    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        """Scrape replies to a tweet (limited by API)."""
        # twikit has limited reply support
        return []


_scraper = TwitterScraper()
register_searcher("twitter", _scraper.search)
