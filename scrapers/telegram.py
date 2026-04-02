"""
Telegram scraper — discovery, channel classification, and incremental monitoring.

Owner: Esha
Libraries: Telethon (MTProto)
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from config.constants import (
    TELEGRAM_AMBIGUOUS_DISCOVERY_TERMS,
    TELEGRAM_CHANNEL_CLASSIFICATION_LABELS,
    TELEGRAM_DISCOVERY_SEED_KEYWORDS,
    TELEGRAM_CHANNEL_FULFILMENT_LLM_BATCH_SIZE,
    TELEGRAM_MESSAGE_ALLOWED_RISK_FLAGS,
    TELEGRAM_MESSAGE_RISK_LABELS,
    TELEGRAM_MESSAGE_SUSPICIOUS_RISK_LABELS,
    TELEGRAM_MONITORED_CLASSIFICATION_LABELS,
)
from config.settings import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_GPT52,
    AZURE_OPENAI_DEPLOYMENT_GPT53,
    AZURE_OPENAI_DEPLOYMENT_GPT54,
    AZURE_OPENAI_ENDPOINT,
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_ACTIVITY_COUNT_SCAN_LIMIT,
    TELEGRAM_ACTIVITY_LOOKBACK_DAYS,
    TELEGRAM_CLASSIFICATION_SAMPLE_MESSAGES,
    TELEGRAM_DISCOVERY_MAX_RESULTS_PER_KEYWORD,
    TELEGRAM_MESSAGE_BACKFILL_LIMIT,
    TELEGRAM_MESSAGE_FETCH_BATCH_SIZE,
    TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MAX_SECONDS,
    TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MIN_SECONDS,
    TELEGRAM_MESSAGE_FETCH_CHANNEL_SLEEP_SECONDS,
    TELEGRAM_MESSAGE_FETCH_DAILY_LOOKBACK_DAYS,
    TELEGRAM_MESSAGE_FETCH_HISTORICAL_MONTHS,
    TELEGRAM_MESSAGE_ANALYSIS_DAILY_BATCH_SIZE,
    TELEGRAM_MESSAGE_ANALYSIS_DAILY_LOOKBACK_HOURS,
    TELEGRAM_MESSAGE_ANALYSIS_HISTORICAL_BATCH_SIZE,
    TELEGRAM_MESSAGE_ANALYSIS_LIMIT_CHANNELS,
    TELEGRAM_MESSAGE_ANALYSIS_MAX_MESSAGES_PER_CHANNEL,
    TELEGRAM_MESSAGE_MEDIA_MAX_BYTES,
    TELEGRAM_MESSAGE_INCREMENTAL_LIMIT,
    TELEGRAM_PHONE,
    TELEGRAM_PIPELINE_PAGE_SIZE,
    TELEGRAM_SESSION_NAME,
)
from scrapers.base import BaseScraper
from search.engine import register_searcher
from search.filters import SearchParams
from storage import queries as db

logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_ANALYSIS_HISTORICAL_LLM_GAP_SECONDS = 5

TELEGRAM_DISCOVERY_SOURCE = "keyword_search"
_LINK_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
_USERNAME_RE = re.compile(r"(?<![\w/])@([A-Za-z0-9_]{4,})")

TELEGRAM_CHANNEL_CLASSIFICATION_PROMPT = (
    "You are a Telegram channel classifier for Physics Wallah (PW) PR-risk monitoring. "
    "Classify each channel into exactly one label using channel metadata and sampled messages. "
    "Labels: official, likely_official, fan_unofficial, suspicious_fake, irrelevant. "
    "Decision guidance: official only when ownership signals are very strong; likely_official when signals are strong but not conclusive; "
    "fan_unofficial for student/community/fan channels discussing PW; suspicious_fake for impersonation/scam/misleading official claims; "
    "irrelevant when PW linkage is weak or absent. "
    "Do not overuse official. Do not classify by sentiment alone. "
    "Return strict JSON with keys: "
    "label (official|likely_official|fan_unofficial|suspicious_fake|irrelevant), "
    "confidence (0..1), reason (string), signals (array of strings), should_monitor (boolean)."
)

TELEGRAM_CHANNEL_FULFILMENT_SYSTEM_PROMPT = """You are a brand-risk and impersonation analyst for Physics Wallah.
Your task is to evaluate Telegram channels only from the perspective of:
- fake/impersonation risk
- misleading official-brand usage
- copyright misuse / reselling / piracy risk
- promotion of non-PW sources under PW-like branding

Do NOT do generic sentiment analysis.
Do NOT judge educational quality generally.
Focus only on whether the channel is official, likely official, fan/unofficial, suspicious fake, or irrelevant from a PR and brand-protection perspective.

Important rules:
- A channel can be unofficial but not fake.
- A channel can be fan-run and still worth monitoring.
- "Official" claims without verification are suspicious.
- Misspelled brand mimicry like "Physics Wala" can be a strong fake signal.
- Description patterns like "For Ads / Collabs" with contact handles are strong reseller/fake signals.
- Promotion of non-PW or third-party material while using PW branding is a strong risk signal.
- Use your knowledge of known Physics Wallah faculty/identity cues (e.g., faculty names) as one signal among many.
- Do not auto-mark every non-verified PW-branded channel as fake; use combined social cues (naming quality, claims, verification, audience/age/activity context).
- Reserve very high fake scores (9-10) for strong mimicry/reseller/impersonation patterns.
- Verified status is helpful but not decisive.
Return strict JSON only."""

TELEGRAM_CHANNEL_FULFILMENT_USER_PROMPT_TEMPLATE = """Analyze this Telegram channel for Physics Wallah brand-risk fulfilment.

Input:
{channel_payload_json}

Return JSON with this exact schema:
{{
  "classification_label": "official|likely_official|fan_unofficial|suspicious_fake|irrelevant",
  "fake_score_10": 0,
  "is_fake": false,
  "should_monitor": true,
  "confidence": 0.0,
  "risk_flags": [
    "impersonation",
    "copyright_risk",
    "third_party_promotion",
    "reseller_behavior",
    "faculty_name_misuse",
    "pw_brand_misuse",
    "ads_collabs_signal",
    "misleading_official_claim",
    "irrelevant"
  ],
  "reason": "short explanation",
  "evidence": [
    "string"
  ]
}}

Decision guidance:
- 0-1 = clearly official or legitimate
- 2-3 = likely legitimate unofficial/fan
- 4-5 = ambiguous
- 6-7 = suspicious
- 8-10 = highly likely fake or impersonating
Calibration guidance:
- Non-verified PW-branded channels without blatant mimicry should usually be mid risk (6-7), not automatic 10.
- Blatant mimicry (e.g., "Physics Wala"/misspellings) with impersonation/reseller cues should be 9-10.
Return JSON only."""

TELEGRAM_CHANNEL_FULFILMENT_BATCH_USER_PROMPT_TEMPLATE = """Analyze these Telegram channels for Physics Wallah brand-risk fulfilment.

Input channels:
{channels_payload_json}

Return JSON with this exact schema:
{{
  "results": [
    {{
      "channel_id": "string",
      "classification_label": "official|likely_official|fan_unofficial|suspicious_fake|irrelevant",
      "fake_score_10": 0,
      "is_fake": false,
      "should_monitor": true,
      "confidence": 0.0,
      "risk_flags": [
        "impersonation",
        "copyright_risk",
        "third_party_promotion",
        "reseller_behavior",
        "faculty_name_misuse",
        "pw_brand_misuse",
        "ads_collabs_signal",
        "misleading_official_claim",
        "irrelevant"
      ],
      "reason": "short explanation",
      "evidence": [
        "string"
      ]
    }}
  ]
}}

Decision guidance:
- 0-1 = clearly official or legitimate
- 2-3 = likely legitimate unofficial/fan
- 4-5 = ambiguous
- 6-7 = suspicious
- 8-10 = highly likely fake or impersonating
Calibration guidance:
- Non-verified PW-branded channels without blatant mimicry should usually be mid risk (6-7), not automatic 10.
- Blatant mimicry (e.g., "Physics Wala"/misspellings) with impersonation/reseller cues should be 9-10.
Process each channel independently and return one result per input channel_id. Return JSON only."""

TELEGRAM_CHANNEL_FULFILMENT_ALLOWED_RISK_FLAGS = frozenset(
    {
        "impersonation",
        "copyright_risk",
        "third_party_promotion",
        "reseller_behavior",
        "faculty_name_misuse",
        "pw_brand_misuse",
        "ads_collabs_signal",
        "misleading_official_claim",
        "irrelevant",
    }
)

TELEGRAM_MESSAGE_RISK_SYSTEM_PROMPT = """You are a Physics Wallah Telegram message-risk analyst.
Assess Telegram messages only for Physics Wallah content-distribution and copyright risk.

Focus only on:
- whether the message is safely promoting PW-owned/PW-related resources
- whether it is suspicious and needs more review/context
- whether it is likely copyright infringement / piracy / competitor-resource distribution

Classification rules:
- `safe`:
  clearly promotes PW or PW faculty resources with no strong misuse signal.
  Official PW YouTube links and clearly PW-oriented updates can be safe.
- `suspicious`:
  ambiguous or needs context, especially unknown external websites, WhatsApp redirects,
  Telegram invite funnels, c360/landing-page style links, or off-platform promos not clearly PW-owned.
- `copyright_infringement`:
  leaked/unauthorized PDFs, modules, notes, backups, competitor resources, or evasion wording like
  "download fast", "deleted soon", "copyright aa jayega", and all Terabox/Terashare links.

Hard rules:
- Any `terabox`, `1024terabox`, `terasharelink`, or `terasharefile` URL is `copyright_infringement`.
- Phrases about downloading quickly before copyright/deletion are strong copyright signals.
- Competitor resources (Allen, Aakash, Resonance, Motion, Vedantu, Unacademy, Narayana, Sri Chaitanya, FIITJEE, etc.) should strongly increase copyright risk.
- Hidden links in button URLs and text URLs matter.
- Do not do generic sentiment analysis.

Return strict JSON only."""

TELEGRAM_MESSAGE_RISK_USER_PROMPT_TEMPLATE = """Analyze this Telegram message for Physics Wallah content-risk.

Input:
{message_payload_json}

Return JSON with this exact schema:
{{
  "risk_label": "safe|suspicious|copyright_infringement",
  "risk_score": 0,
  "is_suspicious": false,
  "confidence": 0.0,
  "risk_flags": [
    "pw_resource_reference",
    "copyright_risk",
    "piracy_signal",
    "external_redirect",
    "third_party_promotion",
    "telegram_invite_link",
    "whatsapp_redirect",
    "terabox_link",
    "competitor_resource",
    "urgency_download_language",
    "copyright_evasion_language",
    "needs_context",
    "irrelevant"
  ],
  "reason": "short explanation",
  "evidence": [
    "string"
  ]
}}

Decision guidance:
- 0-2 = clearly safe / clearly PW-promotional
- 3-6 = suspicious / needs context / unclear external redirect
- 7-10 = copyright infringement / piracy / competitor-resource distribution
Return JSON only."""

TELEGRAM_MESSAGE_RISK_BATCH_USER_PROMPT_TEMPLATE = """Analyze these Telegram messages for Physics Wallah content-risk.

Input messages:
{messages_payload_json}

Return JSON with this exact schema:
{{
  "results": [
    {{
      "message_row_id": "string",
      "risk_label": "safe|suspicious|copyright_infringement",
      "risk_score": 0,
      "is_suspicious": false,
      "confidence": 0.0,
      "risk_flags": [
        "pw_resource_reference",
        "copyright_risk",
        "piracy_signal",
        "external_redirect",
        "third_party_promotion",
        "telegram_invite_link",
        "whatsapp_redirect",
        "terabox_link",
        "competitor_resource",
        "urgency_download_language",
        "copyright_evasion_language",
        "needs_context",
        "irrelevant"
      ],
      "reason": "short explanation",
      "evidence": [
        "string"
      ]
    }}
  ]
}}

Decision guidance:
- `safe`: clearly PW-promotional / PW-resource content with no strong misuse cue
- `suspicious`: ambiguous, unclear external redirects, or off-platform funnels needing review
- `copyright_infringement`: piracy, leaks, competitor resources, copyright-evasion language, Terabox/Terashare
Return one result per input `message_row_id`. Return JSON only."""

PW_SAFE_LINK_DOMAINS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "physicswallah.com",
        "www.physicswallah.com",
        "pw.live",
        "www.pw.live",
        "pwonlyias.com",
        "www.pwonlyias.com",
    }
)

PW_ALWAYS_COPYRIGHT_LINK_DOMAINS = frozenset(
    {
        "terabox.com",
        "www.terabox.com",
        "1024terabox.com",
        "www.1024terabox.com",
        "terasharelink.com",
        "www.terasharelink.com",
        "terasharefile.com",
        "www.terasharefile.com",
    }
)

PW_SUSPICIOUS_LINK_DOMAINS = frozenset(
    {
        "c360.me",
        "whatsapp.com",
        "www.whatsapp.com",
        "chat.whatsapp.com",
        "t.me",
        "neet2026.live",
        "www.neet2026.live",
    }
)

PW_COMPETITOR_TERMS = (
    "allen",
    "aakash",
    "unacademy",
    "vedantu",
    "resonance",
    "motion",
    "narayana",
    "sri chaitanya",
    "fiitjee",
    "fitjee",
    "akash",
)

PW_COPYRIGHT_EVASION_TERMS = (
    "copyright aa jaega",
    "copyright aa jayega",
    "due to copyright",
    "deleted soon",
    "delete soon",
    "before link expires",
    "download before",
    "download fast",
    "jaldi se download",
    "backup alert",
    "fast deleted",
)

PW_URGENCY_DOWNLOAD_TERMS = (
    "download kar",
    "download karlo",
    "download asap",
    "jaldi",
    "jaldi se",
    "join now",
    "expires",
    "expire",
)

PW_RESOURCE_TERMS = (
    "pw notes",
    "pw pdf",
    "physics wallah notes",
    "physics wallah pdf",
    "pw video",
    "pw lecture",
    "pw class",
    "pw module",
)

PW_COPYRIGHT_RESOURCE_TERMS = (
    "module",
    "pdf",
    "notes",
    "drive",
    "recorded lectures",
    "lecture",
    "short notes",
    "backup",
)

PW_ANCHOR_TERMS = (
    "physics wallah",
    "physics wala",
    "physicswallah",
    "physicswala",
    "jee wallah",
    "neet wallah",
    "pw vidyapeeth",
    "pw pathshala",
    "alakh pandey",
    "alakh sir",
    "prateek maheshwari",
    "samriddhi",
    "samridhi",
)

SUSPICIOUS_TERMS = (
    "guaranteed rank",
    "leaked paper",
    "pay and join",
    "admission confirm",
    "official support",
    "refund instantly",
    "double your marks",
    "premium material",
    "hack",
    "scam",
    "fake",
)

FAN_UNOFFICIAL_TERMS = (
    "fan",
    "unofficial",
    "community",
    "students group",
    "doubt group",
)

OFFICIAL_SIGNAL_TERMS = (
    "official",
    "vidyapeeth",
    "pathshala",
    "arjuna",
    "lakshya",
    "udaan",
    "yakeen",
    "prayas",
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(value: datetime | None) -> str:
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_spaces(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _safe_json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _json_safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return _to_iso(value)
    if isinstance(value, bytes):
        return base64.b64encode(value).decode("ascii")
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            out[str(key)] = _json_safe_value(item)
        return out
    if isinstance(value, (list, tuple, set)):
        return [_json_safe_value(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _json_safe_value(to_dict())
        except Exception:
            return str(value)
    return str(value)


def _extract_first_json_object(value: str | None) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {}

    decoded = _safe_json_loads(text)
    if decoded:
        return decoded

    fenced = text
    if fenced.startswith("```"):
        fenced = fenced.strip("`")
        if fenced.startswith("json"):
            fenced = fenced[4:]
        decoded = _safe_json_loads(fenced.strip())
        if decoded:
            return decoded

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return _safe_json_loads(text[start : end + 1])
    return {}


def _safe_tl_object_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        decoded = value
        sanitized = _json_safe_value(decoded)
        return sanitized if isinstance(sanitized, dict) else {}
    to_dict = getattr(value, "to_dict", None)
    if not callable(to_dict):
        return {}
    try:
        decoded = to_dict()
    except Exception:
        return {}
    sanitized = _json_safe_value(decoded)
    return sanitized if isinstance(sanitized, dict) else {}


def normalize_channel_username(value: str | None) -> str:
    username = (value or "").strip().lower()
    if not username:
        return ""
    username = username.replace("https://t.me/", "").replace("http://t.me/", "")
    username = username.split("/", 1)[0]
    if username.startswith("@"):
        username = username[1:]
    return username.strip()


def _safe_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _safe_optional_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return _to_iso(value)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _safe_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_optional_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def build_public_channel_url(username: str | None) -> str | None:
    normalized = normalize_channel_username(username)
    if not normalized:
        return None
    return f"https://t.me/{normalized}"


def should_monitor_for_label(label: str | None) -> bool:
    normalized = normalize_channel_label(label)
    return normalized in TELEGRAM_MONITORED_CLASSIFICATION_LABELS


def normalize_channel_label(label: str | None) -> str:
    raw = _normalize_spaces(str(label or ""))
    if not raw:
        return "irrelevant"

    token = raw.replace("-", "_").replace(" ", "_")
    if token in TELEGRAM_CHANNEL_CLASSIFICATION_LABELS:
        return token

    # Common variants/synonyms from deterministic or LLM outputs.
    if "suspicious" in raw or "fake" in raw or "imperson" in raw or "scam" in raw:
        return "suspicious_fake"
    if "fan" in raw or "unofficial" in raw or "community" in raw:
        return "fan_unofficial"
    if "likely" in raw and "official" in raw:
        return "likely_official"
    if raw.startswith("official") or raw == "owned" or raw == "brand_official":
        return "official"
    return "irrelevant"


def normalize_channel_classification(
    raw: dict[str, Any],
    fallback_reason: str = "",
) -> dict[str, Any]:
    label = normalize_channel_label(
        raw.get("label")
        or raw.get("classification_label")
        or raw.get("channel_label")
    )
    confidence = max(0.0, min(1.0, _safe_float(raw.get("confidence"), default=0.0)))

    signals_raw = raw.get("signals")
    signals: list[str] = []
    if isinstance(signals_raw, list):
        for item in signals_raw:
            text = str(item or "").strip()
            if text:
                signals.append(text)

    reason = str(raw.get("reason") or fallback_reason or "classification_unavailable").strip()

    return {
        "label": label,
        "confidence": confidence,
        "reason": reason,
        "signals": signals,
        "should_monitor": should_monitor_for_label(label),
    }


def build_telegram_channel_fulfilment_payload(channel_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "brand_name": "Physics Wallah",
        "platform": "telegram",
        "task": "channel_fulfilment_fake_risk_scoring",
        "channel": {
            "discovery_keyword": str(channel_row.get("discovery_keyword") or "") or None,
            "channel_id": str(channel_row.get("channel_id") or "") or None,
            "channel_username": (
                normalize_channel_username(channel_row.get("channel_username")) or None
            ),
            "channel_title": str(channel_row.get("channel_title") or "") or None,
            "is_verified": _safe_optional_bool(channel_row.get("is_verified")),
            "channel_type": str(channel_row.get("channel_type") or "") or None,
            "channel_description": str(channel_row.get("channel_description") or "") or None,
            "participants_count": _safe_optional_int(channel_row.get("participants_count")),
            "channel_created_at": _safe_optional_iso(channel_row.get("channel_created_at")),
            "last_message_timestamp": _safe_optional_iso(channel_row.get("last_message_timestamp")),
            "message_count_7d": _safe_optional_int(channel_row.get("message_count_7d")),
        },
    }


def normalize_fulfilment_label(label: str | None) -> str:
    normalized = normalize_channel_label(label)
    if normalized in TELEGRAM_CHANNEL_CLASSIFICATION_LABELS:
        return normalized
    return "irrelevant"


def _normalize_fulfilment_risk_flags(
    value: Any,
    label: str,
) -> list[str]:
    if not isinstance(value, list):
        return ["irrelevant"] if label == "irrelevant" else []

    normalized: list[str] = []
    for item in value:
        token = str(item or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not token:
            continue
        if token not in TELEGRAM_CHANNEL_FULFILMENT_ALLOWED_RISK_FLAGS:
            continue
        if token not in normalized:
            normalized.append(token)
    if label == "irrelevant" and "irrelevant" not in normalized:
        normalized.append("irrelevant")
    return normalized


def _normalize_fulfilment_fake_score(value: Any) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(10, score))


def _normalize_fulfilment_confidence(value: Any) -> float:
    return max(0.0, min(1.0, _safe_float(value, default=0.0)))


def _normalize_fulfilment_is_fake(value: Any, label: str, fake_score_10: int) -> bool:
    explicit = _safe_optional_bool(value)
    if explicit is not None:
        return explicit
    return fake_score_10 >= 8


def _normalize_fulfilment_should_monitor(value: Any, label: str) -> bool:
    if label == "irrelevant":
        return False
    return True


def normalize_telegram_channel_fulfilment_response(
    raw: dict[str, Any],
) -> dict[str, Any]:
    label = normalize_fulfilment_label(raw.get("classification_label") or raw.get("label"))
    fake_score_10 = _normalize_fulfilment_fake_score(raw.get("fake_score_10"))
    confidence = _normalize_fulfilment_confidence(raw.get("confidence"))
    is_fake = _normalize_fulfilment_is_fake(raw.get("is_fake"), label, fake_score_10)
    should_monitor = _normalize_fulfilment_should_monitor(raw.get("should_monitor"), label)

    reason = str(raw.get("reason") or "").strip() or "classification_unavailable"
    evidence_raw = raw.get("evidence")
    evidence: list[str] = []
    if isinstance(evidence_raw, list):
        for item in evidence_raw:
            text = str(item or "").strip()
            if text:
                evidence.append(text)

    return {
        "classification_label": label,
        "fake_score_10": fake_score_10,
        "is_fake": is_fake,
        "should_monitor": should_monitor,
        "confidence": confidence,
        "risk_flags": _normalize_fulfilment_risk_flags(raw.get("risk_flags"), label),
        "reason": reason,
        "evidence": evidence,
    }


def _verified_channel_auto_fulfilment_response(
    channel_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "classification_label": "official",
        "fake_score_10": 0,
        "is_fake": False,
        "should_monitor": False,
        "confidence": 1.0,
        "risk_flags": [],
        "reason": "verified_channel_auto_bypass",
        "evidence": [
            "is_verified=true",
            f"channel_id={channel_payload.get('channel', {}).get('channel_id') or ''}",
        ],
    }


def build_telegram_fulfilment_writeback_updates(
    channel_row: dict[str, Any],
    normalized: dict[str, Any],
    llm_classification_response: dict[str, Any],
) -> dict[str, Any]:
    updates: dict[str, Any] = {
        "llm_classification_response": llm_classification_response,
        "classification_label": normalized["classification_label"],
        "should_monitor": normalized["should_monitor"],
        "is_fake": normalized["is_fake"],
        "updated_at": _to_iso(_now_utc()),
    }
    if "fake_score_10" in channel_row:
        updates["fake_score_10"] = normalized["fake_score_10"]
    if "confidence" in channel_row:
        updates["confidence"] = normalized["confidence"]
    return updates


def _dedupe_text_items(values: Iterable[Any]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        if text not in normalized:
            normalized.append(text)
    return normalized


def _truncate_text(value: Any, max_chars: int = 1200) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _extract_message_links_from_row(message_row: dict[str, Any]) -> dict[str, list[str]]:
    visible_links: list[str] = []
    hidden_entity_links: list[str] = []
    button_urls: list[str] = []
    mentioned_usernames: list[str] = []

    media_metadata = message_row.get("media_metadata")
    if isinstance(media_metadata, dict):
        visible_links.extend(media_metadata.get("outbound_links") or [])
        mentioned_usernames.extend(media_metadata.get("mentioned_usernames") or [])

    raw_data = message_row.get("raw_data")
    raw_message = raw_data.get("message") if isinstance(raw_data, dict) else {}
    if not isinstance(raw_message, dict):
        raw_message = {}

    entities = raw_message.get("entities")
    if isinstance(entities, list):
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            candidate = str(entity.get("url") or "").strip()
            if candidate:
                hidden_entity_links.append(candidate)

    reply_markup = raw_message.get("reply_markup")
    rows = reply_markup.get("rows") if isinstance(reply_markup, dict) else []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            buttons = row.get("buttons")
            if not isinstance(buttons, list):
                continue
            for button in buttons:
                if not isinstance(button, dict):
                    continue
                candidate = str(button.get("url") or "").strip()
                if candidate:
                    button_urls.append(candidate)

    visible_links = _dedupe_text_items(visible_links)
    hidden_entity_links = _dedupe_text_items(hidden_entity_links)
    button_urls = _dedupe_text_items(button_urls)
    all_urls = _dedupe_text_items([*visible_links, *hidden_entity_links, *button_urls])
    mentioned_usernames = _dedupe_text_items(mentioned_usernames)

    return {
        "visible_links": visible_links,
        "hidden_entity_links": hidden_entity_links,
        "button_urls": button_urls,
        "all_urls": all_urls,
        "mentioned_usernames": mentioned_usernames,
    }


def _extract_message_reply_count(message_row: dict[str, Any]) -> int | None:
    raw_data = message_row.get("raw_data")
    raw_message = raw_data.get("message") if isinstance(raw_data, dict) else {}
    if not isinstance(raw_message, dict):
        return None
    replies = raw_message.get("replies")
    if not isinstance(replies, dict):
        return None
    return _safe_optional_int(replies.get("replies"))


def _extract_message_raw_link_context(message_row: dict[str, Any]) -> dict[str, Any]:
    raw_data = message_row.get("raw_data")
    raw_message = raw_data.get("message") if isinstance(raw_data, dict) else {}
    if not isinstance(raw_message, dict):
        raw_message = {}

    raw_entities = raw_message.get("entities")
    if not isinstance(raw_entities, list):
        raw_entities = []

    raw_reply_markup = raw_message.get("reply_markup")
    if not isinstance(raw_reply_markup, dict):
        raw_reply_markup = {}

    return {
        "raw_entities": raw_entities,
        "raw_reply_markup": raw_reply_markup,
    }


def _message_domain(url: str) -> str:
    if not url:
        return ""
    from urllib.parse import urlparse

    parsed = urlparse(url.strip())
    return str(parsed.netloc or "").strip().lower()


def _message_channel_context(channel_row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(channel_row, dict):
        return {}
    return {
        "channel_row_id": str(channel_row.get("id") or "") or None,
        "channel_title": str(channel_row.get("channel_title") or "") or None,
        "classification_label": str(channel_row.get("classification_label") or "") or None,
        "should_monitor": _safe_optional_bool(channel_row.get("should_monitor")),
        "is_fake": _safe_optional_bool(channel_row.get("is_fake")),
        "fake_score_10": _safe_optional_int(channel_row.get("fake_score_10")),
        "is_verified": _safe_optional_bool(channel_row.get("is_verified")),
        "participants_count": _safe_optional_int(channel_row.get("participants_count")),
    }


def build_telegram_message_risk_payload(
    message_row: dict[str, Any],
    channel_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    links = _extract_message_links_from_row(message_row)
    reply_count = _extract_message_reply_count(message_row)
    raw_link_context = _extract_message_raw_link_context(message_row)
    message_text = str(message_row.get("message_text") or "")
    return {
        "brand_name": "Physics Wallah",
        "platform": "telegram",
        "task": "message_content_risk_scoring",
        "message": {
            "message_row_id": str(message_row.get("id") or "") or None,
            "telegram_channel_row_id": str(message_row.get("telegram_channel_id") or "") or None,
            "channel_id": str(message_row.get("channel_id") or "") or None,
            "channel_username": normalize_channel_username(message_row.get("channel_username")) or None,
            "channel_name": str(message_row.get("channel_name") or "") or None,
            "channel_context": _message_channel_context(channel_row),
            "discovery_keyword": str(message_row.get("discovery_keyword") or "") or None,
            "message_id": str(message_row.get("message_id") or "") or None,
            "message_text": _truncate_text(message_text),
            "message_text_length": len(message_text.strip()) if message_text.strip() else 0,
            "media_type": str(message_row.get("media_type") or "") or None,
            "message_timestamp": _safe_optional_iso(message_row.get("message_timestamp")),
            "views": _safe_optional_int(message_row.get("views")),
            "forwards_count": _safe_optional_int(message_row.get("forwards_count")),
            "reply_count": reply_count,
            "reply_to_message_id": str(message_row.get("reply_to_message_id") or "") or None,
            "sender_username": normalize_channel_username(message_row.get("sender_username")) or None,
            "message_url": str(message_row.get("message_url") or "") or None,
            "is_pinned": _safe_optional_bool(message_row.get("is_pinned")),
            **links,
            **raw_link_context,
        },
    }


def normalize_telegram_message_risk_label(label: str | None) -> str:
    raw = _normalize_spaces(str(label or ""))
    token = raw.replace("-", "_").replace(" ", "_")
    if token in TELEGRAM_MESSAGE_RISK_LABELS:
        return token
    if "copyright" in raw or "piracy" in raw or "infringement" in raw:
        return "copyright_infringement"
    if "suspicious" in raw or "high" in raw or "critical" in raw or "watch" in raw or "medium" in raw:
        return "suspicious"
    return "safe"


def _normalize_telegram_message_risk_flags(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        return ["irrelevant"] if label == "safe" else []

    normalized: list[str] = []
    for item in value:
        token = str(item or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not token:
            continue
        if token not in TELEGRAM_MESSAGE_ALLOWED_RISK_FLAGS:
            continue
        if token not in normalized:
            normalized.append(token)

    if label == "safe" and not normalized:
        normalized.append("irrelevant")
    return normalized


def _normalize_telegram_message_risk_score(value: Any) -> float:
    score = _safe_float(value, default=0.0)
    return max(0.0, min(10.0, round(score, 3)))


def _normalize_telegram_message_is_suspicious(
    value: Any,
    label: str,
    risk_score: float,
) -> bool:
    explicit = _safe_optional_bool(value)
    if explicit is not None:
        return explicit
    return label in TELEGRAM_MESSAGE_SUSPICIOUS_RISK_LABELS or risk_score >= 6.0


def normalize_telegram_message_risk_response(raw: dict[str, Any]) -> dict[str, Any]:
    risk_label = normalize_telegram_message_risk_label(
        raw.get("risk_label") or raw.get("label")
    )
    risk_score = _normalize_telegram_message_risk_score(raw.get("risk_score"))
    confidence = _normalize_fulfilment_confidence(raw.get("confidence"))
    is_suspicious = _normalize_telegram_message_is_suspicious(
        raw.get("is_suspicious"),
        risk_label,
        risk_score,
    )

    reason = str(raw.get("reason") or "").strip() or "analysis_unavailable"
    evidence_raw = raw.get("evidence")
    evidence: list[str] = []
    if isinstance(evidence_raw, list):
        for item in evidence_raw:
            text = str(item or "").strip()
            if text:
                evidence.append(text)

    return {
        "risk_label": risk_label,
        "risk_score": risk_score,
        "is_suspicious": is_suspicious,
        "confidence": confidence,
        "risk_flags": _normalize_telegram_message_risk_flags(raw.get("risk_flags"), risk_label),
        "reason": reason,
        "evidence": evidence,
    }


def build_telegram_message_risk_writeback_updates(
    message_row: dict[str, Any],
    normalized: dict[str, Any],
    llm_analysis_response: dict[str, Any],
) -> dict[str, Any]:
    analyzed_at_iso = _to_iso(_now_utc())
    return {
        "risk_label": normalized["risk_label"],
        "risk_score": normalized["risk_score"],
        "is_suspicious": normalized["is_suspicious"],
        "risk_flags": normalized["risk_flags"],
        "llm_analysis_response": llm_analysis_response,
        "analyzed_at": analyzed_at_iso,
    }


def _message_risk_features(message_payload: dict[str, Any]) -> dict[str, Any]:
    message = message_payload.get("message") if isinstance(message_payload, dict) else {}
    if not isinstance(message, dict):
        message = {}

    text_parts = [
        str(message.get("message_text") or ""),
        str(message.get("channel_name") or ""),
        str(message.get("channel_username") or ""),
        str(message.get("discovery_keyword") or ""),
    ]
    combined = _normalize_spaces(" ".join(text_parts))
    urls = _dedupe_text_items(message.get("all_urls") or [])
    domains = [_message_domain(url) for url in urls if _message_domain(url)]

    has_pw_reference = any(term in combined for term in PW_ANCHOR_TERMS) or any(
        term in combined for term in PW_RESOURCE_TERMS
    )
    has_terabox = any(domain in PW_ALWAYS_COPYRIGHT_LINK_DOMAINS for domain in domains)
    has_competitor = any(term in combined for term in PW_COMPETITOR_TERMS)
    has_copyright_evasion = any(term in combined for term in PW_COPYRIGHT_EVASION_TERMS)
    has_urgency = any(term in combined for term in PW_URGENCY_DOWNLOAD_TERMS)
    has_resource_term = any(term in combined for term in PW_COPYRIGHT_RESOURCE_TERMS)
    has_whatsapp = any(domain.endswith("whatsapp.com") for domain in domains)
    has_telegram_invite = any(domain == "t.me" for domain in domains)
    has_safe_domain = bool(domains) and all(domain in PW_SAFE_LINK_DOMAINS for domain in domains)
    has_unknown_external = any(
        domain not in PW_SAFE_LINK_DOMAINS and domain not in PW_ALWAYS_COPYRIGHT_LINK_DOMAINS
        for domain in domains
    )
    has_suspicious_domain = any(domain in PW_SUSPICIOUS_LINK_DOMAINS for domain in domains)

    return {
        "combined": combined,
        "urls": urls,
        "domains": domains,
        "has_pw_reference": has_pw_reference,
        "has_terabox": has_terabox,
        "has_competitor": has_competitor,
        "has_copyright_evasion": has_copyright_evasion,
        "has_urgency": has_urgency,
        "has_resource_term": has_resource_term,
        "has_whatsapp": has_whatsapp,
        "has_telegram_invite": has_telegram_invite,
        "has_safe_domain": has_safe_domain,
        "has_unknown_external": has_unknown_external,
        "has_suspicious_domain": has_suspicious_domain,
    }


def _message_risk_rule_override(message_payload: dict[str, Any]) -> dict[str, Any] | None:
    features = _message_risk_features(message_payload)
    evidence = features["urls"][:3]

    if features["has_terabox"]:
        return {
            "risk_label": "copyright_infringement",
            "risk_score": 10,
            "is_suspicious": True,
            "confidence": 0.99,
            "risk_flags": ["terabox_link", "copyright_risk", "piracy_signal"],
            "reason": "Terabox/Terashare links are treated as unauthorized distribution.",
            "evidence": evidence or [features["combined"][:220]],
        }

    if (features["has_competitor"] and features["has_resource_term"]) or (
        features["has_copyright_evasion"] and (features["has_resource_term"] or bool(features["urls"]))
    ):
        flags = ["copyright_risk", "piracy_signal", "copyright_evasion_language"]
        if features["has_competitor"]:
            flags.append("competitor_resource")
        if features["has_urgency"]:
            flags.append("urgency_download_language")
        return {
            "risk_label": "copyright_infringement",
            "risk_score": 9.2,
            "is_suspicious": True,
            "confidence": 0.95,
            "risk_flags": flags,
            "reason": "Strong copyright-evasion or competitor-resource distribution signal.",
            "evidence": evidence or [features["combined"][:220]],
        }

    if features["has_safe_domain"] and features["has_pw_reference"] and not (
        features["has_competitor"] or features["has_copyright_evasion"] or features["has_urgency"]
    ):
        return {
            "risk_label": "safe",
            "risk_score": 1.0,
            "is_suspicious": False,
            "confidence": 0.93,
            "risk_flags": ["pw_resource_reference"],
            "reason": "Message looks like direct PW resource or PW YouTube promotion.",
            "evidence": evidence or [features["combined"][:220]],
        }

    return None


def _message_risk_heuristic_response(message_payload: dict[str, Any]) -> dict[str, Any]:
    features = _message_risk_features(message_payload)
    combined = features["combined"]
    evidence = features["urls"][:3] or ([combined[:220]] if combined else [])

    if not combined and not features["urls"]:
        return {
            "risk_label": "safe",
            "risk_score": 0.5,
            "is_suspicious": False,
            "confidence": 0.55,
            "risk_flags": ["irrelevant"],
            "reason": "No meaningful text or URL signal present.",
            "evidence": [],
        }

    if features["has_competitor"] and (features["has_resource_term"] or features["has_unknown_external"]):
        return {
            "risk_label": "copyright_infringement",
            "risk_score": 8.8,
            "is_suspicious": True,
            "confidence": 0.82,
            "risk_flags": ["competitor_resource", "copyright_risk", "piracy_signal"],
            "reason": "Competitor resource distribution signal detected.",
            "evidence": evidence,
        }

    if features["has_unknown_external"] or features["has_suspicious_domain"] or features["has_whatsapp"] or features["has_telegram_invite"]:
        flags = ["external_redirect", "needs_context"]
        if features["has_whatsapp"]:
            flags.append("whatsapp_redirect")
        if features["has_telegram_invite"]:
            flags.append("telegram_invite_link")
        return {
            "risk_label": "suspicious",
            "risk_score": 5.2,
            "is_suspicious": True,
            "confidence": 0.72,
            "risk_flags": flags,
            "reason": "Message redirects users to non-PW or unclear destinations.",
            "evidence": evidence,
        }

    if features["has_pw_reference"]:
        return {
            "risk_label": "safe",
            "risk_score": 1.8,
            "is_suspicious": False,
            "confidence": 0.68,
            "risk_flags": ["pw_resource_reference"],
            "reason": "Message appears to reference PW-oriented study content without a strong misuse cue.",
            "evidence": evidence,
        }

    return {
        "risk_label": "suspicious",
        "risk_score": 4.0,
        "is_suspicious": True,
        "confidence": 0.60,
        "risk_flags": ["needs_context"],
        "reason": "Message lacks enough context to safely treat as legitimate PW promotion.",
        "evidence": evidence,
    }


def _apply_message_risk_policy_overrides(
    message_payload: dict[str, Any],
    normalized: dict[str, Any],
) -> dict[str, Any]:
    hard_rule = _message_risk_rule_override(message_payload)
    if hard_rule is None:
        return normalized
    return normalize_telegram_message_risk_response(hard_rule)


def _build_message_channel_context_maps(
    channel_rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_row_id: dict[str, dict[str, Any]] = {}
    by_channel_id: dict[str, dict[str, Any]] = {}
    by_username: dict[str, dict[str, Any]] = {}
    for row in channel_rows:
        row_id = str(row.get("id") or "").strip()
        channel_id = str(row.get("channel_id") or "").strip()
        username = normalize_channel_username(row.get("channel_username"))
        if row_id:
            by_row_id[row_id] = row
        if channel_id:
            by_channel_id[channel_id] = row
        if username:
            by_username[username] = row
    return by_row_id, by_channel_id, by_username


def _resolve_message_channel_context(
    message_row: dict[str, Any],
    channel_maps: tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]],
) -> dict[str, Any] | None:
    by_row_id, by_channel_id, by_username = channel_maps
    row_id = str(message_row.get("telegram_channel_id") or "").strip()
    if row_id and row_id in by_row_id:
        return by_row_id[row_id]
    channel_id = str(message_row.get("channel_id") or "").strip()
    if channel_id and channel_id in by_channel_id:
        return by_channel_id[channel_id]
    username = normalize_channel_username(message_row.get("channel_username"))
    if username and username in by_username:
        return by_username[username]
    return None


def classify_telegram_message_risk_row(
    message_row: dict[str, Any],
    classifier: AzureTelegramChannelClassifier | None = None,
    channel_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    batch_results = classify_telegram_message_risk_rows_batch(
        message_rows=[message_row],
        classifier=classifier,
        channel_rows=[channel_row] if isinstance(channel_row, dict) else None,
        batch_mode="single",
    )
    if batch_results:
        return batch_results[0]
    return {
        "status": "failed",
        "message_row_id": message_row.get("id"),
    }


def classify_telegram_message_risk_rows_batch(
    message_rows: list[dict[str, Any]],
    classifier: AzureTelegramChannelClassifier | None = None,
    channel_rows: list[dict[str, Any]] | None = None,
    batch_mode: str = "daily",
) -> list[dict[str, Any]]:
    if not message_rows:
        return []

    classifier = classifier or _scraper._classifier
    channel_maps = _build_message_channel_context_maps(channel_rows or [])
    now_iso = _to_iso(_now_utc())
    ordered_results: list[dict[str, Any]] = []

    llm_rows: list[dict[str, Any]] = []
    llm_payloads: list[dict[str, Any]] = []
    payload_by_message_row_id: dict[str, dict[str, Any]] = {}

    for message_row in message_rows:
        channel_row = _resolve_message_channel_context(message_row, channel_maps)
        payload = build_telegram_message_risk_payload(
            message_row=message_row,
            channel_row=channel_row,
        )
        message_row_id = str(payload.get("message", {}).get("message_row_id") or "").strip()
        if not message_row_id:
            continue
        payload_by_message_row_id[message_row_id] = payload

        hard_rule = _message_risk_rule_override(payload)
        if hard_rule is not None:
            normalized = normalize_telegram_message_risk_response(hard_rule)
            llm_response = {
                "status": "policy_rule_bypass",
                "mode": batch_mode,
                "provider_response_id": None,
                "error": None,
                "analyzed_at": now_iso,
                "input_payload": payload,
                "raw_response": hard_rule,
                "normalized": normalized,
            }
            updates = build_telegram_message_risk_writeback_updates(
                message_row=message_row,
                normalized=normalized,
                llm_analysis_response=llm_response,
            )
            updated = db.update_telegram_message(message_row["id"], updates)
            ordered_results.append(
                {
                    "status": "analyzed",
                    "llm_call_attempted": False,
                    "llm_status": "policy_rule_bypass",
                    "message_row_id": updated.get("id", message_row.get("id")),
                    "channel_id": updated.get("channel_id", message_row.get("channel_id")),
                    "channel_username": updated.get("channel_username", message_row.get("channel_username")),
                    "risk_label": normalized["risk_label"],
                    "risk_score": normalized["risk_score"],
                    "is_suspicious": normalized["is_suspicious"],
                }
            )
            continue

        llm_rows.append(message_row)
        llm_payloads.append(payload)

    raw_result_map: dict[str, dict[str, Any]] = {}
    llm_meta: dict[str, Any] = {
        "mode": batch_mode,
        "status": "not_called",
    }
    llm_call_attempted = bool(llm_payloads)
    if llm_payloads:
        raw_batch, llm_meta = classifier.classify_messages_risk_batch(llm_payloads)
        raw_results = raw_batch.get("results") if isinstance(raw_batch, dict) else None
        if isinstance(raw_results, list):
            for item in raw_results:
                if not isinstance(item, dict):
                    continue
                message_row_id = str(item.get("message_row_id") or "").strip()
                if message_row_id:
                    raw_result_map[message_row_id] = item
        else:
            raw_batch = {}

    for message_row in llm_rows:
        message_row_id = str(message_row.get("id") or "").strip()
        payload = payload_by_message_row_id.get(message_row_id, {})
        raw_item = raw_result_map.get(message_row_id)

        if llm_meta.get("status") == "completed" and isinstance(raw_item, dict):
            normalized = normalize_telegram_message_risk_response(raw_item)
            normalized = _apply_message_risk_policy_overrides(payload, normalized)
            status = "completed"
            raw_response = raw_item
            error = llm_meta.get("error")
        else:
            heuristic = _message_risk_heuristic_response(payload)
            normalized = normalize_telegram_message_risk_response(heuristic)
            normalized = _apply_message_risk_policy_overrides(payload, normalized)
            status = "heuristic_fallback"
            raw_response = heuristic
            error = llm_meta.get("error")

        llm_response = {
            "status": status,
            "mode": batch_mode,
            "provider_response_id": llm_meta.get("provider_response_id"),
            "error": error,
            "analyzed_at": now_iso,
            "input_payload": payload,
            "raw_response": raw_response,
            "normalized": normalized,
        }
        updates = build_telegram_message_risk_writeback_updates(
            message_row=message_row,
            normalized=normalized,
            llm_analysis_response=llm_response,
        )
        updated = db.update_telegram_message(message_row["id"], updates)
        ordered_results.append(
            {
                "status": "analyzed",
                "llm_call_attempted": llm_call_attempted,
                "llm_status": status,
                "message_row_id": updated.get("id", message_row.get("id")),
                "channel_id": updated.get("channel_id", message_row.get("channel_id")),
                "channel_username": updated.get("channel_username", message_row.get("channel_username")),
                "risk_label": normalized["risk_label"],
                "risk_score": normalized["risk_score"],
                "is_suspicious": normalized["is_suspicious"],
            }
        )

    row_positions = {
        str(row.get("id") or ""): idx
        for idx, row in enumerate(message_rows)
        if str(row.get("id") or "")
    }
    ordered_results.sort(
        key=lambda item: row_positions.get(str(item.get("message_row_id") or ""), 10**9)
    )
    return ordered_results


def _build_channel_rollup_from_messages(
    channel_id: str,
    messages: list[dict[str, Any]],
) -> dict[str, Any]:
    analyzed = [m for m in messages if m.get("analyzed_at")]
    copyright_rows = [
        m for m in analyzed
        if normalize_telegram_message_risk_label(m.get("risk_label")) == "copyright_infringement"
    ]
    suspicious = [
        m for m in analyzed
        if normalize_telegram_message_risk_label(m.get("risk_label")) == "suspicious"
    ]
    unsafe = [m for m in analyzed if bool(m.get("is_suspicious"))]
    safe = [m for m in analyzed if normalize_telegram_message_risk_label(m.get("risk_label")) == "safe"]
    risk_scores = [_safe_float(m.get("risk_score"), 0.0) for m in analyzed]

    flag_counter: dict[str, int] = {}
    last_ts = None
    for m in analyzed:
        ts = _safe_optional_iso(m.get("message_timestamp"))
        if ts and (not last_ts or ts > last_ts):
            last_ts = ts
        flags = m.get("risk_flags")
        if isinstance(flags, list):
            for flag in flags:
                token = str(flag or "").strip()
                if not token:
                    continue
                flag_counter[token] = flag_counter.get(token, 0) + 1

    top_flags = sorted(
        flag_counter.items(),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )[:5]

    return {
        "channel_id": channel_id,
        "message_count_total": len(messages),
        "message_count_analyzed": len(analyzed),
        "safe_count": len(safe),
        "suspicious_count": len(suspicious),
        "copyright_infringement_count": len(copyright_rows),
        "unsafe_count": len(unsafe),
        "avg_risk_score": round((sum(risk_scores) / len(risk_scores)), 3) if risk_scores else 0.0,
        "max_risk_score": round(max(risk_scores), 3) if risk_scores else 0.0,
        "latest_analyzed_message_timestamp": last_ts,
        "top_risk_flags": [{"flag": flag, "count": count} for flag, count in top_flags],
        "rolled_up_at": _to_iso(_now_utc()),
    }


def run_telegram_message_analysis_pipeline(
    brand_id: str | None = None,
    mode: str = "daily",
    limit: int = 500,
    only_unanalyzed: bool = True,
    message_since_hours: int | None = None,
    force_reanalysis: bool = False,
    target_channels: Iterable[str] | None = None,
    batch_size: int | None = None,
    limit_channels: int = TELEGRAM_MESSAGE_ANALYSIS_LIMIT_CHANNELS,
    max_messages_per_channel: int = TELEGRAM_MESSAGE_ANALYSIS_MAX_MESSAGES_PER_CHANNEL,
    persist_channel_rollup: bool = True,
) -> dict[str, Any]:
    if not brand_id:
        return {
            "phase": "telegram_message_analysis",
            "status": "skipped_missing_brand_id",
        }

    normalized_mode = str(mode or "daily").strip().lower()
    if normalized_mode not in {"historical", "daily"}:
        normalized_mode = "daily"

    target_ids, target_usernames = normalize_channel_targets(target_channels or [])
    monitored_channels = db.list_telegram_channels_for_brand(
        brand_id=brand_id,
        should_monitor=True,
        limit=max(1, _safe_int(limit_channels, default=TELEGRAM_MESSAGE_ANALYSIS_LIMIT_CHANNELS)),
    )

    if target_ids or target_usernames:
        filtered_channels: list[dict[str, Any]] = []
        for row in monitored_channels:
            channel_id = str(row.get("channel_id") or "").strip()
            channel_username = normalize_channel_username(row.get("channel_username"))
            if channel_id in target_ids or channel_username in target_usernames:
                filtered_channels.append(row)
        monitored_channels = filtered_channels

    channel_maps = _build_message_channel_context_maps(monitored_channels)
    resolved_batch_size = max(
        1,
        _safe_int(
            batch_size,
            default=(
                TELEGRAM_MESSAGE_ANALYSIS_HISTORICAL_BATCH_SIZE
                if normalized_mode == "historical"
                else TELEGRAM_MESSAGE_ANALYSIS_DAILY_BATCH_SIZE
            ),
        ),
    )
    resolved_message_since_hours = message_since_hours
    if normalized_mode == "daily" and resolved_message_since_hours is None:
        resolved_message_since_hours = TELEGRAM_MESSAGE_ANALYSIS_DAILY_LOOKBACK_HOURS

    summary: dict[str, Any] = {
        "phase": "telegram_message_analysis",
        "brand_id": brand_id,
        "mode": normalized_mode,
        "total_considered": 0,
        "analyzed": 0,
        "safe": 0,
        "suspicious": 0,
        "copyright_infringement": 0,
        "is_suspicious_count": 0,
        "failed": 0,
        "llm_batches_processed": 0,
        "batch_size": resolved_batch_size,
        "channels_considered": len(monitored_channels),
        "channels_with_messages": 0,
        "only_unanalyzed": bool(only_unanalyzed and not force_reanalysis),
        "force_reanalysis": bool(force_reanalysis),
        "message_since_hours": resolved_message_since_hours,
        "limit": max(1, _safe_int(limit, default=500)),
        "limit_channels": max(1, _safe_int(limit_channels, default=TELEGRAM_MESSAGE_ANALYSIS_LIMIT_CHANNELS)),
        "max_messages_per_channel": max(
            1,
            _safe_int(max_messages_per_channel, default=TELEGRAM_MESSAGE_ANALYSIS_MAX_MESSAGES_PER_CHANNEL),
        ),
        "ran_at": _to_iso(_now_utc()),
    }

    classifier = _scraper._classifier
    analyzed_channel_targets: list[str] = []

    if normalized_mode == "historical":
        for channel_row in monitored_channels:
            channel_id = str(channel_row.get("channel_id") or "").strip()
            if not channel_id:
                continue
            channel_messages = db.get_telegram_messages(
                brand_id=brand_id,
                channel_id=channel_id,
                limit=max(
                    1,
                    _safe_int(
                        max_messages_per_channel,
                        default=TELEGRAM_MESSAGE_ANALYSIS_MAX_MESSAGES_PER_CHANNEL,
                    ),
                ),
            )
            eligible_rows = []
            for row in channel_messages:
                if bool(only_unanalyzed and not force_reanalysis) and not db._telegram_message_needs_analysis(row):
                    continue
                eligible_rows.append(row)

            if not eligible_rows:
                continue

            summary["channels_with_messages"] += 1
            summary["total_considered"] += len(eligible_rows)
            analyzed_channel_targets.append(channel_id)

            chunks = _paginate(eligible_rows, resolved_batch_size)
            for idx, chunk in enumerate(chunks):
                summary["llm_batches_processed"] += 1
                try:
                    batch_results = classify_telegram_message_risk_rows_batch(
                        message_rows=chunk,
                        classifier=classifier,
                        channel_rows=[channel_row],
                        batch_mode="historical",
                    )
                except Exception:
                    logger.exception(
                        "Telegram historical message analysis failed for channel_id=%s",
                        channel_id,
                    )
                    summary["failed"] += len(chunk)
                    continue

                for result in batch_results:
                    if result.get("status") != "analyzed":
                        continue
                    summary["analyzed"] += 1
                    label = normalize_telegram_message_risk_label(result.get("risk_label"))
                    if label in summary:
                        summary[label] += 1
                    if bool(result.get("is_suspicious")):
                        summary["is_suspicious_count"] += 1

                if (
                    idx < (len(chunks) - 1)
                    and any(bool(result.get("llm_call_attempted")) for result in batch_results)
                ):
                    time.sleep(TELEGRAM_MESSAGE_ANALYSIS_HISTORICAL_LLM_GAP_SECONDS)
    else:
        rows = db.list_telegram_messages_for_analysis(
            brand_id=brand_id,
            only_unanalyzed=bool(only_unanalyzed and not force_reanalysis),
            message_since_hours=resolved_message_since_hours,
            limit=max(1, _safe_int(limit, default=500)),
            target_channel_ids=list(target_ids),
            target_channel_usernames=list(target_usernames),
        )

        eligible_rows: list[dict[str, Any]] = []
        for row in rows:
            channel_row = _resolve_message_channel_context(row, channel_maps)
            if channel_row is None:
                continue
            eligible_rows.append(row)
            channel_id = str(channel_row.get("channel_id") or "").strip()
            if channel_id and channel_id not in analyzed_channel_targets:
                analyzed_channel_targets.append(channel_id)

        summary["total_considered"] = len(eligible_rows)
        summary["channels_with_messages"] = len(
            {
                str(row.get("channel_id") or "").strip()
                for row in eligible_rows
                if str(row.get("channel_id") or "").strip()
            }
        )

        for chunk in _paginate(eligible_rows, resolved_batch_size):
            summary["llm_batches_processed"] += 1
            channel_rows = []
            seen_channel_row_ids: set[str] = set()
            for row in chunk:
                channel_row = _resolve_message_channel_context(row, channel_maps)
                channel_row_id = str((channel_row or {}).get("id") or "").strip()
                if channel_row_id and channel_row_id not in seen_channel_row_ids:
                    channel_rows.append(channel_row)
                    seen_channel_row_ids.add(channel_row_id)

            try:
                batch_results = classify_telegram_message_risk_rows_batch(
                    message_rows=chunk,
                    classifier=classifier,
                    channel_rows=channel_rows,
                    batch_mode="daily",
                )
            except Exception:
                logger.exception("Telegram daily message analysis batch failed")
                summary["failed"] += len(chunk)
                continue

            for result in batch_results:
                if result.get("status") != "analyzed":
                    continue
                summary["analyzed"] += 1
                label = normalize_telegram_message_risk_label(result.get("risk_label"))
                if label in summary:
                    summary[label] += 1
                if bool(result.get("is_suspicious")):
                    summary["is_suspicious_count"] += 1

    rollup_summary = {
        "channels_considered": 0,
        "updated_channel_rows": 0,
    }
    if persist_channel_rollup and analyzed_channel_targets:
        rollup_summary = run_telegram_channel_risk_rollup_summary(
            brand_id=brand_id,
            message_since_hours=(resolved_message_since_hours if normalized_mode == "daily" else None),
            max_messages_per_channel=max_messages_per_channel,
            limit_channels=limit_channels,
            target_channels=analyzed_channel_targets,
            persist_to_channels=True,
        )

    summary["channels_rolled_up"] = rollup_summary.get("channels_considered", 0)
    summary["updated_channel_rows"] = rollup_summary.get("updated_channel_rows", 0)
    summary["rollup_summary"] = rollup_summary
    return summary


def run_telegram_message_suspicious_activity_analysis(
    brand_id: str | None = None,
    limit: int = 300,
    only_unanalyzed: bool = True,
    message_since_hours: int | None = None,
    force_reanalysis: bool = False,
    target_channels: Iterable[str] | None = None,
    mode: str = "daily",
    batch_size: int | None = None,
    limit_channels: int = TELEGRAM_MESSAGE_ANALYSIS_LIMIT_CHANNELS,
    max_messages_per_channel: int = TELEGRAM_MESSAGE_ANALYSIS_MAX_MESSAGES_PER_CHANNEL,
    persist_channel_rollup: bool = True,
) -> dict[str, Any]:
    return run_telegram_message_analysis_pipeline(
        brand_id=brand_id,
        mode=mode,
        limit=limit,
        only_unanalyzed=only_unanalyzed,
        message_since_hours=message_since_hours,
        force_reanalysis=force_reanalysis,
        target_channels=target_channels,
        batch_size=batch_size,
        limit_channels=limit_channels,
        max_messages_per_channel=max_messages_per_channel,
        persist_channel_rollup=persist_channel_rollup,
    )


def run_telegram_channel_risk_rollup_summary(
    brand_id: str | None = None,
    message_since_hours: int | None = 24,
    max_messages_per_channel: int = 500,
    limit_channels: int = 300,
    target_channels: Iterable[str] | None = None,
    persist_to_channels: bool = True,
) -> dict[str, Any]:
    channels = db.list_telegram_channels_for_brand(
        brand_id=brand_id,
        limit=max(1, _safe_int(limit_channels, default=300)),
    )
    target_ids, target_usernames = normalize_channel_targets(target_channels or [])

    since = None
    if message_since_hours is not None and int(message_since_hours) > 0:
        since = _now_utc() - timedelta(hours=int(message_since_hours))

    rollups: list[dict[str, Any]] = []
    updated_channels = 0
    for channel_row in channels:
        channel_id = str(channel_row.get("channel_id") or "").strip()
        if not channel_id:
            continue
        channel_username = normalize_channel_username(channel_row.get("channel_username"))
        if target_ids or target_usernames:
            if channel_id not in target_ids and channel_username not in target_usernames:
                continue

        messages = db.get_telegram_messages(
            brand_id=brand_id,
            channel_id=channel_id,
            since=since,
            limit=max(1, _safe_int(max_messages_per_channel, default=500)),
        )
        rollup = _build_channel_rollup_from_messages(channel_id=channel_id, messages=messages)
        rollup["channel_row_id"] = channel_row.get("id")
        rollup["channel_username"] = channel_username or None
        rollup["channel_name"] = channel_row.get("channel_title")
        rollups.append(rollup)

        if persist_to_channels:
            updates = {
                "updated_at": _to_iso(_now_utc()),
            }
            if "message_risk_rollup" in channel_row:
                updates["message_risk_rollup"] = rollup
            if "message_risk_rollup_at" in channel_row:
                updates["message_risk_rollup_at"] = _to_iso(_now_utc())
            if len(updates) > 1:
                try:
                    db.update_telegram_channel(channel_row["id"], updates)
                    updated_channels += 1
                except Exception:
                    logger.debug(
                        "Telegram channel rollup persistence failed for channel_id=%s",
                        channel_id,
                    )

    rollups.sort(
        key=lambda item: (
            _safe_int(item.get("unsafe_count"), 0),
            _safe_float(item.get("max_risk_score"), 0.0),
        ),
        reverse=True,
    )
    return {
        "phase": "telegram_channel_message_risk_rollup",
        "brand_id": brand_id,
        "channels_considered": len(rollups),
        "channels_with_suspicious": sum(1 for r in rollups if _safe_int(r.get("unsafe_count"), 0) > 0),
        "total_suspicious_messages": sum(_safe_int(r.get("suspicious_count"), 0) for r in rollups),
        "total_copyright_infringement_messages": sum(
            _safe_int(r.get("copyright_infringement_count"), 0) for r in rollups
        ),
        "total_unsafe_messages": sum(_safe_int(r.get("unsafe_count"), 0) for r in rollups),
        "total_safe_messages": sum(_safe_int(r.get("safe_count"), 0) for r in rollups),
        "updated_channel_rows": updated_channels,
        "message_since_hours": message_since_hours,
        "max_messages_per_channel": max(1, _safe_int(max_messages_per_channel, default=500)),
        "limit_channels": max(1, _safe_int(limit_channels, default=300)),
        "channel_rollups": rollups,
        "ran_at": _to_iso(_now_utc()),
    }


def _extract_message_entities(text: str) -> dict[str, list[str]]:
    if not text:
        return {"links": [], "usernames": []}
    links = sorted(set(_LINK_RE.findall(text)))
    usernames = sorted({u.lower() for u in _USERNAME_RE.findall(text)})
    return {
        "links": links,
        "usernames": usernames,
    }


def _message_media_type(message: Any) -> str:
    if getattr(message, "voice", None):
        return "voice"
    if getattr(message, "video", None):
        return "video"
    if getattr(message, "photo", None):
        return "photo"
    if getattr(message, "document", None):
        return "document"
    if getattr(message, "sticker", None):
        return "sticker"
    if getattr(message, "poll", None):
        return "poll"
    if getattr(message, "media", None):
        return "media"
    return "text"


def _serialize_reactions(message: Any) -> dict[str, Any]:
    reactions = getattr(message, "reactions", None)
    if reactions is None:
        return {}

    payload: dict[str, Any] = {
        "can_see_list": bool(getattr(reactions, "can_see_list", False)),
        "recent_reactions": [],
    }

    results = getattr(reactions, "results", None)
    if isinstance(results, list):
        serialized = []
        for item in results:
            emoji = None
            reaction_obj = getattr(item, "reaction", None)
            if reaction_obj is not None:
                emoji = getattr(reaction_obj, "emoticon", None)
            if not emoji:
                emoji = str(reaction_obj or "")
            serialized.append({
                "emoji": emoji,
                "count": _safe_int(getattr(item, "count", 0)),
            })
        payload["recent_reactions"] = serialized

    return payload


def _channel_type_from_chat(chat: Any) -> str:
    if bool(getattr(chat, "broadcast", False)):
        return "channel"
    if bool(getattr(chat, "megagroup", False) or getattr(chat, "gigagroup", False)):
        return "group"
    return "chat"


def map_discovered_chat_to_channel_row(
    chat: Any,
    brand_id: str | None,
    discovery_keyword: str,
    metadata: dict[str, Any] | None = None,
    discovered_at: datetime | None = None,
) -> dict[str, Any]:
    discovered_at = discovered_at or _now_utc()
    username = normalize_channel_username(getattr(chat, "username", None))
    channel_id = str(getattr(chat, "id", "") or "").strip()
    title = str(getattr(chat, "title", "") or "").strip()
    metadata_map = metadata if isinstance(metadata, dict) else {}
    raw_chat = _safe_tl_object_dict(chat)

    participants_count = _safe_int(getattr(chat, "participants_count", 0))
    if metadata_map.get("participants_count") is not None:
        participants_count = _safe_int(metadata_map.get("participants_count"))

    public_url = str(
        metadata_map.get("public_url")
        or build_public_channel_url(username)
        or ""
    ).strip() or None

    live_test_run_at = str(metadata_map.get("live_test_run_at") or "").strip() or None
    created_at = getattr(chat, "date", None)
    created_at_iso = _to_iso(created_at if isinstance(created_at, datetime) else None) or None
    channel_description = str(
        metadata_map.get("about")
        or metadata_map.get("channel_description")
        or ""
    ).strip() or None

    return {
        "brand_id": brand_id,
        "channel_id": channel_id,
        "channel_username": username or None,
        "channel_title": title or None,
        "channel_type": _channel_type_from_chat(chat),
        "discovery_keyword": discovery_keyword,
        "discovery_source": TELEGRAM_DISCOVERY_SOURCE,
        # Discovery-mode explicit metadata columns.
        "public_url": public_url,
        "is_verified": bool(metadata_map.get("is_verified", getattr(chat, "verified", False))),
        "participants_count": participants_count,
        "live_test": bool(metadata_map.get("live_test", False)),
        "live_test_run_at": live_test_run_at,
        "channel_created_at": created_at_iso,
        "channel_description": channel_description,
        "updated_at": _to_iso(discovered_at),
        "raw_data": {
            "chat": raw_chat,
            "discovered_at": _to_iso(discovered_at),
            "discovery_keyword": discovery_keyword,
            "discovery_metadata": metadata_map,
        },
    }


def map_telegram_message_to_row(
    message: Any,
    channel_row: dict[str, Any],
    brand_id: str | None,
) -> dict[str, Any]:
    message_text = str(
        getattr(message, "message", None)
        or getattr(message, "text", None)
        or ""
    ).strip()
    message_id = str(getattr(message, "id", "") or "").strip()
    channel_username = normalize_channel_username(channel_row.get("channel_username"))
    entities = _extract_message_entities(message_text)

    sender_username = ""
    sender = getattr(message, "sender", None)
    if sender is not None:
        sender_username = normalize_channel_username(getattr(sender, "username", None))

    reply_to = getattr(message, "reply_to", None)
    reply_to_message_id = str(getattr(reply_to, "reply_to_msg_id", "") or "").strip() or None

    timestamp = getattr(message, "date", None)
    timestamp_iso = _to_iso(timestamp if isinstance(timestamp, datetime) else _now_utc())

    message_url = None
    if channel_username and message_id:
        message_url = f"https://t.me/{channel_username}/{message_id}"

    raw_payload = _safe_tl_object_dict(message)

    return {
        "brand_id": brand_id,
        "telegram_channel_id": channel_row.get("id"),
        "channel_id": str(channel_row.get("channel_id") or "").strip() or None,
        "channel_name": channel_row.get("channel_title"),
        "channel_username": channel_username or None,
        "message_id": message_id or None,
        "message_text": message_text,
        "media_type": _message_media_type(message),
        "media_metadata": {
            "has_media": bool(getattr(message, "media", None)),
            "has_link_preview": bool(getattr(message, "web_preview", None)),
            "outbound_links": entities["links"],
            "mentioned_usernames": entities["usernames"],
        },
        "sender_username": sender_username or None,
        "sender_id": str(getattr(message, "sender_id", "") or "").strip() or None,
        "views": _safe_int(getattr(message, "views", 0)),
        "forwards_count": _safe_int(getattr(message, "forwards", 0)),
        "reply_to_message_id": reply_to_message_id,
        "reactions": _serialize_reactions(message),
        "message_timestamp": timestamp_iso,
        "message_url": message_url,
        "is_pinned": bool(getattr(message, "pinned", False)),
        "discovery_keyword": channel_row.get("discovery_keyword"),
        "discovery_source": channel_row.get("discovery_source") or TELEGRAM_DISCOVERY_SOURCE,
        "scraped_at": _to_iso(_now_utc()),
        "raw_data": {
            "message": raw_payload,
            "entities": entities,
            "channel": {
                "channel_id": channel_row.get("channel_id"),
                "channel_username": channel_username,
                "channel_title": channel_row.get("channel_title"),
            },
        },
    }


def map_telegram_message_to_search_result(
    message: Any,
    channel_row: dict[str, Any],
) -> dict[str, Any]:
    row = map_telegram_message_to_row(message=message, channel_row=channel_row, brand_id=None)
    return {
        "id": f"{row.get('channel_id') or ''}:{row.get('message_id') or ''}",
        "platform_ref_id": f"{row.get('channel_id') or ''}:{row.get('message_id') or ''}",
        "content_text": row.get("message_text") or "",
        "content_type": "voice" if row.get("media_type") == "voice" else "text",
        "author_handle": row.get("sender_username") or row.get("sender_id") or "",
        "author_name": "",
        "engagement_score": _safe_int(row.get("views")),
        "likes": _safe_int(row.get("forwards_count")),
        "shares": _safe_int(row.get("forwards_count")),
        "comments_count": 0,
        "source_url": row.get("message_url") or channel_row.get("public_url") or "",
        "published_at": row.get("message_timestamp"),
        "language": "en",
        "raw_data": row.get("raw_data") or {},
    }


def _channel_metadata_for_classification(channel_row: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}

    # Explicit DB columns (preferred).
    for key in (
        "public_url",
        "is_verified",
        "participants_count",
        "live_test",
        "live_test_run_at",
        "channel_description",
    ):
        value = channel_row.get(key)
        if value is not None:
            metadata[key] = value

    # Discovery metadata may carry fields like about/linked_chat_id.
    raw_data = channel_row.get("raw_data")
    if isinstance(raw_data, dict):
        discovery_metadata = raw_data.get("discovery_metadata")
        if isinstance(discovery_metadata, dict):
            for key, value in discovery_metadata.items():
                if value is not None and key not in metadata:
                    metadata[key] = value

    return metadata


def build_discovery_keywords(
    keywords: Iterable[str] | None = None,
    brand_keywords: Iterable[str] | None = None,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    for source in (keywords or [], brand_keywords or [], TELEGRAM_DISCOVERY_SEED_KEYWORDS):
        normalized = _normalize_spaces(str(source or ""))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)

    return prioritize_discovery_keywords(ordered)


def prioritize_discovery_keywords(keywords: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for item in keywords:
        keyword = _normalize_spaces(str(item or ""))
        if not keyword or keyword in seen:
            continue
        seen.add(keyword)
        normalized.append(keyword)

    seed_position = {
        _normalize_spaces(keyword): idx
        for idx, keyword in enumerate(TELEGRAM_DISCOVERY_SEED_KEYWORDS)
    }

    def _score(keyword: str) -> tuple[int, int, str]:
        is_ambiguous = 1 if keyword in TELEGRAM_AMBIGUOUS_DISCOVERY_TERMS else 0
        explicit = 0 if keyword in seed_position else 1
        position = seed_position.get(keyword, 10_000)
        return (is_ambiguous, explicit, position if explicit == 0 else 10_000)

    return sorted(normalized, key=lambda k: (*_score(k), k))


def build_message_fetch_plan(
    channel_row: dict[str, Any],
    backfill_limit: int,
    incremental_limit: int,
) -> dict[str, Any]:
    latest_known_id = _safe_int(channel_row.get("last_message_id"), default=0)
    if latest_known_id > 0:
        return {
            "mode": "incremental",
            "min_id": latest_known_id,
            "limit": max(1, _safe_int(incremental_limit, default=50)),
        }

    return {
        "mode": "backfill",
        "min_id": 0,
        "limit": max(1, _safe_int(backfill_limit, default=50)),
    }


def _paginate(items: list[dict[str, Any]], page_size: int) -> list[list[dict[str, Any]]]:
    size = max(1, _safe_int(page_size, default=25))
    return [items[idx : idx + size] for idx in range(0, len(items), size)]


def compute_channel_cursor_update(
    channel_row: dict[str, Any],
    ingested_message_rows: list[dict[str, Any]],
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    checked_at_iso = _to_iso(checked_at or _now_utc())

    last_message_id = str(channel_row.get("last_message_id") or "").strip() or None
    last_message_ts = channel_row.get("last_message_timestamp")

    if ingested_message_rows:
        newest = max(
            ingested_message_rows,
            key=lambda row: _safe_int(row.get("message_id"), default=0),
        )
        if newest.get("message_id"):
            last_message_id = str(newest.get("message_id"))
        if newest.get("message_timestamp"):
            last_message_ts = newest.get("message_timestamp")

    return {
        "last_checked_at": checked_at_iso,
        "last_message_id": last_message_id,
        "last_message_timestamp": last_message_ts,
        "updated_at": checked_at_iso,
    }


def _channel_message_fetch_window(
    channel_row: dict[str, Any],
    historical_months: int = TELEGRAM_MESSAGE_FETCH_HISTORICAL_MONTHS,
    daily_lookback_days: int = TELEGRAM_MESSAGE_FETCH_DAILY_LOOKBACK_DAYS,
) -> dict[str, Any]:
    now = _now_utc()
    historical_done = bool(channel_row.get("historical_data") is True)
    if not historical_done:
        # Approximate six months as 182 days for deterministic execution.
        since = now - timedelta(days=max(1, int(historical_months) * 30 + 2))
        return {
            "mode": "historical_6m",
            "since": since,
            "historical_data_after_run": True,
        }
    since = now - timedelta(days=max(1, int(daily_lookback_days)))
    return {
        "mode": "daily_incremental",
        "since": since,
        "historical_data_after_run": True,
    }


def _to_aware_utc(value: datetime | None) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _classification_payload(
    brand: dict[str, Any],
    channel_row: dict[str, Any],
    sampled_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    channel_metadata = _channel_metadata_for_classification(channel_row)

    return {
        "brand_name": brand.get("name") or "Physics Wallah",
        "brand_keywords": build_discovery_keywords(brand_keywords=brand.get("keywords") or []),
        "required_labels": list(TELEGRAM_CHANNEL_CLASSIFICATION_LABELS),
        "channel": {
            "channel_id": channel_row.get("channel_id"),
            "channel_username": channel_row.get("channel_username"),
            "channel_title": channel_row.get("channel_title"),
            "channel_type": channel_row.get("channel_type"),
            "discovery_keyword": channel_row.get("discovery_keyword"),
            "metadata": channel_metadata,
        },
        "sample_messages": sampled_messages,
        "monitoring_policy": {
            "monitor_labels": list(TELEGRAM_MONITORED_CLASSIFICATION_LABELS),
            "ignore_labels": ["irrelevant"],
        },
    }


def heuristic_classify_channel(
    brand: dict[str, Any],
    channel_row: dict[str, Any],
    sampled_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    channel_metadata = _channel_metadata_for_classification(channel_row)

    text_parts = [
        str(brand.get("name") or ""),
        str(channel_row.get("channel_title") or ""),
        str(channel_row.get("channel_username") or ""),
        str(channel_metadata.get("channel_description") or channel_metadata.get("about") or ""),
    ]
    for sample in sampled_messages:
        text_parts.append(str(sample.get("text") or ""))

    combined = _normalize_spaces(" ".join(text_parts))

    signals: list[str] = []
    if any(term in combined for term in PW_ANCHOR_TERMS):
        signals.append("pw_anchor_match")

    if bool(channel_metadata.get("is_verified")):
        signals.append("telegram_verified_flag")

    if any(term in combined for term in SUSPICIOUS_TERMS):
        signals.append("suspicious_term_match")

    if any(term in combined for term in FAN_UNOFFICIAL_TERMS):
        signals.append("fan_or_unofficial_term")

    if any(term in combined for term in OFFICIAL_SIGNAL_TERMS):
        signals.append("official_signal_term")

    has_anchor = "pw_anchor_match" in signals
    has_suspicious_term = "suspicious_term_match" in signals
    has_fan_term = "fan_or_unofficial_term" in signals
    has_official_signal = "official_signal_term" in signals
    is_verified = "telegram_verified_flag" in signals

    if not has_anchor:
        label = "irrelevant"
        confidence = 0.86
        reason = "No strong Physics Wallah identity signals detected."
    elif has_suspicious_term and ("official" in combined or "support" in combined):
        label = "suspicious_fake"
        confidence = 0.80
        reason = "Impersonation-like terms detected with PW branding signals."
    elif is_verified and has_official_signal:
        label = "official"
        confidence = 0.78
        reason = "Verified channel with official program/brand cues."
    elif has_fan_term:
        label = "fan_unofficial"
        confidence = 0.72
        reason = "Looks like fan/community activity around PW."
    elif has_official_signal:
        label = "likely_official"
        confidence = 0.69
        reason = "Strong PW and program cues but no definitive ownership proof."
    else:
        label = "fan_unofficial"
        confidence = 0.60
        reason = "PW-related discussion channel without official ownership evidence."

    return {
        "label": label,
        "confidence": confidence,
        "reason": reason,
        "signals": signals,
        "should_monitor": should_monitor_for_label(label),
    }


class AzureTelegramChannelClassifier:
    def __init__(self):
        self.api_key = AZURE_OPENAI_API_KEY
        self.endpoint = AZURE_OPENAI_ENDPOINT.rstrip("/") if AZURE_OPENAI_ENDPOINT else ""
        self.api_version = AZURE_OPENAI_API_VERSION
        self.deployment = (
            AZURE_OPENAI_DEPLOYMENT_GPT54
            or AZURE_OPENAI_DEPLOYMENT_GPT53
            or AZURE_OPENAI_DEPLOYMENT_GPT52
        )
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.endpoint and self.deployment)

    def _ensure_client(self):
        if self._client is not None:
            return self._client

        from openai import AzureOpenAI

        self._client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
        )
        return self._client

    def _chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.is_configured:
            return {}, {
                "mode": "direct",
                "status": "not_configured",
            }

        try:
            client = self._ensure_client()
            response = client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            choice = response.choices[0] if response.choices else None
            content = choice.message.content if choice and choice.message else ""
            parsed = _extract_first_json_object(content)
            return parsed, {
                "mode": "direct",
                "status": "completed",
                "provider_response_id": getattr(response, "id", None),
                "raw_content": content,
            }
        except Exception as exc:
            logger.exception("Telegram channel classification LLM call failed")
            return {}, {
                "mode": "direct",
                "status": "failed",
                "error": {"message": str(exc)},
            }

    def classify_channel(self, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        return self._chat_json(
            system_prompt=TELEGRAM_CHANNEL_CLASSIFICATION_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False),
        )

    def classify_channel_fulfilment(
        self,
        channel_payload: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_prompt = TELEGRAM_CHANNEL_FULFILMENT_USER_PROMPT_TEMPLATE.format(
            channel_payload_json=json.dumps(channel_payload, ensure_ascii=False),
        )
        return self._chat_json(
            system_prompt=TELEGRAM_CHANNEL_FULFILMENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

    def classify_channels_fulfilment_batch(
        self,
        channel_payloads: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_prompt = TELEGRAM_CHANNEL_FULFILMENT_BATCH_USER_PROMPT_TEMPLATE.format(
            channels_payload_json=json.dumps(channel_payloads, ensure_ascii=False),
        )
        return self._chat_json(
            system_prompt=TELEGRAM_CHANNEL_FULFILMENT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

    def classify_message_risk(
        self,
        message_payload: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_prompt = TELEGRAM_MESSAGE_RISK_USER_PROMPT_TEMPLATE.format(
            message_payload_json=json.dumps(message_payload, ensure_ascii=False),
        )
        return self._chat_json(
            system_prompt=TELEGRAM_MESSAGE_RISK_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

    def classify_messages_risk_batch(
        self,
        message_payloads: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_prompt = TELEGRAM_MESSAGE_RISK_BATCH_USER_PROMPT_TEMPLATE.format(
            messages_payload_json=json.dumps(message_payloads, ensure_ascii=False),
        )
        return self._chat_json(
            system_prompt=TELEGRAM_MESSAGE_RISK_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )


class TelegramScraper(BaseScraper):
    platform = "telegram"

    def __init__(self):
        super().__init__()
        self._client = None
        self._classifier = AzureTelegramChannelClassifier()

    async def _get_client(self):
        if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
            raise RuntimeError("Missing TELEGRAM_API_ID/TELEGRAM_API_HASH")

        if self._client is None:
            from telethon import TelegramClient

            self._client = TelegramClient(
                TELEGRAM_SESSION_NAME,
                int(TELEGRAM_API_ID),
                TELEGRAM_API_HASH,
            )

        if not self._client.is_connected():
            await self._client.connect()

        try:
            authorized = await self._client.is_user_authorized()
        except Exception:
            authorized = False

        if not authorized:
            if not TELEGRAM_PHONE:
                raise RuntimeError("Missing TELEGRAM_PHONE for Telegram login")
            await self._client.start(phone=TELEGRAM_PHONE)

        if not self._client.is_connected():
            raise RuntimeError("Telegram client failed to establish active connection")
        return self._client

    async def _resolve_channel_entity(self, channel_row: dict[str, Any]) -> Any | None:
        client = await self._get_client()

        username = normalize_channel_username(channel_row.get("channel_username"))
        channel_id = str(channel_row.get("channel_id") or "").strip()

        candidates: list[Any] = []
        if username:
            candidates.extend([username, f"@{username}"])
        if channel_id.lstrip("-").isdigit():
            candidates.append(int(channel_id))

        for candidate in candidates:
            try:
                return await self._retry(client.get_entity, candidate)
            except Exception:
                continue

        return None

    @staticmethod
    def _is_discoverable_chat(chat: Any) -> bool:
        if chat is None:
            return False

        channel_id = str(getattr(chat, "id", "") or "").strip()
        if not channel_id:
            return False

        username = normalize_channel_username(getattr(chat, "username", None))
        return bool(username)

    async def _channel_full_metadata(self, chat: Any) -> dict[str, Any]:
        client = await self._get_client()

        if not bool(getattr(chat, "broadcast", False) or getattr(chat, "megagroup", False) or getattr(chat, "gigagroup", False)):
            return {}

        try:
            from telethon.tl.functions.channels import GetFullChannelRequest

            response = await self._retry(client, GetFullChannelRequest(channel=chat))
            full_chat = getattr(response, "full_chat", None)

            return {
                "about": str(getattr(full_chat, "about", "") or "").strip() or None,
                "channel_description": str(getattr(full_chat, "about", "") or "").strip() or None,
                "participants_count": _safe_int(getattr(full_chat, "participants_count", 0)),
                "linked_chat_id": str(getattr(full_chat, "linked_chat_id", "") or "").strip() or None,
            }
        except Exception:
            logger.debug("Could not fetch full Telegram metadata for chat=%s", getattr(chat, "id", None))
            return {}

    async def _fetch_channel_activity_snapshot(
        self,
        entity: Any,
        lookback_days: int = TELEGRAM_ACTIVITY_LOOKBACK_DAYS,
        count_scan_limit: int = TELEGRAM_ACTIVITY_COUNT_SCAN_LIMIT,
    ) -> dict[str, Any]:
        client = await self._get_client()
        now = _now_utc()
        since = now - timedelta(days=max(1, _safe_int(lookback_days, default=7)))
        max_scan = max(1, _safe_int(count_scan_limit, default=5000))

        last_message_timestamp: str | None = None
        message_count_7d: int | None = 0

        try:
            async for message in client.iter_messages(entity, limit=1):
                message_dt = _to_aware_utc(getattr(message, "date", None))
                if message_dt:
                    last_message_timestamp = _to_iso(message_dt)
                break
        except Exception:
            logger.debug("Failed fetching last message timestamp for entity=%s", entity)

        scanned = 0
        try:
            async for message in client.iter_messages(entity, limit=max_scan):
                message_dt = _to_aware_utc(getattr(message, "date", None))
                if message_dt is None:
                    continue
                if message_dt < since:
                    break
                message_count_7d += 1
                scanned += 1
        except Exception:
            logger.debug("Failed counting 7-day messages for entity=%s", entity)
            message_count_7d = None

        return {
            "message_count_7d": message_count_7d,
            "last_message_timestamp": last_message_timestamp,
            "activity_scanned_count": scanned,
            "activity_lookback_days": max(1, _safe_int(lookback_days, default=7)),
            "activity_scan_limit": max_scan,
        }

    async def refresh_channel_activity(
        self,
        channel_row: dict[str, Any],
        lookback_days: int = TELEGRAM_ACTIVITY_LOOKBACK_DAYS,
        count_scan_limit: int = TELEGRAM_ACTIVITY_COUNT_SCAN_LIMIT,
    ) -> dict[str, Any]:
        entity = await self._resolve_channel_entity(channel_row)
        checked_at_iso = _to_iso(_now_utc())
        if entity is None:
            updates = {
                "last_checked_at": checked_at_iso,
                "updated_at": checked_at_iso,
            }
            updated = db.update_telegram_channel(channel_row["id"], updates)
            return {
                "status": "skipped_entity_not_found",
                "channel_id": channel_row.get("channel_id"),
                "updated": updated,
            }

        entity_created_at = _to_aware_utc(getattr(entity, "date", None))
        activity = await self._fetch_channel_activity_snapshot(
            entity=entity,
            lookback_days=lookback_days,
            count_scan_limit=count_scan_limit,
        )

        updates: dict[str, Any] = {
            "last_checked_at": checked_at_iso,
            "updated_at": checked_at_iso,
            "message_count_7d": activity.get("message_count_7d"),
        }
        if activity.get("last_message_timestamp"):
            updates["last_message_timestamp"] = activity.get("last_message_timestamp")
        if entity_created_at:
            updates["channel_created_at"] = _to_iso(entity_created_at)

        updated = db.update_telegram_channel(channel_row["id"], updates)
        return {
            "status": "completed",
            "channel_id": channel_row.get("channel_id"),
            "message_count_7d": activity.get("message_count_7d"),
            "last_message_timestamp": activity.get("last_message_timestamp"),
            "updated": updated,
        }

    async def discover_public_channels(
        self,
        brand_id: str | None,
        keywords: Iterable[str],
        per_keyword_limit: int,
    ) -> list[dict[str, Any]]:
        client = await self._get_client()
        ordered_keywords = prioritize_discovery_keywords(keywords)
        limit = max(1, _safe_int(per_keyword_limit, default=TELEGRAM_DISCOVERY_MAX_RESULTS_PER_KEYWORD))

        discovered_by_channel_id: dict[str, dict[str, Any]] = {}

        from telethon.tl.functions.contacts import SearchRequest

        for keyword in ordered_keywords:
            try:
                response = await self._retry(client, SearchRequest(q=keyword, limit=limit))
            except Exception:
                logger.exception("Telegram discovery failed for keyword=%s", keyword)
                continue

            for chat in getattr(response, "chats", []):
                if not self._is_discoverable_chat(chat):
                    continue

                metadata = await self._channel_full_metadata(chat)
                row = map_discovered_chat_to_channel_row(
                    chat=chat,
                    brand_id=brand_id,
                    discovery_keyword=keyword,
                    metadata=metadata,
                    discovered_at=_now_utc(),
                )

                channel_id = row.get("channel_id")
                if not channel_id:
                    continue

                existing = discovered_by_channel_id.get(channel_id)
                if not existing:
                    discovered_by_channel_id[channel_id] = row
                    continue

                # Merge explicit discovery metadata columns.
                existing["public_url"] = existing.get("public_url") or row.get("public_url")
                existing["is_verified"] = bool(existing.get("is_verified") or row.get("is_verified"))
                existing["live_test"] = bool(existing.get("live_test") or row.get("live_test"))
                existing["live_test_run_at"] = (
                    existing.get("live_test_run_at")
                    or row.get("live_test_run_at")
                )
                existing["participants_count"] = max(
                    _safe_int(existing.get("participants_count"), default=0),
                    _safe_int(row.get("participants_count"), default=0),
                )
                existing["channel_created_at"] = (
                    existing.get("channel_created_at")
                    or row.get("channel_created_at")
                )
                existing["channel_description"] = (
                    existing.get("channel_description")
                    or row.get("channel_description")
                )
                existing["updated_at"] = row.get("updated_at") or existing.get("updated_at")

                existing_raw = existing.get("raw_data") if isinstance(existing.get("raw_data"), dict) else {}
                row_raw = row.get("raw_data") if isinstance(row.get("raw_data"), dict) else {}
                existing_meta = existing_raw.get("discovery_metadata") if isinstance(existing_raw.get("discovery_metadata"), dict) else {}
                row_meta = row_raw.get("discovery_metadata") if isinstance(row_raw.get("discovery_metadata"), dict) else {}
                merged_meta = {**existing_meta, **row_meta}

                merged_keywords: list[str] = []
                for item in (existing_raw.get("discovery_keywords") if isinstance(existing_raw.get("discovery_keywords"), list) else []):
                    text = str(item or "").strip()
                    if text and text not in merged_keywords:
                        merged_keywords.append(text)
                if keyword not in merged_keywords:
                    merged_keywords.append(keyword)

                existing["raw_data"] = {
                    **existing_raw,
                    "discovery_metadata": merged_meta,
                    "discovery_keywords": merged_keywords,
                    "latest_discovery_keyword": keyword,
                    "last_discovered_at": _to_iso(_now_utc()),
                }

        return list(discovered_by_channel_id.values())

    async def _sample_recent_messages(
        self,
        channel_row: dict[str, Any],
        limit: int,
    ) -> list[dict[str, Any]]:
        entity = await self._resolve_channel_entity(channel_row)
        if entity is None:
            return []

        client = await self._get_client()
        sampled: list[dict[str, Any]] = []

        try:
            async for message in client.iter_messages(entity, limit=max(0, limit)):
                text = str(
                    getattr(message, "message", None)
                    or getattr(message, "text", None)
                    or ""
                ).strip()
                if not text:
                    continue
                sampled.append(
                    {
                        "message_id": str(getattr(message, "id", "") or "").strip(),
                        "timestamp": _to_iso(getattr(message, "date", None)),
                        "text": text,
                    }
                )
                if len(sampled) >= limit:
                    break
        except Exception:
            logger.debug("Failed to sample channel messages for channel_id=%s", channel_row.get("channel_id"))

        return sampled

    async def classify_channel_row(
        self,
        brand: dict[str, Any],
        channel_row: dict[str, Any],
        force_reclassify: bool = False,
        sample_messages_limit: int = TELEGRAM_CLASSIFICATION_SAMPLE_MESSAGES,
    ) -> dict[str, Any]:
        existing_response = channel_row.get("llm_classification_response")
        if (
            not force_reclassify
            and isinstance(existing_response, dict)
            and str(existing_response.get("status") or "").strip().lower() in {"completed", "heuristic"}
        ):
            return {
                "status": "skipped_existing",
                "channel_id": channel_row.get("channel_id"),
                "label": normalize_channel_label(channel_row.get("classification_label")),
                "should_monitor": channel_row.get("should_monitor"),
            }

        sampled_messages = await self._sample_recent_messages(
            channel_row,
            limit=max(0, _safe_int(sample_messages_limit, TELEGRAM_CLASSIFICATION_SAMPLE_MESSAGES)),
        )
        payload = _classification_payload(brand, channel_row, sampled_messages)

        raw_llm, llm_meta = self._classifier.classify_channel(payload)
        normalized = normalize_channel_classification(
            raw_llm,
            fallback_reason="llm_unavailable_or_invalid",
        )

        mode = str(llm_meta.get("status") or "").strip().lower()
        if mode != "completed":
            heuristic = heuristic_classify_channel(brand, channel_row, sampled_messages)
            normalized = normalize_channel_classification(
                heuristic,
                fallback_reason="heuristic_fallback",
            )
            llm_meta["status"] = "heuristic"
            llm_meta["heuristic_applied"] = True
            llm_meta["heuristic_result"] = heuristic

        now_iso = _to_iso(_now_utc())
        stored_response = {
            "status": llm_meta.get("status"),
            "mode": llm_meta.get("mode", "direct"),
            "provider_response_id": llm_meta.get("provider_response_id"),
            "error": llm_meta.get("error"),
            "raw_response": raw_llm,
            "normalized": normalized,
            "sample_message_count": len(sampled_messages),
            "classified_at": now_iso,
        }

        updates = {
            "classification_label": normalized["label"],
            "should_monitor": normalized["should_monitor"],
            "llm_classification_response": stored_response,
            "updated_at": now_iso,
        }

        updated = db.update_telegram_channel(channel_row["id"], updates)
        return {
            "status": "classified",
            "channel_id": updated.get("channel_id", channel_row.get("channel_id")),
            "label": updated.get("classification_label", normalized["label"]),
            "should_monitor": updated.get("should_monitor", normalized["should_monitor"]),
            "confidence": normalized["confidence"],
        }

    async def ingest_messages_for_channel(
        self,
        channel_row: dict[str, Any],
        brand_id: str | None,
        backfill_limit: int,
        incremental_limit: int,
    ) -> dict[str, Any]:
        entity = await self._resolve_channel_entity(channel_row)
        if entity is None:
            cursor_updates = compute_channel_cursor_update(channel_row, [])
            db.update_telegram_channel(channel_row["id"], cursor_updates)
            return {
                "status": "skipped_entity_not_found",
                "channel_id": channel_row.get("channel_id"),
                "messages_ingested": 0,
                "mode": "unknown",
            }

        plan = build_message_fetch_plan(
            channel_row,
            backfill_limit=backfill_limit,
            incremental_limit=incremental_limit,
        )

        client = await self._get_client()
        fetched_messages: list[Any] = []

        try:
            async for message in client.iter_messages(
                entity,
                limit=plan["limit"],
                min_id=plan["min_id"],
            ):
                if not getattr(message, "id", None):
                    continue
                fetched_messages.append(message)
        except Exception:
            logger.exception(
                "Telegram message ingestion failed for channel_id=%s",
                channel_row.get("channel_id"),
            )
            cursor_updates = compute_channel_cursor_update(channel_row, [])
            db.update_telegram_channel(channel_row["id"], cursor_updates)
            return {
                "status": "failed",
                "channel_id": channel_row.get("channel_id"),
                "messages_ingested": 0,
                "mode": plan["mode"],
            }

        fetched_messages.sort(key=lambda item: _safe_int(getattr(item, "id", 0)))

        rows_to_upsert = [
            map_telegram_message_to_row(message=message, channel_row=channel_row, brand_id=brand_id)
            for message in fetched_messages
        ]
        if rows_to_upsert:
            db.upsert_telegram_messages_batch(rows_to_upsert)

        cursor_updates = compute_channel_cursor_update(channel_row, rows_to_upsert)
        db.update_telegram_channel(channel_row["id"], cursor_updates)

        return {
            "status": "completed",
            "channel_id": channel_row.get("channel_id"),
            "messages_ingested": len(rows_to_upsert),
            "mode": plan["mode"],
            "min_id": plan["min_id"],
            "limit": plan["limit"],
            "last_message_id": cursor_updates.get("last_message_id"),
        }

    async def _extract_message_media_payload(
        self,
        client: Any,
        message: Any,
        max_media_bytes: int = TELEGRAM_MESSAGE_MEDIA_MAX_BYTES,
    ) -> dict[str, Any]:
        if not getattr(message, "media", None):
            return {}

        media_type = _message_media_type(message)
        resolved_max_media_bytes = int(max_media_bytes or 0)
        if resolved_max_media_bytes <= 0:
            return {
                "media_metadata_patch": {
                    "media_download_status": "skipped_disabled",
                    "media_type": media_type,
                },
            }

        mime_type = None
        file_name = None
        known_size_bytes = None

        if getattr(message, "document", None) is not None:
            document = getattr(message, "document")
            mime_type = str(getattr(document, "mime_type", "") or "").strip() or None
            known_size_bytes = _safe_optional_int(getattr(document, "size", None))
            attributes = getattr(document, "attributes", None)
            if isinstance(attributes, list):
                for attr in attributes:
                    candidate = str(getattr(attr, "file_name", "") or "").strip()
                    if candidate:
                        file_name = candidate
                        break
        elif getattr(message, "photo", None) is not None:
            mime_type = "image/jpeg"
        elif getattr(message, "video", None) is not None:
            mime_type = "video/mp4"

        file_meta = getattr(message, "file", None)
        if known_size_bytes is None and file_meta is not None:
            known_size_bytes = _safe_optional_int(getattr(file_meta, "size", None))

        limit_bytes = max(1, resolved_max_media_bytes)
        if known_size_bytes is not None and known_size_bytes > limit_bytes:
            return {
                "media_mime_type": mime_type,
                "media_file_name": file_name,
                "media_file_size_bytes": known_size_bytes,
                "media_metadata_patch": {
                    "media_download_status": "skipped_size_limit",
                    "media_type": media_type,
                    "max_media_bytes": limit_bytes,
                    "actual_size_bytes": known_size_bytes,
                },
            }

        try:
            raw_bytes = await self._retry(client.download_media, message, file=bytes)
        except Exception:
            logger.debug("Telegram media download failed for message_id=%s", getattr(message, "id", None))
            return {
                "media_mime_type": mime_type,
                "media_file_name": file_name,
                "media_metadata_patch": {
                    "media_download_status": "failed",
                    "media_type": media_type,
                },
            }

        if not isinstance(raw_bytes, (bytes, bytearray)):
            return {
                "media_mime_type": mime_type,
                "media_file_name": file_name,
                "media_metadata_patch": {
                    "media_download_status": "empty",
                    "media_type": media_type,
                },
            }

        blob = bytes(raw_bytes)
        size_bytes = len(blob)
        if size_bytes > limit_bytes:
            return {
                "media_mime_type": mime_type,
                "media_file_name": file_name,
                "media_file_size_bytes": size_bytes,
                "media_metadata_patch": {
                    "media_download_status": "skipped_size_limit",
                    "media_type": media_type,
                    "max_media_bytes": limit_bytes,
                    "actual_size_bytes": size_bytes,
                },
            }

        return {
            "media_base64": base64.b64encode(blob).decode("ascii"),
            "media_mime_type": mime_type,
            "media_file_name": file_name,
            "media_file_size_bytes": size_bytes,
            "media_downloaded_at": _to_iso(_now_utc()),
            "media_metadata_patch": {
                "media_download_status": "ok",
                "media_type": media_type,
                "actual_size_bytes": size_bytes,
            },
        }

    async def fetch_messages_for_channel_window(
        self,
        channel_row: dict[str, Any],
        brand_id: str | None,
        since: datetime,
        batch_size: int = TELEGRAM_MESSAGE_FETCH_BATCH_SIZE,
        batch_sleep_min_seconds: int = TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MIN_SECONDS,
        batch_sleep_max_seconds: int = TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MAX_SECONDS,
        max_media_bytes: int = TELEGRAM_MESSAGE_MEDIA_MAX_BYTES,
    ) -> dict[str, Any]:
        entity = await self._resolve_channel_entity(channel_row)
        if entity is None:
            updates = {
                "last_checked_at": _to_iso(_now_utc()),
                "updated_at": _to_iso(_now_utc()),
            }
            db.update_telegram_channel(channel_row["id"], updates)
            return {
                "status": "skipped_entity_not_found",
                "channel_id": channel_row.get("channel_id"),
                "messages_upserted": 0,
                "batches_processed": 0,
            }

        resolved_username = normalize_channel_username(
            channel_row.get("channel_username") or getattr(entity, "username", None),
        )
        if not resolved_username:
            updates = {
                "last_checked_at": _to_iso(_now_utc()),
                "updated_at": _to_iso(_now_utc()),
            }
            db.update_telegram_channel(channel_row["id"], updates)
            return {
                "status": "skipped_missing_channel_username",
                "channel_id": channel_row.get("channel_id"),
                "messages_upserted": 0,
                "batches_processed": 0,
            }

        existing_username = normalize_channel_username(channel_row.get("channel_username"))
        if existing_username != resolved_username:
            channel_row = {
                **channel_row,
                "channel_username": resolved_username,
            }
            db.update_telegram_channel(
                channel_row["id"],
                {
                    "channel_username": resolved_username,
                    "updated_at": _to_iso(_now_utc()),
                },
            )

        client = await self._get_client()
        since_utc = _to_aware_utc(since) or (_now_utc() - timedelta(days=1))
        effective_batch_size = max(1, int(batch_size or 1))
        sleep_min = max(0, int(batch_sleep_min_seconds))
        sleep_max = max(sleep_min, int(batch_sleep_max_seconds))

        pending_rows: list[dict[str, Any]] = []
        all_rows: list[dict[str, Any]] = []
        batches_processed = 0
        messages_scanned = 0
        messages_upserted = 0

        async for message in client.iter_messages(entity, limit=None):
            message_dt = _to_aware_utc(getattr(message, "date", None))
            if message_dt is None:
                continue
            if message_dt < since_utc:
                break
            messages_scanned += 1

            row = map_telegram_message_to_row(
                message=message,
                channel_row=channel_row,
                brand_id=brand_id,
            )
            if getattr(message, "media", None):
                media_payload = await self._extract_message_media_payload(
                    client=client,
                    message=message,
                    max_media_bytes=max_media_bytes,
                )
                media_patch = media_payload.pop("media_metadata_patch", None)
                if isinstance(media_patch, dict):
                    metadata = row.get("media_metadata") if isinstance(row.get("media_metadata"), dict) else {}
                    row["media_metadata"] = {**metadata, **media_patch}
                row.update(media_payload)

            pending_rows.append(row)
            all_rows.append(row)

            if len(pending_rows) >= effective_batch_size:
                db.upsert_telegram_messages_batch(pending_rows)
                messages_upserted += len(pending_rows)
                batches_processed += 1
                pending_rows = []
                await asyncio.sleep(random.randint(sleep_min, sleep_max))

        if pending_rows:
            db.upsert_telegram_messages_batch(pending_rows)
            messages_upserted += len(pending_rows)
            batches_processed += 1

        cursor_updates = compute_channel_cursor_update(channel_row, all_rows)
        db.update_telegram_channel(channel_row["id"], cursor_updates)
        return {
            "status": "completed",
            "channel_id": channel_row.get("channel_id"),
            "channel_username": channel_row.get("channel_username"),
            "messages_scanned": messages_scanned,
            "messages_upserted": messages_upserted,
            "batches_processed": batches_processed,
            "window_since": _to_iso(since_utc),
            "batch_size": effective_batch_size,
        }

    async def run_message_fetch_pipeline_for_brand(
        self,
        brand: dict[str, Any],
        limit_channels: int = 500,
        batch_size: int = TELEGRAM_MESSAGE_FETCH_BATCH_SIZE,
        historical_months: int = TELEGRAM_MESSAGE_FETCH_HISTORICAL_MONTHS,
        daily_lookback_days: int = TELEGRAM_MESSAGE_FETCH_DAILY_LOOKBACK_DAYS,
        batch_sleep_min_seconds: int = TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MIN_SECONDS,
        batch_sleep_max_seconds: int = TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MAX_SECONDS,
        between_channels_sleep_seconds: int = TELEGRAM_MESSAGE_FETCH_CHANNEL_SLEEP_SECONDS,
        target_channels: Iterable[str] | None = None,
        max_media_bytes: int = TELEGRAM_MESSAGE_MEDIA_MAX_BYTES,
    ) -> dict[str, Any]:
        brand_id = brand.get("id")
        if not brand_id:
            return {
                "phase": "telegram_message_fetch",
                "status": "skipped_missing_brand_id",
                "brand": brand.get("name"),
            }

        target_ids, target_usernames = normalize_channel_targets(target_channels or [])
        channels = db.list_telegram_channels_for_message_fetch(
            brand_id=brand_id,
            limit=max(1, int(limit_channels or 1)),
            target_channel_ids=list(target_ids),
            target_channel_usernames=list(target_usernames),
        )
        channels.sort(
            key=lambda row: (1 if bool(row.get("historical_data")) else 0, str(row.get("channel_username") or "")),
        )

        channel_results: list[dict[str, Any]] = []
        historical_channels = 0
        daily_channels = 0
        messages_upserted = 0
        batches_processed = 0
        failed = 0

        for idx, channel_row in enumerate(channels):
            window = _channel_message_fetch_window(
                channel_row=channel_row,
                historical_months=historical_months,
                daily_lookback_days=daily_lookback_days,
            )
            mode = window["mode"]
            since = window["since"]
            if mode == "historical_6m":
                historical_channels += 1
            else:
                daily_channels += 1

            try:
                effective_max_media_bytes = (
                    0 if mode == "historical_6m" else max(0, int(max_media_bytes or 0))
                )
                result = await self.fetch_messages_for_channel_window(
                    channel_row=channel_row,
                    brand_id=brand_id,
                    since=since,
                    batch_size=batch_size,
                    batch_sleep_min_seconds=batch_sleep_min_seconds,
                    batch_sleep_max_seconds=batch_sleep_max_seconds,
                    max_media_bytes=effective_max_media_bytes,
                )
            except Exception:
                logger.exception(
                    "Telegram message fetch failed for channel_id=%s",
                    channel_row.get("channel_id"),
                )
                failed += 1
                continue

            result["mode"] = mode
            channel_results.append(result)
            messages_upserted += _safe_int(result.get("messages_upserted"), 0)
            batches_processed += _safe_int(result.get("batches_processed"), 0)

            if mode == "historical_6m" and result.get("status") == "completed":
                db.update_telegram_channel(
                    channel_row["id"],
                    {
                        "historical_data": True,
                        "updated_at": _to_iso(_now_utc()),
                    },
                )

            next_mode = None
            if idx < len(channels) - 1:
                next_window = _channel_message_fetch_window(
                    channel_row=channels[idx + 1],
                    historical_months=historical_months,
                    daily_lookback_days=daily_lookback_days,
                )
                next_mode = next_window["mode"]

            if mode == "historical_6m" and next_mode == "historical_6m":
                await asyncio.sleep(max(0, int(between_channels_sleep_seconds)))

        return {
            "phase": "telegram_message_fetch",
            "status": "completed",
            "brand_id": brand_id,
            "brand_name": brand.get("name"),
            "channels_considered": len(channels),
            "historical_channels": historical_channels,
            "daily_channels": daily_channels,
            "channels_completed": sum(1 for row in channel_results if row.get("status") == "completed"),
            "messages_upserted": messages_upserted,
            "batches_processed": batches_processed,
            "failed": failed,
            "batch_size": max(1, int(batch_size or 1)),
            "batch_sleep_min_seconds": max(0, int(batch_sleep_min_seconds)),
            "batch_sleep_max_seconds": max(max(0, int(batch_sleep_min_seconds)), int(batch_sleep_max_seconds)),
            "between_channels_sleep_seconds": max(0, int(between_channels_sleep_seconds)),
            "historical_months": max(1, int(historical_months)),
            "daily_lookback_days": max(1, int(daily_lookback_days)),
            "max_media_bytes": max(0, int(max_media_bytes or 0)),
            "target_channel_count": len(target_ids) + len(target_usernames),
            "ran_at": _to_iso(_now_utc()),
            "channel_results": channel_results,
        }

    async def run_phase2_pipeline_for_brand(
        self,
        brand: dict[str, Any],
        keywords: Iterable[str] | None = None,
        per_keyword_limit: int = TELEGRAM_DISCOVERY_MAX_RESULTS_PER_KEYWORD,
        message_backfill_limit: int = TELEGRAM_MESSAGE_BACKFILL_LIMIT,
        incremental_fetch_limit: int = TELEGRAM_MESSAGE_INCREMENTAL_LIMIT,
        force_reclassify: bool = False,
        target_channels: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        brand_id = brand.get("id")
        if not brand_id:
            return {
                "phase": "telegram_phase2",
                "status": "skipped_missing_brand_id",
                "brand": brand.get("name"),
            }

        discovery_keywords = build_discovery_keywords(
            keywords=keywords,
            brand_keywords=brand.get("keywords") or [],
        )

        discovered_rows = await self.discover_public_channels(
            brand_id=brand_id,
            keywords=discovery_keywords,
            per_keyword_limit=max(1, _safe_int(per_keyword_limit, TELEGRAM_DISCOVERY_MAX_RESULTS_PER_KEYWORD)),
        )

        persisted_rows = db.upsert_telegram_channels_batch(discovered_rows)
        persisted_by_channel_id = {
            str(row.get("channel_id") or "").strip(): row
            for row in persisted_rows
            if str(row.get("channel_id") or "").strip()
        }

        if force_reclassify:
            existing_rows = db.list_telegram_channels_for_brand(brand_id=brand_id, limit=1_000)
            for row in existing_rows:
                channel_id = str(row.get("channel_id") or "").strip()
                if channel_id and channel_id not in persisted_by_channel_id:
                    persisted_by_channel_id[channel_id] = row

        target_ids, target_usernames = normalize_channel_targets(target_channels or [])

        def _matches_target(channel_row: dict[str, Any]) -> bool:
            if not target_ids and not target_usernames:
                return True
            channel_id = str(channel_row.get("channel_id") or "").strip()
            channel_username = normalize_channel_username(channel_row.get("channel_username"))
            return bool(
                (channel_id and channel_id in target_ids)
                or (channel_username and channel_username in target_usernames)
            )

        channels_for_classification = [
            row for row in persisted_by_channel_id.values() if _matches_target(row)
        ]

        classification_results: list[dict[str, Any]] = []
        classification_pages = _paginate(channels_for_classification, TELEGRAM_PIPELINE_PAGE_SIZE)
        for page in classification_pages:
            for channel_row in page:
                try:
                    classification_results.append(
                        await self.classify_channel_row(
                            brand=brand,
                            channel_row=channel_row,
                            force_reclassify=force_reclassify,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Telegram channel classification failed for channel_id=%s",
                        channel_row.get("channel_id"),
                    )

        activity_results: list[dict[str, Any]] = []
        activity_pages = _paginate(channels_for_classification, TELEGRAM_PIPELINE_PAGE_SIZE)
        for page in activity_pages:
            for channel_row in page:
                try:
                    activity_results.append(
                        await self.refresh_channel_activity(channel_row=channel_row)
                    )
                except Exception:
                    logger.exception(
                        "Telegram channel activity refresh failed for channel_id=%s",
                        channel_row.get("channel_id"),
                    )

        monitored_channels = db.list_telegram_channels_for_brand(
            brand_id=brand_id,
            should_monitor=True,
            limit=1_000,
        )
        monitored_channels = [row for row in monitored_channels if _matches_target(row)]

        ingestion_results: list[dict[str, Any]] = []
        ingestion_pages = _paginate(monitored_channels, TELEGRAM_PIPELINE_PAGE_SIZE)
        for page in ingestion_pages:
            for channel_row in page:
                try:
                    ingestion_results.append(
                        await self.ingest_messages_for_channel(
                            channel_row=channel_row,
                            brand_id=brand_id,
                            backfill_limit=max(1, _safe_int(message_backfill_limit, TELEGRAM_MESSAGE_BACKFILL_LIMIT)),
                            incremental_limit=max(1, _safe_int(incremental_fetch_limit, TELEGRAM_MESSAGE_INCREMENTAL_LIMIT)),
                        )
                    )
                except Exception:
                    logger.exception(
                        "Telegram channel ingestion failed for channel_id=%s",
                        channel_row.get("channel_id"),
                    )

        return {
            "phase": "telegram_phase2",
            "status": "completed",
            "brand_id": brand_id,
            "brand_name": brand.get("name"),
            "keywords_used": discovery_keywords,
            "discovered": len(discovered_rows),
            "channels_persisted": len(persisted_rows),
            "channels_classified": sum(1 for row in classification_results if row.get("status") == "classified"),
            "channels_classification_skipped": sum(1 for row in classification_results if row.get("status") == "skipped_existing"),
            "channels_activity_refreshed": sum(1 for row in activity_results if row.get("status") == "completed"),
            "channels_monitored": len(monitored_channels),
            "messages_ingested": sum(_safe_int(row.get("messages_ingested"), 0) for row in ingestion_results),
            "channels_with_new_messages": sum(1 for row in ingestion_results if _safe_int(row.get("messages_ingested"), 0) > 0),
            "force_reclassify": bool(force_reclassify),
            "per_keyword_limit": max(1, _safe_int(per_keyword_limit, TELEGRAM_DISCOVERY_MAX_RESULTS_PER_KEYWORD)),
            "message_backfill_limit": max(1, _safe_int(message_backfill_limit, TELEGRAM_MESSAGE_BACKFILL_LIMIT)),
            "incremental_fetch_limit": max(1, _safe_int(incremental_fetch_limit, TELEGRAM_MESSAGE_INCREMENTAL_LIMIT)),
            "page_size": max(1, _safe_int(TELEGRAM_PIPELINE_PAGE_SIZE, 25)),
            "classification_pages_processed": len(classification_pages),
            "activity_pages_processed": len(activity_pages),
            "ingestion_pages_processed": len(ingestion_pages),
            "target_channel_count": len(target_ids) + len(target_usernames),
            "ran_at": _to_iso(_now_utc()),
        }

    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        """Search Telegram channels/groups for keyword mentions."""
        if not params.keywords:
            return []

        discovery_rows = await self.discover_public_channels(
            brand_id=params.brand_id,
            keywords=params.keywords,
            per_keyword_limit=max(1, min(params.max_results_per_platform, TELEGRAM_DISCOVERY_MAX_RESULTS_PER_KEYWORD)),
        )

        results: list[dict[str, Any]] = []
        query = " ".join(params.keywords)
        client = await self._get_client()

        for channel_row in discovery_rows:
            entity = await self._resolve_channel_entity(channel_row)
            if entity is None:
                continue

            try:
                async for message in client.iter_messages(entity, limit=20, search=query):
                    text = str(
                        getattr(message, "message", None)
                        or getattr(message, "text", None)
                        or ""
                    ).strip()
                    if not text:
                        continue
                    results.append(map_telegram_message_to_search_result(message, channel_row))
                    if len(results) >= params.max_results_per_platform:
                        return results
            except Exception:
                logger.debug(
                    "Telegram search message scan failed for channel_id=%s",
                    channel_row.get("channel_id"),
                )

        return results

    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        """Telegram replies scraping is not used in the current MVP."""
        return []

    async def listen_realtime(self, channel_ids: list[int], callback):
        """Real-time event handler for new messages in monitored channels."""
        client = await self._get_client()
        from telethon import events

        @client.on(events.NewMessage(chats=channel_ids))
        async def handler(event):
            await callback(
                {
                    "content_text": event.text or "",
                    "content_type": "voice" if event.voice else "text",
                    "author_handle": str(event.sender_id or ""),
                    "source_url": "",
                    "published_at": event.date.isoformat() if event.date else None,
                    "raw_data": {"chat_id": event.chat_id, "message_id": event.id},
                }
            )

        logger.info("Listening to %d Telegram channels", len(channel_ids))
        await client.run_until_disconnected()



def normalize_channel_targets(target_channels: Iterable[str]) -> tuple[set[str], set[str]]:
    target_ids: set[str] = set()
    target_usernames: set[str] = set()

    for item in target_channels:
        value = str(item or "").strip()
        if not value:
            continue

        username = normalize_channel_username(value)
        if username and not value.lstrip("-").isdigit():
            target_usernames.add(username)

        if value.lstrip("-").isdigit():
            target_ids.add(str(int(value)))

    return target_ids, target_usernames


def _fulfilment_heuristic_response(channel_payload: dict[str, Any]) -> dict[str, Any]:
    channel = channel_payload.get("channel") if isinstance(channel_payload, dict) else {}
    if not isinstance(channel, dict):
        channel = {}

    text_parts = [
        str(channel.get("channel_title") or ""),
        str(channel.get("channel_username") or ""),
        str(channel.get("channel_description") or ""),
        str(channel.get("discovery_keyword") or ""),
    ]
    combined = _normalize_spaces(" ".join(text_parts))

    has_pw_anchor = any(
        token in combined
        for token in (
            "physics wallah",
            "physicswala",
            "physics walla",
            "physics wala",
            "pw ",
            " pw",
            "alakh",
        )
    )
    has_official_claim = bool(re.search(r"\bofficial\b", combined))
    has_ads_collabs = any(
        token in combined
        for token in (
            "for ads",
            "for ad",
            "for collab",
            "for promotion",
            "promotion",
            "reseller",
            "buy now",
            "paid",
        )
    )
    has_misspelled_wala = bool(
        re.search(r"\bphysics\s+wala\b|\bphysics\s+walla\b|\bphysicswala\b", combined)
    )
    has_fan_term = any(
        token in combined
        for token in (
            "fan",
            "unofficial",
            "community",
            "students group",
        )
    )

    if not has_pw_anchor:
        return {
            "classification_label": "irrelevant",
            "fake_score_10": 0,
            "is_fake": False,
            "should_monitor": False,
            "confidence": 0.70,
            "risk_flags": ["irrelevant"],
            "reason": "No clear Physics Wallah brand linkage in channel metadata.",
            "evidence": [combined[:200]],
        }

    if has_ads_collabs or has_misspelled_wala:
        return {
            "classification_label": "suspicious_fake",
            "fake_score_10": 9,
            "is_fake": True,
            "should_monitor": True,
            "confidence": 0.80,
            "risk_flags": ["pw_brand_misuse", "ads_collabs_signal", "reseller_behavior"],
            "reason": "PW-like branding with ad/collab or misspelling signals indicates impersonation risk.",
            "evidence": [combined[:200]],
        }

    if has_official_claim:
        return {
            "classification_label": "suspicious_fake",
            "fake_score_10": 7,
            "is_fake": True,
            "should_monitor": True,
            "confidence": 0.68,
            "risk_flags": ["misleading_official_claim", "pw_brand_misuse"],
            "reason": "Official positioning without strong ownership proof appears misleading.",
            "evidence": [combined[:200]],
        }

    if has_fan_term:
        return {
            "classification_label": "fan_unofficial",
            "fake_score_10": 3,
            "is_fake": False,
            "should_monitor": True,
            "confidence": 0.72,
            "risk_flags": [],
            "reason": "Fan/community context present without clear impersonation indicators.",
            "evidence": [combined[:200]],
        }

    return {
        "classification_label": "likely_official",
        "fake_score_10": 2,
        "is_fake": False,
        "should_monitor": True,
        "confidence": 0.60,
        "risk_flags": [],
        "reason": "PW-related branding detected but ownership confidence is limited.",
        "evidence": [combined[:200]],
    }


def _persist_channel_fulfilment_result(
    channel_row: dict[str, Any],
    channel_payload: dict[str, Any],
    normalized: dict[str, Any],
    raw_response: dict[str, Any] | None,
    llm_meta: dict[str, Any],
) -> dict[str, Any]:
    now_iso = _to_iso(_now_utc())
    llm_response = {
        "status": llm_meta.get("status"),
        "mode": llm_meta.get("mode", "direct"),
        "provider_response_id": llm_meta.get("provider_response_id"),
        "error": llm_meta.get("error"),
        "classified_at": now_iso,
        "input_payload": channel_payload,
        "raw_response": raw_response,
        "normalized": normalized,
    }
    updates = build_telegram_fulfilment_writeback_updates(
        channel_row=channel_row,
        normalized=normalized,
        llm_classification_response=llm_response,
    )
    updated = db.update_telegram_channel(channel_row["id"], updates)
    return {
        "status": "classified",
        "channel_id": updated.get("channel_id", channel_row.get("channel_id")),
        "classification_label": normalized["classification_label"],
        "should_monitor": normalized["should_monitor"],
        "is_fake": normalized["is_fake"],
        "fake_score_10": normalized["fake_score_10"],
    }


def _contains_pw_brand_resource_signal(channel_payload: dict[str, Any]) -> bool:
    channel = channel_payload.get("channel") if isinstance(channel_payload, dict) else {}
    if not isinstance(channel, dict):
        channel = {}

    text = _normalize_spaces(
        " ".join(
            [
                str(channel.get("channel_title") or ""),
                str(channel.get("channel_username") or ""),
                str(channel.get("channel_description") or ""),
                str(channel.get("discovery_keyword") or ""),
            ]
        )
    )
    if not text:
        return False

    anchor_terms = (
        "physics wallah",
        "physicswallah",
        "physics wala",
        "physicswala",
        "physics walla",
        "pw skills",
        "pwskills",
        "vidyapeeth",
        "pathshala",
        "arjuna",
        "lakshya",
        "yakeen",
        "prayas",
        "neet wallah",
        "jee wallah",
        "alakh",
        "pw ",
    )
    if any(term in text for term in anchor_terms):
        return True
    return bool(re.search(r"\bpw\b", text))


def _contains_pw_mimicry_signal(text: str) -> bool:
    return bool(re.search(r"\bphysics\s+wala\b|\bphysics\s+walla\b|\bphysicswala\b", text))


def _contains_reseller_signal(text: str) -> bool:
    return any(
        token in text
        for token in (
            "for ads",
            "for collab",
            "for promotion",
            "promotion",
            "reseller",
            "paid",
            "contact @",
            "dm @",
        )
    )


PW_FACULTY_SIGNAL_TERMS = (
    "mr sir",
    "saleem sir",
    "alakh pandey",
    "alakh sir",
    "tarun sir",
    "pankaj sir",
)


def _contains_faculty_signal(text: str) -> bool:
    return any(term in text for term in PW_FACULTY_SIGNAL_TERMS)


def _apply_unofficial_pw_policy_calibration(
    channel_payload: dict[str, Any],
    normalized: dict[str, Any],
) -> dict[str, Any]:
    channel = channel_payload.get("channel") if isinstance(channel_payload, dict) else {}
    if not isinstance(channel, dict):
        channel = {}

    text = _normalize_spaces(
        " ".join(
            [
                str(channel.get("channel_title") or ""),
                str(channel.get("channel_username") or ""),
                str(channel.get("channel_description") or ""),
                str(channel.get("discovery_keyword") or ""),
            ]
        )
    )

    is_verified = False
    is_verified = bool(channel.get("is_verified") is True)
    if is_verified:
        return normalized
    if not _contains_pw_brand_resource_signal(channel_payload):
        return normalized

    participants_count = max(0, _safe_optional_int(channel.get("participants_count")) or 0)
    created_at = _safe_optional_datetime(channel.get("channel_created_at"))
    channel_age_days = None
    if created_at is not None:
        channel_age_days = max(0, int((_now_utc() - created_at).total_seconds() // 86_400))

    has_mimicry = _contains_pw_mimicry_signal(text)
    has_reseller = _contains_reseller_signal(text)
    has_official_claim = bool(re.search(r"\bofficial\b", text))
    has_faculty_signal = _contains_faculty_signal(text)

    risk_flags = list(normalized.get("risk_flags") or [])
    evidence = list(normalized.get("evidence") or [])
    evidence.append("policy_calibration_non_verified_pw_brand_channel")

    if has_mimicry or (has_reseller and has_official_claim):
        for required_flag in ("pw_brand_misuse", "misleading_official_claim", "copyright_risk"):
            if required_flag not in risk_flags:
                risk_flags.append(required_flag)
        if has_reseller and "reseller_behavior" not in risk_flags:
            risk_flags.append("reseller_behavior")
        if has_reseller and "ads_collabs_signal" not in risk_flags:
            risk_flags.append("ads_collabs_signal")
        high_score = 10 if has_mimicry and (has_reseller or has_official_claim) else 9
        return {
            **normalized,
            "classification_label": "suspicious_fake",
            "fake_score_10": high_score,
            "is_fake": True,
            "should_monitor": True,
            "confidence": max(_safe_float(normalized.get("confidence"), 0.0), 0.90),
            "risk_flags": risk_flags,
            "reason": "Calibration: strong mimicry/reseller impersonation cues indicate high fake risk.",
            "evidence": evidence,
        }

    # Non-mimic PW-brand channels should stay mid-risk and not be auto-marked fake.
    mid_score = 6
    if participants_count < 50_000 and not has_faculty_signal:
        mid_score = 7
    if channel_age_days is not None and channel_age_days < 90 and participants_count < 20_000:
        mid_score = 7
    if has_faculty_signal and participants_count >= 100_000:
        mid_score = 6

    for required_flag in ("pw_brand_misuse",):
        if required_flag not in risk_flags:
            risk_flags.append(required_flag)
    if has_official_claim and "misleading_official_claim" not in risk_flags:
        risk_flags.append("misleading_official_claim")

    return {
        **normalized,
        "classification_label": "fan_unofficial",
        "fake_score_10": mid_score,
        "is_fake": False,
        "should_monitor": True,
        "confidence": max(_safe_float(normalized.get("confidence"), 0.0), 0.70),
        "risk_flags": risk_flags,
        "reason": "Calibration: non-verified PW-branded channel without blatant mimicry kept at medium risk (6-7); message-level evidence needed for hard fake conclusion.",
        "evidence": evidence,
    }


def classify_telegram_channel_fulfilment_rows_batch(
    channel_rows: list[dict[str, Any]],
    classifier: AzureTelegramChannelClassifier | None = None,
    batch_size: int = TELEGRAM_CHANNEL_FULFILMENT_LLM_BATCH_SIZE,
) -> list[dict[str, Any]]:
    classifier = classifier or _scraper._classifier
    results: list[dict[str, Any]] = []

    llm_candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for channel_row in channel_rows:
        channel_payload = build_telegram_channel_fulfilment_payload(channel_row)
        if channel_payload.get("channel", {}).get("is_verified") is True:
            normalized = _verified_channel_auto_fulfilment_response(channel_payload)
            results.append(
                _persist_channel_fulfilment_result(
                    channel_row=channel_row,
                    channel_payload=channel_payload,
                    normalized=normalized,
                    raw_response=None,
                    llm_meta={
                        "status": "verified_auto_bypass",
                        "mode": "verified_auto",
                        "provider_response_id": None,
                        "error": None,
                    },
                )
            )
            continue
        llm_candidates.append((channel_row, channel_payload))

    effective_batch_size = max(1, _safe_int(batch_size, default=TELEGRAM_CHANNEL_FULFILMENT_LLM_BATCH_SIZE))
    for chunk in [
        llm_candidates[idx : idx + effective_batch_size]
        for idx in range(0, len(llm_candidates), effective_batch_size)
    ]:
        chunk_payloads = [payload for _, payload in chunk]
        raw_batch, llm_meta = classifier.classify_channels_fulfilment_batch(chunk_payloads)
        raw_items = raw_batch.get("results") if isinstance(raw_batch, dict) else []
        if not isinstance(raw_items, list):
            raw_items = []

        by_channel_id: dict[str, dict[str, Any]] = {}
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            item_channel_id = str(item.get("channel_id") or "").strip()
            if item_channel_id and item_channel_id not in by_channel_id:
                by_channel_id[item_channel_id] = item

        llm_status = str(llm_meta.get("status") or "").strip().lower()
        for idx, (channel_row, channel_payload) in enumerate(chunk):
            channel_id = str(channel_row.get("channel_id") or "").strip()
            candidate_raw = by_channel_id.get(channel_id)
            if not candidate_raw and idx < len(raw_items) and isinstance(raw_items[idx], dict):
                candidate_raw = raw_items[idx]

            row_meta = dict(llm_meta)
            if llm_status != "completed" or not isinstance(candidate_raw, dict) or not candidate_raw:
                heuristic = _fulfilment_heuristic_response(channel_payload)
                normalized = normalize_telegram_channel_fulfilment_response(heuristic)
                normalized = _apply_unofficial_pw_policy_calibration(channel_payload, normalized)
                row_meta["status"] = (
                    "heuristic_fallback"
                    if llm_status != "completed"
                    else "heuristic_fallback_missing_row_result"
                )
                row_meta["heuristic_result"] = heuristic
                results.append(
                    _persist_channel_fulfilment_result(
                        channel_row=channel_row,
                        channel_payload=channel_payload,
                        normalized=normalized,
                        raw_response=candidate_raw if isinstance(candidate_raw, dict) else None,
                        llm_meta=row_meta,
                    )
                )
                continue

            normalized = normalize_telegram_channel_fulfilment_response(candidate_raw)
            normalized = _apply_unofficial_pw_policy_calibration(channel_payload, normalized)
            row_meta["status"] = "completed"
            results.append(
                _persist_channel_fulfilment_result(
                    channel_row=channel_row,
                    channel_payload=channel_payload,
                    normalized=normalized,
                    raw_response=candidate_raw,
                    llm_meta=row_meta,
                )
            )

    return results


def classify_telegram_channel_fulfilment_row(
    channel_row: dict[str, Any],
    classifier: AzureTelegramChannelClassifier | None = None,
) -> dict[str, Any]:
    batch_results = classify_telegram_channel_fulfilment_rows_batch(
        channel_rows=[channel_row],
        classifier=classifier,
        batch_size=1,
    )
    if batch_results:
        return batch_results[0]
    return {
        "status": "failed",
        "channel_id": channel_row.get("channel_id"),
    }


def run_telegram_channel_fulfilment(
    brand_id: str | None = None,
    limit: int = 200,
    only_unclassified: bool = True,
    discovered_since_hours: int | None = None,
    force_refulfilment: bool = False,
    target_channels: Iterable[str] | None = None,
) -> dict[str, Any]:
    target_ids, target_usernames = normalize_channel_targets(target_channels or [])
    batch_size = TELEGRAM_CHANNEL_FULFILMENT_LLM_BATCH_SIZE
    rows = db.list_telegram_channels_for_fulfilment(
        brand_id=brand_id,
        only_unclassified=bool(only_unclassified and not force_refulfilment),
        discovered_since_hours=discovered_since_hours,
        limit=max(1, _safe_int(limit, default=200)),
        target_channel_ids=list(target_ids),
        target_channel_usernames=list(target_usernames),
    )

    summary: dict[str, Any] = {
        "phase": "telegram_channel_fulfilment",
        "brand_id": brand_id,
        "total_considered": len(rows),
        "classified": 0,
        "official": 0,
        "likely_official": 0,
        "fan_unofficial": 0,
        "suspicious_fake": 0,
        "irrelevant": 0,
        "should_monitor_count": 0,
        "failed": 0,
        "only_unclassified": bool(only_unclassified and not force_refulfilment),
        "force_refulfilment": bool(force_refulfilment),
        "discovered_since_hours": discovered_since_hours,
        "limit": max(1, _safe_int(limit, default=200)),
        "llm_batch_size": batch_size,
        "llm_batches_processed": 0,
        "ran_at": _to_iso(_now_utc()),
    }

    classifier = _scraper._classifier
    for chunk in _paginate(rows, batch_size):
        summary["llm_batches_processed"] += 1
        try:
            chunk_results = classify_telegram_channel_fulfilment_rows_batch(
                channel_rows=chunk,
                classifier=classifier,
                batch_size=batch_size,
            )
        except Exception:
            logger.exception("Telegram fulfilment batch failed; falling back to per-row processing")
            chunk_results = []
            for row in chunk:
                try:
                    chunk_results.append(
                        classify_telegram_channel_fulfilment_row(
                            channel_row=row,
                            classifier=classifier,
                        )
                    )
                except Exception:
                    logger.exception(
                        "Telegram fulfilment failed for channel_id=%s",
                        row.get("channel_id"),
                    )
                    summary["failed"] += 1
                    continue

        for result in chunk_results:
            if result.get("status") != "classified":
                continue
            summary["classified"] += 1
            label = normalize_fulfilment_label(result.get("classification_label"))
            if label in summary:
                summary[label] += 1
            if bool(result.get("should_monitor")):
                summary["should_monitor_count"] += 1

    return summary


def fulfill_discovered_telegram_channels(
    brand_id: str | None = None,
    limit: int = 200,
    only_unclassified: bool = True,
    discovered_since_hours: int | None = None,
    force_refulfilment: bool = False,
    target_channels: Iterable[str] | None = None,
) -> dict[str, Any]:
    return run_telegram_channel_fulfilment(
        brand_id=brand_id,
        limit=limit,
        only_unclassified=only_unclassified,
        discovered_since_hours=discovered_since_hours,
        force_refulfilment=force_refulfilment,
        target_channels=target_channels,
    )


def analyze_telegram_messages_suspicious_activity(
    brand_id: str | None = None,
    limit: int = 300,
    only_unanalyzed: bool = True,
    message_since_hours: int | None = None,
    force_reanalysis: bool = False,
    target_channels: Iterable[str] | None = None,
    mode: str = "daily",
    batch_size: int | None = None,
    limit_channels: int = TELEGRAM_MESSAGE_ANALYSIS_LIMIT_CHANNELS,
    max_messages_per_channel: int = TELEGRAM_MESSAGE_ANALYSIS_MAX_MESSAGES_PER_CHANNEL,
    persist_channel_rollup: bool = True,
) -> dict[str, Any]:
    return run_telegram_message_suspicious_activity_analysis(
        brand_id=brand_id,
        limit=limit,
        only_unanalyzed=only_unanalyzed,
        message_since_hours=message_since_hours,
        force_reanalysis=force_reanalysis,
        target_channels=target_channels,
        mode=mode,
        batch_size=batch_size,
        limit_channels=limit_channels,
        max_messages_per_channel=max_messages_per_channel,
        persist_channel_rollup=persist_channel_rollup,
    )


def analyze_historical_telegram_messages(
    brand_id: str | None = None,
    limit_channels: int = TELEGRAM_MESSAGE_ANALYSIS_LIMIT_CHANNELS,
    max_messages_per_channel: int = TELEGRAM_MESSAGE_ANALYSIS_MAX_MESSAGES_PER_CHANNEL,
    only_unanalyzed: bool = True,
    force_reanalysis: bool = False,
    target_channels: Iterable[str] | None = None,
    batch_size: int = TELEGRAM_MESSAGE_ANALYSIS_HISTORICAL_BATCH_SIZE,
    persist_channel_rollup: bool = True,
) -> dict[str, Any]:
    return run_telegram_message_analysis_pipeline(
        brand_id=brand_id,
        mode="historical",
        limit=max_messages_per_channel,
        only_unanalyzed=only_unanalyzed,
        message_since_hours=None,
        force_reanalysis=force_reanalysis,
        target_channels=target_channels,
        batch_size=batch_size,
        limit_channels=limit_channels,
        max_messages_per_channel=max_messages_per_channel,
        persist_channel_rollup=persist_channel_rollup,
    )


def analyze_daily_telegram_messages(
    brand_id: str | None = None,
    limit: int = 500,
    only_unanalyzed: bool = True,
    message_since_hours: int | None = TELEGRAM_MESSAGE_ANALYSIS_DAILY_LOOKBACK_HOURS,
    force_reanalysis: bool = False,
    target_channels: Iterable[str] | None = None,
    batch_size: int = TELEGRAM_MESSAGE_ANALYSIS_DAILY_BATCH_SIZE,
    limit_channels: int = TELEGRAM_MESSAGE_ANALYSIS_LIMIT_CHANNELS,
    max_messages_per_channel: int = TELEGRAM_MESSAGE_ANALYSIS_MAX_MESSAGES_PER_CHANNEL,
    persist_channel_rollup: bool = True,
) -> dict[str, Any]:
    return run_telegram_message_analysis_pipeline(
        brand_id=brand_id,
        mode="daily",
        limit=limit,
        only_unanalyzed=only_unanalyzed,
        message_since_hours=message_since_hours,
        force_reanalysis=force_reanalysis,
        target_channels=target_channels,
        batch_size=batch_size,
        limit_channels=limit_channels,
        max_messages_per_channel=max_messages_per_channel,
        persist_channel_rollup=persist_channel_rollup,
    )


def summarize_telegram_channel_message_risk(
    brand_id: str | None = None,
    message_since_hours: int | None = 24,
    max_messages_per_channel: int = 500,
    limit_channels: int = 300,
    target_channels: Iterable[str] | None = None,
    persist_to_channels: bool = True,
) -> dict[str, Any]:
    return run_telegram_channel_risk_rollup_summary(
        brand_id=brand_id,
        message_since_hours=message_since_hours,
        max_messages_per_channel=max_messages_per_channel,
        limit_channels=limit_channels,
        target_channels=target_channels,
        persist_to_channels=persist_to_channels,
    )


async def run_telegram_message_fetch_pipeline_for_brand(
    brand: dict[str, Any],
    limit_channels: int = 500,
    batch_size: int = TELEGRAM_MESSAGE_FETCH_BATCH_SIZE,
    historical_months: int = TELEGRAM_MESSAGE_FETCH_HISTORICAL_MONTHS,
    daily_lookback_days: int = TELEGRAM_MESSAGE_FETCH_DAILY_LOOKBACK_DAYS,
    batch_sleep_min_seconds: int = TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MIN_SECONDS,
    batch_sleep_max_seconds: int = TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MAX_SECONDS,
    between_channels_sleep_seconds: int = TELEGRAM_MESSAGE_FETCH_CHANNEL_SLEEP_SECONDS,
    target_channels: Iterable[str] | None = None,
    max_media_bytes: int = TELEGRAM_MESSAGE_MEDIA_MAX_BYTES,
) -> dict[str, Any]:
    return await _scraper.run_message_fetch_pipeline_for_brand(
        brand=brand,
        limit_channels=limit_channels,
        batch_size=batch_size,
        historical_months=historical_months,
        daily_lookback_days=daily_lookback_days,
        batch_sleep_min_seconds=batch_sleep_min_seconds,
        batch_sleep_max_seconds=batch_sleep_max_seconds,
        between_channels_sleep_seconds=between_channels_sleep_seconds,
        target_channels=target_channels,
        max_media_bytes=max_media_bytes,
    )


def run_telegram_message_fetch_pipeline(
    brand_id: str | None = None,
    limit_channels: int = 500,
    batch_size: int = TELEGRAM_MESSAGE_FETCH_BATCH_SIZE,
    historical_months: int = TELEGRAM_MESSAGE_FETCH_HISTORICAL_MONTHS,
    daily_lookback_days: int = TELEGRAM_MESSAGE_FETCH_DAILY_LOOKBACK_DAYS,
    batch_sleep_min_seconds: int = TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MIN_SECONDS,
    batch_sleep_max_seconds: int = TELEGRAM_MESSAGE_FETCH_BATCH_SLEEP_MAX_SECONDS,
    between_channels_sleep_seconds: int = TELEGRAM_MESSAGE_FETCH_CHANNEL_SLEEP_SECONDS,
    target_channels: Iterable[str] | None = None,
    max_media_bytes: int = TELEGRAM_MESSAGE_MEDIA_MAX_BYTES,
) -> dict[str, Any]:
    if not brand_id:
        return {
            "phase": "telegram_message_fetch",
            "status": "skipped_missing_brand_id",
        }
    brand = {"id": brand_id, "name": ""}
    return asyncio.run(
        run_telegram_message_fetch_pipeline_for_brand(
            brand=brand,
            limit_channels=limit_channels,
            batch_size=batch_size,
            historical_months=historical_months,
            daily_lookback_days=daily_lookback_days,
            batch_sleep_min_seconds=batch_sleep_min_seconds,
            batch_sleep_max_seconds=batch_sleep_max_seconds,
            between_channels_sleep_seconds=between_channels_sleep_seconds,
            target_channels=target_channels,
            max_media_bytes=max_media_bytes,
        )
    )


async def run_telegram_phase2_pipeline_for_brand(
    brand: dict[str, Any],
    keywords: Iterable[str] | None = None,
    per_keyword_limit: int = TELEGRAM_DISCOVERY_MAX_RESULTS_PER_KEYWORD,
    message_backfill_limit: int = TELEGRAM_MESSAGE_BACKFILL_LIMIT,
    incremental_fetch_limit: int = TELEGRAM_MESSAGE_INCREMENTAL_LIMIT,
    force_reclassify: bool = False,
    target_channels: Iterable[str] | None = None,
) -> dict[str, Any]:
    return await _scraper.run_phase2_pipeline_for_brand(
        brand=brand,
        keywords=keywords,
        per_keyword_limit=per_keyword_limit,
        message_backfill_limit=message_backfill_limit,
        incremental_fetch_limit=incremental_fetch_limit,
        force_reclassify=force_reclassify,
        target_channels=target_channels,
    )


_scraper = TelegramScraper()
register_searcher("telegram", _scraper.search)
