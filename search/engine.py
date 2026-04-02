"""
Step 1: Multi-platform search engine.

Takes user input (keywords, filters) and dispatches searches across platforms.
Results go through fulfillment before being queued for scraping/transcription.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from typing import Any

from search.filters import SearchParams, build_search_params
from search.fulfillment import check_fulfillment
from storage import queries as db
from storage.models import Mention, FulfillmentResult

logger = logging.getLogger(__name__)

# Registry of platform search functions — populated by scrapers on import
_platform_searchers: dict[str, Any] = {}
_SEARCHER_MODULES: dict[str, str] = {
    "youtube": "scrapers.youtube",
    "telegram": "scrapers.telegram",
    "instagram": "scrapers.instagram",
    "reddit": "scrapers.reddit",
    "twitter": "scrapers.twitter",
    "facebook": "scrapers.facebook",
    "linkedin": "scrapers.linkedin",
    "seo_news": "scrapers.seo_news",
}
_loaded_searcher_modules: set[str] = set()


def register_searcher(platform: str, search_fn):
    """Register a platform-specific search function.

    Each search_fn signature: async def search(params: SearchParams) -> list[dict]
    """
    _platform_searchers[platform] = search_fn


def ensure_searchers_loaded(platforms: list[str] | None = None) -> None:
    """
    Deterministically import scraper modules so register_searcher side effects run.

    Safe to call multiple times.
    """
    requested_platforms = platforms or list(_SEARCHER_MODULES.keys())
    for platform in requested_platforms:
        module_path = _SEARCHER_MODULES.get(platform)
        if not module_path:
            continue
        if module_path in _loaded_searcher_modules:
            continue
        try:
            importlib.import_module(module_path)
            _loaded_searcher_modules.add(module_path)
            if platform not in _platform_searchers:
                logger.warning(
                    "Searcher bootstrap loaded %s but platform %s was not registered",
                    module_path,
                    platform,
                )
        except Exception:
            logger.exception(
                "Searcher bootstrap failed for platform %s via %s",
                platform,
                module_path,
            )


async def search_platform(
    platform: str, params: SearchParams
) -> list[dict]:
    """Run search on a single platform."""
    searcher = _platform_searchers.get(platform)
    if searcher is None:
        logger.warning("No searcher registered for platform: %s", platform)
        return []
    try:
        results = await searcher(params)
        return results[: params.max_results_per_platform]
    except Exception:
        logger.exception("Search failed for %s", platform)
        return []


async def search_all(params: SearchParams) -> dict[str, list[dict]]:
    """Search all requested platforms concurrently."""
    ensure_searchers_loaded(params.platforms)
    tasks = {
        platform: search_platform(platform, params)
        for platform in params.platforms
        if platform in _platform_searchers
    }
    results: dict[str, list[dict]] = {}
    gathered = await asyncio.gather(
        *tasks.values(), return_exceptions=True
    )
    for platform, result in zip(tasks.keys(), gathered):
        if isinstance(result, Exception):
            logger.error("Platform %s raised %s", platform, result)
            results[platform] = []
        else:
            results[platform] = result
    return results


async def search_and_fulfill(
    raw_params: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Full Step 1 + Step 2: search all platforms, run fulfillment, persist results.

    Returns list of fulfilled results ready for scraping/transcription queues.
    """
    params = build_search_params(raw_params)
    ensure_searchers_loaded(params.platforms)
    all_results = await search_all(params)

    fulfilled = []
    for platform, results in all_results.items():
        for result in results:
            result.setdefault("platform", platform)
            outcome = check_fulfillment(raw_params, result)

            # Persist the mention
            mention_data = {
                "brand_id": params.brand_id,
                "platform": platform,
                "content_text": result.get("content_text", ""),
                "content_type": result.get("content_type", "text"),
                "author_handle": result.get("author_handle", ""),
                "author_name": result.get("author_name", ""),
                "engagement_score": result.get("engagement_score", 0),
                "likes": result.get("likes", 0),
                "shares": result.get("shares", 0),
                "comments_count": result.get("comments_count", 0),
                "language": result.get("language"),
                "source_url": result.get("source_url", ""),
                "published_at": result.get("published_at"),
                "raw_data": result,
            }

            try:
                mention = db.insert_mention(mention_data)
                mention_id = mention.get("id")
            except Exception:
                logger.exception("Failed to persist mention")
                continue

            # Persist fulfillment result
            fulfillment_data = {
                "search_query": raw_params,
                "mention_id": mention_id,
                "passed": outcome["passed"],
                "score": outcome["score"],
                "criteria_met": outcome["criteria_met"],
                "queued_for_scraping": outcome["queued_for_scraping"],
                "queued_for_transcription": outcome["queued_for_transcription"],
            }
            try:
                db.insert_fulfillment_result(fulfillment_data)
            except Exception:
                logger.exception("Failed to persist fulfillment result")

            if outcome["passed"]:
                outcome["mention_id"] = mention_id
                outcome["platform"] = platform
                outcome["result"] = result
                fulfilled.append(outcome)

    logger.info(
        "Search complete: %d total results, %d passed fulfillment",
        sum(len(r) for r in all_results.values()),
        len(fulfilled),
    )
    return fulfilled
