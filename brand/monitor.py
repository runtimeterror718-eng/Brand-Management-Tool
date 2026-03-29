"""
Brand monitoring — which brands to track, on which platforms.
"""

from __future__ import annotations

import logging
from typing import Any

from storage import queries as db
from config.settings import MONITORED_BRANDS

logger = logging.getLogger(__name__)


def get_monitored_brands() -> list[dict[str, Any]]:
    """Return all brands being actively monitored."""
    brands = db.get_all_brands()
    if not brands:
        # Auto-create from env if DB is empty
        for name in MONITORED_BRANDS:
            if name:
                try:
                    db.upsert_brand({
                        "name": name,
                        "keywords": [name.lower()],
                        "platforms": [
                            "youtube", "telegram", "instagram", "reddit",
                            "twitter", "seo_news",
                        ],
                    })
                except Exception:
                    logger.exception("Failed to create brand: %s", name)
        brands = db.get_all_brands()
    return brands


def add_brand(
    name: str,
    keywords: list[str] | None = None,
    hashtags: list[str] | None = None,
    platforms: list[str] | None = None,
    competitors: list[str] | None = None,
) -> dict[str, Any]:
    """Add a new brand to monitor."""
    brand_data = {
        "name": name,
        "keywords": keywords or [name.lower()],
        "hashtags": hashtags or [],
        "platforms": platforms or ["youtube", "reddit", "twitter", "instagram", "seo_news"],
        "competitors": competitors or [],
    }
    return db.upsert_brand(brand_data)


def update_brand(brand_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update brand configuration."""
    return db.upsert_brand({"id": brand_id, **updates})
