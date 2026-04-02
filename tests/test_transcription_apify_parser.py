from __future__ import annotations

from transcription.extractor import _build_transcript_from_apify_item


def test_apify_parser_handles_string_caption_lines() -> None:
    item = {
        "captions": [
            "line one",
            "line two",
            "line three",
        ],
        "language": "hi",
    }

    transcript = _build_transcript_from_apify_item(item)

    assert transcript["language"] == "hi"
    assert transcript["text"] == "line one line two line three"
    assert isinstance(transcript["segments"], list)
    assert len(transcript["segments"]) == 3
    assert transcript["segments"][0]["text"] == "line one"
