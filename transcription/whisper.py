"""
OpenAI Whisper transcription — local model or API.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_model = None


def _load_model(model_size: str = "base"):
    global _model
    if _model is None:
        import whisper

        logger.info("Loading Whisper model: %s", model_size)
        _model = whisper.load_model(model_size)
    return _model


def transcribe(audio_path: str | Path, model_size: str = "base") -> dict:
    """
    Transcribe an audio file using Whisper.

    Returns dict with 'text', 'language', 'segments', 'duration'.
    """
    model = _load_model(model_size)
    result = model.transcribe(str(audio_path))
    duration = 0
    if result.get("segments"):
        duration = int(result["segments"][-1].get("end", 0))

    return {
        "text": result.get("text", "").strip(),
        "language": result.get("language", "en"),
        "segments": result.get("segments", []),
        "duration": duration,
    }


async def transcribe_async(audio_path: str | Path, model_size: str = "base") -> dict:
    """Async wrapper around Whisper transcription."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(
        None, transcribe, audio_path, model_size
    )
