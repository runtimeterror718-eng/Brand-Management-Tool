"""
Reddit scraper — PRAW (Python Reddit API Wrapper).

Owner: Abhishek
Auth: Reddit app credentials (free) | Rate: 60 req/min
"""

from __future__ import annotations

import logging
from typing import Any

import praw

from scrapers.base import BaseScraper
from search.engine import register_searcher
from search.filters import SearchParams
from config.settings import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

logger = logging.getLogger(__name__)


def _get_reddit() -> praw.Reddit:
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )


class RedditScraper(BaseScraper):
    platform = "reddit"

    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        """Search Reddit for posts matching keywords."""
        import asyncio

        reddit = _get_reddit()
        query = " ".join(params.keywords)
        results = []

        def _search():
            for submission in reddit.subreddit("all").search(
                query, limit=params.max_results_per_platform, sort="relevance"
            ):
                results.append({
                    "content_text": f"{submission.title}\n{submission.selftext}",
                    "content_type": "text",
                    "author_handle": str(submission.author) if submission.author else "[deleted]",
                    "author_name": str(submission.author) if submission.author else "[deleted]",
                    "engagement_score": submission.score,
                    "likes": submission.score,
                    "shares": 0,
                    "comments_count": submission.num_comments,
                    "source_url": f"https://reddit.com{submission.permalink}",
                    "published_at": __import__("datetime").datetime.utcfromtimestamp(
                        submission.created_utc
                    ).isoformat(),
                    "language": "en",
                    "raw_data": {
                        "subreddit": str(submission.subreddit),
                        "id": submission.id,
                        "upvote_ratio": submission.upvote_ratio,
                    },
                })

        await asyncio.get_event_loop().run_in_executor(None, _search)
        return results

    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        """Scrape comments from a Reddit post."""
        import asyncio

        reddit = _get_reddit()
        comments = []

        def _scrape():
            submission = reddit.submission(url=source_url)
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list()[:limit]:
                if comment.body and comment.body != "[deleted]":
                    comments.append({
                        "text": comment.body,
                        "author": str(comment.author) if comment.author else "[deleted]",
                        "likes": comment.score,
                        "published_at": __import__("datetime").datetime.utcfromtimestamp(
                            comment.created_utc
                        ).isoformat(),
                    })

        await asyncio.get_event_loop().run_in_executor(None, _scrape)
        return comments


_scraper = RedditScraper()
register_searcher("reddit", _scraper.search)
