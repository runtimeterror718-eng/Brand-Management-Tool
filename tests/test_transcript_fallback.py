from __future__ import annotations

import asyncio
from pathlib import Path

from transcription import captions as cap


def test_transcript_fallback_uses_captions_first(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_captions(video_id: str, languages=None):
        calls.append("captions")
        return {"text": "captions text", "language": "en", "segments": [], "duration": 10}

    async def fake_provider(video_id: str, languages=None):
        calls.append("provider")
        return {"text": "provider text", "language": "en", "segments": [], "duration": 10}

    async def fake_downloader(url: str, platform: str):
        calls.append("downloader")
        return None

    monkeypatch.setattr(cap, "get_captions_async", fake_captions)

    result = asyncio.run(
        cap.get_transcript_with_fallback(
            video_id="abc",
            source_url="https://youtube.com/watch?v=abc",
            external_provider_fn=fake_provider,
            audio_downloader_fn=fake_downloader,
        )
    )

    assert result["source_type"] == "youtube_captions"
    assert calls == ["captions"]


def test_transcript_fallback_uses_provider_second(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_captions(video_id: str, languages=None):
        calls.append("captions")
        return {"text": "", "language": "", "segments": [], "duration": 0}

    async def fake_provider(video_id: str, languages=None):
        calls.append("provider")
        return {"text": "provider text", "language": "en", "segments": [], "duration": 8}

    async def fake_downloader(url: str, platform: str):
        calls.append("downloader")
        return None

    monkeypatch.setattr(cap, "get_captions_async", fake_captions)

    result = asyncio.run(
        cap.get_transcript_with_fallback(
            video_id="abc",
            source_url="https://youtube.com/watch?v=abc",
            external_provider_fn=fake_provider,
            audio_downloader_fn=fake_downloader,
        )
    )

    assert result["source_type"] == "external_provider"
    assert calls == ["captions", "provider"]


def test_transcript_fallback_uses_whisper_last(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []

    async def fake_captions(video_id: str, languages=None):
        calls.append("captions")
        return {"text": "", "language": "", "segments": [], "duration": 0}

    async def fake_provider(video_id: str, languages=None):
        calls.append("provider")
        return {"text": "", "language": "", "segments": [], "duration": 0}

    temp_audio = tmp_path / "audio.wav"
    temp_audio.write_text("x")

    async def fake_downloader(url: str, platform: str):
        calls.append("downloader")
        return temp_audio

    async def fake_whisper(path: Path):
        calls.append("whisper")
        return {"text": "whisper text", "language": "en", "segments": [], "duration": 6}

    monkeypatch.setattr(cap, "get_captions_async", fake_captions)

    result = asyncio.run(
        cap.get_transcript_with_fallback(
            video_id="abc",
            source_url="https://youtube.com/watch?v=abc",
            external_provider_fn=fake_provider,
            audio_downloader_fn=fake_downloader,
            whisper_transcriber_fn=fake_whisper,
        )
    )

    assert result["source_type"] == "whisper_fallback"
    assert calls == ["captions", "provider", "downloader", "whisper"]


def test_transcript_fallback_whisper_failure_is_non_fatal(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []

    async def fake_captions(video_id: str, languages=None):
        calls.append("captions")
        return {"text": "", "language": "", "segments": [], "duration": 0}

    async def fake_provider(video_id: str, languages=None):
        calls.append("provider")
        return {"text": "", "language": "", "segments": [], "duration": 0}

    temp_audio = tmp_path / "audio.wav"
    temp_audio.write_text("x")

    async def fake_downloader(url: str, platform: str):
        calls.append("downloader")
        return temp_audio

    async def fake_whisper(path: Path):
        calls.append("whisper")
        raise ModuleNotFoundError("whisper")

    monkeypatch.setattr(cap, "get_captions_async", fake_captions)

    result = asyncio.run(
        cap.get_transcript_with_fallback(
            video_id="abc",
            source_url="https://youtube.com/watch?v=abc",
            external_provider_fn=fake_provider,
            audio_downloader_fn=fake_downloader,
            whisper_transcriber_fn=fake_whisper,
        )
    )

    assert result["source_type"] == "none"
    assert result["text"] == ""
    assert calls == ["captions", "provider", "downloader", "whisper"]


def test_transcript_fallback_provider_exception_is_non_fatal(tmp_path: Path, monkeypatch) -> None:
    calls: list[str] = []

    async def fake_captions(video_id: str, languages=None):
        calls.append("captions")
        return {"text": "", "language": "", "segments": [], "duration": 0}

    async def fake_provider(video_id: str, languages=None):
        calls.append("provider")
        raise RuntimeError("provider_down")

    temp_audio = tmp_path / "audio.wav"
    temp_audio.write_text("x")

    async def fake_downloader(url: str, platform: str):
        calls.append("downloader")
        return temp_audio

    async def fake_whisper(path: Path):
        calls.append("whisper")
        return {"text": "whisper text", "language": "en", "segments": [], "duration": 6}

    monkeypatch.setattr(cap, "get_captions_async", fake_captions)

    result = asyncio.run(
        cap.get_transcript_with_fallback(
            video_id="abc",
            source_url="https://youtube.com/watch?v=abc",
            external_provider_fn=fake_provider,
            audio_downloader_fn=fake_downloader,
            whisper_transcriber_fn=fake_whisper,
        )
    )

    assert result["source_type"] == "whisper_fallback"
    assert result["text"] == "whisper text"
    assert calls == ["captions", "provider", "downloader", "whisper"]
