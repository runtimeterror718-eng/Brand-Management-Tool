from __future__ import annotations

from config import settings
from workers import tasks


def test_run_telegram_phase2_pipeline_task_passes_bounded_args(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW", "keywords": ["physics wallah"]}
    calls: list[dict] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_telegram_phase2_pipeline",
        lambda b, **kwargs: calls.append(kwargs) or {"phase": "telegram_phase2", "messages_ingested": 0},
    )

    out = tasks.run_telegram_phase2_pipeline.run(
        brand_id="brand-1",
        keywords=["physics wallah", "pw"],
        per_keyword_limit=10,
        message_backfill_limit=30,
        incremental_fetch_limit=60,
        force_reclassify=True,
        target_channels=["@pw_official", "100100"],
    )

    assert out and out[0]["phase"] == "telegram_phase2"
    assert len(calls) == 1
    assert calls[0]["keywords"] == ["physics wallah", "pw"]
    assert calls[0]["per_keyword_limit"] == 10
    assert calls[0]["message_backfill_limit"] == 30
    assert calls[0]["incremental_fetch_limit"] == 60
    assert calls[0]["force_reclassify"] is True
    assert calls[0]["target_channels"] == ["@pw_official", "100100"]


def test_run_telegram_phase2_pipeline_task_uses_defaults(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW", "keywords": ["physics wallah"]}
    calls: list[dict] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_telegram_phase2_pipeline",
        lambda b, **kwargs: calls.append(kwargs) or {"phase": "telegram_phase2", "messages_ingested": 0},
    )

    tasks.run_telegram_phase2_pipeline.run(brand_id="brand-1")

    assert len(calls) == 1
    assert calls[0]["per_keyword_limit"] == settings.TELEGRAM_DISCOVERY_MAX_RESULTS_PER_KEYWORD
    assert calls[0]["message_backfill_limit"] == settings.TELEGRAM_MESSAGE_BACKFILL_LIMIT
    assert calls[0]["incremental_fetch_limit"] == settings.TELEGRAM_MESSAGE_INCREMENTAL_LIMIT


def test_scrape_platform_telegram_routes_to_phase2_pipeline(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW", "keywords": ["physics wallah"]}
    calls: list[dict] = []

    import search.engine as engine

    async def _should_not_run(_params):
        raise AssertionError("search_and_fulfill should not run for telegram branch")

    monkeypatch.setattr(engine, "ensure_searchers_loaded", lambda platforms=None: None)
    monkeypatch.setattr(engine, "search_and_fulfill", _should_not_run)
    monkeypatch.setattr(tasks, "get_monitored_brands", lambda: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_telegram_phase2_pipeline",
        lambda b, **kwargs: calls.append(kwargs)
        or {
            "discovered": 1,
            "channels_classified": 1,
            "channels_monitored": 1,
            "messages_ingested": 2,
        },
    )

    tasks.scrape_platform.run("telegram")

    assert len(calls) == 1
    assert calls[0]["per_keyword_limit"] == settings.TELEGRAM_DISCOVERY_MAX_RESULTS_PER_KEYWORD
    assert calls[0]["force_reclassify"] is False
