"""
Telegram scraper — search channels/groups, real-time listener.

Owner: Esha
Libraries: Telethon (MTProto)
"""

from __future__ import annotations

import logging
from typing import Any

from scrapers.base import BaseScraper
from search.engine import register_searcher
from search.filters import SearchParams
from config.settings import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE

logger = logging.getLogger(__name__)


class TelegramScraper(BaseScraper):
    platform = "telegram"

    def __init__(self):
        super().__init__()
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from telethon import TelegramClient

            self._client = TelegramClient(
                "brand_tool_session",
                int(TELEGRAM_API_ID),
                TELEGRAM_API_HASH,
            )
            await self._client.start(phone=TELEGRAM_PHONE)
        return self._client

    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        """Search Telegram channels/groups for keyword mentions."""
        client = await self._get_client()
        query = " ".join(params.keywords)
        results = []

        try:
            from telethon.tl.functions.contacts import SearchRequest

            search_result = await self._retry(
                client, SearchRequest, q=query, limit=params.max_results_per_platform
            )
            # Search across found chats for messages
            for chat in getattr(search_result, "chats", []):
                async for message in client.iter_messages(
                    chat, limit=20, search=query
                ):
                    if message.text:
                        results.append({
                            "content_text": message.text,
                            "content_type": "voice" if message.voice else "text",
                            "author_handle": str(message.sender_id or ""),
                            "author_name": "",
                            "engagement_score": message.views or 0,
                            "likes": getattr(message, "forwards", 0) or 0,
                            "shares": getattr(message, "forwards", 0) or 0,
                            "comments_count": message.replies.replies if message.replies else 0,
                            "source_url": "",
                            "published_at": message.date.isoformat() if message.date else None,
                            "language": "en",
                            "raw_data": {"chat_id": chat.id, "message_id": message.id},
                        })
        except Exception:
            logger.exception("Telegram search failed")

        return results

    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        """Scrape replies to a Telegram message."""
        # Telegram comments = replies in groups/channels
        return []

    async def listen_realtime(self, channel_ids: list[int], callback):
        """Real-time event handler for new messages in monitored channels."""
        client = await self._get_client()
        from telethon import events

        @client.on(events.NewMessage(chats=channel_ids))
        async def handler(event):
            await callback({
                "content_text": event.text or "",
                "content_type": "voice" if event.voice else "text",
                "author_handle": str(event.sender_id or ""),
                "source_url": "",
                "published_at": event.date.isoformat() if event.date else None,
                "raw_data": {"chat_id": event.chat_id, "message_id": event.id},
            })

        logger.info("Listening to %d Telegram channels", len(channel_ids))
        await client.run_until_disconnected()


_scraper = TelegramScraper()
register_searcher("telegram", _scraper.search)
