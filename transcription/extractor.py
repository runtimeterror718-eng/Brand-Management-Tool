"""
Audio/video downloader for transcription pipeline.

Downloads audio tracks from YouTube, Instagram, Facebook, Telegram.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from config.settings import (
    YOUTUBE_TRANSCRIPT_APIFY_ACTOR_ID,
    YOUTUBE_TRANSCRIPT_APIFY_KEY,
    YOUTUBE_TRANSCRIPT_APIFY_MAX_RETRIES,
    YOUTUBE_TRANSCRIPT_APIFY_PROXY_GROUP,
)

logger = logging.getLogger(__name__)


async def download_audio(source_url: str, platform: str) -> Path | None:
    """
    Download audio from a video/audio URL.

    Returns path to a temporary .wav file, or None on failure.
    """
    import asyncio

    if platform == "youtube":
        return await _download_youtube_audio(source_url)
    elif platform in ("instagram", "facebook"):
        return await _download_playwright_audio(source_url)
    elif platform == "telegram":
        # Telegram voice messages are handled via Telethon directly
        return None
    else:
        logger.warning("No audio extractor for platform: %s", platform)
        return None


def _extract_video_id_from_url(url: str) -> str:
    value = (url or "").strip()
    if "watch?v=" in value:
        return value.split("watch?v=", 1)[1].split("&", 1)[0]
    if "youtu.be/" in value:
        return value.split("youtu.be/", 1)[1].split("?", 1)[0]
    return ""


def _build_transcript_from_apify_item(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {"text": "", "language": "", "segments": [], "duration": 0}

    segments: list[dict[str, Any]] = []
    raw_captions = item.get("captions")
    if isinstance(raw_captions, list):
        for seg in raw_captions:
            if isinstance(seg, str):
                text_line = seg.strip()
                if not text_line:
                    continue
                # Actor often returns captions as plain text lines without timing.
                segments.append({"text": text_line})
                continue
            if not isinstance(seg, dict):
                continue
            text = str(seg.get("text") or seg.get("caption") or "").strip()
            if not text:
                continue
            segments.append(seg)

    text = ""
    if segments:
        text = " ".join(str(seg.get("text") or seg.get("caption") or "").strip() for seg in segments).strip()
    if not text:
        text = str(item.get("transcript") or item.get("captionsText") or item.get("subtitleText") or "").strip()

    language = str(
        item.get("language")
        or item.get("languageCode")
        or item.get("captionsLanguage")
        or ""
    ).strip()

    duration = 0
    if segments:
        try:
            last = segments[-1]
            duration = int(float(last.get("start", 0)) + float(last.get("duration", 0)))
        except (TypeError, ValueError):
            duration = 0

    return {
        "text": text,
        "language": language,
        "segments": segments,
        "duration": duration,
    }


def get_apify_transcripts_batch(video_urls: list[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """
    Fetch transcripts from Apify YouTube actor in one synchronous batch.

    Returns:
      (transcripts_by_video_id, run_metadata)
    """
    cleaned_urls = [str(url).strip() for url in (video_urls or []) if str(url).strip()]
    if not cleaned_urls:
        return {}, {
            "status": "noop",
            "requested_urls": 0,
            "actor_id": YOUTUBE_TRANSCRIPT_APIFY_ACTOR_ID,
            "run_id": None,
            "dataset_id": None,
        }
    if not YOUTUBE_TRANSCRIPT_APIFY_KEY:
        logger.warning("YOUTUBE_TRANSCRIPT_APIFY_KEY missing; Apify transcript batch skipped")
        return {}, {
            "status": "missing_api_key",
            "requested_urls": len(cleaned_urls),
            "actor_id": YOUTUBE_TRANSCRIPT_APIFY_ACTOR_ID,
            "run_id": None,
            "dataset_id": None,
        }

    try:
        from apify_client import ApifyClient
    except Exception as exc:
        logger.warning("apify-client import failed: %s", exc)
        return {}, {
            "status": "client_import_failed",
            "requested_urls": len(cleaned_urls),
            "actor_id": YOUTUBE_TRANSCRIPT_APIFY_ACTOR_ID,
            "run_id": None,
            "dataset_id": None,
            "error": str(exc),
        }

    run_input = {
        "outputFormat": "captions",
        "urls": cleaned_urls,
        "maxRetries": max(1, YOUTUBE_TRANSCRIPT_APIFY_MAX_RETRIES),
        "channelNameBoolean": True,
        "channelIDBoolean": True,
        "dateTextBoolean": False,
        "relativeDateTextBoolean": False,
        "datePublishedBoolean": True,
        "viewCountBoolean": False,
        "likesBoolean": False,
        "commentsBoolean": False,
        "keywordsBoolean": False,
        "thumbnailBoolean": False,
        "descriptionBoolean": False,
        "proxyOptions": {
            "useApifyProxy": True,
            "apifyProxyGroups": [YOUTUBE_TRANSCRIPT_APIFY_PROXY_GROUP],
        },
    }

    client = ApifyClient(YOUTUBE_TRANSCRIPT_APIFY_KEY)
    try:
        run = client.actor(YOUTUBE_TRANSCRIPT_APIFY_ACTOR_ID).call(run_input=run_input)
    except Exception as exc:
        logger.warning("Apify actor call failed: %s", exc)
        return {}, {
            "status": "actor_call_failed",
            "requested_urls": len(cleaned_urls),
            "actor_id": YOUTUBE_TRANSCRIPT_APIFY_ACTOR_ID,
            "run_id": None,
            "dataset_id": None,
            "error": str(exc),
        }

    dataset_id = str(run.get("defaultDatasetId") or "")
    transcripts_by_video_id: dict[str, dict[str, Any]] = {}
    items_count = 0
    if dataset_id:
        try:
            for item in client.dataset(dataset_id).iterate_items():
                items_count += 1
                item_url = str(
                    item.get("url")
                    or item.get("videoUrl")
                    or item.get("canonicalUrl")
                    or ""
                ).strip()
                video_id = str(item.get("videoId") or "").strip() or _extract_video_id_from_url(item_url)
                if not video_id:
                    continue
                transcript = _build_transcript_from_apify_item(item)
                transcript["source_metadata"] = {
                    "provider": "apify_actor",
                    "actor_id": YOUTUBE_TRANSCRIPT_APIFY_ACTOR_ID,
                    "dataset_id": dataset_id,
                    "item_url": item_url,
                }
                transcripts_by_video_id[video_id] = transcript
        except Exception as exc:
            logger.warning("Apify dataset iteration failed: %s", exc)
            return {}, {
                "status": "dataset_read_failed",
                "requested_urls": len(cleaned_urls),
                "actor_id": YOUTUBE_TRANSCRIPT_APIFY_ACTOR_ID,
                "dataset_id": dataset_id,
                "run_id": run.get("id"),
                "error": str(exc),
            }

    return transcripts_by_video_id, {
        "status": "ok",
        "requested_urls": len(cleaned_urls),
        "resolved_video_ids": len(transcripts_by_video_id),
        "items_count": items_count,
        "actor_id": YOUTUBE_TRANSCRIPT_APIFY_ACTOR_ID,
        "run_id": run.get("id"),
        "dataset_id": dataset_id,
    }


def get_external_transcript(
    video_id: str,
    languages: list[str] | None = None,
) -> dict[str, Any]:
    """
    Provider-style transcript fetch path.

    This is intentionally separate from the captions module so the fallback chain
    can try multiple retrieval strategies in deterministic order.
    """
    if languages is None:
        languages = ["en", "hi"]

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        segments = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        text = " ".join(seg.get("text", "") for seg in segments).strip()
        duration = 0
        if segments:
            last = segments[-1]
            duration = int(last.get("start", 0) + last.get("duration", 0))
        return {
            "text": text,
            "language": languages[0] if languages else "en",
            "segments": segments,
            "duration": duration,
            "source_metadata": {
                "provider": "youtube_transcript_api_get_transcript",
            },
        }
    except Exception as exc:
        logger.warning("External transcript provider failed for %s", video_id)
        return {
            "text": "",
            "language": "",
            "segments": [],
            "duration": 0,
            "source_metadata": {
                "provider": "youtube_transcript_api_get_transcript",
                "error": str(exc),
            },
        }


async def get_external_transcript_async(
    video_id: str,
    languages: list[str] | None = None,
) -> dict[str, Any]:
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(
        None,
        get_external_transcript,
        video_id,
        languages,
    )


async def _download_youtube_audio(url: str) -> Path | None:
    """Download audio from YouTube using yt-dlp with multiple fallback strategies."""
    import asyncio
    import yt_dlp

    tmp = tempfile.mktemp(suffix=".wav")
    out_template = tmp.replace(".wav", ".%(ext)s")

    base_opts = {
        "outtmpl": out_template,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "16",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    # Strategy 1: Use browser cookies (bypasses PO token requirement)
    strategies = [
        {**base_opts, "format": "bestaudio/best", "cookiesfrombrowser": ("chrome",)},
        {**base_opts, "format": "bestaudio/best", "cookiesfrombrowser": ("safari",)},
        # Strategy 2: Force iOS client (no PO token needed)
        {**base_opts, "format": "bestaudio/best", "extractor_args": {"youtube": {"player_client": ["ios"]}}},
        # Strategy 3: Force Android client
        {**base_opts, "format": "bestaudio/best", "extractor_args": {"youtube": {"player_client": ["android"]}}},
        # Strategy 4: Plain (no cookies, no special client)
        {**base_opts, "format": "bestaudio/best"},
    ]

    for i, ydl_opts in enumerate(strategies):
        def _dl(opts=ydl_opts):
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

        try:
            await asyncio.get_event_loop().run_in_executor(None, _dl)
            out_path = Path(tmp)
            if out_path.exists():
                logger.info("YouTube audio downloaded via strategy %d for %s", i + 1, url)
                return out_path
        except Exception:
            if i < len(strategies) - 1:
                logger.debug("yt-dlp strategy %d failed for %s, trying next", i + 1, url)
            else:
                logger.warning("All yt-dlp strategies failed for %s", url)

    return None


async def _download_playwright_audio(url: str) -> Path | None:
    """Download video from Instagram/Facebook, extract audio with ffmpeg."""
    import asyncio
    import subprocess

    tmp_video = tempfile.mktemp(suffix=".mp4")
    tmp_audio = tempfile.mktemp(suffix=".wav")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)

            # Try to find video element src
            video_src = await page.evaluate("""
                () => {
                    const v = document.querySelector('video');
                    return v ? v.src : null;
                }
            """)
            await browser.close()

        if not video_src:
            return None

        # Download video and extract audio
        def _extract():
            import urllib.request
            urllib.request.urlretrieve(video_src, tmp_video)
            subprocess.run(
                ["ffmpeg", "-i", tmp_video, "-vn", "-acodec", "pcm_s16le",
                 "-ar", "16000", "-ac", "1", tmp_audio, "-y"],
                capture_output=True, check=True,
            )

        await asyncio.get_event_loop().run_in_executor(None, _extract)
        out = Path(tmp_audio)
        return out if out.exists() else None

    except Exception:
        logger.exception("Playwright audio download failed: %s", url)
        return None
    finally:
        Path(tmp_video).unlink(missing_ok=True)


async def download_telegram_voice(client, message) -> Path | None:
    """Download a Telegram voice message via Telethon."""
    try:
        tmp = tempfile.mktemp(suffix=".ogg")
        await client.download_media(message, file=tmp)
        return Path(tmp)
    except Exception:
        logger.exception("Telegram voice download failed")
        return None
