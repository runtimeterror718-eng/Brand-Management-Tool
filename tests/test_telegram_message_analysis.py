from __future__ import annotations

from copy import deepcopy

from scrapers import telegram as tg


class _FakeMessageRiskClassifier:
    def __init__(self, payload: dict | None = None, meta: dict | None = None):
        self.payload = payload or {"results": []}
        self.meta = meta or {"status": "completed", "mode": "direct", "provider_response_id": "msg-batch-1"}
        self.batch_calls = 0
        self.batch_payload_sizes: list[int] = []

    def classify_messages_risk_batch(self, message_payloads: list[dict]):
        self.batch_calls += 1
        self.batch_payload_sizes.append(len(message_payloads))
        if self.payload.get("results"):
            return deepcopy(self.payload), deepcopy(self.meta)

        results = []
        for payload in message_payloads:
            message = payload.get("message") if isinstance(payload, dict) else {}
            results.append(
                {
                    "message_row_id": (message or {}).get("message_row_id"),
                    "risk_label": "suspicious",
                    "risk_score": 5.5,
                    "is_suspicious": True,
                    "confidence": 0.82,
                    "risk_flags": ["needs_context", "external_redirect"],
                    "reason": "unclear redirect",
                    "evidence": ["c360.me"],
                }
            )
        return {"results": results}, deepcopy(self.meta)


def test_build_telegram_message_risk_payload_includes_hidden_and_button_links() -> None:
    payload = tg.build_telegram_message_risk_payload(
        message_row={
            "id": "msg-row-1",
            "telegram_channel_id": "chan-row-1",
            "channel_id": "2146022836",
            "channel_username": "pw_mr_sir_neet_physics_wallah",
            "channel_name": "Mr Sir Physics Wallah",
            "discovery_keyword": "physics wallah",
            "message_id": "3984",
            "message_text": "Download pdf fast",
            "media_type": "photo",
            "message_timestamp": "2026-04-02T08:42:07+00:00",
            "views": 419,
            "forwards_count": 2,
            "message_url": "https://t.me/pw_mr_sir_neet_physics_wallah/3984",
            "is_pinned": False,
            "reply_to_message_id": None,
            "sender_username": None,
            "media_metadata": {
                "outbound_links": ["https://terasharelink.com/s/abc"],
                "mentioned_usernames": ["pwhelp"],
            },
            "raw_data": {
                "message": {
                    "entities": [
                        {"url": "https://1024terabox.com/s/xyz"},
                    ],
                    "reply_markup": {
                        "rows": [
                            {
                                "buttons": [
                                    {"url": "https://neet2026.live/Physics-PYQs"},
                                ]
                            }
                        ]
                    },
                    "replies": {"replies": 3},
                }
            },
        },
        channel_row={
            "id": "chan-row-1",
            "channel_title": "Mr Sir Physics Wallah",
            "classification_label": "fan_unofficial",
            "should_monitor": True,
            "is_fake": False,
            "fake_score_10": 6,
            "is_verified": False,
            "participants_count": 150000,
        },
    )

    message = payload["message"]
    assert message["message_row_id"] == "msg-row-1"
    assert message["views"] == 419
    assert message["forwards_count"] == 2
    assert message["reply_count"] == 3
    assert message["visible_links"] == ["https://terasharelink.com/s/abc"]
    assert message["hidden_entity_links"] == ["https://1024terabox.com/s/xyz"]
    assert message["button_urls"] == ["https://neet2026.live/Physics-PYQs"]
    assert message["raw_entities"] == [{"url": "https://1024terabox.com/s/xyz"}]
    assert message["raw_reply_markup"] == {
        "rows": [
            {
                "buttons": [
                    {"url": "https://neet2026.live/Physics-PYQs"},
                ]
            }
        ]
    }
    assert message["all_urls"] == [
        "https://terasharelink.com/s/abc",
        "https://1024terabox.com/s/xyz",
        "https://neet2026.live/Physics-PYQs",
    ]
    assert message["mentioned_usernames"] == ["pwhelp"]
    assert message["channel_context"]["classification_label"] == "fan_unofficial"
    assert message["channel_context"]["fake_score_10"] == 6


def test_normalize_telegram_message_risk_response_maps_watch_to_suspicious() -> None:
    normalized = tg.normalize_telegram_message_risk_response(
        {
            "risk_label": "watch",
            "risk_score": "5.7",
            "is_suspicious": None,
            "confidence": "1.2",
            "risk_flags": ["needs context", "external redirect", "unknown"],
            "reason": "unclear landing page",
            "evidence": ["https://c360.me/x"],
        }
    )

    assert normalized["risk_label"] == "suspicious"
    assert normalized["risk_score"] == 5.7
    assert normalized["is_suspicious"] is True
    assert normalized["confidence"] == 1.0
    assert normalized["risk_flags"] == ["needs_context", "external_redirect"]


def test_message_risk_rule_override_marks_terabox_as_copyright() -> None:
    override = tg._message_risk_rule_override(
        {
            "message": {
                "message_row_id": "row-1",
                "channel_name": "PW Notes",
                "channel_username": "pw_notes",
                "message_text": "Download fast",
                "all_urls": ["https://1024terabox.com/s/1abc"],
            }
        }
    )

    assert override is not None
    assert override["risk_label"] == "copyright_infringement"
    assert "terabox_link" in override["risk_flags"]


def test_message_risk_rule_override_marks_pw_youtube_as_safe() -> None:
    override = tg._message_risk_rule_override(
        {
            "message": {
                "message_row_id": "row-2",
                "channel_name": "Mr Sir Physics Wallah",
                "channel_username": "pw_mr_sir_neet_physics_wallah",
                "message_text": "PW class live now",
                "all_urls": ["https://www.youtube.com/live/JKJQvv8k4kw"],
            }
        }
    )

    assert override is not None
    assert override["risk_label"] == "safe"
    assert override["is_suspicious"] is False


def test_classify_telegram_message_risk_rows_batch_skips_hard_rules_and_llm_for_rest(monkeypatch) -> None:
    writes: list[dict] = []

    def _fake_update(row_id: str, updates: dict):
        writes.append({"row_id": row_id, **deepcopy(updates)})
        return {"id": row_id, **updates}

    monkeypatch.setattr(tg.db, "update_telegram_message", _fake_update)
    classifier = _FakeMessageRiskClassifier()

    out = tg.classify_telegram_message_risk_rows_batch(
        message_rows=[
            {
                "id": "msg-1",
                "channel_id": "1",
                "channel_username": "pw_fake",
                "channel_name": "PW Fake",
                "message_text": "Jaldi se download karlo",
                "media_metadata": {"outbound_links": ["https://terasharelink.com/s/abc"]},
                "raw_data": {},
            },
            {
                "id": "msg-2",
                "channel_id": "2",
                "channel_username": "pw_unclear",
                "channel_name": "PW Unclear",
                "message_text": "Download roadmap",
                "media_metadata": {"outbound_links": ["https://c360.me/PTHFDR/0b4b5e"]},
                "raw_data": {},
            },
        ],
        classifier=classifier,
        channel_rows=[],
        batch_mode="daily",
    )

    assert [row["risk_label"] for row in out] == ["copyright_infringement", "suspicious"]
    assert classifier.batch_calls == 1
    assert classifier.batch_payload_sizes == [1]
    statuses = [(row.get("llm_analysis_response") or {}).get("status") for row in writes]
    assert "policy_rule_bypass" in statuses
    assert "completed" in statuses


def test_run_telegram_message_analysis_pipeline_historical_summarizes_counts(monkeypatch) -> None:
    channels = [
        {"id": "chan-1", "channel_id": "1001", "channel_username": "alpha", "channel_title": "Alpha", "should_monitor": True},
        {"id": "chan-2", "channel_id": "1002", "channel_username": "beta", "channel_title": "Beta", "should_monitor": True},
    ]

    def _fake_get_messages(brand_id=None, channel_id=None, since=None, limit=500):
        if channel_id == "1001":
            return [
                {"id": "m1", "channel_id": "1001", "channel_username": "alpha", "message_text": "PW class", "analyzed_at": None, "llm_analysis_response": None},
                {"id": "m2", "channel_id": "1001", "channel_username": "alpha", "message_text": "download fast", "analyzed_at": None, "llm_analysis_response": None},
            ]
        return [
            {"id": "m3", "channel_id": "1002", "channel_username": "beta", "message_text": "unclear", "analyzed_at": None, "llm_analysis_response": None},
        ]

    def _fake_classify(message_rows, classifier=None, channel_rows=None, batch_mode="historical"):
        results = []
        for row in message_rows:
            label = "safe"
            is_suspicious = False
            if row["id"] == "m2":
                label = "copyright_infringement"
                is_suspicious = True
            elif row["id"] == "m3":
                label = "suspicious"
                is_suspicious = True
            results.append(
                {
                    "status": "analyzed",
                    "message_row_id": row["id"],
                    "channel_id": row["channel_id"],
                    "risk_label": label,
                    "risk_score": 8.5 if label == "copyright_infringement" else (5.0 if label == "suspicious" else 1.0),
                    "is_suspicious": is_suspicious,
                }
            )
        return results

    monkeypatch.setattr(tg.db, "list_telegram_channels_for_brand", lambda **_kwargs: deepcopy(channels))
    monkeypatch.setattr(tg.db, "get_telegram_messages", _fake_get_messages)
    monkeypatch.setattr(tg, "classify_telegram_message_risk_rows_batch", _fake_classify)
    monkeypatch.setattr(
        tg,
        "run_telegram_channel_risk_rollup_summary",
        lambda **_kwargs: {"channels_considered": 2, "updated_channel_rows": 2},
    )

    summary = tg.run_telegram_message_analysis_pipeline(
        brand_id="brand-1",
        mode="historical",
        batch_size=2,
        limit_channels=10,
        max_messages_per_channel=50,
    )

    assert summary["mode"] == "historical"
    assert summary["total_considered"] == 3
    assert summary["analyzed"] == 3
    assert summary["safe"] == 1
    assert summary["suspicious"] == 1
    assert summary["copyright_infringement"] == 1
    assert summary["is_suspicious_count"] == 2
    assert summary["channels_rolled_up"] == 2


def test_run_telegram_message_analysis_pipeline_historical_sleeps_between_llm_chunks(monkeypatch) -> None:
    channels = [
        {"id": "chan-1", "channel_id": "1001", "channel_username": "alpha", "channel_title": "Alpha", "should_monitor": True},
    ]
    message_rows = [
        {
            "id": "m1",
            "channel_id": "1001",
            "channel_username": "alpha",
            "channel_name": "Alpha",
            "message_text": "See https://c360.me/a1",
            "analyzed_at": None,
            "llm_analysis_response": None,
            "raw_data": {},
        },
        {
            "id": "m2",
            "channel_id": "1001",
            "channel_username": "alpha",
            "channel_name": "Alpha",
            "message_text": "See https://c360.me/a2",
            "analyzed_at": None,
            "llm_analysis_response": None,
            "raw_data": {},
        },
        {
            "id": "m3",
            "channel_id": "1001",
            "channel_username": "alpha",
            "channel_name": "Alpha",
            "message_text": "See https://c360.me/a3",
            "analyzed_at": None,
            "llm_analysis_response": None,
            "raw_data": {},
        },
    ]
    sleep_calls: list[int] = []

    def _fake_classify(message_rows, classifier=None, channel_rows=None, batch_mode="historical"):
        results = []
        for row in message_rows:
            results.append(
                {
                    "status": "analyzed",
                    "llm_call_attempted": True,
                    "llm_status": "completed",
                    "message_row_id": row["id"],
                    "channel_id": row["channel_id"],
                    "channel_username": row["channel_username"],
                    "risk_label": "suspicious",
                    "risk_score": 5.0,
                    "is_suspicious": True,
                }
            )
        return results

    monkeypatch.setattr(tg.db, "list_telegram_channels_for_brand", lambda **_kwargs: deepcopy(channels))
    monkeypatch.setattr(tg.db, "get_telegram_messages", lambda **_kwargs: deepcopy(message_rows))
    monkeypatch.setattr(tg, "classify_telegram_message_risk_rows_batch", _fake_classify)
    monkeypatch.setattr(tg, "time", type("FakeTime", (), {"sleep": staticmethod(lambda seconds: sleep_calls.append(seconds))}))
    monkeypatch.setattr(
        tg,
        "run_telegram_channel_risk_rollup_summary",
        lambda **_kwargs: {"channels_considered": 1, "updated_channel_rows": 1},
    )

    summary = tg.run_telegram_message_analysis_pipeline(
        brand_id="brand-1",
        mode="historical",
        batch_size=2,
        limit_channels=10,
        max_messages_per_channel=50,
    )

    assert summary["analyzed"] == 3
    assert sleep_calls == [tg.TELEGRAM_MESSAGE_ANALYSIS_HISTORICAL_LLM_GAP_SECONDS]
