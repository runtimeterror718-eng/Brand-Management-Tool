"""
Audio/video downloader for transcription pipeline.

Downloads audio tracks from YouTube, Instagram, Facebook, Telegram.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

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


async def _download_youtube_audio(url: str) -> Path | None:
    """Download audio from YouTube using yt-dlp."""
    import asyncio
    import yt_dlp

    tmp = tempfile.mktemp(suffix=".wav")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": tmp.replace(".wav", ".%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "16",
            }
        ],
        "quiet": True,
    }

    def _dl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    try:
        await asyncio.get_event_loop().run_in_executor(None, _dl)
        out_path = Path(tmp)
        if out_path.exists():
            return out_path
    except Exception:
        logger.exception("YouTube audio download failed: %s", url)

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
