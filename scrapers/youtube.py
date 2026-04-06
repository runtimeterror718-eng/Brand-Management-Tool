"""
YouTube unofficial pipeline: discovery, triage, enrichment, persistence.

Owner: Team B
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import httpx

from config.constants import (
    YOUTUBE_OFFICIAL_CHANNEL_HANDLES_ALL,
    YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL,
)
from config.settings import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_BATCH_ENABLED,
    AZURE_OPENAI_BATCH_INPUT_DIR,
    AZURE_OPENAI_BATCH_OUTPUT_DIR,
    AZURE_OPENAI_BATCH_POLL_INTERVAL_SECONDS,
    AZURE_OPENAI_BATCH_POLL_TIMEOUT_SECONDS,
    AZURE_OPENAI_DEPLOYMENT_GPT52,
    AZURE_OPENAI_DEPLOYMENT_GPT53,
    AZURE_OPENAI_DEPLOYMENT_GPT54,
    AZURE_OPENAI_ENDPOINT,
    YOUTUBE_API_KEY,
    YOUTUBE_UNOFFICIAL_MAX_COMMENTS_PER_FLAGGED_VIDEO,
    YOUTUBE_UNOFFICIAL_MAX_RESULTS_PER_KEYWORD,
    YOUTUBE_UNOFFICIAL_PUBLISHED_AFTER_DAYS,
)
from scrapers.base import BaseScraper
from search.engine import register_searcher
from search.filters import SearchParams
from search.fulfillment import build_youtube_fulfillment_from_triage
from storage import queries as db
from transcription.captions import get_transcript_with_fallback
from transcription.extractor import get_apify_transcripts_batch

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
YOUTUBE_ANALYSIS_VERSION = "youtube-unofficial-mvp-v1"
DEFAULT_QUERY_CHUNK_SIZE = 8


PRIMARY_PW_QUERY_TERMS = (
    # ── Core brand ──────────────────────────────────────────────
    "physics wallah",
    "physics wala",
    "physicswallah",
    "physicswala",
    "pw",
    "pw live",
    "pw app",
    "pw website",
    "pw.live",
    # ── Products / Batches ──────────────────────────────────────
    "pw batch",
    "pw course",
    "pw classes",
    "pw coaching",
    "pw online coaching",
    "pw teacher",
    "pw faculty",
    "pw notes",
    "pw modules",
    "pw dpp",
    "pw test series",
    "pw books",
    "pw store",
    "pw coupon",
    "pw discount",
    "pw scholarship",
    "pw arjuna",
    "pw lakshya",
    "pw udaan",
    "pw yakeen",
    "pw prayas",
    "pw manzil",
    "pw warriors",
    "pw foundation",
    "pw sankalp",
    "pw umeed",
    "pw neev",
    "pw ncert punch",
    "pw crash course",
    "pw revision batch",
    "pw droppers batch",
    "arjuna pw",
    "lakshya pw",
    "udaan pw",
    "yakeen pw",
    "prayas pw",
    "manzil pw",
    "warriors pw",
    "arjuna batch pw",
    "lakshya batch pw",
    "udaan batch pw",
    "yakeen batch pw",
    "prayas batch pw",
    "manzil batch pw",
    "arjuna jee pw",
    "arjuna neet pw",
    "lakshya jee pw",
    "lakshya neet pw",
    "udaan jee pw",
    "udaan neet pw",
    "yakeen neet pw",
    "prayas jee pw",
    "arjuna batch",
    "lakshya batch",
    "yakeen batch",
    "prayas batch",
    "udaan batch",
    "neev batch",
    # ── Wallah vertical brands ──────────────────────────────────
    "jee wallah",
    "neet wallah",
    "banking wallah",
    "ssc wallah",
    "gate wallah",
    "law wallah",
    "ca wallah",
    "cs wallah",
    "commerce wallah",
    "upsc wallah",
    "college wallah",
    "mba wallah",
    "defence wallah",
    "ncert wallah",
    "competition wallah",
    "pw only ias",
    "pw onlyias",
    # ── Vidyapeeth (offline centres) ────────────────────────────
    "pw vidyapeeth",
    "vidyapeeth pw",
    "pw pathshala",
    "pathshala pw",
    "pw offline centre",
    "pw offline coaching",
    "pw vidyapeeth jee",
    "pw vidyapeeth neet",
    "pw foundation vidyapeeth",
    "pw delhi ncr vidyapeeth",
    "pw tamil nadu vidyapeeth",
    "pw lucknow vidyapeeth",
    "pw bihar vidyapeeth",
    "pw up vidyapeeth",
    "pw patna vidyapeeth",
    "pw kota vidyapeeth",
    "vidyapeeth bhopal",
    "vidyapeeth jaipur",
    "vidyapeeth delhi",
    "vidyapeeth indore",
    "vidyapeeth gandhinagar",
    # ── PW IOI (Institute of Innovation) ────────────────────────
    "pw ioi",
    "pwioi",
    "pw institute of innovation",
    "pw ioi hackathon",
    "pw ioi bangalore",
    "medhavi skills university pw",
    # ── PW Skills (upskilling vertical) ─────────────────────────
    "pw skills",
    "pwskills",
    "pw skills review",
    "pw skills data science",
    "pw skills full stack",
    "pw skills devops",
    "pw skills data analytics",
    "pw skills course review",
    "pw skills placement",
    "pw skills fraud",
    "pw skills scam",
    # ── MedEd (medical education) ───────────────────────────────
    "pw meded",
    "meded pw",
    "pw med ed",
    "pw neet pg",
    "pw fmge",
    "pw inicet",
    # ── Other exam verticals ────────────────────────────────────
    "pw banking",
    "pw ssc",
    "pw gate",
    "pw mba",
    "pw cuet",
    "pw defence",
    "pw judiciary",
    "pw clat",
    "pw commerce",
    "pw ca",
    "pw cs",
    "pw ugc net",
    "pw olympiad",
    # ── Founders / Leadership ───────────────────────────────────
    "alakh pandey",
    "alakh sir",
    "alakh pandey pw",
    "alakh sir pw",
    "alakh pandey physics wallah",
    "physics wallah alakh pandey",
    "alakh sir batch",
    "alakh sir motivation",
    "prateek maheshwari",
    "prateek maheshwari pw",
    "prateek sir pw",
    "prateek maheshwari physics wallah",
    "prateek boob",
    # ── Negative PR / Controversy signals ───────────────────────
    "pw scam",
    "pw fraud",
    "pw exposed",
    "pw controversy",
    "pw refund",
    "pw layoffs",
    "pw data leak",
    "pw data breach",
    "pw quality",
    "pw downfall",
    "pw fired",
    "pw terminated",
    "pw bribe",
    "pw bribery",
    "physics wallah scam",
    "physics wallah fraud",
    "physics wallah refund",
    "physics wallah controversy",
    "physics wallah exposed",
    "physics wallah complaint",
    "pw consumer court",
    "pw unpaid",
    "pw salary",
    "pw attrition",
    "physics wallah vs byju",
    "physics wallah vs unacademy",
    "physics wallah vs allen",
    # ── Kashmir / casteist controversies ─────────────────────────
    "pw kashmir",
    "pw fir",
    "pw toofan",
    "baderkote pw",
    "chor chamar pw",
    "rishi jain pw",
    "casteist pw",
    # ── IPO / Business ──────────────────────────────────────────
    "pw ipo",
    "physicswallah ipo",
    "physics wallah ipo",
    "pw stock",
    "pw share price",
    "pw listing",
    "pw valuation",
    # ── Teacher exodus / hiring ─────────────────────────────────
    "pw teachers leaving",
    "left pw",
    "quit pw",
    "resigned pw",
    "pw sell pen interview",
    "pw interview experience",
    "pw glassdoor",
    "pw employee review",
)

SECONDARY_PW_QUERY_TERMS = (
    # ── Top faculty (Physics) ───────────────────────────────────
    "rajwant sir pw",
    "rajwant sir physics wallah",
    "rj sir pw",
    "saleem sir pw",
    "saleem sir physics wallah",
    "nkc sir pw",
    "neeraj kumar choudhary pw",
    "amit sir pw",
    "amit mahajan sir pw",
    "sachin sir pw",
    "sachin jakhar sir",
    "sarvesh sir pw",
    # ── Top faculty (Chemistry) ─────────────────────────────────
    "om pandey pw",
    "om sir pw",
    "pankaj sir pw",
    "babua sir pw",
    "anushka mam pw",
    "anushka mam physics wallah",
    # ── Top faculty (Biology) ───────────────────────────────────
    "nidhi mam pw",
    "nidhi mam biology pw",
    # ── Top faculty (Maths) ─────────────────────────────────────
    "mr sir pw",
    "mr sir physics wallah",
    "ritik sir pw",
    "ritik sir physics wallah",
    # ── Top faculty (General / Other) ───────────────────────────
    "samriddhi maam",
    "samriddhi mam",
    "samridhi maam",
    "samridhi mam",
    "samriddhi pw",
    "samridhi pw",
    "tarun sir pw",
    "tarun kumar physics pw",
    "khazana pw faculty",
    "pw faculty live",
    "pw faculties",
    "pw teacher live",
    # ── Ex-PW teachers / criticism ──────────────────────────────
    "sankalp bharat pw",
    "tarun kumar left pw",
    "manish dubey pw",
    "sarvesh dixit pw",
    "udaan companions reality",
    "ex pw teacher",
    "pw teacher controversy",
    # ── Misspellings / alternate names ──────────────────────────
    "physics wala pw",
    "physics walla",
    "phisics wallah",
    "fisics wallah",
    "alakh pande",
    "alakh pande sir",
    "alakh pw",
    "prateek pw",
    "samridhi mam pw",
    "samriddhi mam pw",
    "pw med ed",
    "pw vidhyapeeth",
    # ── Edtech commentary / comparison ──────────────────────────
    "kota factory memes pw",
    "neet jee aspirants pw",
    "pw vs allen youtube",
    "pw vs unacademy review",
    "pw vs byju review",
    "pw vs vedantu",
    "pw vs aakash",
    "best coaching jee neet 2026",
    "edtech scam india",
    "edtech fraud india",
    # ── App / product reviews ───────────────────────────────────
    "pw app review",
    "pw app crash",
    "pw app not working",
    "pw app rating",
    "physics wallah app review",
    "pw modules review",
    "pw books review",
    "pw dpp quality",
)

EXPANDED_PW_QUERY_RULES = (
    ("arjuna", ("pw", "physics wallah")),
    ("lakshya", ("pw", "physics wallah")),
    ("udaan", ("pw", "physics wallah")),
    ("yakeen", ("pw", "physics wallah")),
    ("prayas", ("pw", "physics wallah")),
    ("manzil", ("pw", "physics wallah")),
    ("neev", ("pw", "physics wallah")),
    ("sankalp", ("pw", "physics wallah")),
    ("umeed", ("pw", "physics wallah")),
    ("vidyapeeth", ("pw", "physics wallah")),
    ("pathshala", ("pw", "physics wallah")),
    ("meded", ("pw", "physics wallah")),
    ("pw skills", ("review", "scam", "placement")),
    ("pw ioi", ("review", "hackathon", "bangalore")),
    ("alakh pandey", ("controversy", "ipo", "motivation", "interview")),
    ("physics wallah", ("scam", "refund", "complaint", "review", "vs allen", "vs unacademy")),
)

AMBIGUOUS_STANDALONE_TERMS = frozenset(
    {"arjuna", "lakshya", "udaan", "yakeen", "prayas", "manzil", "vidyapeeth", "pathshala", "meded"}
)

ALLOWED_TRIAGE_LABELS = {"positive", "negative", "uncertain"}
ALLOWED_FINAL_SENTIMENTS = {"positive", "negative", "neutral", "mixed", "uncertain"}
ALLOWED_SIMPLE_SENTIMENTS = {"positive", "neutral", "negative"}
ALLOWED_TRANSCRIPT_PRIORITY = {"low", "medium", "high"}
ALLOWED_TRANSCRIPT_PR_SENTIMENTS = {"positive", "neutral", "negative", "uncertain"}
ALLOWED_TRANSCRIPT_PR_SEVERITY = {"low", "medium", "high"}
ALLOWED_TRANSCRIPT_PR_ISSUE_TYPES = {
    "motivational",
    "social_commentary",
    "student_wellbeing",
    "brand_attack",
    "faculty_criticism",
    "teaching_quality",
    "pricing",
    "refund",
    "technical_issue",
    "misinformation",
    "controversy",
    "praise",
    "other",
}
ALLOWED_TRANSCRIPT_PR_TARGETS = {
    "brand",
    "faculty",
    "product",
    "parents",
    "students",
    "education_system",
    "society",
    "none",
}
ALLOWED_TRANSCRIPT_PR_ACTIONS = {"ignore", "monitor", "respond", "escalate"}
TERMINAL_BATCH_STATUSES = {"completed", "failed", "cancelled", "expired"}
ACTIVE_BATCH_STATUSES = {
    "validating",
    "in_progress",
    "finalizing",
    "pending",
    "queued",
    "running",
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_spaces(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


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


def _sha12(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _chunked(items: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        return [items]
    return [items[i : i + size] for i in range(0, len(items), size)]


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _to_iso(value: datetime | None) -> str:
    if not isinstance(value, datetime):
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _parse_duration_seconds(duration: str | None) -> int:
    if not duration:
        return 0
    match = re.match(
        r"P(?:\d+Y)?(?:\d+M)?(?:\d+D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?",
        duration,
    )
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return (hours * 3600) + (minutes * 60) + seconds


def normalize_channel_handle(handle: str | None) -> str:
    value = (handle or "").strip().lower()
    if value.startswith("http"):
        value = value.rsplit("/", 1)[-1]
    if value.startswith("@"):
        value = value[1:]
    return value.strip()


def extract_video_id(source_url: str) -> str:
    if "watch?v=" in source_url:
        return source_url.split("watch?v=", 1)[1].split("&", 1)[0]
    if "youtu.be/" in source_url:
        return source_url.split("youtu.be/", 1)[1].split("?", 1)[0]
    return ""


def dedupe_query_terms(terms: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for term in terms:
        normalized = _normalize_spaces(term)
        if not normalized:
            continue
        if normalized in AMBIGUOUS_STANDALONE_TERMS:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def build_expanded_query_terms() -> list[str]:
    expanded: list[str] = []
    for head, options in EXPANDED_PW_QUERY_RULES:
        for option in options:
            expanded.append(f"{head} {option}")
    return dedupe_query_terms(expanded)


def build_discovery_query_buckets(
    extra_terms: Iterable[str] | None = None,
    include_secondary: bool = True,
) -> dict[str, list[str]]:
    primary = dedupe_query_terms(list(PRIMARY_PW_QUERY_TERMS) + list(extra_terms or []))
    secondary = dedupe_query_terms(SECONDARY_PW_QUERY_TERMS) if include_secondary else []
    expanded = build_expanded_query_terms()
    return {
        "primary": primary,
        "secondary": secondary,
        "expanded": expanded,
    }


def build_query_buckets(
    query_buckets: dict[str, list[str]],
    bucket_size: int = DEFAULT_QUERY_CHUNK_SIZE,
) -> dict[str, list[list[str]]]:
    return {
        bucket: _chunked(list(terms), bucket_size)
        for bucket, terms in query_buckets.items()
        if terms
    }


def is_blacklisted_channel(channel_id: str | None, channel_handle: str | None) -> bool:
    if channel_id and channel_id in YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL:
        return True
    normalized_handle = normalize_channel_handle(channel_handle)
    if normalized_handle and normalized_handle in YOUTUBE_OFFICIAL_CHANNEL_HANDLES_ALL:
        return True
    return False


def classify_channel_owner(channel_id: str | None, channel_handle: str | None) -> str:
    return "Owned" if is_blacklisted_channel(channel_id, channel_handle) else "Not Owned"


def _build_video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def map_video_to_raw_video_row(
    candidate: dict[str, Any],
    brand_id: str | None,
    title_triage: dict[str, Any] | None = None,
    title_custom_id: str | None = None,
    title_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    video = candidate.get("video", {})
    snippet = video.get("snippet", {})
    statistics = video.get("statistics", {})
    content = video.get("contentDetails", {})
    triage = title_triage or {}
    triage_meta = title_meta or {}

    title_artifacts = {
        "stage": "title_triage",
        "custom_id": title_custom_id or "",
        "status": triage_meta.get("status"),
        "mode": triage_meta.get("mode"),
        "provider_batch_id": triage_meta.get("provider_batch_id"),
        "input_file_id": triage_meta.get("input_file_id"),
        "output_file_id": triage_meta.get("output_file_id"),
        "error_file_id": triage_meta.get("error_file_id"),
        "batch_input_path": triage_meta.get("batch_input_path"),
        "batch_output_path": triage_meta.get("batch_output_path"),
        "batch_error_path": triage_meta.get("batch_error_path"),
        "correlation_id": triage_meta.get("correlation_id"),
        "submitted_at": triage_meta.get("submitted_at"),
        "polled_at": triage_meta.get("polled_at"),
        "completed_at": triage_meta.get("completed_at"),
        "ingested_at": triage_meta.get("ingested_at"),
        "error": triage_meta.get("error"),
    }

    return {
        "brand_id": brand_id,
        "channel_id": candidate.get("channel_id"),
        "video_id": candidate.get("video_id"),
        "video_title": snippet.get("title", ""),
        "video_date": _to_iso(_parse_iso_datetime(snippet.get("publishedAt")) or _now_utc()),
        "video_resolution": candidate.get("video_resolution") or "",
        "video_duration": _parse_duration_seconds(content.get("duration")),
        "video_views": _safe_int(statistics.get("viewCount")),
        "video_likes": _safe_int(statistics.get("likeCount")),
        "video_description": snippet.get("description", ""),
        "video_comment_count": _safe_int(statistics.get("commentCount")),
        "media_type": "video",
        "source_url": candidate.get("source_url") or _build_video_url(candidate.get("video_id", "")),
        "scraped_at": _to_iso(_now_utc()),
        "title_triage_label": triage.get("label"),
        "title_triage_confidence": _safe_float(triage.get("confidence")),
        "title_triage_is_pr_risk": bool(triage.get("is_pr_risk", False)),
        "title_triage_issue_type": triage.get("issue_type"),
        "title_triage_reason": triage.get("reason"),
        "title_triage_custom_id": title_custom_id or "",
        "title_triage_mode": triage_meta.get("mode"),
        "title_triage_batch_input": triage_meta.get("batch_input_path"),
        "title_triage_batch_output": triage_meta.get("batch_output_path"),
        "title_triage_processed_at": _to_iso(_now_utc()),
        "analysis_artifacts": {
            "title_triage": title_artifacts,
        },
        "raw_data": {
            "video": video,
            "channel": candidate.get("channel", {}),
            "search_hits": candidate.get("search_hits", []),
            "title_triage": triage,
            "title_triage_artifacts": title_artifacts,
        },
    }


def map_channel_to_raw_channel_row(candidate: dict[str, Any], brand_id: str | None) -> dict[str, Any]:
    channel = candidate.get("channel", {})
    snippet = channel.get("snippet", {})
    statistics = channel.get("statistics", {})
    channel_id = candidate.get("channel_id")
    channel_handle = snippet.get("customUrl")

    return {
        "brand_id": brand_id,
        "channel_id": channel_id,
        "channel_name": snippet.get("title", ""),
        "channel_subscribers": _safe_int(statistics.get("subscriberCount")),
        "channel_owner": classify_channel_owner(channel_id, channel_handle),
        "scraped_at": _to_iso(_now_utc()),
    }


def map_video_to_mention(
    brand_id: str,
    candidate: dict[str, Any],
    triage: dict[str, Any],
    final_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    video = candidate.get("video", {})
    channel = candidate.get("channel", {})
    snippet = video.get("snippet", {})
    stats = video.get("statistics", {})
    channel_snippet = channel.get("snippet", {})

    sentiment_label = triage.get("label", "uncertain")
    confidence = float(triage.get("confidence") or 0.0)
    sentiment_score = 0.0
    if sentiment_label == "negative":
        sentiment_score = -confidence
    elif sentiment_label == "positive":
        sentiment_score = confidence

    merged_analysis = final_analysis or {}

    return {
        "brand_id": brand_id,
        "platform": "youtube",
        "platform_ref_id": candidate.get("video_id", ""),
        "content_text": snippet.get("title", ""),
        "content_type": "video",
        "author_handle": normalize_channel_handle(channel_snippet.get("customUrl")),
        "author_name": channel_snippet.get("title", "") or snippet.get("channelTitle", ""),
        "engagement_score": _safe_int(stats.get("viewCount")),
        "likes": _safe_int(stats.get("likeCount")),
        "shares": 0,
        "comments_count": _safe_int(stats.get("commentCount")),
        "sentiment_score": sentiment_score,
        "sentiment_label": sentiment_label,
        "language": snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or "",
        "theme": merged_analysis.get("issue_type") if merged_analysis else None,
        "source_url": candidate.get("source_url") or _build_video_url(candidate.get("video_id", "")),
        "published_at": _to_iso(_parse_iso_datetime(snippet.get("publishedAt")) or _now_utc()),
        "scraped_at": _to_iso(_now_utc()),
        "raw_data": {
            "youtube": {
                "video": video,
                "channel": channel,
                "search_hits": candidate.get("search_hits", []),
            },
            "title_triage": triage,
            "final_analysis": merged_analysis,
            "analysis_version": YOUTUBE_ANALYSIS_VERSION,
        },
    }


def map_video_to_search_result(candidate: dict[str, Any]) -> dict[str, Any]:
    video = candidate.get("video", {})
    channel = candidate.get("channel", {})
    snippet = video.get("snippet", {})
    stats = video.get("statistics", {})
    channel_snippet = channel.get("snippet", {})

    return {
        "id": candidate.get("video_id", ""),
        "platform_ref_id": candidate.get("video_id", ""),
        "content_text": snippet.get("title", ""),
        "content_type": "video",
        "author_handle": normalize_channel_handle(channel_snippet.get("customUrl")),
        "author_name": channel_snippet.get("title", "") or snippet.get("channelTitle", ""),
        "engagement_score": _safe_int(stats.get("viewCount")),
        "likes": _safe_int(stats.get("likeCount")),
        "comments_count": _safe_int(stats.get("commentCount")),
        "source_url": candidate.get("source_url") or _build_video_url(candidate.get("video_id", "")),
        "published_at": _parse_iso_datetime(snippet.get("publishedAt")) or _now_utc(),
        "language": snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage") or "en",
        "raw_data": {
            "video": video,
            "channel": channel,
            "search_hits": candidate.get("search_hits", []),
        },
    }


def _load_youtube_api_keys() -> list[str]:
    """Load all YouTube API keys from env (KEY, KEY_1, KEY_2, KEY_3, KEY_4)."""
    import os
    keys = []
    primary = os.environ.get("YOUTUBE_API_KEY", "")
    if primary:
        keys.append(primary)
    for i in range(1, 10):
        k = os.environ.get(f"YOUTUBE_API_KEY_{i}", "")
        if k and k not in keys:
            keys.append(k)
    return keys


import threading

class _KeyPool:
    """Thread-safe API key pool with rotation on quota exhaustion."""

    def __init__(self, keys: list[str]):
        self._keys = list(keys)
        self._lock = threading.Lock()
        self._exhausted: set[str] = set()
        self._current_idx = 0

    @property
    def total(self) -> int:
        return len(self._keys)

    def get_key(self) -> str:
        """Get the current active key (thread-safe)."""
        with self._lock:
            available = [k for k in self._keys if k not in self._exhausted]
            if not available:
                return ""
            return available[0]

    def mark_exhausted(self, key: str) -> str | None:
        """Mark a key as exhausted and return the next available key, or None if all gone."""
        with self._lock:
            self._exhausted.add(key)
            available = [k for k in self._keys if k not in self._exhausted]
            if not available:
                logger.error("All %d YouTube API keys exhausted (quota exceeded)", len(self._keys))
                return None
            next_key = available[0]
            logger.info(
                "YouTube key ...%s exhausted. Rotated to ...%s (%d of %d remaining)",
                key[-6:], next_key[-6:], len(available), len(self._keys),
            )
            return next_key

    def is_all_exhausted(self) -> bool:
        with self._lock:
            return len(self._exhausted) >= len(self._keys)


class YouTubeDataAPIClient:
    def __init__(self, api_key: str, timeout: float = 30.0):
        all_keys = _load_youtube_api_keys()
        if api_key and api_key not in all_keys:
            all_keys.insert(0, api_key)
        if not all_keys:
            all_keys = [api_key] if api_key else []
        self._pool = _KeyPool(all_keys)
        self.api_key = self._pool.get_key()  # kept for backward compat
        self.timeout = timeout
        logger.info("YouTubeDataAPIClient: %d API keys loaded for rotation", self._pool.total)

    async def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """GET with per-request key selection and retry on 403."""
        for _attempt in range(self._pool.total + 1):
            current_key = self._pool.get_key()
            if not current_key:
                raise RuntimeError("All YouTube API keys exhausted")

            request_params = dict(params)
            request_params["key"] = current_key
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(f"{YOUTUBE_API_BASE_URL}{endpoint}", params=request_params)
                    if resp.status_code == 403:
                        next_key = self._pool.mark_exhausted(current_key)
                        if next_key is None:
                            resp.raise_for_status()
                        continue  # retry with next key
                    resp.raise_for_status()
                    payload = resp.json()
                    if isinstance(payload, dict) and payload.get("error"):
                        raise RuntimeError(payload["error"])
                    return payload
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    next_key = self._pool.mark_exhausted(current_key)
                    if next_key is None:
                        raise
                    continue
                raise
        raise RuntimeError("All YouTube API keys exhausted")

    def _get_sync(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        """Sync GET with per-request key selection and retry on 403."""
        for _attempt in range(self._pool.total + 1):
            current_key = self._pool.get_key()
            if not current_key:
                raise RuntimeError("All YouTube API keys exhausted")

            request_params = dict(params)
            request_params["key"] = current_key
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(f"{YOUTUBE_API_BASE_URL}{endpoint}", params=request_params)
                    if resp.status_code == 403:
                        self._pool.mark_exhausted(current_key)
                        continue
                    resp.raise_for_status()
                    payload = resp.json()
                    if isinstance(payload, dict) and payload.get("error"):
                        raise RuntimeError(payload["error"])
                    return payload
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    self._pool.mark_exhausted(current_key)
                    continue
                raise
        raise RuntimeError("All YouTube API keys exhausted")

    async def search_videos(
        self,
        query: str,
        published_after: datetime,
        max_results: int,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page_token: str | None = None

        while len(results) < max_results:
            req_size = min(50, max_results - len(results))
            payload = await self._get(
                "/search",
                {
                    "part": "snippet",
                    "type": "video",
                    "order": "date",
                    "q": query,
                    "maxResults": req_size,
                    "publishedAfter": published_after.isoformat().replace("+00:00", "Z"),
                    "pageToken": page_token,
                },
            )

            for item in payload.get("items", []):
                video_id = ((item.get("id") or {}).get("videoId"))
                if not video_id:
                    continue
                results.append(
                    {
                        "video_id": video_id,
                        "channel_id": (item.get("snippet") or {}).get("channelId"),
                        "search_item": item,
                    }
                )

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return results[:max_results]

    async def videos_by_id(self, video_ids: list[str]) -> dict[str, dict[str, Any]]:
        videos: dict[str, dict[str, Any]] = {}
        for chunk in _chunked(video_ids, 50):
            if not chunk:
                continue
            payload = await self._get(
                "/videos",
                {
                    "part": "snippet,contentDetails,statistics,status",
                    "id": ",".join(chunk),
                    "maxResults": 50,
                },
            )
            for item in payload.get("items", []):
                item_id = item.get("id")
                if item_id:
                    videos[item_id] = item
        return videos

    async def channels_by_id(self, channel_ids: list[str]) -> dict[str, dict[str, Any]]:
        channels: dict[str, dict[str, Any]] = {}
        for chunk in _chunked(channel_ids, 50):
            if not chunk:
                continue
            payload = await self._get(
                "/channels",
                {
                    "part": "snippet,statistics",
                    "id": ",".join(chunk),
                    "maxResults": 50,
                },
            )
            for item in payload.get("items", []):
                item_id = item.get("id")
                if item_id:
                    channels[item_id] = item
        return channels

    async def fetch_comments(self, video_id: str, max_results: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        page_token: str | None = None

        while len(comments) < max_results:
            req_size = min(100, max_results - len(comments))
            payload = await self._get(
                "/commentThreads",
                {
                    "part": "snippet,replies",
                    "videoId": video_id,
                    "textFormat": "plainText",
                    "maxResults": req_size,
                    "pageToken": page_token,
                    "order": "time",
                },
            )

            for item in payload.get("items", []):
                top_level = ((item.get("snippet") or {}).get("topLevelComment") or {}).get("snippet", {})
                comments.append(
                    {
                        "video_id": video_id,
                        "comment_author": top_level.get("authorDisplayName", ""),
                        "comment_text": top_level.get("textDisplay", ""),
                        "comment_replies": _safe_int((item.get("snippet") or {}).get("totalReplyCount")),
                        "comment_likes": _safe_int(top_level.get("likeCount")),
                        "comment_date": _to_iso(_parse_iso_datetime(top_level.get("publishedAt")) or _now_utc()),
                        "scraped_at": _to_iso(_now_utc()),
                    }
                )

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return comments[:max_results]

    def _build_comment_row(
        self,
        video_id: str,
        snippet: dict[str, Any],
        comment_id: str,
        parent_comment_id: str | None,
        thread_comment_id: str,
        is_reply: bool,
        raw_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "video_id": video_id,
            "comment_id": comment_id,
            "parent_comment_id": parent_comment_id or None,
            "thread_comment_id": thread_comment_id or comment_id,
            "is_reply": bool(is_reply),
            "comment_author": snippet.get("authorDisplayName", ""),
            "comment_text": snippet.get("textDisplay", ""),
            "comment_replies": 0 if is_reply else _safe_int(snippet.get("totalReplyCount")),
            "comment_likes": _safe_int(snippet.get("likeCount")),
            "comment_date": _to_iso(_parse_iso_datetime(snippet.get("publishedAt")) or _now_utc()),
            "scraped_at": _to_iso(_now_utc()),
            "raw_payload": raw_payload or {},
        }

    def _fetch_replies_sync(
        self,
        video_id: str,
        parent_comment_id: str,
        max_results: int,
        seen_ids: set[str],
    ) -> list[dict[str, Any]]:
        replies: list[dict[str, Any]] = []
        page_token: str | None = None
        while len(replies) < max_results:
            req_size = min(100, max_results - len(replies))
            payload = self._get_sync(
                "/comments",
                {
                    "part": "snippet",
                    "parentId": parent_comment_id,
                    "maxResults": req_size,
                    "pageToken": page_token,
                    "textFormat": "plainText",
                },
            )
            for item in payload.get("items", []):
                comment_id = str(item.get("id") or "").strip()
                if not comment_id or comment_id in seen_ids:
                    continue
                seen_ids.add(comment_id)
                snippet = item.get("snippet") or {}
                replies.append(
                    self._build_comment_row(
                        video_id=video_id,
                        snippet=snippet,
                        comment_id=comment_id,
                        parent_comment_id=parent_comment_id,
                        thread_comment_id=parent_comment_id,
                        is_reply=True,
                        raw_payload=item,
                    )
                )
                if len(replies) >= max_results:
                    break
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
        return replies

    def fetch_comments_with_replies_sync(self, video_id: str, max_results: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        page_token: str | None = None
        seen_ids: set[str] = set()

        while len(comments) < max_results:
            req_size = min(100, max_results - len(comments))
            payload = self._get_sync(
                "/commentThreads",
                {
                    "part": "snippet,replies",
                    "videoId": video_id,
                    "textFormat": "plainText",
                    "maxResults": req_size,
                    "pageToken": page_token,
                    "order": "time",
                },
            )

            for item in payload.get("items", []):
                top_level = ((item.get("snippet") or {}).get("topLevelComment") or {})
                top_level_snippet = top_level.get("snippet") or {}
                thread_snippet = item.get("snippet") or {}
                top_level_id = str(top_level.get("id") or "").strip()
                if top_level_id and top_level_id not in seen_ids:
                    seen_ids.add(top_level_id)
                    top_level_row_snippet = {
                        **top_level_snippet,
                        "totalReplyCount": thread_snippet.get("totalReplyCount", 0),
                    }
                    comments.append(
                        self._build_comment_row(
                            video_id=video_id,
                            snippet=top_level_row_snippet,
                            comment_id=top_level_id,
                            parent_comment_id=None,
                            thread_comment_id=top_level_id,
                            is_reply=False,
                            raw_payload=top_level,
                        )
                    )
                if len(comments) >= max_results:
                    break

                inline_replies = ((item.get("replies") or {}).get("comments") or [])
                for reply in inline_replies:
                    reply_id = str(reply.get("id") or "").strip()
                    if not reply_id or reply_id in seen_ids:
                        continue
                    seen_ids.add(reply_id)
                    comments.append(
                        self._build_comment_row(
                            video_id=video_id,
                            snippet=reply.get("snippet") or {},
                            comment_id=reply_id,
                            parent_comment_id=top_level_id or None,
                            thread_comment_id=top_level_id or reply_id,
                            is_reply=True,
                            raw_payload=reply,
                        )
                    )
                    if len(comments) >= max_results:
                        break

                total_reply_count = _safe_int((item.get("snippet") or {}).get("totalReplyCount"))
                inline_count = len(inline_replies)
                if (
                    top_level_id
                    and total_reply_count > inline_count
                    and len(comments) < max_results
                ):
                    remaining = max_results - len(comments)
                    extra_replies = self._fetch_replies_sync(
                        video_id=video_id,
                        parent_comment_id=top_level_id,
                        max_results=remaining,
                        seen_ids=seen_ids,
                    )
                    comments.extend(extra_replies)
                    if len(comments) >= max_results:
                        break

            page_token = payload.get("nextPageToken")
            if not page_token:
                break

        return comments[:max_results]


TITLE_TRIAGE_PROMPT = (
    "You are a PR-risk triage model for YouTube content about Physics Wallah (PW). "
    "Use BOTH title and description from the input payload when making the decision. "
    "Return strict JSON with keys: label (positive|negative|uncertain), is_pr_risk (boolean), "
    "confidence (0..1), issue_type (string), reason (string)."
)

TRANSCRIPT_ANALYSIS_PROMPT = (
    "Analyze transcript text for PR risk. Return strict JSON with keys: "
    "sentiment (positive|negative|neutral|mixed|uncertain), severity (low|medium|high|critical), "
    "issue_type, target_entity, key_claims (array), transcript_summary (string), reason (string)."
)

COMMENT_ANALYSIS_PROMPT = (
    "Analyze YouTube comments for public sentiment and risk. Return strict JSON with keys: "
    "sentiment (positive|negative|neutral|mixed|uncertain), top_negative_themes (array), "
    "comment_sentiment_summary (string), is_pr_risk (boolean), reason (string)."
)

TRANSCRIPT_SENTIMENT_TRIAGE_PROMPT = (
    "You are a PR-risk analyst for Physics Wallah.\n\n"
    "Your job is NOT to do generic sentiment analysis.\n"
    "Your job is to assess transcript content ONLY from a PR / brand-reputation perspective.\n\n"
    "Important:\n"
    "- Emotional, sad, serious, or sensitive topics are NOT automatically negative PR.\n"
    "- Motivational speeches, mental health discussions, cautionary examples, student struggles, exam pressure, suicide/depression awareness, or criticism of society/parenting are often neutral or positive from a PR perspective if they are not attacking the brand.\n"
    "- Classify as negative only when the transcript creates reputational risk for the brand, its leadership, faculty, product, policies, teaching quality, trust, ethics, pricing, refunds, safety, or public perception.\n"
    "- If the speaker is discussing social problems, student pressure, motivation, empathy, or reform-oriented commentary, do NOT mark it negative unless the brand is being blamed or harmed.\n"
    "- Separate emotional tone from PR risk.\n"
    "- The question is: \"Does this transcript harm the brand's reputation?\" not \"Is this transcript sad?\"\n\n"
    "Analyze the input transcript ONLY from a PR-risk perspective for Physics Wallah.\n"
    "Input payload fields are: brand_name, video_title, channel_name, speaker_context, transcript_text.\n\n"
    "Return JSON with this exact schema:\n"
    "{\n"
    "  \"pr_sentiment\": \"positive|neutral|negative|uncertain\",\n"
    "  \"is_pr_risk\": true,\n"
    "  \"severity\": \"low|medium|high\",\n"
    "  \"issue_type\": \"motivational|social_commentary|student_wellbeing|brand_attack|faculty_criticism|teaching_quality|pricing|refund|technical_issue|misinformation|controversy|praise|other\",\n"
    "  \"target_entity\": \"brand|faculty|product|parents|students|education_system|society|none\",\n"
    "  \"transcript_summary\": \"string\",\n"
    "  \"key_claims\": [\"string\"],\n"
    "  \"brand_harm_evidence\": [\"string\"],\n"
    "  \"protective_context\": [\"string\"],\n"
    "  \"recommended_action\": \"ignore|monitor|respond|escalate\",\n"
    "  \"reason\": \"string\"\n"
    "}\n\n"
    "Decision rules:\n"
    "1. Mark \"negative\" ONLY if the transcript contains direct or indirect reputational harm to the brand.\n"
    "2. Mark \"neutral\" if the transcript is emotional, sad, intense, or controversial in tone, but does not damage the brand.\n"
    "3. Mark \"positive\" if the transcript is motivational, empathetic, trust-building, student-supportive, or socially responsible in a way that helps the brand.\n"
    "4. If the speaker criticizes parents, society, exam pressure, or the education system in a general way, that is usually NOT brand-negative.\n"
    "5. If the transcript discusses suicide, depression, pressure, or failure as cautionary or motivational examples, do NOT mark it negative unless the brand is blamed.\n"
    "6. Use \"brand_harm_evidence\" only for lines or ideas that actually create PR risk for the brand.\n"
    "7. Use \"protective_context\" for signals that reduce PR risk, such as empathy, motivation, student support, awareness, or reform-oriented messaging.\n"
    "8. High severity only if there is strong evidence of scandal, backlash, harmful conduct, or clear reputational damage to the brand.\n"
    "9. Do not confuse serious subject matter with negative PR.\n"
    "10. Return JSON only."
)

COMMENT_SENTIMENT_BATCH_PROMPT = (
    "You are an expert YouTube comment analyst for an education channel. "
    "Your job is to label sentiment of each comment for triage. "
    "You are based out of India and clearly understand student colloquial and slangs specific to indian audience.\n\n"
    "You will receive a JSON ARRAY under `comments` (up to 40 items). Each item contains:\n"
    "- Comment ID\n"
    "- Video title\n"
    "- Comment String\n"
    "- type of comment\n\n"
    "FOR EACH COMMENT: assign exactly one sentiment from neutral, positive and negative using the context of video title and type of comment.\n\n"
    "SENTIMENT RULES- infer on the basis of text and not emojis\n"
    "- positive: praise/love/success gratitude, excited tone\n"
    "- negative: complaints/frustration/anger/disappointement/sadness and all other negative emotions directed at company PW and the offerings, any bad experience with company, and anything else negative.\n"
    "- neutral: plain question/statement, mixed/unclear tone, most community discussions, most noise, feelings directed at self and not company PW.\n\n"
    "IMPORTANT- ALWAYS OUTPUT IN ALL LOWERCASE, NEVER OUTPUT title case (Negative/Postive/Neutral) or All caps. only "
    "\"neutral\", \"positive\", \"negative\" is allowed. Always make sure case sensitivity of comment ID matches EXACTLY since it is the join key.\n\n"
    "Return strict JSON object with key `results`, where value is an array of objects in this exact shape:\n"
    "{\"Comment ID\":\"<exact_input_comment_id>\",\"Sentiment\":\"positive|neutral|negative\"}"
)

FINAL_SYNTHESIS_PROMPT = (
    "Synthesize title, transcript, and comments into final PR output. Return strict JSON with keys: "
    "title_sentiment, final_sentiment, is_pr_risk, severity, issue_type, target_entity, key_claims, "
    "top_negative_themes, comment_sentiment_summary, transcript_summary, recommended_action, "
    "analysis_version, processing_status."
)

PROMPTS_BY_STAGE = {
    "title_triage": TITLE_TRIAGE_PROMPT,
    "transcript_analysis": TRANSCRIPT_ANALYSIS_PROMPT,
    "comment_analysis": COMMENT_ANALYSIS_PROMPT,
    "transcript_sentiment_triage": TRANSCRIPT_SENTIMENT_TRIAGE_PROMPT,
    "comment_sentiment_batch_triage": COMMENT_SENTIMENT_BATCH_PROMPT,
    "final_synthesis": FINAL_SYNTHESIS_PROMPT,
}


class AzureYouTubeAnalyzer:
    def __init__(self):
        self.api_key = AZURE_OPENAI_API_KEY
        self.endpoint = AZURE_OPENAI_ENDPOINT.rstrip("/") if AZURE_OPENAI_ENDPOINT else ""
        self.api_version = AZURE_OPENAI_API_VERSION
        self.batch_enabled = AZURE_OPENAI_BATCH_ENABLED
        self.input_dir = Path(AZURE_OPENAI_BATCH_INPUT_DIR)
        self.output_dir = Path(AZURE_OPENAI_BATCH_OUTPUT_DIR)
        self.batch_poll_interval_seconds = max(2, AZURE_OPENAI_BATCH_POLL_INTERVAL_SECONDS)
        self.batch_poll_timeout_seconds = max(30, AZURE_OPENAI_BATCH_POLL_TIMEOUT_SECONDS)
        self.deployment = (
            AZURE_OPENAI_DEPLOYMENT_GPT54
            or AZURE_OPENAI_DEPLOYMENT_GPT53
            or AZURE_OPENAI_DEPLOYMENT_GPT52
        )
        self._client = None
        # Fallback: use regular OpenAI when Azure is not configured
        self._use_openai_fallback = False
        if not (self.api_key and self.endpoint and self.deployment):
            import os
            _openai_key = os.environ.get("OPENAI_API_KEY", "")
            if _openai_key:
                self._use_openai_fallback = True
                self._openai_api_key = _openai_key
                self._openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
                self.deployment = self._openai_model
                logger.info("AzureYouTubeAnalyzer: Azure not configured, falling back to OpenAI %s", self._openai_model)

    @property
    def is_configured(self) -> bool:
        return bool(
            (self.api_key and self.endpoint and self.deployment)
            or self._use_openai_fallback
        )

    def custom_id(self, stage: str, brand_id: str, video_id: str) -> str:
        return f"{stage}:{_sha12(f'{brand_id}:{video_id}:{stage}')}:video:{video_id}"

    def _request_payload(self, stage: str, custom_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "custom_id": custom_id,
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.deployment,
                "messages": [
                    {"role": "system", "content": PROMPTS_BY_STAGE[stage]},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
        }

    def _write_batch_jsonl(
        self,
        stage: str,
        brand_id: str,
        payloads_by_custom_id: dict[str, dict[str, Any]],
    ) -> Path | None:
        if not payloads_by_custom_id:
            return None
        self.input_dir.mkdir(parents=True, exist_ok=True)
        signature = _sha12("|".join(sorted(payloads_by_custom_id.keys())))
        path = self.input_dir / f"{stage}_{brand_id}_{signature}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for custom_id in sorted(payloads_by_custom_id.keys()):
                line = self._request_payload(stage, custom_id, payloads_by_custom_id[custom_id])
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")
        return path

    def _output_candidates(self, input_path: Path) -> list[Path]:
        return [
            self.output_dir / input_path.name,
            self.output_dir / f"{input_path.stem}.results.jsonl",
        ]

    @staticmethod
    def _safe_json_loads(value: str | None) -> dict[str, Any]:
        if not value:
            return {}
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _to_iso_from_epoch(value: Any) -> str | None:
        if value in (None, ""):
            return None
        try:
            return _to_iso(datetime.fromtimestamp(float(value), tz=timezone.utc))
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _safe_model_dump(obj: Any) -> dict[str, Any]:
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            dumped = obj.model_dump()
            return dumped if isinstance(dumped, dict) else {}
        return {}

    @staticmethod
    def _extract_correlation_id(obj: Any) -> str | None:
        request_id = getattr(obj, "_request_id", None)
        if request_id:
            return str(request_id)
        as_dict = AzureYouTubeAnalyzer._safe_model_dump(obj)
        value = as_dict.get("request_id") or as_dict.get("correlation_id")
        return str(value) if value else None

    def parse_batch_output_records(
        self,
        output_path: Path,
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        parsed: dict[str, dict[str, Any]] = {}
        parsed_meta: dict[str, dict[str, Any]] = {}
        with output_path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                custom_id = str(row.get("custom_id") or "").strip()
                if not custom_id:
                    continue
                response = row.get("response") or {}
                body = response.get("body") or {}
                content = (body.get("choices", [{}])[0].get("message", {}) or {}).get("content")
                parsed[custom_id] = self._safe_json_loads(content)
                parsed_meta[custom_id] = {
                    "correlation_id": (
                        response.get("request_id")
                        or row.get("request_id")
                        or row.get("correlation_id")
                    ),
                    "status_code": response.get("status_code"),
                    "provider_response_id": body.get("id"),
                    "error": body.get("error"),
                }
        return parsed, parsed_meta

    def parse_batch_results(self, output_path: Path) -> dict[str, dict[str, Any]]:
        parsed, _ = self.parse_batch_output_records(output_path)
        return parsed

    def parse_batch_error_records(self, error_path: Path) -> dict[str, dict[str, Any]]:
        errors: dict[str, dict[str, Any]] = {}
        with error_path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                custom_id = str(row.get("custom_id") or "").strip()
                if not custom_id:
                    continue
                payload = row.get("error")
                if isinstance(payload, dict):
                    errors[custom_id] = payload
                else:
                    errors[custom_id] = {"message": str(payload or "unknown_error")}
        return errors

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if self._use_openai_fallback:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._openai_api_key)
        else:
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.endpoint,
            )
        return self._client

    def direct_call_with_meta(
        self,
        stage: str,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.is_configured:
            return {}, {"mode": "direct", "status": "not_configured"}
        try:
            client = self._ensure_client()
            response = client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": PROMPTS_BY_STAGE[stage]},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            choice = response.choices[0] if response.choices else None
            content = choice.message.content if choice and choice.message else ""
            return self._safe_json_loads(content), {
                "mode": "direct",
                "status": "completed",
                "correlation_id": self._extract_correlation_id(response),
                "provider_response_id": getattr(response, "id", None),
            }
        except Exception as exc:
            logger.exception("Azure direct call failed for stage=%s", stage)
            return {}, {
                "mode": "direct",
                "status": "failed",
                "error": {"message": str(exc)},
            }

    def direct_call(self, stage: str, payload: dict[str, Any]) -> dict[str, Any]:
        result, _ = self.direct_call_with_meta(stage, payload)
        return result

    def submit_batch_stage(
        self,
        stage: str,
        brand_id: str,
        payloads_by_custom_id: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        input_path = self._write_batch_jsonl(stage, brand_id, payloads_by_custom_id)
        metadata: dict[str, Any] = {
            "stage": stage,
            "mode": "batch" if self.batch_enabled else "direct",
            "status": "pending_submission",
            "provider_batch_id": None,
            "input_file_id": None,
            "output_file_id": None,
            "error_file_id": None,
            "batch_input_path": str(input_path) if input_path else None,
            "batch_output_path": None,
            "batch_error_path": None,
            "submitted_at": _to_iso(_now_utc()),
            "polled_at": None,
            "completed_at": None,
            "ingested_at": None,
            "correlation_id": None,
            "error": None,
            "results_meta_by_custom_id": {},
        }
        if not payloads_by_custom_id:
            metadata["status"] = "noop"
            return {}, metadata

        if self.batch_enabled and self.is_configured and input_path:
            try:
                client = self._ensure_client()
                with input_path.open("rb") as fh:
                    input_file = client.files.create(file=fh, purpose="batch")
                batch = client.batches.create(
                    input_file_id=input_file.id,
                    endpoint="/v1/chat/completions",
                    completion_window="24h",
                    metadata={
                        "stage": stage,
                        "brand_id": str(brand_id),
                        "deployment": self.deployment,
                    },
                )
                batch_data = self._safe_model_dump(batch)
                metadata.update(
                    {
                        "status": str(batch_data.get("status") or "submitted").strip().lower(),
                        "provider_batch_id": batch_data.get("id"),
                        "input_file_id": batch_data.get("input_file_id") or input_file.id,
                        "output_file_id": batch_data.get("output_file_id"),
                        "error_file_id": batch_data.get("error_file_id"),
                        "correlation_id": self._extract_correlation_id(batch),
                        "submitted_at": self._to_iso_from_epoch(batch_data.get("created_at"))
                        or metadata.get("submitted_at"),
                        "completed_at": (
                            self._to_iso_from_epoch(batch_data.get("completed_at"))
                            or self._to_iso_from_epoch(batch_data.get("failed_at"))
                            or self._to_iso_from_epoch(batch_data.get("cancelled_at"))
                        ),
                        "error": batch_data.get("errors"),
                    }
                )
                return {}, metadata
            except Exception as exc:
                logger.exception("Azure batch submit failed for stage=%s", stage)
                metadata.update(
                    {
                        "mode": "direct_fallback",
                        "status": "fallback_direct",
                        "error": {"message": str(exc)},
                    }
                )

        direct_results: dict[str, dict[str, Any]] = {}
        direct_meta_by_custom_id: dict[str, dict[str, Any]] = {}
        for custom_id, payload in payloads_by_custom_id.items():
            parsed, parsed_meta = self.direct_call_with_meta(stage, payload)
            direct_results[custom_id] = parsed
            direct_meta_by_custom_id[custom_id] = parsed_meta

        if metadata["status"] not in {"fallback_direct"}:
            metadata["status"] = "completed"
        metadata["mode"] = metadata.get("mode") or "direct"
        metadata["results_meta_by_custom_id"] = direct_meta_by_custom_id
        if not metadata.get("correlation_id"):
            for item in direct_meta_by_custom_id.values():
                if item.get("correlation_id"):
                    metadata["correlation_id"] = item.get("correlation_id")
                    break
        return direct_results, metadata

    def poll_batch_stage(self, batch_id: str) -> dict[str, Any]:
        if not batch_id:
            return {"status": "missing_batch_id"}
        if not self.is_configured:
            return {
                "status": "not_configured",
                "provider_batch_id": batch_id,
            }
        try:
            client = self._ensure_client()
            batch = client.batches.retrieve(batch_id)
            batch_data = self._safe_model_dump(batch)
            status = str(batch_data.get("status") or "unknown").strip().lower()
            return {
                "provider_batch_id": batch_data.get("id") or batch_id,
                "status": status,
                "input_file_id": batch_data.get("input_file_id"),
                "output_file_id": batch_data.get("output_file_id"),
                "error_file_id": batch_data.get("error_file_id"),
                "submitted_at": self._to_iso_from_epoch(batch_data.get("created_at")),
                "polled_at": _to_iso(_now_utc()),
                "completed_at": (
                    self._to_iso_from_epoch(batch_data.get("completed_at"))
                    or self._to_iso_from_epoch(batch_data.get("failed_at"))
                    or self._to_iso_from_epoch(batch_data.get("cancelled_at"))
                    or self._to_iso_from_epoch(batch_data.get("expired_at"))
                ),
                "correlation_id": self._extract_correlation_id(batch),
                "error": batch_data.get("errors"),
            }
        except Exception as exc:
            logger.exception("Azure batch poll failed for batch_id=%s", batch_id)
            return {
                "provider_batch_id": batch_id,
                "status": "poll_failed",
                "polled_at": _to_iso(_now_utc()),
                "error": {"message": str(exc)},
            }

    def _download_batch_file(self, file_id: str, suffix: str) -> Path | None:
        if not file_id or not self.is_configured:
            return None
        try:
            client = self._ensure_client()
            response = client.files.content(file_id)
            text_value = getattr(response, "text", None)
            if callable(text_value):
                content_text = text_value()
            elif isinstance(text_value, str):
                content_text = text_value
            else:
                content = getattr(response, "content", None)
                if callable(content):
                    content = content()
                if isinstance(content, bytes):
                    content_text = content.decode("utf-8", errors="replace")
                else:
                    content_text = str(content or "")

            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / f"{file_id}.{suffix}.jsonl"
            output_path.write_text(content_text, encoding="utf-8")
            return output_path
        except Exception:
            logger.exception("Failed to download Azure batch file_id=%s", file_id)
            return None

    def fetch_batch_outputs(self, batch_meta: dict[str, Any]) -> dict[str, Any]:
        output_file_id = str(batch_meta.get("output_file_id") or "").strip()
        error_file_id = str(batch_meta.get("error_file_id") or "").strip()
        output_path = self._download_batch_file(output_file_id, "output") if output_file_id else None
        error_path = self._download_batch_file(error_file_id, "error") if error_file_id else None

        results_by_custom_id: dict[str, dict[str, Any]] = {}
        result_meta_by_custom_id: dict[str, dict[str, Any]] = {}
        errors_by_custom_id: dict[str, dict[str, Any]] = {}
        if output_path and output_path.exists():
            results_by_custom_id, result_meta_by_custom_id = self.parse_batch_output_records(output_path)
        if error_path and error_path.exists():
            errors_by_custom_id = self.parse_batch_error_records(error_path)
        return {
            "results_by_custom_id": results_by_custom_id,
            "result_meta_by_custom_id": result_meta_by_custom_id,
            "errors_by_custom_id": errors_by_custom_id,
            "batch_output_path": str(output_path) if output_path else None,
            "batch_error_path": str(error_path) if error_path else None,
        }

    def run_stage(
        self,
        stage: str,
        brand_id: str,
        payloads_by_custom_id: dict[str, dict[str, Any]],
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        input_path = self._write_batch_jsonl(stage, brand_id, payloads_by_custom_id)
        metadata = {
            "stage": stage,
            "batch_input_path": str(input_path) if input_path else None,
            "batch_output_path": None,
            "batch_error_path": None,
            "mode": "batch" if self.batch_enabled else "direct",
            "status": "pending",
            "correlation_id": None,
        }
        results: dict[str, dict[str, Any]] = {}

        if input_path and self.batch_enabled and self.is_configured:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            for candidate in self._output_candidates(input_path):
                if candidate.exists():
                    results = self.parse_batch_results(candidate)
                    metadata["batch_output_path"] = str(candidate)
                    metadata["status"] = "completed"
                    break

        if not results:
            for custom_id, payload in payloads_by_custom_id.items():
                parsed, parsed_meta = self.direct_call_with_meta(stage, payload)
                results[custom_id] = parsed
                if parsed_meta.get("correlation_id") and not metadata.get("correlation_id"):
                    metadata["correlation_id"] = parsed_meta.get("correlation_id")
            metadata["mode"] = "direct"
            metadata["status"] = "completed"

        return results, metadata


def normalize_title_triage(triage: dict[str, Any], fallback_reason: str = "") -> dict[str, Any]:
    label = str(triage.get("label") or "uncertain").strip().lower()
    if label not in ALLOWED_TRIAGE_LABELS:
        label = "uncertain"
    try:
        confidence = float(triage.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    return {
        "label": label,
        "is_pr_risk": bool(triage.get("is_pr_risk", label != "positive")),
        "confidence": confidence,
        "issue_type": str(triage.get("issue_type") or "general").strip() or "general",
        "reason": str(triage.get("reason") or fallback_reason or "triage unavailable").strip(),
    }


def normalize_final_analysis(analysis: dict[str, Any], title_triage: dict[str, Any]) -> dict[str, Any]:
    sentiment = str(analysis.get("final_sentiment") or title_triage.get("label") or "uncertain").strip().lower()
    if sentiment not in ALLOWED_FINAL_SENTIMENTS:
        sentiment = "uncertain"

    severity = str(analysis.get("severity") or "medium").strip().lower()
    if severity not in {"low", "medium", "high", "critical"}:
        severity = "medium"

    return {
        "title_sentiment": str(analysis.get("title_sentiment") or title_triage.get("label") or "uncertain"),
        "final_sentiment": sentiment,
        "is_pr_risk": bool(analysis.get("is_pr_risk", title_triage.get("is_pr_risk", True))),
        "severity": severity,
        "issue_type": str(analysis.get("issue_type") or title_triage.get("issue_type") or "general"),
        "target_entity": str(analysis.get("target_entity") or "physics wallah"),
        "key_claims": analysis.get("key_claims") if isinstance(analysis.get("key_claims"), list) else [],
        "top_negative_themes": (
            analysis.get("top_negative_themes")
            if isinstance(analysis.get("top_negative_themes"), list)
            else []
        ),
        "comment_sentiment_summary": str(analysis.get("comment_sentiment_summary") or ""),
        "transcript_summary": str(analysis.get("transcript_summary") or ""),
        "recommended_action": str(analysis.get("recommended_action") or "monitor"),
        "analysis_version": str(analysis.get("analysis_version") or YOUTUBE_ANALYSIS_VERSION),
        "processing_status": str(analysis.get("processing_status") or "complete"),
    }


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        out = []
        for item in value:
            text = str(item or "").strip()
            if text:
                out.append(text)
        return out
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    return []


def normalize_transcript_sentiment_triage(
    payload: dict[str, Any],
    fallback_reason: str = "",
) -> dict[str, Any]:
    pr_sentiment = str(payload.get("pr_sentiment") or payload.get("sentiment") or "uncertain").strip().lower()
    if pr_sentiment not in ALLOWED_TRANSCRIPT_PR_SENTIMENTS:
        pr_sentiment = "uncertain"

    is_pr_risk = bool(payload.get("is_pr_risk", pr_sentiment == "negative"))

    severity = str(payload.get("severity") or "low").strip().lower()
    if severity not in ALLOWED_TRANSCRIPT_PR_SEVERITY:
        severity = "low"

    issue_type = str(payload.get("issue_type") or "other").strip().lower()
    if issue_type not in ALLOWED_TRANSCRIPT_PR_ISSUE_TYPES:
        issue_type = "other"

    target_entity = str(payload.get("target_entity") or "none").strip().lower()
    if target_entity not in ALLOWED_TRANSCRIPT_PR_TARGETS:
        target_entity = "none"

    key_claims = _normalize_string_list(payload.get("key_claims"))
    brand_harm_evidence = _normalize_string_list(payload.get("brand_harm_evidence"))
    protective_context = _normalize_string_list(payload.get("protective_context"))

    recommended_action = str(payload.get("recommended_action") or "monitor").strip().lower()
    if recommended_action not in ALLOWED_TRANSCRIPT_PR_ACTIONS:
        recommended_action = "monitor"

    reason = str(payload.get("reason") or fallback_reason or "transcript pr analysis unavailable").strip()
    transcript_summary = str(payload.get("transcript_summary") or "").strip()

    # Heuristic requested: when risk is false and there is no explicit brand harm evidence,
    # force overall label away from negative.
    if not is_pr_risk and pr_sentiment == "negative" and not brand_harm_evidence:
        pr_sentiment = "neutral"

    return {
        "pr_sentiment": pr_sentiment,
        "is_pr_risk": is_pr_risk,
        "severity": severity,
        "issue_type": issue_type,
        "target_entity": target_entity,
        "transcript_summary": transcript_summary,
        "key_claims": key_claims,
        "brand_harm_evidence": brand_harm_evidence,
        "protective_context": protective_context,
        "recommended_action": recommended_action,
        "reason": reason,
    }


def parse_comment_sentiment_results(
    payload: Any,
    expected_comment_ids: list[str],
) -> dict[str, str]:
    expected_set = {
        str(comment_id).strip()
        for comment_id in (expected_comment_ids or [])
        if str(comment_id).strip()
    }
    extracted: list[Any]
    if isinstance(payload, list):
        extracted = payload
    elif isinstance(payload, dict):
        extracted = (
            payload.get("results")
            or payload.get("comments")
            or payload.get("items")
            or []
        )
        if not isinstance(extracted, list):
            extracted = [payload]
    else:
        extracted = []

    mapped: dict[str, str] = {}
    for row in extracted:
        if not isinstance(row, dict):
            continue
        comment_id = str(
            row.get("Comment ID")
            or row.get("comment_id")
            or row.get("commentId")
            or row.get("id")
            or ""
        ).strip()
        if not comment_id or (expected_set and comment_id not in expected_set):
            continue
        sentiment = str(
            row.get("Sentiment")
            or row.get("sentiment")
            or row.get("label")
            or ""
        ).strip().lower()
        if sentiment not in ALLOWED_SIMPLE_SENTIMENTS:
            sentiment = "neutral"
        mapped[comment_id] = sentiment

    for comment_id in expected_set:
        mapped.setdefault(comment_id, "neutral")
    return mapped


async def discover_unofficial_video_candidates(
    client: YouTubeDataAPIClient,
    query_buckets: dict[str, list[str]],
    max_results_per_keyword: int,
    published_after_days: int,
    query_chunk_size: int = DEFAULT_QUERY_CHUNK_SIZE,
) -> list[dict[str, Any]]:
    published_after = _now_utc() - timedelta(days=max(1, published_after_days))
    bucketed_chunks = build_query_buckets(query_buckets, bucket_size=query_chunk_size)
    discovery_stats: dict[str, Any] = {
        "query_terms_total": sum(len(v or []) for v in query_buckets.values()),
        "query_chunks_total": sum(len(v or []) for v in bucketed_chunks.values()),
        "query_errors": 0,
        "discovered_video_ids": 0,
        "excluded_missing_video_details": 0,
        "excluded_blacklisted": 0,
        "unofficial_candidates": 0,
    }

    search_hits_by_video: dict[str, dict[str, Any]] = {}
    for bucket_name in ("primary", "secondary", "expanded"):
        for chunk in bucketed_chunks.get(bucket_name, []):
            tasks = [
                client.search_videos(
                    query=term,
                    published_after=published_after,
                    max_results=max_results_per_keyword,
                )
                for term in chunk
            ]
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            for term, rows in zip(chunk, chunk_results):
                if isinstance(rows, Exception):
                    logger.exception("YouTube search failed for term=%s", term)
                    discovery_stats["query_errors"] += 1
                    continue
                for row in rows:
                    video_id = row.get("video_id")
                    if not video_id:
                        continue
                    existing = search_hits_by_video.setdefault(
                        video_id,
                        {
                            "video_id": video_id,
                            "channel_id": row.get("channel_id"),
                            "search_hits": [],
                        },
                    )
                    if not existing.get("channel_id") and row.get("channel_id"):
                        existing["channel_id"] = row.get("channel_id")
                    existing["search_hits"].append({"query": term, "bucket": bucket_name})

    if not search_hits_by_video:
        setattr(discover_unofficial_video_candidates, "last_stats", discovery_stats)
        return []

    video_ids = sorted(search_hits_by_video.keys())
    discovery_stats["discovered_video_ids"] = len(video_ids)
    videos_by_id = await client.videos_by_id(video_ids)

    channel_ids = sorted(
        {
            (videos_by_id.get(video_id, {}).get("snippet") or {}).get("channelId")
            or search_hits_by_video[video_id].get("channel_id")
            for video_id in video_ids
            if (
                (videos_by_id.get(video_id, {}).get("snippet") or {}).get("channelId")
                or search_hits_by_video[video_id].get("channel_id")
            )
        }
    )
    channels_by_id = await client.channels_by_id(channel_ids)

    unofficial_candidates: list[dict[str, Any]] = []
    for video_id in video_ids:
        video = videos_by_id.get(video_id)
        if not video:
            discovery_stats["excluded_missing_video_details"] += 1
            continue

        channel_id = (video.get("snippet") or {}).get("channelId") or search_hits_by_video[video_id].get("channel_id")
        channel = channels_by_id.get(channel_id or "", {})
        channel_handle = ((channel.get("snippet") or {}).get("customUrl"))
        if is_blacklisted_channel(channel_id, channel_handle):
            discovery_stats["excluded_blacklisted"] += 1
            continue

        unofficial_candidates.append(
            {
                "video_id": video_id,
                "channel_id": channel_id,
                "video": video,
                "channel": channel,
                "search_hits": search_hits_by_video[video_id].get("search_hits", []),
                "source_url": _build_video_url(video_id),
            }
        )

    discovery_stats["unofficial_candidates"] = len(unofficial_candidates)
    setattr(discover_unofficial_video_candidates, "last_stats", discovery_stats)
    return unofficial_candidates


def _deep_merge_dicts(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in (patch or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _pending_triage_payload() -> dict[str, Any]:
    return {
        "label": "uncertain",
        "is_pr_risk": False,
        "confidence": 0.0,
        "issue_type": "pending",
        "reason": "pending_batch_result",
    }


def _candidate_from_video_row(video_row: dict[str, Any]) -> dict[str, Any]:
    raw_data = video_row.get("raw_data") if isinstance(video_row.get("raw_data"), dict) else {}
    video = raw_data.get("video") if isinstance(raw_data.get("video"), dict) else {}
    channel = raw_data.get("channel") if isinstance(raw_data.get("channel"), dict) else {}
    search_hits = raw_data.get("search_hits") if isinstance(raw_data.get("search_hits"), list) else []
    video_id = str(video_row.get("video_id") or "")
    if not video:
        video = {
            "id": video_id,
            "snippet": {
                "title": str(video_row.get("video_title") or ""),
                "description": str(video_row.get("video_description") or ""),
                "publishedAt": str(video_row.get("video_date") or ""),
                "channelTitle": str(video_row.get("channel_name") or ""),
            },
            "statistics": {
                "viewCount": str(video_row.get("video_views") or 0),
                "likeCount": str(video_row.get("video_likes") or 0),
                "commentCount": str(video_row.get("video_comment_count") or 0),
            },
            "contentDetails": {"duration": ""},
        }
    return {
        "video_id": video_id,
        "channel_id": str(video_row.get("channel_id") or ""),
        "video": video,
        "channel": channel,
        "search_hits": search_hits,
        "source_url": video_row.get("source_url") or _build_video_url(video_id),
    }


def _title_triage_artifact(
    custom_id: str,
    triage_meta: dict[str, Any],
    status: str | None = None,
    correlation_id: str | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "stage": "title_triage",
        "custom_id": custom_id,
        "mode": triage_meta.get("mode"),
        "status": status or triage_meta.get("status"),
        "provider_batch_id": triage_meta.get("provider_batch_id"),
        "input_file_id": triage_meta.get("input_file_id"),
        "output_file_id": triage_meta.get("output_file_id"),
        "error_file_id": triage_meta.get("error_file_id"),
        "batch_input_path": triage_meta.get("batch_input_path"),
        "batch_output_path": triage_meta.get("batch_output_path"),
        "batch_error_path": triage_meta.get("batch_error_path"),
        "correlation_id": correlation_id or triage_meta.get("correlation_id"),
        "submitted_at": triage_meta.get("submitted_at"),
        "polled_at": triage_meta.get("polled_at"),
        "completed_at": triage_meta.get("completed_at"),
        "ingested_at": triage_meta.get("ingested_at"),
        "error": error if error is not None else triage_meta.get("error"),
    }
    return {
        key: value
        for key, value in artifact.items()
        if value is not None or key in {"stage", "custom_id", "mode", "status"}
    }


def _merge_title_triage_artifacts(video_id: str, artifact: dict[str, Any]) -> None:
    _merge_video_analysis_artifacts(video_id, {"title_triage": artifact})


def _merge_video_analysis_artifacts(video_id: str, patch: dict[str, Any]) -> None:
    merge_fn = getattr(db, "merge_youtube_video_analysis_artifacts", None)
    if callable(merge_fn):
        merge_fn(video_id, patch)
        return

    existing_video = db.get_youtube_video_by_video_id(video_id) or {}
    existing_artifacts = (
        existing_video.get("analysis_artifacts")
        if isinstance(existing_video.get("analysis_artifacts"), dict)
        else {}
    )
    merged = _deep_merge_dicts(existing_artifacts, patch)
    db.update_youtube_video_by_video_id(video_id, {"analysis_artifacts": merged})


def _merge_layer_status(
    video_id: str,
    layer_name: str,
    status: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    layer_payload = {
        "status": status,
        "updated_at": _to_iso(_now_utc()),
        **(metadata or {}),
    }
    _merge_video_analysis_artifacts(
        video_id,
        {
            "layers": {
                layer_name: layer_payload,
            }
        },
    )


def _resolve_query_buckets(
    brand: dict[str, Any],
    include_secondary: bool = True,
    query_buckets_override: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    brand_keywords = brand.get("keywords", []) or []
    if query_buckets_override:
        return {
            bucket_name: dedupe_query_terms(bucket_terms or [])
            for bucket_name, bucket_terms in query_buckets_override.items()
            if bucket_terms
        }
    return build_discovery_query_buckets(
        extra_terms=brand_keywords,
        include_secondary=include_secondary,
    )


def _triage_payload_for_candidate(brand: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    snippet = (candidate.get("video") or {}).get("snippet", {})
    title = str(snippet.get("title") or candidate.get("video_title") or "").strip()
    description = str(snippet.get("description") or candidate.get("video_description") or "").strip()
    return {
        "brand": brand.get("name", ""),
        "video_id": candidate.get("video_id"),
        "title": title,
        "description": description,
        "channel_title": snippet.get("channelTitle", ""),
        "search_hits": candidate.get("search_hits", []),
    }


def _upsert_pending_normalized_rows(
    brand: dict[str, Any],
    candidate: dict[str, Any],
    query_buckets: dict[str, list[str]],
    triage_artifact: dict[str, Any],
) -> dict[str, Any]:
    brand_id = str(brand.get("id"))
    triage = _pending_triage_payload()
    try:
        mention_existing = db.get_mention_by_platform_ref(brand_id, "youtube", candidate.get("video_id", ""))
    except Exception:
        mention_existing = None

    mention_payload = map_video_to_mention(
        brand_id=brand_id,
        candidate=candidate,
        triage=triage,
    )
    mention = db.upsert_mention_by_platform_ref(mention_payload)
    mention_id = mention.get("id")
    if not mention_id:
        return {
            "mention": mention,
            "mention_created": 0,
            "mention_updated": 0,
            "fulfillment_created": 0,
            "fulfillment_updated": 0,
        }

    try:
        fulfillment_existing = db.get_latest_fulfillment_result_for_mention(mention_id)
    except Exception:
        fulfillment_existing = None

    db.upsert_fulfillment_result_for_mention(
        {
            "search_query": {
                "pipeline": "youtube_unofficial_mvp",
                "query_buckets": query_buckets,
                "title_triage_batch": triage_artifact,
            },
            "mention_id": mention_id,
            "passed": False,
            "score": 0.0,
            "criteria_met": ["title_triage_pending"],
            "queued_for_scraping": False,
            "queued_for_transcription": False,
            "evaluated_at": _to_iso(_now_utc()),
        }
    )

    return {
        "mention": mention,
        "mention_created": 0 if mention_existing else 1,
        "mention_updated": 1 if mention_existing else 0,
        "fulfillment_created": 0 if fulfillment_existing else 1,
        "fulfillment_updated": 1 if fulfillment_existing else 0,
    }


def _apply_triage_result_to_rows(
    brand: dict[str, Any],
    candidate: dict[str, Any],
    triage: dict[str, Any],
    custom_id: str,
    triage_meta: dict[str, Any],
    query_buckets: dict[str, list[str]],
    queue_followups: bool = True,
) -> dict[str, Any]:
    brand_id = str(brand.get("id"))
    video_id = candidate.get("video_id", "")
    artifact = _title_triage_artifact(
        custom_id=custom_id,
        triage_meta=triage_meta,
        status=triage_meta.get("status"),
        correlation_id=triage_meta.get("correlation_id"),
        error=triage_meta.get("error") if isinstance(triage_meta.get("error"), dict) else None,
    )

    db.update_youtube_video_by_video_id(
        video_id,
        {
            "title_triage_label": triage.get("label"),
            "title_triage_confidence": _safe_float(triage.get("confidence")),
            "title_triage_is_pr_risk": bool(triage.get("is_pr_risk", False)),
            "title_triage_issue_type": triage.get("issue_type"),
            "title_triage_reason": triage.get("reason"),
            "title_triage_custom_id": custom_id,
            "title_triage_mode": triage_meta.get("mode"),
            "title_triage_batch_input": triage_meta.get("batch_input_path"),
            "title_triage_batch_output": triage_meta.get("batch_output_path"),
            "title_triage_processed_at": _to_iso(_now_utc()),
        },
    )
    _merge_title_triage_artifacts(video_id, artifact)

    try:
        mention_existing = db.get_mention_by_platform_ref(brand_id, "youtube", video_id)
    except Exception:
        mention_existing = None

    mention_payload = map_video_to_mention(
        brand_id=brand_id,
        candidate=candidate,
        triage=triage,
    )
    mention = db.upsert_mention_by_platform_ref(mention_payload)
    mention_id = mention.get("id")
    if not mention_id:
        return {
            "video_id": video_id,
            "mention": mention,
            "flagged": False,
            "mention_created": 0,
            "mention_updated": 0,
            "fulfillment_created": 0,
            "fulfillment_updated": 0,
            "triage_applied": 1,
        }

    fulfillment = build_youtube_fulfillment_from_triage(
        triage_label=triage.get("label", "uncertain"),
        confidence=float(triage.get("confidence") or 0.0),
        is_pr_risk=bool(triage.get("is_pr_risk", False)),
    )
    if not queue_followups:
        fulfillment = {
            **fulfillment,
            "queued_for_scraping": False,
            "queued_for_transcription": False,
            "criteria_met": list(dict.fromkeys(list(fulfillment.get("criteria_met", [])) + ["sync_triage_only"])),
        }

    try:
        fulfillment_existing = db.get_latest_fulfillment_result_for_mention(mention_id)
    except Exception:
        fulfillment_existing = None

    db.upsert_fulfillment_result_for_mention(
        {
            "search_query": {
                "pipeline": "youtube_unofficial_mvp",
                "query_buckets": query_buckets,
                "title_triage_batch": artifact,
            },
            "mention_id": mention_id,
            "passed": fulfillment["passed"],
            "score": fulfillment["score"],
            "criteria_met": fulfillment["criteria_met"],
            "queued_for_scraping": fulfillment["queued_for_scraping"],
            "queued_for_transcription": fulfillment["queued_for_transcription"],
            "evaluated_at": _to_iso(_now_utc()),
        }
    )

    flagged = bool(queue_followups and (fulfillment["queued_for_scraping"] or fulfillment["queued_for_transcription"]))
    _merge_layer_status(
        video_id,
        "layer_1",
        "completed",
        metadata={
            "triage_mode": triage_meta.get("mode"),
            "triage_label": triage.get("label"),
        },
    )
    _merge_layer_status(
        video_id,
        "layer_2",
        "queued" if flagged else "not_required",
        metadata={
            "queued_for_scraping": bool(fulfillment["queued_for_scraping"]),
            "queued_for_transcription": bool(fulfillment["queued_for_transcription"]),
        },
    )
    return {
        "video_id": video_id,
        "mention": mention,
        "flagged": flagged,
        "mention_created": 0 if mention_existing else 1,
        "mention_updated": 1 if mention_existing else 0,
        "fulfillment_created": 0 if fulfillment_existing else 1,
        "fulfillment_updated": 1 if fulfillment_existing else 0,
        "triage_applied": 1,
    }


async def run_youtube_title_triage_sync_ingestion_for_brand(
    brand: dict[str, Any],
    include_secondary: bool = True,
    query_buckets_override: dict[str, list[str]] | None = None,
    max_results_per_keyword_override: int | None = None,
    published_after_days_override: int | None = None,
    triage_batch_size: int = 10,
    queue_followups_from_triage: bool = True,
) -> dict[str, Any]:
    brand_id = brand.get("id")
    if not brand_id:
        return {
            "brand_id": None,
            "status": "skipped",
            "reason": "missing_brand_id",
            "discovered": 0,
        }
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY missing; skipping sync title-triage ingestion")
        return {
            "brand_id": brand_id,
            "status": "skipped",
            "reason": "missing_youtube_api_key",
            "discovered": 0,
        }

    query_buckets = _resolve_query_buckets(
        brand=brand,
        include_secondary=include_secondary,
        query_buckets_override=query_buckets_override,
    )
    max_results_per_keyword = (
        max(1, int(max_results_per_keyword_override))
        if max_results_per_keyword_override is not None
        else YOUTUBE_UNOFFICIAL_MAX_RESULTS_PER_KEYWORD
    )
    published_after_days = (
        max(1, int(published_after_days_override))
        if published_after_days_override is not None
        else YOUTUBE_UNOFFICIAL_PUBLISHED_AFTER_DAYS
    )

    client = YouTubeDataAPIClient(YOUTUBE_API_KEY)
    candidates = await discover_unofficial_video_candidates(
        client=client,
        query_buckets=query_buckets,
        max_results_per_keyword=max_results_per_keyword,
        published_after_days=published_after_days,
        query_chunk_size=DEFAULT_QUERY_CHUNK_SIZE,
    )
    discovery_stats = getattr(discover_unofficial_video_candidates, "last_stats", {})
    if not isinstance(discovery_stats, dict):
        discovery_stats = {}

    analyzer = AzureYouTubeAnalyzer()
    batch_size = max(1, int(triage_batch_size or 10))

    raw_channels_created = 0
    raw_channels_updated = 0
    raw_videos_created = 0
    raw_videos_updated = 0
    mentions_created = 0
    mentions_updated = 0
    fulfillment_created = 0
    fulfillment_updated = 0
    triage_results_applied = 0
    titles_triaged = 0
    triage_chunks_processed = 0
    failed_triage_count = 0
    queued_for_scraping_count = 0
    queued_for_transcription_count = 0
    flagged_video_ids: list[str] = []
    skipped_reasons: list[str] = []

    for start in range(0, len(candidates), batch_size):
        chunk = candidates[start : start + batch_size]
        if not chunk:
            continue
        triage_chunks_processed += 1
        submitted_at = _to_iso(_now_utc())

        chunk_results: dict[str, dict[str, Any]] = {}
        chunk_meta_by_custom_id: dict[str, dict[str, Any]] = {}
        custom_id_to_candidate: dict[str, dict[str, Any]] = {}

        for candidate in chunk:
            video_id = candidate.get("video_id", "")
            custom_id = analyzer.custom_id("title_triage", str(brand_id), video_id)
            payload = _triage_payload_for_candidate(brand, candidate)
            parsed, parsed_meta = analyzer.direct_call_with_meta("title_triage", payload)
            chunk_results[custom_id] = parsed
            chunk_meta_by_custom_id[custom_id] = parsed_meta
            custom_id_to_candidate[custom_id] = candidate

        for custom_id, candidate in custom_id_to_candidate.items():
            per_custom_meta = chunk_meta_by_custom_id.get(custom_id, {})
            response_payload = chunk_results.get(custom_id, {})
            error_payload = per_custom_meta.get("error") if isinstance(per_custom_meta.get("error"), dict) else None
            fallback_reason = ""
            if error_payload:
                fallback_reason = str(error_payload.get("message") or "direct_call_failed")
            elif not response_payload:
                fallback_reason = "direct_unavailable"

            triage = normalize_title_triage(response_payload, fallback_reason=fallback_reason)
            if not response_payload:
                failed_triage_count += 1

            triage_meta = {
                "stage": "title_triage",
                "mode": "sync_direct",
                "status": "ingested" if response_payload else "failed",
                "submitted_at": submitted_at,
                "ingested_at": _to_iso(_now_utc()),
                "correlation_id": per_custom_meta.get("correlation_id"),
                "error": error_payload,
            }

            try:
                channel_existing = db.find_youtube_channel(
                    candidate.get("channel_id", ""),
                    brand_id=brand_id,
                )
            except Exception:
                channel_existing = None
            db.upsert_youtube_channel(map_channel_to_raw_channel_row(candidate, brand_id))
            if channel_existing:
                raw_channels_updated += 1
            else:
                raw_channels_created += 1

            video_id = candidate.get("video_id", "")
            try:
                video_existing = db.get_youtube_video_by_video_id(video_id)
            except Exception:
                video_existing = None
            video_row = map_video_to_raw_video_row(
                candidate,
                brand_id,
                title_triage=triage,
                title_custom_id=custom_id,
                title_meta=triage_meta,
            )
            db.upsert_youtube_video(video_row)
            if video_existing:
                raw_videos_updated += 1
            else:
                raw_videos_created += 1

            applied = _apply_triage_result_to_rows(
                brand=brand,
                candidate=candidate,
                triage=triage,
                custom_id=custom_id,
                triage_meta=triage_meta,
                query_buckets=query_buckets,
                queue_followups=queue_followups_from_triage,
            )
            triage_results_applied += _safe_int(applied.get("triage_applied"))
            mentions_created += _safe_int(applied.get("mention_created"))
            mentions_updated += _safe_int(applied.get("mention_updated"))
            fulfillment_created += _safe_int(applied.get("fulfillment_created"))
            fulfillment_updated += _safe_int(applied.get("fulfillment_updated"))
            titles_triaged += 1
            if applied.get("flagged"):
                flagged_video_ids.append(video_id)
                queued_for_scraping_count += 1
                queued_for_transcription_count += 1

            if not applied.get("mention", {}).get("id"):
                skipped_reasons.append(f"missing_mention_id:{video_id}")

    return {
        "brand_id": brand_id,
        "status": "ok",
        "phase": "sync_title_triage_ingestion",
        "workflow": "independent_sync_ingestion_only",
        "discovered": len(candidates),
        "discovered_video_count": _safe_int(discovery_stats.get("discovered_video_ids"), len(candidates)),
        "blacklisted_excluded_count": _safe_int(discovery_stats.get("excluded_blacklisted")),
        "excluded_missing_video_details_count": _safe_int(
            discovery_stats.get("excluded_missing_video_details")
        ),
        "unofficial_candidate_count": len(candidates),
        "titles_triaged": titles_triaged,
        "failed_triage_count": failed_triage_count,
        "triage_batch_size": batch_size,
        "triage_chunks_processed": triage_chunks_processed,
        "raw_channels_created": raw_channels_created,
        "raw_channels_updated": raw_channels_updated,
        "raw_videos_created": raw_videos_created,
        "raw_videos_updated": raw_videos_updated,
        "mentions_created": mentions_created,
        "mentions_updated": mentions_updated,
        "fulfillment_created": fulfillment_created,
        "fulfillment_updated": fulfillment_updated,
        "triage_results_applied": triage_results_applied,
        "flagged": len([v for v in flagged_video_ids if v]),
        "flagged_video_ids": [v for v in flagged_video_ids if v],
        "queued_for_scraping_count": queued_for_scraping_count,
        "queued_for_transcription_count": queued_for_transcription_count,
        "triage_mode": "sync_direct",
        "enrichment_triggered": False,
        "queue_followups_from_triage": bool(queue_followups_from_triage),
        "skipped_reasons": skipped_reasons,
    }


def _collect_layer2_candidates_for_brand(
    brand_id: str,
    scan_limit: int = 2000,
    include_completed: bool = False,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    videos = _get_brand_video_rows(brand_id, limit=scan_limit)
    for row in videos:
        video_id = str(row.get("video_id") or "").strip()
        if not video_id:
            continue
        mention = db.get_mention_by_platform_ref(str(brand_id), "youtube", video_id) or {}
        mention_id = mention.get("id")
        if not mention_id:
            continue
        fulfillment = db.get_latest_fulfillment_result_for_mention(mention_id) or {}
        queued_for_scraping = bool(fulfillment.get("queued_for_scraping"))
        queued_for_transcription = bool(fulfillment.get("queued_for_transcription"))
        if not (queued_for_scraping or queued_for_transcription):
            continue
        artifacts = row.get("analysis_artifacts")
        if not isinstance(artifacts, dict):
            artifacts = {}
        layers = artifacts.get("layers")
        if not isinstance(layers, dict):
            layers = {}
        layer2 = layers.get("layer_2")
        if not isinstance(layer2, dict):
            layer2 = {}
        layer2_status = str(layer2.get("status") or "").strip().lower()
        if layer2_status == "completed" and not include_completed:
            continue

        candidate = _candidate_from_video_row(row)
        candidate["mention"] = mention
        candidate["queued_for_scraping"] = queued_for_scraping
        candidate["queued_for_transcription"] = queued_for_transcription
        candidate["has_transcript_text"] = bool(str(row.get("transcript_text") or "").strip())
        candidate["existing_transcript_source_type"] = str(row.get("transcript_source_type") or "").strip()
        candidates.append(candidate)
    return candidates


def run_youtube_layer2_fetch_sync_for_brand(
    brand: dict[str, Any],
    page_size: int = 50,
    page_offset: int = 0,
    scan_limit: int = 2000,
    comments_max_per_video_override: int | None = None,
    include_completed: bool = False,
    use_fallback_transcript: bool = True,
) -> dict[str, Any]:
    """
    Layer-2 cron-style sync pipeline:
    - reads queued rows from Supabase
    - fetches transcript via Apify batch (primary path)
    - fetches YouTube comments including replies (sync)
    - writes transcript/comments and layer-2 status metadata back to Supabase
    """
    brand_id = brand.get("id")
    if not brand_id:
        return {"brand_id": None, "status": "skipped", "reason": "missing_brand_id"}

    all_candidates = _collect_layer2_candidates_for_brand(
        str(brand_id),
        scan_limit=scan_limit,
        include_completed=include_completed,
    )
    start = max(0, int(page_offset or 0))
    size = max(1, int(page_size or 50))
    paged_candidates = all_candidates[start : start + size]

    video_ids = [str(c.get("video_id") or "") for c in paged_candidates if c.get("video_id")]
    transcript_request_candidates = [
        c
        for c in paged_candidates
        if c.get("queued_for_transcription") and not bool(c.get("has_transcript_text"))
    ]
    transcript_urls = [
        c.get("source_url") or _build_video_url(c.get("video_id", ""))
        for c in transcript_request_candidates
    ]
    transcript_by_video_id, transcript_batch_meta = get_apify_transcripts_batch(transcript_urls)
    transcript_batch_meta = dict(transcript_batch_meta or {})
    transcript_batch_meta["skipped_existing"] = len(
        [
            c
            for c in paged_candidates
            if c.get("queued_for_transcription") and bool(c.get("has_transcript_text"))
        ]
    )
    transcript_batch_meta["requested_after_skip"] = len(transcript_urls)

    comments_max_per_video = (
        max(1, int(comments_max_per_video_override))
        if comments_max_per_video_override is not None
        else YOUTUBE_UNOFFICIAL_MAX_COMMENTS_PER_FLAGGED_VIDEO
    )
    youtube_client = YouTubeDataAPIClient(YOUTUBE_API_KEY) if YOUTUBE_API_KEY else None

    transcript_success = 0
    transcript_failed = 0
    comments_success = 0
    comments_failed = 0
    comments_fetched_total = 0
    comments_inserted_total = 0
    processed_count = 0
    skipped_count = 0
    failures: list[str] = []

    for candidate in paged_candidates:
        video_id = str(candidate.get("video_id") or "").strip()
        mention = candidate.get("mention") or {}
        mention_id = mention.get("id")
        if not video_id or not mention_id:
            skipped_count += 1
            continue

        processed_count += 1
        transcript_status = "not_requested"
        comments_status = "not_requested"
        transcript_meta: dict[str, Any] = {}
        comments_meta: dict[str, Any] = {}

        if candidate.get("queued_for_transcription"):
            if candidate.get("has_transcript_text"):
                transcript_status = "completed"
                transcript_success += 1
                transcript_meta = {
                    "source": candidate.get("existing_transcript_source_type") or "existing",
                    "has_text": True,
                    "reused_existing_transcript": True,
                }
            else:
                transcript = transcript_by_video_id.get(video_id) or {}
                text = str(transcript.get("text") or "").strip()
                transcript_meta = {
                    "primary_source": "apify_actor",
                    "apify_status": transcript_batch_meta.get("status"),
                    "apify_actor_id": transcript_batch_meta.get("actor_id"),
                    "apify_run_id": transcript_batch_meta.get("run_id"),
                    "apify_dataset_id": transcript_batch_meta.get("dataset_id"),
                }
                if text:
                    db.upsert_youtube_video_transcript(
                        video_id,
                        {
                            "source_type": "apify_youtube_actor",
                            "transcript_text": text,
                            "language": str(transcript.get("language") or ""),
                            "duration_seconds": _safe_int(transcript.get("duration")),
                            "brand_mentions": {
                                "brand": brand.get("name"),
                                "video_id": video_id,
                                "source_metadata": transcript.get("source_metadata")
                                if isinstance(transcript.get("source_metadata"), dict)
                                else {},
                            },
                            "created_at": _to_iso(_now_utc()),
                        },
                    )
                    transcript_status = "completed"
                    transcript_success += 1
                    transcript_meta.update({"source": "apify_actor", "has_text": True, "length": len(text)})
                else:
                    fallback_result: dict[str, Any] = {}
                    if use_fallback_transcript:
                        try:
                            # Keep sync cron flow while reusing async fallback chain.
                            fallback_result = asyncio.run(
                                get_transcript_with_fallback(
                                    video_id=video_id,
                                    source_url=str(candidate.get("source_url") or _build_video_url(video_id)),
                                )
                            )
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            try:
                                fallback_result = loop.run_until_complete(
                                    get_transcript_with_fallback(
                                        video_id=video_id,
                                        source_url=str(candidate.get("source_url") or _build_video_url(video_id)),
                                    )
                                )
                            finally:
                                loop.close()
                        except Exception as exc:
                            fallback_result = {
                                "text": "",
                                "language": "",
                                "segments": [],
                                "duration": 0,
                                "source_type": "none",
                                "source_metadata": {"error": str(exc)},
                            }
                    fallback_text = str(fallback_result.get("text") or "").strip()
                    if fallback_text:
                        source_type = str(fallback_result.get("source_type") or "fallback_transcript")
                        db.upsert_youtube_video_transcript(
                            video_id,
                            {
                                "source_type": source_type,
                                "transcript_text": fallback_text,
                                "language": str(fallback_result.get("language") or ""),
                                "duration_seconds": _safe_int(fallback_result.get("duration")),
                                "brand_mentions": {
                                    "brand": brand.get("name"),
                                    "video_id": video_id,
                                    "source_metadata": fallback_result.get("source_metadata")
                                    if isinstance(fallback_result.get("source_metadata"), dict)
                                    else {},
                                    "attempt_order": fallback_result.get("attempt_order")
                                    if isinstance(fallback_result.get("attempt_order"), list)
                                    else [],
                                },
                                "created_at": _to_iso(_now_utc()),
                            },
                        )
                        transcript_status = "completed"
                        transcript_success += 1
                        transcript_meta.update(
                            {
                                "source": source_type,
                                "has_text": True,
                                "length": len(fallback_text),
                                "fallback_used": True,
                            }
                        )
                    else:
                        transcript_status = "failed"
                        transcript_failed += 1
                        transcript_meta.update(
                            {
                                "source": "apify_actor",
                                "has_text": False,
                                "fallback_used": bool(use_fallback_transcript),
                                "error": "transcript_unavailable",
                            }
                        )

        if candidate.get("queued_for_scraping"):
            if not youtube_client:
                comments_status = "failed"
                comments_failed += 1
                comments_meta = {"error": "missing_youtube_api_key"}
            else:
                try:
                    fetched = youtube_client.fetch_comments_with_replies_sync(
                        video_id=video_id,
                        max_results=comments_max_per_video,
                    )
                    inserted = db.insert_youtube_comments_batch(fetched)
                    comments_fetched_total += len(fetched)
                    comments_inserted_total += len(inserted)
                    comments_status = "completed"
                    comments_success += 1
                    comments_meta = {
                        "fetched": len(fetched),
                        "inserted": len(inserted),
                    }
                except Exception as exc:
                    comments_status = "failed"
                    comments_failed += 1
                    comments_meta = {"error": str(exc)}
                    failures.append(f"comments:{video_id}")

        if transcript_status == "failed" or comments_status == "failed":
            layer2_status = "partial_failed"
        elif transcript_status == "not_requested" and comments_status == "not_requested":
            layer2_status = "not_required"
        else:
            layer2_status = "completed"

        _merge_video_analysis_artifacts(
            video_id,
            {
                "transcript_fetch": {
                    "status": transcript_status,
                    "metadata": transcript_meta,
                    "updated_at": _to_iso(_now_utc()),
                },
                "comments_fetch": {
                    "status": comments_status,
                    "metadata": comments_meta,
                    "updated_at": _to_iso(_now_utc()),
                },
                "layer2": {
                    "transcript_status": transcript_status,
                    "comments_status": comments_status,
                    "include_completed": bool(include_completed),
                },
            },
        )
        _merge_layer_status(
            video_id,
            "layer_2",
            layer2_status,
            metadata={
                "transcript_status": transcript_status,
                "comments_status": comments_status,
            },
        )

    return {
        "brand_id": brand_id,
        "status": "ok",
        "phase": "layer_2_sync_fetch",
        "workflow": "manual_sync_cron_ready",
        "total_candidates": len(all_candidates),
        "page_offset": start,
        "page_size": size,
        "page_candidates": len(paged_candidates),
        "video_ids": video_ids,
        "processed_count": processed_count,
        "skipped_count": skipped_count,
        "transcript_batch_meta": transcript_batch_meta,
        "transcript_requested_count": len(transcript_urls),
        "transcript_skipped_existing_count": _safe_int(transcript_batch_meta.get("skipped_existing")),
        "transcript_success": transcript_success,
        "transcript_failed": transcript_failed,
        "comments_success": comments_success,
        "comments_failed": comments_failed,
        "comments_fetched_total": comments_fetched_total,
        "comments_inserted_total": comments_inserted_total,
        "failures": failures,
    }


def _get_layer3_eligible_video_rows(
    brand_id: str,
    scan_limit: int,
) -> list[dict[str, Any]]:
    candidates = _collect_layer2_candidates_for_brand(
        str(brand_id),
        scan_limit=scan_limit,
        include_completed=True,
    )
    eligible_video_ids = [
        str(candidate.get("video_id") or "").strip()
        for candidate in candidates
        if str(candidate.get("video_id") or "").strip()
    ]
    if not eligible_video_ids:
        return []
    rows = db.get_youtube_videos_by_video_ids(eligible_video_ids)
    row_by_video_id = {str(row.get("video_id") or "").strip(): row for row in rows}
    return [row_by_video_id[video_id] for video_id in eligible_video_ids if video_id in row_by_video_id]


def run_youtube_transcript_sentiment_sync_for_brand(
    brand: dict[str, Any],
    page_size: int = 100,
    page_offset: int = 0,
    scan_limit: int = 5000,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    brand_id = brand.get("id")
    if not brand_id:
        return {"brand_id": None, "status": "skipped", "reason": "missing_brand_id"}

    analyzer = AzureYouTubeAnalyzer()
    if not analyzer.is_configured:
        return {"brand_id": brand_id, "status": "skipped", "reason": "azure_not_configured"}

    rows = _get_layer3_eligible_video_rows(str(brand_id), scan_limit=scan_limit)
    eligible_rows: list[dict[str, Any]] = []
    for row in rows:
        transcript_text = str(row.get("transcript_text") or "").strip()
        if not transcript_text:
            continue
        if not force_reprocess and (row.get("transcript_pr_processed_at") or row.get("transcript_sentiment_processed_at")):
            continue
        eligible_rows.append(row)

    start = max(0, int(page_offset or 0))
    size = max(1, int(page_size or 100))
    paged_rows = eligible_rows[start : start + size]

    processed = 0
    updated = 0
    failed = 0
    failures: list[str] = []

    for row in paged_rows:
        video_id = str(row.get("video_id") or "").strip()
        if not video_id:
            continue
        processed += 1
        custom_id = analyzer.custom_id("transcript_sentiment_triage", str(brand_id), video_id)
        payload = {
            "brand_name": brand.get("name", ""),
            "video_id": video_id,
            "video_title": str(row.get("video_title") or ""),
            "channel_name": str(row.get("channel_name") or ""),
            "speaker_context": str(row.get("channel_name") or ""),
            "transcript_text": str(row.get("transcript_text") or ""),
        }
        parsed, meta = analyzer.direct_call_with_meta("transcript_sentiment_triage", payload)
        fallback_reason = ""
        error_payload = meta.get("error") if isinstance(meta.get("error"), dict) else None
        if error_payload:
            fallback_reason = str(error_payload.get("message") or "transcript_pr_analysis_failed")
        elif not parsed:
            fallback_reason = "transcript_pr_analysis_empty_response"

        normalized = normalize_transcript_sentiment_triage(parsed, fallback_reason=fallback_reason)
        if not parsed:
            failed += 1
            failures.append(video_id)

        processed_at = _to_iso(_now_utc())
        monitor_bool = bool(normalized.get("is_pr_risk")) or str(normalized.get("recommended_action") or "") in {
            "monitor",
            "respond",
            "escalate",
        }
        db.update_youtube_video_by_video_id(
            video_id,
            {
                "transcript_pr_sentiment": normalized.get("pr_sentiment"),
                "transcript_pr_is_risk": bool(normalized.get("is_pr_risk")),
                "transcript_pr_severity": normalized.get("severity"),
                "transcript_pr_issue_type": normalized.get("issue_type"),
                "transcript_pr_target_entity": normalized.get("target_entity"),
                "transcript_pr_summary": normalized.get("transcript_summary"),
                "transcript_pr_key_claims": normalized.get("key_claims"),
                "transcript_pr_brand_harm_evidence": normalized.get("brand_harm_evidence"),
                "transcript_pr_protective_context": normalized.get("protective_context"),
                "transcript_pr_recommended_action": normalized.get("recommended_action"),
                "transcript_pr_reason": normalized.get("reason"),
                "transcript_pr_custom_id": custom_id,
                "transcript_pr_processed_at": processed_at,
                "transcript_pr_raw": normalized,
                # Backward-compatible mirrors for existing consumers.
                "transcript_sentiment_label": normalized.get("pr_sentiment"),
                "transcript_sentiment_priority": normalized.get("severity"),
                "transcript_sentiment_monitor": monitor_bool,
                "transcript_sentiment_reason": normalized.get("reason"),
                "transcript_sentiment_custom_id": custom_id,
                "transcript_sentiment_processed_at": processed_at,
            },
        )
        _merge_video_analysis_artifacts(
            video_id,
            {
                "transcript_pr_analysis": {
                    "stage": "transcript_sentiment_triage",
                    "custom_id": custom_id,
                    "mode": meta.get("mode"),
                    "status": "completed" if parsed else "failed",
                    "correlation_id": meta.get("correlation_id"),
                    "provider_response_id": meta.get("provider_response_id"),
                    "pr_sentiment": normalized.get("pr_sentiment"),
                    "is_pr_risk": bool(normalized.get("is_pr_risk")),
                    "severity": normalized.get("severity"),
                    "recommended_action": normalized.get("recommended_action"),
                    "updated_at": processed_at,
                    "error": error_payload,
                }
            },
        )
        _merge_layer_status(
            video_id,
            "layer_3",
            "completed" if parsed else "partial_failed",
            metadata={
                "transcript_pr_sentiment": normalized.get("pr_sentiment"),
                "transcript_is_pr_risk": bool(normalized.get("is_pr_risk")),
            },
        )
        updated += 1

    return {
        "brand_id": brand_id,
        "status": "ok",
        "phase": "layer_3_transcript_sentiment_sync",
        "workflow": "manual_sync_cron_ready",
        "eligible_total": len(eligible_rows),
        "page_offset": start,
        "page_size": size,
        "page_rows": len(paged_rows),
        "processed": processed,
        "updated": updated,
        "failed": failed,
        "failures": failures,
    }


def run_youtube_comment_sentiment_sync_for_brand(
    brand: dict[str, Any],
    video_page_size: int = 100,
    video_page_offset: int = 0,
    scan_limit: int = 5000,
    comment_batch_size: int = 20,
    max_comments_per_video: int = 2000,
    force_reprocess: bool = False,
) -> dict[str, Any]:
    brand_id = brand.get("id")
    if not brand_id:
        return {"brand_id": None, "status": "skipped", "reason": "missing_brand_id"}

    analyzer = AzureYouTubeAnalyzer()
    if not analyzer.is_configured:
        return {"brand_id": brand_id, "status": "skipped", "reason": "azure_not_configured"}

    rows = _get_layer3_eligible_video_rows(str(brand_id), scan_limit=scan_limit)
    start = max(0, int(video_page_offset or 0))
    size = max(1, int(video_page_size or 100))
    paged_rows = rows[start : start + size]
    batch_size = max(1, min(40, int(comment_batch_size or 20)))
    comments_limit = max(1, int(max_comments_per_video or 2000))

    videos_processed = 0
    batches_processed = 0
    comments_seen = 0
    comments_classified = 0
    comments_updated = 0
    failures: list[str] = []

    for row in paged_rows:
        video_id = str(row.get("video_id") or "").strip()
        if not video_id:
            continue
        videos_processed += 1
        comments = db.get_youtube_comments(video_id, limit=comments_limit)
        candidate_comments = []
        for comment in comments:
            comment_id = str(comment.get("comment_id") or "").strip()
            comment_text = str(comment.get("comment_text") or "").strip()
            if not comment_id or not comment_text:
                continue
            if not force_reprocess and str(comment.get("comment_sentiment_label") or "").strip():
                continue
            candidate_comments.append(comment)

        comments_seen += len(candidate_comments)
        video_failures = 0
        for batch_index, chunk in enumerate(_chunked(candidate_comments, batch_size), start=1):
            if not chunk:
                continue
            batches_processed += 1
            custom_id = analyzer.custom_id(
                "comment_sentiment_batch_triage",
                str(brand_id),
                f"{video_id}:batch:{batch_index}",
            )
            payload_comments = []
            expected_comment_ids: list[str] = []
            for comment in chunk:
                comment_id = str(comment.get("comment_id") or "").strip()
                expected_comment_ids.append(comment_id)
                payload_comments.append(
                    {
                        "Comment ID": comment_id,
                        "Video title": str(row.get("video_title") or ""),
                        "Comment String": str(comment.get("comment_text") or ""),
                        "type of comment": "reply" if bool(comment.get("is_reply")) else "top_level",
                    }
                )

            payload = {
                "brand": brand.get("name", ""),
                "video_id": video_id,
                "comments": payload_comments,
            }
            parsed, meta = analyzer.direct_call_with_meta("comment_sentiment_batch_triage", payload)
            sentiment_map = parse_comment_sentiment_results(parsed, expected_comment_ids)
            processed_at = _to_iso(_now_utc())
            updates = [
                {
                    "comment_id": comment_id,
                    "comment_sentiment_label": sentiment_map.get(comment_id, "neutral"),
                    "comment_sentiment_custom_id": custom_id,
                    "comment_sentiment_processed_at": processed_at,
                }
                for comment_id in expected_comment_ids
            ]
            updated_count = db.update_youtube_comment_sentiments(updates)
            comments_updated += updated_count
            comments_classified += len(expected_comment_ids)

            error_payload = meta.get("error") if isinstance(meta.get("error"), dict) else None
            if error_payload or not parsed:
                video_failures += 1

            _merge_video_analysis_artifacts(
                video_id,
                {
                    "comment_sentiment": {
                        "stage": "comment_sentiment_batch_triage",
                        "custom_id": custom_id,
                        "mode": meta.get("mode"),
                        "status": "completed" if parsed else "failed",
                        "correlation_id": meta.get("correlation_id"),
                        "provider_response_id": meta.get("provider_response_id"),
                        "batch_size": len(expected_comment_ids),
                        "updated_count": updated_count,
                        "updated_at": processed_at,
                        "error": error_payload,
                    }
                },
            )

        _merge_layer_status(
            video_id,
            "layer_3",
            "completed" if video_failures == 0 else "partial_failed",
            metadata={
                "comment_sentiment_batches": _safe_int(len(list(_chunked(candidate_comments, batch_size)))),
            },
        )
        if video_failures:
            failures.append(video_id)

    return {
        "brand_id": brand_id,
        "status": "ok",
        "phase": "layer_3_comment_sentiment_sync",
        "workflow": "manual_sync_cron_ready",
        "eligible_videos_total": len(rows),
        "video_page_offset": start,
        "video_page_size": size,
        "video_page_rows": len(paged_rows),
        "videos_processed": videos_processed,
        "batches_processed": batches_processed,
        "comments_seen": comments_seen,
        "comments_classified": comments_classified,
        "comments_updated": comments_updated,
        "failures": failures,
    }


async def submit_youtube_title_triage_batch_for_brand(
    brand: dict[str, Any],
    include_secondary: bool = True,
    query_buckets_override: dict[str, list[str]] | None = None,
    max_results_per_keyword_override: int | None = None,
    published_after_days_override: int | None = None,
) -> dict[str, Any]:
    brand_id = brand.get("id")
    if not brand_id:
        return {
            "brand_id": None,
            "status": "skipped",
            "reason": "missing_brand_id",
            "discovered": 0,
            "submitted_custom_ids": 0,
            "provider_batch_id": None,
        }
    if not YOUTUBE_API_KEY:
        logger.warning("YOUTUBE_API_KEY missing; skipping unofficial YouTube pipeline")
        return {
            "brand_id": brand_id,
            "status": "skipped",
            "reason": "missing_youtube_api_key",
            "discovered": 0,
            "submitted_custom_ids": 0,
            "provider_batch_id": None,
        }

    query_buckets = _resolve_query_buckets(
        brand=brand,
        include_secondary=include_secondary,
        query_buckets_override=query_buckets_override,
    )
    max_results_per_keyword = (
        max(1, int(max_results_per_keyword_override))
        if max_results_per_keyword_override is not None
        else YOUTUBE_UNOFFICIAL_MAX_RESULTS_PER_KEYWORD
    )
    published_after_days = (
        max(1, int(published_after_days_override))
        if published_after_days_override is not None
        else YOUTUBE_UNOFFICIAL_PUBLISHED_AFTER_DAYS
    )

    client = YouTubeDataAPIClient(YOUTUBE_API_KEY)
    candidates = await discover_unofficial_video_candidates(
        client=client,
        query_buckets=query_buckets,
        max_results_per_keyword=max_results_per_keyword,
        published_after_days=published_after_days,
        query_chunk_size=DEFAULT_QUERY_CHUNK_SIZE,
    )
    discovery_stats = getattr(discover_unofficial_video_candidates, "last_stats", {})
    if not isinstance(discovery_stats, dict):
        discovery_stats = {}

    analyzer = AzureYouTubeAnalyzer()
    triage_payloads: dict[str, dict[str, Any]] = {}
    candidate_by_custom_id: dict[str, dict[str, Any]] = {}
    custom_id_by_video_id: dict[str, str] = {}
    raw_channels_created = 0
    raw_channels_updated = 0
    raw_videos_created = 0
    raw_videos_updated = 0
    mentions_created = 0
    mentions_updated = 0
    fulfillment_created = 0
    fulfillment_updated = 0

    for candidate in candidates:
        video_id = candidate.get("video_id", "")
        custom_id = analyzer.custom_id("title_triage", str(brand_id), video_id)
        custom_id_by_video_id[video_id] = custom_id
        triage_payloads[custom_id] = _triage_payload_for_candidate(brand, candidate)
        candidate_by_custom_id[custom_id] = candidate

        pending_meta = {
            "stage": "title_triage",
            "mode": "batch" if analyzer.batch_enabled else "direct",
            "status": "pending_submission",
            "submitted_at": _to_iso(_now_utc()),
        }
        pending_triage = _pending_triage_payload()

        try:
            channel_existing = db.find_youtube_channel(candidate.get("channel_id", ""), brand_id=brand_id)
        except Exception:
            channel_existing = None
        db.upsert_youtube_channel(map_channel_to_raw_channel_row(candidate, brand_id))
        if channel_existing:
            raw_channels_updated += 1
        else:
            raw_channels_created += 1

        try:
            video_existing = db.get_youtube_video_by_video_id(video_id)
        except Exception:
            video_existing = None
        video_row = map_video_to_raw_video_row(
            candidate,
            brand_id,
            title_triage=pending_triage,
            title_custom_id=custom_id,
            title_meta=pending_meta,
        )
        video_row["analysis_artifacts"] = {
            "title_triage": _title_triage_artifact(custom_id, pending_meta),
        }
        db.upsert_youtube_video(video_row)
        if video_existing:
            raw_videos_updated += 1
        else:
            raw_videos_created += 1

        pending_rows_summary = _upsert_pending_normalized_rows(
            brand=brand,
            candidate=candidate,
            query_buckets=query_buckets,
            triage_artifact=_title_triage_artifact(custom_id, pending_meta),
        )
        mentions_created += _safe_int(pending_rows_summary.get("mention_created"))
        mentions_updated += _safe_int(pending_rows_summary.get("mention_updated"))
        fulfillment_created += _safe_int(pending_rows_summary.get("fulfillment_created"))
        fulfillment_updated += _safe_int(pending_rows_summary.get("fulfillment_updated"))

    direct_results, submit_meta = analyzer.submit_batch_stage("title_triage", str(brand_id), triage_payloads)
    submission_result_meta = submit_meta.get("results_meta_by_custom_id", {})
    videos_updated_with_batch_metadata = 0
    for custom_id, candidate in candidate_by_custom_id.items():
        video_id = candidate.get("video_id", "")
        if not video_id:
            continue
        per_custom_meta = submission_result_meta.get(custom_id, {})
        artifact = _title_triage_artifact(
            custom_id=custom_id,
            triage_meta=submit_meta,
            status=submit_meta.get("status"),
            correlation_id=per_custom_meta.get("correlation_id") or submit_meta.get("correlation_id"),
            error=submit_meta.get("error") if isinstance(submit_meta.get("error"), dict) else None,
        )
        _merge_title_triage_artifacts(video_id, artifact)
        db.update_youtube_video_by_video_id(
            video_id,
            {
                "title_triage_custom_id": custom_id,
                "title_triage_mode": submit_meta.get("mode"),
                "title_triage_batch_input": submit_meta.get("batch_input_path"),
                "title_triage_batch_output": submit_meta.get("batch_output_path"),
            },
        )
        videos_updated_with_batch_metadata += 1

    triage_results_applied = 0
    flagged_video_ids: list[str] = []
    if direct_results:
        for custom_id, candidate in candidate_by_custom_id.items():
            triage = normalize_title_triage(
                direct_results.get(custom_id, {}),
                fallback_reason="direct_fallback_unavailable",
            )
            per_custom_meta = submission_result_meta.get(custom_id, {})
            apply_meta = dict(submit_meta)
            apply_meta["status"] = "ingested"
            apply_meta["ingested_at"] = _to_iso(_now_utc())
            if per_custom_meta.get("correlation_id"):
                apply_meta["correlation_id"] = per_custom_meta.get("correlation_id")
            applied = _apply_triage_result_to_rows(
                brand=brand,
                candidate=candidate,
                triage=triage,
                custom_id=custom_id,
                triage_meta=apply_meta,
                query_buckets=query_buckets,
            )
            triage_results_applied += _safe_int(applied.get("triage_applied"))
            mentions_created += _safe_int(applied.get("mention_created"))
            mentions_updated += _safe_int(applied.get("mention_updated"))
            fulfillment_created += _safe_int(applied.get("fulfillment_created"))
            fulfillment_updated += _safe_int(applied.get("fulfillment_updated"))
            if applied.get("flagged"):
                flagged_video_ids.append(candidate.get("video_id", ""))

    return {
        "brand_id": brand_id,
        "status": "ok",
        "phase": "submit",
        "discovered": len(candidates),
        "discovered_video_count": _safe_int(discovery_stats.get("discovered_video_ids"), len(candidates)),
        "blacklisted_excluded_count": _safe_int(discovery_stats.get("excluded_blacklisted")),
        "excluded_missing_video_details_count": _safe_int(
            discovery_stats.get("excluded_missing_video_details")
        ),
        "unofficial_candidate_count": len(candidates),
        "raw_channels_created": raw_channels_created,
        "raw_channels_updated": raw_channels_updated,
        "raw_videos_created": raw_videos_created,
        "raw_videos_updated": raw_videos_updated,
        "mentions_created": mentions_created,
        "mentions_updated": mentions_updated,
        "fulfillment_created": fulfillment_created,
        "fulfillment_updated": fulfillment_updated,
        "submitted_custom_ids": len(triage_payloads),
        "videos_updated_with_batch_metadata": videos_updated_with_batch_metadata,
        "triage_results_applied": triage_results_applied,
        "flagged_video_ids": [v for v in flagged_video_ids if v],
        "provider_batch_id": submit_meta.get("provider_batch_id"),
        "input_file_id": submit_meta.get("input_file_id"),
        "output_file_id": submit_meta.get("output_file_id"),
        "error_file_id": submit_meta.get("error_file_id"),
        "batch_status": submit_meta.get("status"),
        "triage_mode": submit_meta.get("mode"),
        "triage_batch_input": submit_meta.get("batch_input_path"),
        "triage_batch_output": submit_meta.get("batch_output_path"),
        "triage_batch_error": submit_meta.get("batch_error_path"),
        "triage_correlation_id": submit_meta.get("correlation_id"),
        "triage_error": submit_meta.get("error"),
    }


def _get_brand_video_rows(brand_id: str, limit: int = 800) -> list[dict[str, Any]]:
    getter = getattr(db, "get_youtube_videos_for_brand", None)
    if not callable(getter):
        return []
    try:
        return getter(str(brand_id), limit=limit)
    except Exception:
        logger.exception("Failed to load youtube_videos for brand=%s", brand_id)
        return []


def ingest_youtube_title_triage_results_for_brand(
    brand: dict[str, Any],
    batch_meta: dict[str, Any],
    target_custom_ids: list[str] | None = None,
    query_buckets_hint: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    brand_id = brand.get("id")
    if not brand_id:
        return {"brand_id": None, "status": "skipped", "reason": "missing_brand_id"}

    analyzer = AzureYouTubeAnalyzer()
    fetched = analyzer.fetch_batch_outputs(batch_meta)
    results_by_custom_id = fetched.get("results_by_custom_id") or {}
    result_meta_by_custom_id = fetched.get("result_meta_by_custom_id") or {}
    errors_by_custom_id = fetched.get("errors_by_custom_id") or {}

    videos = _get_brand_video_rows(str(brand_id), limit=1000)
    custom_to_row: dict[str, dict[str, Any]] = {}
    for row in videos:
        custom_id = str(row.get("title_triage_custom_id") or "").strip()
        if not custom_id:
            artifacts = row.get("analysis_artifacts") if isinstance(row.get("analysis_artifacts"), dict) else {}
            triage_artifacts = artifacts.get("title_triage") if isinstance(artifacts.get("title_triage"), dict) else {}
            custom_id = str(triage_artifacts.get("custom_id") or "").strip()
        if custom_id:
            custom_to_row[custom_id] = row

    custom_ids = list(
        dict.fromkeys(
            [c for c in (target_custom_ids or []) if c]
            + list(results_by_custom_id.keys())
            + list(errors_by_custom_id.keys())
        )
    )

    query_buckets = query_buckets_hint or {}
    flagged_video_ids: list[str] = []
    videos_updated_with_triage_results = 0
    mentions_created = 0
    mentions_updated = 0
    fulfillment_created = 0
    fulfillment_updated = 0

    for custom_id in custom_ids:
        row = custom_to_row.get(custom_id)
        if not row:
            continue
        candidate = _candidate_from_video_row(row)
        result_payload = results_by_custom_id.get(custom_id, {})
        result_meta = result_meta_by_custom_id.get(custom_id, {})
        error_payload = errors_by_custom_id.get(custom_id)
        if not isinstance(error_payload, dict):
            error_payload = None

        fallback_reason = "batch_result_missing"
        if error_payload:
            fallback_reason = str(error_payload.get("message") or "batch_error")
        triage = normalize_title_triage(result_payload, fallback_reason=fallback_reason)

        apply_meta = dict(batch_meta)
        apply_meta.update(
            {
                "mode": "batch",
                "batch_output_path": fetched.get("batch_output_path"),
                "batch_error_path": fetched.get("batch_error_path"),
                "correlation_id": result_meta.get("correlation_id") or batch_meta.get("correlation_id"),
                "status": "ingested" if result_payload else "failed",
                "ingested_at": _to_iso(_now_utc()),
                "error": error_payload
                or (result_meta.get("error") if isinstance(result_meta.get("error"), dict) else None),
            }
        )

        applied = _apply_triage_result_to_rows(
            brand=brand,
            candidate=candidate,
            triage=triage,
            custom_id=custom_id,
            triage_meta=apply_meta,
            query_buckets=query_buckets,
        )
        videos_updated_with_triage_results += _safe_int(applied.get("triage_applied"))
        mentions_created += _safe_int(applied.get("mention_created"))
        mentions_updated += _safe_int(applied.get("mention_updated"))
        fulfillment_created += _safe_int(applied.get("fulfillment_created"))
        fulfillment_updated += _safe_int(applied.get("fulfillment_updated"))
        if applied.get("flagged"):
            flagged_video_ids.append(applied.get("video_id", ""))

    return {
        "brand_id": brand_id,
        "status": "ok",
        "phase": "ingest",
        "provider_batch_id": batch_meta.get("provider_batch_id"),
        "batch_status": batch_meta.get("status"),
        "batch_output_path": fetched.get("batch_output_path"),
        "batch_error_path": fetched.get("batch_error_path"),
        "videos_updated_with_triage_results": videos_updated_with_triage_results,
        "mentions_created": mentions_created,
        "mentions_updated": mentions_updated,
        "fulfillment_created": fulfillment_created,
        "fulfillment_updated": fulfillment_updated,
        "flagged_video_ids": [v for v in flagged_video_ids if v],
        "result_custom_ids": len(results_by_custom_id),
        "error_custom_ids": len(errors_by_custom_id),
    }


def poll_youtube_title_triage_batch_for_brand(
    brand: dict[str, Any],
    max_batches: int = 10,
    video_scan_limit: int = 800,
) -> dict[str, Any]:
    brand_id = brand.get("id")
    if not brand_id:
        return {"brand_id": None, "status": "skipped", "reason": "missing_brand_id"}

    videos = _get_brand_video_rows(str(brand_id), limit=video_scan_limit)
    pending_by_batch: dict[str, set[str]] = {}
    custom_ids_by_batch: dict[str, set[str]] = {}
    for row in videos:
        artifacts = row.get("analysis_artifacts") if isinstance(row.get("analysis_artifacts"), dict) else {}
        triage_artifacts = artifacts.get("title_triage") if isinstance(artifacts.get("title_triage"), dict) else {}
        batch_id = str(triage_artifacts.get("provider_batch_id") or "").strip()
        if not batch_id:
            continue
        status = str(triage_artifacts.get("status") or "").strip().lower()
        if status in {"ingested"}:
            continue
        if status in TERMINAL_BATCH_STATUSES and not triage_artifacts.get("output_file_id") and not triage_artifacts.get("error_file_id"):
            continue
        pending_by_batch.setdefault(batch_id, set()).add(str(row.get("video_id") or ""))
        custom_id = str(
            row.get("title_triage_custom_id")
            or triage_artifacts.get("custom_id")
            or ""
        ).strip()
        if custom_id:
            custom_ids_by_batch.setdefault(batch_id, set()).add(custom_id)

    analyzer = AzureYouTubeAnalyzer()
    batch_ids = list(pending_by_batch.keys())[:max(1, max_batches)]
    batch_statuses: dict[str, str] = {}
    flagged_video_ids: list[str] = []
    videos_updated_with_batch_metadata = 0
    videos_updated_with_triage_results = 0
    for batch_id in batch_ids:
        poll_meta = analyzer.poll_batch_stage(batch_id)
        batch_status = str(poll_meta.get("status") or "unknown").strip().lower()
        batch_statuses[batch_id] = batch_status
        for video_id in pending_by_batch.get(batch_id, set()):
            row = db.get_youtube_video_by_video_id(video_id) or {}
            artifacts = row.get("analysis_artifacts") if isinstance(row.get("analysis_artifacts"), dict) else {}
            triage_artifacts = artifacts.get("title_triage") if isinstance(artifacts.get("title_triage"), dict) else {}
            custom_id = str(
                row.get("title_triage_custom_id")
                or triage_artifacts.get("custom_id")
                or ""
            ).strip()
            artifact = _title_triage_artifact(
                custom_id=custom_id,
                triage_meta=poll_meta,
                status=batch_status,
                correlation_id=poll_meta.get("correlation_id"),
                error=poll_meta.get("error") if isinstance(poll_meta.get("error"), dict) else None,
            )
            _merge_title_triage_artifacts(video_id, artifact)
            db.update_youtube_video_by_video_id(
                video_id,
                {
                    "title_triage_mode": "batch",
                    "title_triage_batch_output": poll_meta.get("output_file_id") or row.get("title_triage_batch_output"),
                },
            )
            videos_updated_with_batch_metadata += 1

        if batch_status in TERMINAL_BATCH_STATUSES:
            ingest_summary = ingest_youtube_title_triage_results_for_brand(
                brand=brand,
                batch_meta=poll_meta,
                target_custom_ids=sorted(custom_ids_by_batch.get(batch_id, set())),
            )
            videos_updated_with_triage_results += _safe_int(
                ingest_summary.get("videos_updated_with_triage_results")
            )
            flagged_video_ids.extend(ingest_summary.get("flagged_video_ids") or [])

    return {
        "brand_id": brand_id,
        "status": "ok",
        "phase": "poll",
        "batches_polled": len(batch_ids),
        "batch_statuses": batch_statuses,
        "videos_updated_with_batch_metadata": videos_updated_with_batch_metadata,
        "videos_updated_with_triage_results": videos_updated_with_triage_results,
        "flagged_video_ids": [v for v in flagged_video_ids if v],
    }


async def enrich_flagged_youtube_mentions(
    brand: dict[str, Any],
    flagged_video_ids: list[str],
) -> dict[str, Any]:
    brand_id = brand.get("id")
    if not brand_id:
        return {"brand_id": None, "status": "skipped", "reason": "missing_brand_id"}
    if not flagged_video_ids:
        return {
            "brand_id": brand_id,
            "status": "ok",
            "enriched": 0,
            "comments_fetched_total": 0,
            "comments_inserted_total": 0,
            "transcript_source_counts": {},
            "transcript_success_count": 0,
            "final_analysis_saved_count": 0,
            "enrichment_failure_video_ids": [],
        }

    analyzer = AzureYouTubeAnalyzer()
    client = YouTubeDataAPIClient(YOUTUBE_API_KEY)
    video_lookup = {
        row.get("video_id"): row
        for row in _get_brand_video_rows(str(brand_id), limit=1200)
        if row.get("video_id")
    }

    enriched_count = 0
    comments_fetched_total = 0
    comments_inserted_total = 0
    transcript_source_counts: dict[str, int] = {}
    transcript_success_count = 0
    final_analysis_saved_count = 0
    enrichment_failures: list[str] = []

    for video_id in flagged_video_ids:
        row = video_lookup.get(video_id)
        if not row:
            continue
        candidate = _candidate_from_video_row(row)
        mention = db.get_mention_by_platform_ref(str(brand_id), "youtube", video_id) or {}
        candidate["mention"] = mention
        candidate["title_triage"] = normalize_title_triage(
            {
                "label": row.get("title_triage_label"),
                "confidence": row.get("title_triage_confidence"),
                "is_pr_risk": row.get("title_triage_is_pr_risk"),
                "issue_type": row.get("title_triage_issue_type"),
                "reason": row.get("title_triage_reason"),
            },
            fallback_reason="triage_missing",
        )

        try:
            enrichment_summary = await enrich_flagged_video_candidate(
                brand=brand,
                candidate=candidate,
                client=client,
                analyzer=analyzer,
            )
            enriched_count += 1
            comments_fetched_total += _safe_int(enrichment_summary.get("comments_fetched"))
            comments_inserted_total += _safe_int(enrichment_summary.get("comments_inserted"))
            transcript_source = str(enrichment_summary.get("transcript_source") or "none")
            transcript_source_counts[transcript_source] = transcript_source_counts.get(transcript_source, 0) + 1
            if transcript_source != "none":
                transcript_success_count += 1
            if enrichment_summary.get("analysis_saved"):
                final_analysis_saved_count += 1
        except Exception:
            logger.exception(
                "Deep enrichment failed for brand=%s video_id=%s",
                brand_id,
                video_id,
            )
            enrichment_failures.append(video_id)

    return {
        "brand_id": brand_id,
        "status": "ok",
        "enriched": enriched_count,
        "comments_fetched_total": comments_fetched_total,
        "comments_inserted_total": comments_inserted_total,
        "transcript_source_counts": transcript_source_counts,
        "transcript_success_count": transcript_success_count,
        "final_analysis_saved_count": final_analysis_saved_count,
        "enrichment_failure_video_ids": enrichment_failures,
    }


async def run_unofficial_youtube_pipeline_for_brand(
    brand: dict[str, Any],
    include_secondary: bool = True,
    query_buckets_override: dict[str, list[str]] | None = None,
    max_results_per_keyword_override: int | None = None,
    published_after_days_override: int | None = None,
) -> dict[str, Any]:
    submit_summary = await submit_youtube_title_triage_batch_for_brand(
        brand=brand,
        include_secondary=include_secondary,
        query_buckets_override=query_buckets_override,
        max_results_per_keyword_override=max_results_per_keyword_override,
        published_after_days_override=published_after_days_override,
    )
    if submit_summary.get("status") != "ok":
        return submit_summary

    poll_summary = poll_youtube_title_triage_batch_for_brand(brand)
    flagged_video_ids = list(
        dict.fromkeys(
            (submit_summary.get("flagged_video_ids") or [])
            + (poll_summary.get("flagged_video_ids") or [])
        )
    )
    enrich_summary = await enrich_flagged_youtube_mentions(brand, flagged_video_ids)

    return {
        "brand_id": submit_summary.get("brand_id"),
        "status": "ok",
        "discovered": submit_summary.get("discovered", 0),
        "discovered_video_count": submit_summary.get("discovered_video_count", 0),
        "blacklisted_excluded_count": submit_summary.get("blacklisted_excluded_count", 0),
        "excluded_missing_video_details_count": submit_summary.get("excluded_missing_video_details_count", 0),
        "unofficial_candidate_count": submit_summary.get("unofficial_candidate_count", 0),
        "mentions_created": submit_summary.get("mentions_created", 0),
        "mentions_updated": submit_summary.get("mentions_updated", 0),
        "fulfillment_created": submit_summary.get("fulfillment_created", 0),
        "fulfillment_updated": submit_summary.get("fulfillment_updated", 0),
        "raw_channels_created": submit_summary.get("raw_channels_created", 0),
        "raw_channels_updated": submit_summary.get("raw_channels_updated", 0),
        "raw_videos_created": submit_summary.get("raw_videos_created", 0),
        "raw_videos_updated": submit_summary.get("raw_videos_updated", 0),
        "flagged": len(flagged_video_ids),
        "flagged_video_ids": flagged_video_ids,
        "videos_updated_with_batch_metadata": (
            _safe_int(submit_summary.get("videos_updated_with_batch_metadata"))
            + _safe_int(poll_summary.get("videos_updated_with_batch_metadata"))
        ),
        "videos_updated_with_triage_results": (
            _safe_int(submit_summary.get("triage_results_applied"))
            + _safe_int(poll_summary.get("videos_updated_with_triage_results"))
        ),
        "enriched": enrich_summary.get("enriched", 0),
        "comments_fetched_total": enrich_summary.get("comments_fetched_total", 0),
        "comments_inserted_total": enrich_summary.get("comments_inserted_total", 0),
        "transcript_source_counts": enrich_summary.get("transcript_source_counts", {}),
        "transcript_success_count": enrich_summary.get("transcript_success_count", 0),
        "final_analysis_saved_count": enrich_summary.get("final_analysis_saved_count", 0),
        "enrichment_failure_video_ids": enrich_summary.get("enrichment_failure_video_ids", []),
        "triage_mode": submit_summary.get("triage_mode"),
        "triage_batch_input": submit_summary.get("triage_batch_input"),
        "triage_batch_output": submit_summary.get("triage_batch_output"),
        "triage_batch_error": submit_summary.get("triage_batch_error"),
        "provider_batch_id": submit_summary.get("provider_batch_id"),
        "batch_status": (
            poll_summary.get("batch_statuses")
            or {submit_summary.get("provider_batch_id"): submit_summary.get("batch_status")}
        ),
    }


async def enrich_flagged_video_candidate(
    brand: dict[str, Any],
    candidate: dict[str, Any],
    client: YouTubeDataAPIClient,
    analyzer: AzureYouTubeAnalyzer,
) -> dict[str, Any]:
    mention = candidate.get("mention") or {}
    mention_id = mention.get("id")
    video_id = candidate.get("video_id", "")
    analysis_saved = False

    transcript = await get_transcript_with_fallback(
        video_id=video_id,
        source_url=candidate.get("source_url") or _build_video_url(video_id),
    )

    if transcript.get("text"):
        db.upsert_youtube_video_transcript(
            video_id,
            {
                "source_type": transcript.get("source_type", "youtube_captions"),
                "transcript_text": transcript.get("text", ""),
                "language": transcript.get("language", ""),
                "duration_seconds": _safe_int(transcript.get("duration")),
                "brand_mentions": {
                    "brand": brand.get("name"),
                    "video_id": video_id,
                    "attempt_order": transcript.get("attempt_order", []),
                    "source_metadata": (
                        transcript.get("source_metadata")
                        if isinstance(transcript.get("source_metadata"), dict)
                        else {}
                    ),
                },
                "created_at": _to_iso(_now_utc()),
            },
        )

    comments: list[dict[str, Any]] = []
    try:
        comments = await client.fetch_comments(
            video_id=video_id,
            max_results=YOUTUBE_UNOFFICIAL_MAX_COMMENTS_PER_FLAGGED_VIDEO,
        )
    except Exception:
        logger.exception("Comment fetch failed for video_id=%s", video_id)

    inserted_comments = db.insert_youtube_comments_batch(comments)

    brand_id = str(brand.get("id"))
    title_triage = candidate.get("title_triage") or {}

    transcript_custom_id = analyzer.custom_id("transcript_analysis", brand_id, video_id)
    transcript_payload = {
        "brand": brand.get("name", ""),
        "video_id": video_id,
        "title": ((candidate.get("video") or {}).get("snippet") or {}).get("title", ""),
        "transcript": transcript.get("text", ""),
    }
    transcript_results, transcript_meta = analyzer.run_stage(
        "transcript_analysis",
        brand_id,
        {transcript_custom_id: transcript_payload},
    )

    comment_custom_id = analyzer.custom_id("comment_analysis", brand_id, video_id)
    comment_payload = {
        "brand": brand.get("name", ""),
        "video_id": video_id,
        "title": ((candidate.get("video") or {}).get("snippet") or {}).get("title", ""),
        "comment_count": len(comments),
        "comments": [c.get("comment_text", "") for c in comments[:100]],
    }
    comment_results, comment_meta = analyzer.run_stage(
        "comment_analysis",
        brand_id,
        {comment_custom_id: comment_payload},
    )

    transcript_analysis = transcript_results.get(transcript_custom_id, {})
    comment_analysis = comment_results.get(comment_custom_id, {})

    final_custom_id = analyzer.custom_id("final_synthesis", brand_id, video_id)
    final_payload = {
        "brand": brand.get("name", ""),
        "video_id": video_id,
        "title": ((candidate.get("video") or {}).get("snippet") or {}).get("title", ""),
        "title_triage": title_triage,
        "transcript_analysis": transcript_analysis,
        "comment_analysis": comment_analysis,
    }
    final_results, final_meta = analyzer.run_stage(
        "final_synthesis",
        brand_id,
        {final_custom_id: final_payload},
    )
    final_analysis = normalize_final_analysis(final_results.get(final_custom_id, {}), title_triage)

    if mention_id:
        raw_data = mention.get("raw_data") if isinstance(mention.get("raw_data"), dict) else {}
        raw_data.update(
            {
                "title_triage": title_triage,
                "transcript": {
                    "source_type": transcript.get("source_type"),
                    "language": transcript.get("language"),
                    "duration": transcript.get("duration"),
                    "attempt_order": transcript.get("attempt_order", []),
                    "source_metadata": (
                        transcript.get("source_metadata")
                        if isinstance(transcript.get("source_metadata"), dict)
                        else {}
                    ),
                },
                "comments": {
                    "fetched_count": len(comments),
                    "inserted_count": len(inserted_comments),
                },
                "analysis": {
                    "transcript": transcript_analysis,
                    "comments": comment_analysis,
                    "final": final_analysis,
                    "artifacts": {
                        "transcript": transcript_meta,
                        "comments": comment_meta,
                        "final": final_meta,
                    },
                },
                "analysis_version": YOUTUBE_ANALYSIS_VERSION,
            }
        )

        db.update_mention(
            mention_id,
            {
                "sentiment_label": final_analysis.get("final_sentiment"),
                "theme": final_analysis.get("issue_type"),
                "raw_data": raw_data,
            },
        )
        analysis_saved = True

    existing_video = db.get_youtube_video_by_video_id(video_id) or {}
    existing_artifacts = (
        existing_video.get("analysis_artifacts")
        if isinstance(existing_video.get("analysis_artifacts"), dict)
        else {}
    )
    existing_artifacts.update(
        {
            "transcript_analysis": {
                "custom_id": transcript_custom_id,
                "mode": transcript_meta.get("mode"),
                "batch_input_path": transcript_meta.get("batch_input_path"),
                "batch_output_path": transcript_meta.get("batch_output_path"),
                "correlation_id": transcript_meta.get("correlation_id"),
            },
            "comment_analysis": {
                "custom_id": comment_custom_id,
                "mode": comment_meta.get("mode"),
                "batch_input_path": comment_meta.get("batch_input_path"),
                "batch_output_path": comment_meta.get("batch_output_path"),
                "correlation_id": comment_meta.get("correlation_id"),
            },
            "final_synthesis": {
                "custom_id": final_custom_id,
                "mode": final_meta.get("mode"),
                "batch_input_path": final_meta.get("batch_input_path"),
                "batch_output_path": final_meta.get("batch_output_path"),
                "correlation_id": final_meta.get("correlation_id"),
            },
            "transcript": {
                "source_type": transcript.get("source_type", "none"),
                "has_text": bool((transcript.get("text") or "").strip()),
                "attempt_order": transcript.get("attempt_order", []),
                "source_metadata": (
                    transcript.get("source_metadata")
                    if isinstance(transcript.get("source_metadata"), dict)
                    else {}
                ),
            },
        }
    )
    db.update_youtube_video_by_video_id(
        video_id,
        {"analysis_artifacts": existing_artifacts},
    )

    return {
        "video_id": video_id,
        "mention_id": mention_id,
        "comments_fetched": len(comments),
        "comments_inserted": len(inserted_comments),
        "transcript_source": transcript.get("source_type", "none"),
        "transcript_has_text": bool((transcript.get("text") or "").strip()),
        "analysis_saved": analysis_saved,
        "final_sentiment": final_analysis.get("final_sentiment"),
        "final_analysis": final_analysis,
    }


class YouTubeScraper(BaseScraper):
    platform = "youtube"

    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        if not YOUTUBE_API_KEY:
            logger.warning("YouTube API key missing; search() returning empty results")
            return []

        client = YouTubeDataAPIClient(YOUTUBE_API_KEY)
        query_terms = list(params.keywords) + [h.lstrip("#") for h in params.hashtags]
        buckets = {"primary": dedupe_query_terms(query_terms)}

        discovered = await discover_unofficial_video_candidates(
            client=client,
            query_buckets=buckets,
            max_results_per_keyword=max(1, params.max_results_per_platform),
            published_after_days=YOUTUBE_UNOFFICIAL_PUBLISHED_AFTER_DAYS,
            query_chunk_size=DEFAULT_QUERY_CHUNK_SIZE,
        )

        return [map_video_to_search_result(item) for item in discovered]

    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        if not YOUTUBE_API_KEY:
            return []
        video_id = extract_video_id(source_url)
        if not video_id:
            return []
        client = YouTubeDataAPIClient(YOUTUBE_API_KEY)
        return await client.fetch_comments(video_id, max_results=limit)

    async def get_transcript(self, video_id: str) -> str | None:
        transcript = await get_transcript_with_fallback(
            video_id=video_id,
            source_url=_build_video_url(video_id),
        )
        text = transcript.get("text", "").strip()
        return text or None


# Instantiate and register for search engine bootstrap
_scraper = YouTubeScraper()
register_searcher("youtube", _scraper.search)
