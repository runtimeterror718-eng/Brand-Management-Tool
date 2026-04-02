from __future__ import annotations

from config import settings
from workers import tasks


def test_run_telegram_message_analysis_task_passes_bounded_args(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    calls: list[dict] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_telegram_message_analysis",
        lambda b, **kwargs: calls.append(kwargs)
        or {
            "phase": "telegram_message_analysis",
            "mode": kwargs.get("mode"),
            "analyzed": 12,
        },
    )

    out = tasks.run_telegram_message_analysis.run(
        brand_id="brand-1",
        mode="historical",
        limit=800,
        only_unanalyzed=False,
        message_since_hours=None,
        force_reanalysis=True,
        target_channels=["@pw_official", "100100"],
        batch_size=22,
        limit_channels=25,
        max_messages_per_channel=900,
        persist_channel_rollup=False,
    )

    assert out and out[0]["phase"] == "telegram_message_analysis"
    assert len(calls) == 1
    assert calls[0]["mode"] == "historical"
    assert calls[0]["limit"] == 800
    assert calls[0]["only_unanalyzed"] is False
    assert calls[0]["force_reanalysis"] is True
    assert calls[0]["target_channels"] == ["@pw_official", "100100"]
    assert calls[0]["batch_size"] == 22
    assert calls[0]["limit_channels"] == 25
    assert calls[0]["max_messages_per_channel"] == 900
    assert calls[0]["persist_channel_rollup"] is False


def test_run_telegram_message_analysis_task_uses_daily_defaults(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    calls: list[dict] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_telegram_message_analysis",
        lambda b, **kwargs: calls.append(kwargs)
        or {
            "phase": "telegram_message_analysis",
            "mode": kwargs.get("mode"),
            "analyzed": 0,
        },
    )

    tasks.run_telegram_message_analysis.run(brand_id="brand-1")

    assert len(calls) == 1
    assert calls[0]["mode"] == "daily"
    assert calls[0]["limit"] == 500
    assert calls[0]["only_unanalyzed"] is True
    assert calls[0]["message_since_hours"] == settings.TELEGRAM_MESSAGE_ANALYSIS_DAILY_LOOKBACK_HOURS
    assert calls[0]["batch_size"] == settings.TELEGRAM_MESSAGE_ANALYSIS_DAILY_BATCH_SIZE
    assert calls[0]["limit_channels"] == settings.TELEGRAM_MESSAGE_ANALYSIS_LIMIT_CHANNELS
    assert calls[0]["max_messages_per_channel"] == settings.TELEGRAM_MESSAGE_ANALYSIS_MAX_MESSAGES_PER_CHANNEL
    assert calls[0]["persist_channel_rollup"] is True
