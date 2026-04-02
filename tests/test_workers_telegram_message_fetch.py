from __future__ import annotations

from config import settings
from workers import tasks


def test_run_telegram_message_fetch_pipeline_task_passes_bounded_args(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    calls: list[dict] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_telegram_message_fetch_pipeline",
        lambda b, **kwargs: calls.append(kwargs)
        or {
            "phase": "telegram_message_fetch",
            "channels_considered": 2,
            "messages_upserted": 20,
        },
    )

    out = tasks.run_telegram_message_fetch_pipeline.run(
        brand_id="brand-1",
        limit_channels=30,
        batch_size=10,
        historical_months=6,
        daily_lookback_days=2,
        batch_sleep_min_seconds=1,
        batch_sleep_max_seconds=3,
        between_channels_sleep_seconds=5,
        target_channels=["@pw_official", "100100"],
        max_media_bytes=4096,
    )

    assert out and out[0]["phase"] == "telegram_message_fetch"
    assert len(calls) == 1
    assert calls[0]["limit_channels"] == 30
    assert calls[0]["batch_size"] == 10
    assert calls[0]["historical_months"] == 6
    assert calls[0]["daily_lookback_days"] == 2
    assert calls[0]["batch_sleep_min_seconds"] == 1
    assert calls[0]["batch_sleep_max_seconds"] == 3
    assert calls[0]["between_channels_sleep_seconds"] == 5
    assert calls[0]["target_channels"] == ["@pw_official", "100100"]
    assert calls[0]["max_media_bytes"] == 4096


def test_run_telegram_message_fetch_pipeline_task_uses_defaults(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    calls: list[dict] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_telegram_message_fetch_pipeline",
        lambda b, **kwargs: calls.append(kwargs)
        or {
            "phase": "telegram_message_fetch",
            "channels_considered": 0,
            "messages_upserted": 0,
        },
    )

    tasks.run_telegram_message_fetch_pipeline.run(brand_id="brand-1")

    assert len(calls) == 1
    assert calls[0]["limit_channels"] == 500
    assert calls[0]["batch_size"] == settings.TELEGRAM_MESSAGE_FETCH_BATCH_SIZE
    assert calls[0]["historical_months"] == settings.TELEGRAM_MESSAGE_FETCH_HISTORICAL_MONTHS
    assert calls[0]["daily_lookback_days"] == settings.TELEGRAM_MESSAGE_FETCH_DAILY_LOOKBACK_DAYS
    assert calls[0]["batch_sleep_min_seconds"] == settings.TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MIN_SECONDS
    assert calls[0]["batch_sleep_max_seconds"] == settings.TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MAX_SECONDS
    assert calls[0]["between_channels_sleep_seconds"] == settings.TELEGRAM_MESSAGE_FETCH_CHANNEL_SLEEP_SECONDS
    assert calls[0]["target_channels"] == []
    assert calls[0]["max_media_bytes"] == settings.TELEGRAM_MESSAGE_MEDIA_MAX_BYTES
