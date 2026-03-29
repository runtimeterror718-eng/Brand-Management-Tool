"""
Instagram scraper — Playwright + stealth + residential proxies.

Owner: Abhishek
Risk: ML fingerprinting, account bans — use burner accounts only.
"""

from __future__ import annotations

import logging
from typing import Any

from scrapers.base import BaseScraper
from search.engine import register_searcher
from search.filters import SearchParams

logger = logging.getLogger(__name__)


class InstagramScraper(BaseScraper):
    platform = "instagram"

    def __init__(self):
        super().__init__()
        self._browser = None
        self._context = None

    async def _get_context(self):
        if self._context is None:
            from playwright.async_api import async_playwright
            from playwright_stealth import stealth_async

            pw = await async_playwright().start()
            proxy_url = self.proxy.get_proxy()
            launch_opts = {"headless": True}
            if proxy_url:
                launch_opts["proxy"] = {"server": proxy_url}

            self._browser = await pw.chromium.launch(**launch_opts)
            self._context = await self._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/16.0 Mobile/15E148 Safari/604.1"
                ),
                viewport={"width": 390, "height": 844},
                locale="en-US",
            )
            page = await self._context.new_page()
            await stealth_async(page)
        return self._context

    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        """Search Instagram via hashtag/explore pages."""
        context = await self._get_context()
        results = []

        for tag in params.hashtags + params.keywords:
            tag_clean = tag.lstrip("#")
            page = await context.new_page()
            try:
                await page.goto(
                    f"https://www.instagram.com/explore/tags/{tag_clean}/",
                    timeout=self.timeout * 1000,
                )
                await page.wait_for_timeout(3000)

                # Extract post links from the tag page
                posts = await page.query_selector_all("article a[href*='/p/']")
                for post in posts[: params.max_results_per_platform]:
                    href = await post.get_attribute("href")
                    if href:
                        results.append({
                            "content_text": "",
                            "content_type": "reel",
                            "source_url": f"https://www.instagram.com{href}",
                            "engagement_score": 0,
                            "likes": 0,
                            "comments_count": 0,
                            "author_handle": "",
                            "published_at": None,
                            "language": "en",
                            "raw_data": {"tag": tag_clean, "href": href},
                        })
            except Exception:
                logger.exception("Instagram search failed for tag: %s", tag_clean)
            finally:
                await page.close()

        return results

    async def scrape_post(self, post_url: str) -> dict[str, Any]:
        """Scrape a single Instagram post for full details."""
        context = await self._get_context()
        page = await context.new_page()
        data: dict[str, Any] = {}

        try:
            await page.goto(post_url, timeout=self.timeout * 1000)
            await page.wait_for_timeout(3000)

            # Extract caption
            caption_el = await page.query_selector("h1[dir='auto']")
            if caption_el:
                data["content_text"] = await caption_el.text_content() or ""

            # Extract likes
            likes_el = await page.query_selector("section span span")
            if likes_el:
                likes_text = await likes_el.text_content() or "0"
                data["likes"] = int(likes_text.replace(",", "")) if likes_text.isdigit() else 0

        except Exception:
            logger.exception("Instagram post scrape failed: %s", post_url)
        finally:
            await page.close()

        return data

    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        """Scrape comments from an Instagram post."""
        context = await self._get_context()
        page = await context.new_page()
        comments = []

        try:
            await page.goto(source_url, timeout=self.timeout * 1000)
            await page.wait_for_timeout(3000)

            comment_els = await page.query_selector_all("ul li div span[dir='auto']")
            for el in comment_els[:limit]:
                text = await el.text_content()
                if text:
                    comments.append({
                        "text": text,
                        "author": "",
                        "likes": 0,
                    })
        except Exception:
            logger.exception("Instagram comment scrape failed: %s", source_url)
        finally:
            await page.close()

        return comments

    async def close(self):
        if self._browser:
            await self._browser.close()


_scraper = InstagramScraper()
register_searcher("instagram", _scraper.search)
