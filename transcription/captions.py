"""
YouTube captions via youtube-transcript-api (free, no Whisper needed).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config.settings import WHISPER_API_KEY

logger = logging.getLogger(__name__)


def get_captions(video_id: str, languages: list[str] | None = None) -> dict[str, Any]:
    """
    Fetch captions for a YouTube video.

    Parameters
    ----------
    video_id : str
        YouTube video ID (e.g., 'dQw4w9WgXcQ')
    languages : list[str], optional
        Preferred languages, defaults to ['en', 'hi']

    Returns
    -------
    dict with 'text', 'language', 'segments', 'duration'
    """
    if languages is None:
        languages = ["en", "hi"]

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try manual captions first, then auto-generated
        transcript = None
        try:
            transcript = transcript_list.find_transcript(languages)
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(languages)
            except Exception:
                # Fall back to whatever is available
                for t in transcript_list:
                    transcript = t
                    break

        if transcript is None:
            return {"text": "", "language": "", "segments": [], "duration": 0}

        segments = transcript.fetch()
        full_text = " ".join(seg["text"] for seg in segments)
        duration = int(segments[-1]["start"] + segments[-1]["duration"]) if segments else 0

        return {
            "text": full_text,
            "language": transcript.language_code,
            "segments": segments,
            "duration": duration,
            "source_metadata": {
                "provider": "youtube_transcript_api_captions",
            },
        }

    except Exception:
        logger.warning("No captions available for video %s", video_id)
        return {
            "text": "",
            "language": "",
            "segments": [],
            "duration": 0,
            "source_metadata": {"provider": "youtube_transcript_api_captions"},
        }


async def get_captions_async(
    video_id: str, languages: list[str] | None = None
) -> dict[str, Any]:
    """Async wrapper."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(
        None, get_captions, video_id, languages
    )


async def get_transcript_with_fallback(
    video_id: str,
    source_url: str,
    languages: list[str] | None = None,
    external_provider_fn=None,
    audio_downloader_fn=None,
    whisper_transcriber_fn=None,
) -> dict[str, Any]:
    """
    Transcript fallback order:
    1) YouTube captions route
    2) External/provider transcript route
    3) Audio download + Whisper route
    """
    if languages is None:
        languages = ["en", "hi"]

    attempt_order = ["youtube_captions", "whisper_fallback"]

    try:
        captions = await get_captions_async(video_id, languages=languages)
    except Exception as exc:
        logger.warning("Caption fetch failed for %s: %s", video_id, exc)
        captions = {
            "text": "",
            "language": "",
            "segments": [],
            "duration": 0,
            "source_metadata": {"provider": "youtube_transcript_api_captions", "error": str(exc)},
        }
    if captions.get("text"):
        return {
            **captions,
            "source_type": "youtube_captions",
            "attempt_order": attempt_order,
        }

    # Skip Apify external provider — go straight to Whisper
    logger.info("No captions for %s, falling back to Whisper transcription", video_id)

    if audio_downloader_fn is None:
        from transcription.extractor import download_audio

        audio_downloader_fn = download_audio
    if whisper_transcriber_fn is None:
        from transcription.whisper import transcribe_async

        whisper_transcriber_fn = transcribe_async
        if not WHISPER_API_KEY:
            logger.warning("WHISPER_API_KEY missing; skipping whisper fallback")
            return {
                "text": "",
                "language": "",
                "segments": [],
                "duration": 0,
                "source_type": "none",
                "attempt_order": attempt_order,
                "source_metadata": {
                    "failure_stage": "whisper_missing_api_key",
                },
            }

    try:
        audio_path = await audio_downloader_fn(source_url, "youtube")
    except Exception as exc:
        logger.warning("Audio download failed for %s: %s", video_id, exc)
        audio_path = None
    if not audio_path:
        return {
            "text": "",
            "language": "",
            "segments": [],
            "duration": 0,
            "source_type": "none",
            "attempt_order": attempt_order,
            "source_metadata": {
                "failure_stage": "audio_download",
            },
        }

    try:
        try:
            transcript = await whisper_transcriber_fn(audio_path)
        except Exception as exc:
            logger.warning("Whisper fallback failed for video %s: %s", video_id, exc)
            transcript = {}

        if transcript.get("text"):
            return {
                **transcript,
                "source_type": "whisper_fallback",
                "attempt_order": attempt_order,
            }
        return {
            "text": "",
            "language": "",
            "segments": [],
            "duration": 0,
            "source_type": "none",
            "attempt_order": attempt_order,
            "source_metadata": {
                "failure_stage": "whisper_result_empty",
            },
        }
    finally:
        try:
            Path(audio_path).unlink(missing_ok=True)
        except Exception:
            logger.warning("Failed to clean up temporary audio: %s", audio_path)
