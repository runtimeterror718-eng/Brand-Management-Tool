"""
OpenAI Whisper transcription — local model or API.
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from config.settings import (
    WHISPER_API_KEY,
    WHISPER_PROXY_LANGUAGE,
    WHISPER_PROXY_POLL_INTERVAL_SECONDS,
    WHISPER_PROXY_POLL_TIMEOUT_SECONDS,
    WHISPER_PROXY_RESULT_URL,
    WHISPER_PROXY_SUBMIT_URL,
    WHISPER_PROXY_WORKFLOW_NAME,
)

logger = logging.getLogger(__name__)
_model = None


def _empty_transcript() -> dict:
    return {
        "text": "",
        "language": "",
        "segments": [],
        "duration": 0,
        "source_metadata": {},
    }


def _load_model(model_size: str = "base"):
    global _model
    if _model is None:
        import whisper

        logger.info("Loading Whisper model: %s", model_size)
        _model = whisper.load_model(model_size)
    return _model


def _deep_find_first(obj: Any, keys: set[str]) -> str:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in keys and isinstance(v, (str, int, float)):
                text = str(v).strip()
                if text:
                    return text
            found = _deep_find_first(v, keys)
            if found:
                return found
    if isinstance(obj, list):
        for item in obj:
            found = _deep_find_first(item, keys)
            if found:
                return found
    return ""


def _parse_remote_transcript(payload: Any, fallback_language: str) -> dict:
    text = _deep_find_first(payload, {"text", "transcript", "transcription"})
    language = (
        _deep_find_first(payload, {"language", "lang"}).lower()
        or fallback_language
        or "hi"
    )
    if not text:
        return _empty_transcript()
    request_id = _deep_find_first(payload, {"request_id", "correlation_id", "id", "task_id"})
    status = _deep_find_first(payload, {"status", "state", "task_status"}).lower()
    return {
        "text": text,
        "language": language,
        "segments": [],
        "duration": 0,
        "source_metadata": {
            "provider": "whisper_proxy",
            "request_id": request_id,
            "status": status or "completed",
        },
    }


def _transcribe_via_remote_proxy(audio_path: str | Path) -> dict:
    if not WHISPER_API_KEY:
        logger.warning("WHISPER_API_KEY missing; skipping whisper proxy fallback")
        return _empty_transcript()

    path = Path(audio_path)
    if not path.exists():
        return _empty_transcript()

    request_name = WHISPER_PROXY_WORKFLOW_NAME
    language = WHISPER_PROXY_LANGUAGE or "hi"

    auth_headers = {
        "Authorization": f"Bearer {WHISPER_API_KEY}",
        "Content-Type": "application/json",
    }

    audio_base64 = base64.b64encode(path.read_bytes()).decode("utf-8")
    submit_payload = {
        "name": request_name,
        "input_data": {
            "audio_file": audio_base64,
            "language": language,
            "task": "transcribe",
            "vad_model": "silero",
            "word_timestamps": False,
            "diarization": False,
            "strict_hallucination_reduction": True,
        },
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            submit_resp = client.post(
                WHISPER_PROXY_SUBMIT_URL,
                headers=auth_headers,
                json=submit_payload,
            )
            submit_resp.raise_for_status()
            submit_data = submit_resp.json() if submit_resp.content else {}

            direct = _parse_remote_transcript(submit_data, fallback_language=language)
            if direct.get("text"):
                return direct

            request_id = _deep_find_first(
                submit_data,
                {"request_id", "correlation_id", "id", "task_id"},
            )
            if not request_id:
                logger.warning("Whisper proxy submit returned no request id")
                return _empty_transcript()

            deadline = time.time() + max(30, WHISPER_PROXY_POLL_TIMEOUT_SECONDS)
            poll_interval = max(2, WHISPER_PROXY_POLL_INTERVAL_SECONDS)
            while time.time() < deadline:
                status_resp = client.get(
                    WHISPER_PROXY_RESULT_URL,
                    headers={"Authorization": f"Bearer {WHISPER_API_KEY}"},
                    params={"name": request_name, "request_id": request_id},
                )
                status_resp.raise_for_status()
                status_data = status_resp.json() if status_resp.content else {}

                parsed = _parse_remote_transcript(status_data, fallback_language=language)
                if parsed.get("text"):
                    source_meta = parsed.get("source_metadata")
                    if isinstance(source_meta, dict):
                        source_meta.setdefault("request_id", request_id)
                    return parsed

                status = _deep_find_first(
                    status_data,
                    {"status", "state", "task_status"},
                ).lower()
                if status in {"failed", "error", "cancelled"}:
                    logger.warning(
                        "Whisper proxy returned terminal status=%s for request_id=%s",
                        status,
                        request_id,
                    )
                    return _empty_transcript()

                time.sleep(poll_interval)
    except Exception as exc:
        logger.warning("Whisper proxy transcription failed: %s", exc)
        return _empty_transcript()

    logger.warning("Whisper proxy timed out before transcript became available")
    return _empty_transcript()


def transcribe(audio_path: str | Path, model_size: str = "base") -> dict:
    """
    Transcribe an audio file using Whisper.

    Returns dict with 'text', 'language', 'segments', 'duration'.
    """
    try:
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
    except ModuleNotFoundError:
        logger.warning("Local whisper package unavailable; using remote whisper proxy")
    except Exception as exc:
        logger.warning("Local whisper transcription failed; using remote proxy: %s", exc)

    return _transcribe_via_remote_proxy(audio_path)


async def transcribe_async(audio_path: str | Path, model_size: str = "base") -> dict:
    """Async wrapper around Whisper transcription."""
    import asyncio

    return await asyncio.get_event_loop().run_in_executor(
        None, transcribe, audio_path, model_size
    )
