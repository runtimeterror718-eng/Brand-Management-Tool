from __future__ import annotations

from copy import deepcopy

from scrapers import telegram as tg


class _FakeClassifier:
    def __init__(self, payload: dict | None = None, meta: dict | None = None, should_raise: bool = False):
        self.payload = payload or {}
        self.meta = meta or {"status": "completed", "mode": "direct", "provider_response_id": "resp-1"}
        self.should_raise = should_raise
        self.calls = 0
        self.batch_calls = 0
        self.batch_payload_sizes: list[int] = []

    def classify_channel_fulfilment(self, channel_payload: dict):
        self.calls += 1
        if self.should_raise:
            raise AssertionError("LLM should not be called for this row")
        return deepcopy(self.payload), deepcopy(self.meta)

    def classify_channels_fulfilment_batch(self, channel_payloads: list[dict]):
        self.batch_calls += 1
        self.batch_payload_sizes.append(len(channel_payloads))
        if self.should_raise:
            raise AssertionError("LLM should not be called for this batch")

        results = []
        for payload in channel_payloads:
            channel = payload.get("channel") if isinstance(payload, dict) else {}
            channel_id = (channel or {}).get("channel_id")
            results.append(
                {
                    "channel_id": channel_id,
                    "classification_label": self.payload.get("classification_label", "fan_unofficial"),
                    "fake_score_10": self.payload.get("fake_score_10", 4),
                    "is_fake": self.payload.get("is_fake", False),
                    "should_monitor": self.payload.get("should_monitor", True),
                    "confidence": self.payload.get("confidence", 0.74),
                    "risk_flags": self.payload.get("risk_flags", []),
                    "reason": self.payload.get("reason", "batch test"),
                    "evidence": self.payload.get("evidence", ["batch"]),
                }
            )
        return {"results": results}, deepcopy(self.meta)


def test_build_telegram_channel_fulfilment_payload_null_safe() -> None:
    payload = tg.build_telegram_channel_fulfilment_payload(
        {
            "channel_id": "100100",
            "channel_username": None,
            "channel_title": "Physics Wallah",
            "is_verified": None,
            "participants_count": None,
            "message_count_7d": None,
        }
    )

    assert payload["brand_name"] == "Physics Wallah"
    assert payload["platform"] == "telegram"
    assert payload["task"] == "channel_fulfilment_fake_risk_scoring"
    assert payload["channel"]["channel_id"] == "100100"
    assert payload["channel"]["channel_username"] is None
    assert payload["channel"]["participants_count"] is None
    assert payload["channel"]["message_count_7d"] is None
    assert payload["channel"]["channel_created_at"] is None


def test_normalize_telegram_channel_fulfilment_response_enum_and_monitor_policy() -> None:
    normalized = tg.normalize_telegram_channel_fulfilment_response(
        {
            "classification_label": "Likely Official",
            "fake_score_10": "3.2",
            "is_fake": None,
            "should_monitor": False,
            "confidence": "1.7",
            "risk_flags": ["third party promotion", "unknown_flag"],
            "reason": "Looks branded",
            "evidence": ["title contains PW"],
        }
    )

    assert normalized["classification_label"] == "likely_official"
    assert normalized["fake_score_10"] == 3
    assert normalized["is_fake"] is False
    assert normalized["should_monitor"] is True
    assert normalized["confidence"] == 1.0
    assert normalized["risk_flags"] == ["third_party_promotion"]


def test_normalize_telegram_channel_fulfilment_response_sets_is_fake_for_high_score() -> None:
    normalized = tg.normalize_telegram_channel_fulfilment_response(
        {
            "classification_label": "suspicious_fake",
            "fake_score_10": 8,
            "is_fake": None,
            "should_monitor": True,
            "confidence": 0.88,
            "risk_flags": ["impersonation"],
            "reason": "Strong impersonation cues",
            "evidence": ["official claim without verification"],
        }
    )
    assert normalized["is_fake"] is True
    assert normalized["should_monitor"] is True


def test_build_telegram_fulfilment_writeback_updates_includes_optional_columns() -> None:
    row = {
        "id": "row-1",
        "channel_id": "100100",
        "fake_score_10": None,
        "confidence": None,
    }
    normalized = {
        "classification_label": "fan_unofficial",
        "fake_score_10": 4,
        "is_fake": False,
        "should_monitor": True,
        "confidence": 0.71,
        "risk_flags": [],
        "reason": "fan-run",
        "evidence": [],
    }
    llm_blob = {"status": "completed"}

    updates = tg.build_telegram_fulfilment_writeback_updates(
        channel_row=row,
        normalized=normalized,
        llm_classification_response=llm_blob,
    )

    assert updates["classification_label"] == "fan_unofficial"
    assert updates["should_monitor"] is True
    assert updates["is_fake"] is False
    assert updates["fake_score_10"] == 4
    assert updates["confidence"] == 0.71
    assert updates["llm_classification_response"] == llm_blob


def test_classify_telegram_channel_fulfilment_row_verified_auto_bypass(monkeypatch) -> None:
    writes: list[dict] = []

    def _fake_update(row_id: str, updates: dict):
        writes.append(deepcopy(updates))
        return {"id": row_id, "channel_id": "100100", **updates}

    monkeypatch.setattr(tg.db, "update_telegram_channel", _fake_update)

    out = tg.classify_telegram_channel_fulfilment_row(
        channel_row={
            "id": "row-1",
            "channel_id": "100100",
            "channel_username": "pw_official",
            "channel_title": "Physics Wallah Official",
            "is_verified": True,
        },
        classifier=_FakeClassifier(should_raise=True),
    )

    assert out["status"] == "classified"
    assert out["fake_score_10"] == 0
    assert out["is_fake"] is False
    assert out["should_monitor"] is False
    assert writes[0]["llm_classification_response"]["status"] == "verified_auto_bypass"


def test_fulfilment_heuristic_scores_strong_fake_signal_high() -> None:
    heuristic = tg._fulfilment_heuristic_response(
        {
            "channel": {
                "channel_title": "Physics Wala (official)",
                "channel_username": "physics_wala_official",
                "channel_description": "For Ads / Collabs - @jay_baba_ri",
                "discovery_keyword": "physics wallah",
            }
        }
    )

    assert heuristic["classification_label"] == "suspicious_fake"
    assert heuristic["fake_score_10"] >= 8
    assert heuristic["is_fake"] is True


def test_fulfilment_heuristic_handles_fan_unofficial_not_fake() -> None:
    heuristic = tg._fulfilment_heuristic_response(
        {
            "channel": {
                "channel_title": "PW Fan Community",
                "channel_username": "pw_fan_community",
                "channel_description": "Unofficial student discussion group",
                "discovery_keyword": "physics wallah",
            }
        }
    )

    assert heuristic["classification_label"] == "fan_unofficial"
    assert heuristic["is_fake"] is False
    assert heuristic["should_monitor"] is True


def test_run_telegram_channel_fulfilment_returns_summary_counts(monkeypatch) -> None:
    rows = [
        {"id": "row-1", "channel_id": "1"},
        {"id": "row-2", "channel_id": "2"},
        {"id": "row-3", "channel_id": "3"},
    ]

    monkeypatch.setattr(
        tg.db,
        "list_telegram_channels_for_fulfilment",
        lambda **_kwargs: deepcopy(rows),
    )

    outcomes = {
        "1": {"status": "classified", "classification_label": "official", "should_monitor": False},
        "2": {"status": "classified", "classification_label": "suspicious_fake", "should_monitor": True},
        "3": {"status": "classified", "classification_label": "fan_unofficial", "should_monitor": True},
    }

    monkeypatch.setattr(
        tg,
        "classify_telegram_channel_fulfilment_row",
        lambda channel_row, classifier=None: deepcopy(outcomes[channel_row["channel_id"]]),
    )

    summary = tg.run_telegram_channel_fulfilment(
        brand_id="brand-1",
        limit=10,
        only_unclassified=True,
        discovered_since_hours=24,
    )

    assert summary["total_considered"] == 3
    assert summary["classified"] == 3
    assert summary["official"] == 1
    assert summary["suspicious_fake"] == 1
    assert summary["fan_unofficial"] == 1
    assert summary["should_monitor_count"] == 2


def test_run_telegram_channel_fulfilment_uses_batch_size_five(monkeypatch) -> None:
    rows = [
        {"id": f"row-{idx}", "channel_id": str(1000 + idx)}
        for idx in range(11)
    ]
    calls: list[tuple[int, int]] = []

    monkeypatch.setattr(
        tg.db,
        "list_telegram_channels_for_fulfilment",
        lambda **_kwargs: deepcopy(rows),
    )

    def _fake_batch(channel_rows, classifier=None, batch_size=5):
        calls.append((len(channel_rows), batch_size))
        return [
            {
                "status": "classified",
                "classification_label": "fan_unofficial",
                "should_monitor": True,
                "is_fake": False,
                "fake_score_10": 4,
                "channel_id": row.get("channel_id"),
            }
            for row in channel_rows
        ]

    monkeypatch.setattr(tg, "classify_telegram_channel_fulfilment_rows_batch", _fake_batch)

    summary = tg.run_telegram_channel_fulfilment(
        brand_id="brand-1",
        limit=100,
        only_unclassified=False,
        force_refulfilment=True,
    )

    assert calls == [(5, 5), (5, 5), (1, 5)]
    assert summary["llm_batch_size"] == 5
    assert summary["llm_batches_processed"] == 3
    assert summary["classified"] == 11


def test_classify_telegram_channel_fulfilment_rows_batch_skips_verified_from_llm(monkeypatch) -> None:
    rows = [
        {"id": "row-v", "channel_id": "2000", "channel_username": "pw_official", "is_verified": True},
        {"id": "row-1", "channel_id": "2001", "channel_username": "pw_fake_1", "is_verified": False},
        {"id": "row-2", "channel_id": "2002", "channel_username": "pw_fake_2", "is_verified": False},
        {"id": "row-3", "channel_id": "2003", "channel_username": "pw_fake_3", "is_verified": False},
        {"id": "row-4", "channel_id": "2004", "channel_username": "pw_fake_4", "is_verified": False},
    ]
    writes: list[dict] = []

    def _fake_update(row_id: str, updates: dict):
        writes.append({"row_id": row_id, **deepcopy(updates)})
        return {"id": row_id, "channel_id": row_id, **updates}

    monkeypatch.setattr(tg.db, "update_telegram_channel", _fake_update)
    classifier = _FakeClassifier(
        payload={
            "classification_label": "suspicious_fake",
            "fake_score_10": 8,
            "is_fake": True,
            "should_monitor": True,
            "confidence": 0.8,
            "risk_flags": ["impersonation"],
            "reason": "batch suspicious",
            "evidence": ["batch"],
        }
    )

    out = tg.classify_telegram_channel_fulfilment_rows_batch(
        channel_rows=rows,
        classifier=classifier,
        batch_size=5,
    )

    assert len(out) == 5
    assert classifier.batch_calls == 1
    assert classifier.batch_payload_sizes == [4]
    statuses = [
        (w.get("llm_classification_response") or {}).get("status")
        for w in writes
    ]
    assert "verified_auto_bypass" in statuses


def test_mimicry_policy_calibration_forces_high_fake_score(monkeypatch) -> None:
    writes: list[dict] = []

    def _fake_update(row_id: str, updates: dict):
        writes.append({"row_id": row_id, **deepcopy(updates)})
        return {"id": row_id, "channel_id": "3433855579", **updates}

    monkeypatch.setattr(tg.db, "update_telegram_channel", _fake_update)
    classifier = _FakeClassifier(
        payload={
            "classification_label": "fan_unofficial",
            "fake_score_10": 5,
            "is_fake": False,
            "should_monitor": True,
            "confidence": 0.72,
            "risk_flags": ["pw_brand_misuse"],
            "reason": "LLM initially returned fan_unofficial",
            "evidence": ["title uses physics wala"],
        }
    )

    out = tg.classify_telegram_channel_fulfilment_rows_batch(
        channel_rows=[
            {
                "id": "row-1",
                "channel_id": "3433855579",
                "channel_username": "pwskillshub",
                "channel_title": "PW skills physics wala",
                "channel_description": "notes and resources",
                "is_verified": False,
            }
        ],
        classifier=classifier,
        batch_size=5,
    )

    assert len(out) == 1
    assert out[0]["classification_label"] == "suspicious_fake"
    assert out[0]["fake_score_10"] >= 9
    assert out[0]["is_fake"] is True

    normalized = (writes[0].get("llm_classification_response") or {}).get("normalized") or {}
    assert normalized.get("classification_label") == "suspicious_fake"
    assert int(normalized.get("fake_score_10") or 0) >= 9
    assert normalized.get("is_fake") is True


def test_non_mimic_faculty_channel_calibrates_mid_risk_not_fake(monkeypatch) -> None:
    writes: list[dict] = []

    def _fake_update(row_id: str, updates: dict):
        writes.append({"row_id": row_id, **deepcopy(updates)})
        return {"id": row_id, "channel_id": "2293419199", **updates}

    monkeypatch.setattr(tg.db, "update_telegram_channel", _fake_update)
    classifier = _FakeClassifier(
        payload={
            "classification_label": "suspicious_fake",
            "fake_score_10": 9,
            "is_fake": True,
            "should_monitor": True,
            "confidence": 0.82,
            "risk_flags": ["pw_brand_misuse"],
            "reason": "LLM initially returned high fake",
            "evidence": ["title has physics wallah"],
        }
    )

    out = tg.classify_telegram_channel_fulfilment_rows_batch(
        channel_rows=[
            {
                "id": "row-2",
                "channel_id": "2293419199",
                "channel_username": "mr_sir_physics_wallah_neet_2026",
                "channel_title": "Mr Sir Physics Wallah Neet 2026",
                "channel_description": "Preparation channel",
                "participants_count": 150000,
                "channel_created_at": "2022-01-01T00:00:00+00:00",
                "is_verified": False,
            }
        ],
        classifier=classifier,
        batch_size=5,
    )

    assert len(out) == 1
    assert out[0]["classification_label"] == "fan_unofficial"
    assert 6 <= out[0]["fake_score_10"] <= 7
    assert out[0]["is_fake"] is False

    normalized = (writes[0].get("llm_classification_response") or {}).get("normalized") or {}
    assert normalized.get("classification_label") == "fan_unofficial"
    assert 6 <= int(normalized.get("fake_score_10") or 0) <= 7
    assert normalized.get("is_fake") is False
