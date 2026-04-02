from __future__ import annotations

from datetime import datetime, timezone

from scrapers import telegram as tg


class _FakeChat:
    def __init__(self):
        self.id = 100100
        self.username = "PW_Official"
        self.title = "Physics Wallah Official"
        self.broadcast = True
        self.megagroup = False
        self.gigagroup = False
        self.verified = True
        self.scam = False
        self.fake = False
        self.photo = object()
        self.participants_count = 42000
        self.date = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "title": self.title,
        }


class _FakeReaction:
    def __init__(self, emoji: str, count: int):
        self.reaction = type("ReactionObj", (), {"emoticon": emoji})()
        self.count = count


class _FakeReactions:
    def __init__(self):
        self.can_see_list = True
        self.results = [_FakeReaction("🔥", 7)]


class _FakeReplyRef:
    reply_to_msg_id = 51


class _FakeSender:
    username = "PWHelpline"


class _FakeMessage:
    def __init__(self):
        self.id = 77
        self.message = "Join https://t.me/pw_channel and ping @PWHelpline"
        self.text = self.message
        self.sender = _FakeSender()
        self.sender_id = 12345
        self.date = datetime(2026, 4, 1, 18, 30, tzinfo=timezone.utc)
        self.views = 900
        self.forwards = 12
        self.reply_to = _FakeReplyRef()
        self.reactions = _FakeReactions()
        self.media = object()
        self.web_preview = object()
        self.pinned = False
        self.voice = None
        self.video = None
        self.photo = None
        self.document = None
        self.sticker = None
        self.poll = None

    def to_dict(self):
        return {
            "id": self.id,
            "message": self.message,
            "entities": [
                {
                    "_": "MessageEntityTextUrl",
                    "url": "https://hidden.example/pw",
                }
            ],
            "reply_markup": {
                "rows": [
                    {
                        "buttons": [
                            {
                                "_": "KeyboardButtonUrl",
                                "text": "Open",
                                "url": "https://button.example/pw",
                            }
                        ]
                    }
                ]
            },
        }


def test_discovered_chat_maps_to_telegram_channel_payload() -> None:
    chat = _FakeChat()

    row = tg.map_discovered_chat_to_channel_row(
        chat=chat,
        brand_id="brand-1",
        discovery_keyword="physics wallah",
        metadata={"about": "Official PW updates", "participants_count": 50000},
    )

    assert row["brand_id"] == "brand-1"
    assert row["channel_id"] == "100100"
    assert row["channel_username"] == "pw_official"
    assert row["channel_title"] == "Physics Wallah Official"
    assert row["channel_type"] == "channel"
    assert row["discovery_keyword"] == "physics wallah"
    assert "classification_label" not in row
    assert "llm_classification_response" not in row
    assert row["public_url"] == "https://t.me/pw_official"
    assert row["is_verified"] is True
    assert "is_scam" not in row
    assert "is_fake" not in row
    assert row["participants_count"] == 50000
    assert row["channel_created_at"] == "2026-01-01T10:00:00+00:00"
    assert row["channel_description"] == "Official PW updates"
    assert row["live_test"] is False
    assert row["raw_data"]["discovery_metadata"]["about"] == "Official PW updates"


def test_channel_classification_normalization_and_monitor_policy() -> None:
    normalized = tg.normalize_channel_classification(
        {
            "label": "Likely Official",
            "confidence": "0.82",
            "reason": "Strong branding and content overlap",
            "signals": ["pw_anchor_match"],
        }
    )

    assert normalized["label"] == "likely_official"
    assert normalized["should_monitor"] is True
    assert normalized["confidence"] == 0.82

    assert tg.should_monitor_for_label("official") is True
    assert tg.should_monitor_for_label("likely_official") is True
    assert tg.should_monitor_for_label("fan_unofficial") is True
    assert tg.should_monitor_for_label("suspicious_fake") is True
    assert tg.should_monitor_for_label("irrelevant") is False


def test_message_maps_to_telegram_message_payload() -> None:
    msg = _FakeMessage()
    channel_row = {
        "id": "row-1",
        "channel_id": "100100",
        "channel_username": "PW_Official",
        "channel_title": "Physics Wallah Official",
        "discovery_keyword": "physics wallah",
        "discovery_source": "keyword_search",
    }

    row = tg.map_telegram_message_to_row(
        message=msg,
        channel_row=channel_row,
        brand_id="brand-1",
    )

    assert row["brand_id"] == "brand-1"
    assert row["telegram_channel_id"] == "row-1"
    assert row["channel_id"] == "100100"
    assert row["message_id"] == "77"
    assert row["message_url"] == "https://t.me/pw_official/77"
    assert row["sender_username"] == "pwhelpline"
    assert row["views"] == 900
    assert row["forwards_count"] == 12
    assert row["media_type"] == "media"
    assert row["media_metadata"]["outbound_links"] == ["https://t.me/pw_channel"]
    assert row["media_metadata"]["mentioned_usernames"] == ["pwhelpline"]
    assert row["raw_data"]["message"]["entities"] == [
        {
            "_": "MessageEntityTextUrl",
            "url": "https://hidden.example/pw",
        }
    ]
    assert row["raw_data"]["message"]["reply_markup"] == {
        "rows": [
            {
                "buttons": [
                    {
                        "_": "KeyboardButtonUrl",
                        "text": "Open",
                        "url": "https://button.example/pw",
                    }
                ]
            }
        ]
    }


def test_incremental_fetch_plan_and_cursor_update() -> None:
    channel_row = {
        "last_message_id": "120",
        "last_message_timestamp": "2026-04-01T17:00:00+00:00",
    }

    incremental_plan = tg.build_message_fetch_plan(
        channel_row=channel_row,
        backfill_limit=30,
        incremental_limit=90,
    )
    assert incremental_plan == {
        "mode": "incremental",
        "min_id": 120,
        "limit": 90,
    }

    backfill_plan = tg.build_message_fetch_plan(
        channel_row={"last_message_id": None},
        backfill_limit=25,
        incremental_limit=90,
    )
    assert backfill_plan == {
        "mode": "backfill",
        "min_id": 0,
        "limit": 25,
    }

    cursor = tg.compute_channel_cursor_update(
        channel_row=channel_row,
        ingested_message_rows=[
            {"message_id": "121", "message_timestamp": "2026-04-01T18:10:00+00:00"},
            {"message_id": "125", "message_timestamp": "2026-04-01T18:25:00+00:00"},
        ],
        checked_at=datetime(2026, 4, 1, 19, 0, tzinfo=timezone.utc),
    )

    assert cursor["last_message_id"] == "125"
    assert cursor["last_message_timestamp"] == "2026-04-01T18:25:00+00:00"
    assert cursor["last_checked_at"] == "2026-04-01T19:00:00+00:00"
