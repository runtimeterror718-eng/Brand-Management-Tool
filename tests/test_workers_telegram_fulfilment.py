from __future__ import annotations

from workers import tasks


def test_run_telegram_fulfilment_task_passes_bounded_args(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    calls: list[dict] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_telegram_channel_fulfilment",
        lambda b, **kwargs: calls.append(kwargs)
        or {
            "phase": "telegram_channel_fulfilment",
            "total_considered": 3,
            "classified": 3,
        },
    )

    out = tasks.run_telegram_fulfilment.run(
        brand_id="brand-1",
        limit=50,
        only_unclassified=False,
        discovered_since_hours=12,
        force_refulfilment=True,
        target_channels=["@pw_official", "100100"],
    )

    assert out and out[0]["phase"] == "telegram_channel_fulfilment"
    assert len(calls) == 1
    assert calls[0]["limit"] == 50
    assert calls[0]["only_unclassified"] is False
    assert calls[0]["discovered_since_hours"] == 12
    assert calls[0]["force_refulfilment"] is True
    assert calls[0]["target_channels"] == ["@pw_official", "100100"]


def test_run_telegram_fulfilment_task_uses_defaults(monkeypatch) -> None:
    brand = {"id": "brand-1", "name": "PW"}
    calls: list[dict] = []

    monkeypatch.setattr(tasks, "_get_target_brands", lambda brand_id=None: [brand])
    monkeypatch.setattr(
        tasks,
        "_run_telegram_channel_fulfilment",
        lambda b, **kwargs: calls.append(kwargs)
        or {
            "phase": "telegram_channel_fulfilment",
            "total_considered": 0,
            "classified": 0,
        },
    )

    tasks.run_telegram_fulfilment.run(brand_id="brand-1")

    assert len(calls) == 1
    assert calls[0]["limit"] == 200
    assert calls[0]["only_unclassified"] is True
    assert calls[0]["discovered_since_hours"] is None
    assert calls[0]["force_refulfilment"] is False
    assert calls[0]["target_channels"] == []
