"""
YouTube captions via youtube-transcript-api (free, no Whisper needed).
"""

from __future__ import annotations

import logging
from typing import Any

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
        }

    except Exception:
        logger.warning("No captions available for video %s", video_id)
        return {"text": "", "language": "", "segments": [], "duration": 0}


async def get_captions_async(
    video_id: str, languages: list[str] | None = None
) -> dict[str, Any]:
    """Async wrapper."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(
        None, get_captions, video_id, languages
    )
