"""
YouTube scraper — search, comments, transcripts.

Owner: Esha
Libraries: yt-dlp, youtube-comment-downloader, youtube-transcript-api
"""

from __future__ import annotations

import logging
from typing import Any

from scrapers.base import BaseScraper
from search.engine import register_searcher
from search.filters import SearchParams

logger = logging.getLogger(__name__)


class YouTubeScraper(BaseScraper):
    platform = "youtube"

    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        """Search YouTube for videos matching keywords."""
        import yt_dlp

        query = " ".join(params.keywords + params.hashtags)
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "default_search": f"ytsearch{params.max_results_per_platform}",
        }

        results = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await self._retry(
                    lambda: __import__("asyncio").get_event_loop().run_in_executor(
                        None, ydl.extract_info, query, False
                    )
                )
                for entry in (info or {}).get("entries", []):
                    if not entry:
                        continue
                    results.append({
                        "content_text": entry.get("title", ""),
                        "content_type": "video",
                        "author_handle": entry.get("uploader_id", ""),
                        "author_name": entry.get("uploader", ""),
                        "engagement_score": entry.get("view_count", 0),
                        "likes": entry.get("like_count", 0),
                        "comments_count": entry.get("comment_count", 0),
                        "source_url": f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                        "published_at": entry.get("upload_date"),
                        "language": "en",
                        "raw_data": entry,
                    })
        except Exception:
            logger.exception("YouTube search failed for query: %s", query)

        return results

    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        """Scrape comments from a YouTube video."""
        from youtube_comment_downloader import YoutubeCommentDownloader

        downloader = YoutubeCommentDownloader()
        comments = []
        try:
            for comment in downloader.get_comments_from_url(source_url, sort_by=0):
                comments.append({
                    "text": comment.get("text", ""),
                    "author": comment.get("author", ""),
                    "likes": comment.get("votes", 0),
                    "published_at": comment.get("time", ""),
                })
                if len(comments) >= limit:
                    break
        except Exception:
            logger.exception("YouTube comment scraping failed: %s", source_url)

        return comments

    async def get_transcript(self, video_id: str) -> str | None:
        """Get transcript using youtube-transcript-api (free, no Whisper)."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join(seg["text"] for seg in transcript_list)
        except Exception:
            logger.warning("No transcript available for %s", video_id)
            return None


# Instantiate and register
_scraper = YouTubeScraper()
register_searcher("youtube", _scraper.search)
