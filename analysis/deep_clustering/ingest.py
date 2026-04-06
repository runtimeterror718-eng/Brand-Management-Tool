"""
Stage 1: Ingest & Normalize — pull all platform data into a common schema.
Cross-platform dedup, language detection, engagement normalization.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from config.supabase_client import get_service_client

logger = logging.getLogger(__name__)

HINGLISH_MARKERS = {
    "hai", "nahi", "kya", "bhai", "yaar", "accha", "karo", "padho",
    "sir", "bohot", "bahut", "wala", "mein", "hoga", "tha", "thi",
    "padhao", "samjha", "dekho", "batao", "pata", "sab", "theek",
    "bilkul", "ekdum", "matlab", "isliye", "aur", "lekin", "toh",
    "bhi", "abhi", "kuch", "haan", "nai", "bas", "chal", "chalo",
}


@dataclass
class NormalizedMention:
    id: str
    platform: str
    content: str
    author: str
    engagement_score: float
    published_at: str | None
    source_url: str
    source_context: str  # e.g. "r/JEENEETards" or "IG @physicswallah"
    language: str
    original_table: str
    original_id: str
    raw_metadata: dict = field(default_factory=dict)


def ingest_all(brand_id: str) -> list[NormalizedMention]:
    """Pull all data across all platforms and normalize into common schema."""
    client = get_service_client()
    all_mentions: list[NormalizedMention] = []

    # --- Reddit posts ---
    resp = client.table("reddit_posts").select("*").eq("brand_id", brand_id).limit(2000).execute()
    for r in resp.data or []:
        text = f"{r.get('post_title', '')}\n{r.get('post_body', '')}".strip()
        if len(text) < 10:
            continue
        all_mentions.append(NormalizedMention(
            id=r["id"], platform="reddit", content=text,
            author=r.get("author_username", ""),
            engagement_score=float(r.get("score", 0)),
            published_at=r.get("created_at"),
            source_url=r.get("post_url", ""),
            source_context=f"r/{r.get('subreddit_name', '?')}",
            language=detect_language(text),
            original_table="reddit_posts", original_id=r["id"],
            raw_metadata={"subreddit": r.get("subreddit_name"), "flair": r.get("post_flair"),
                          "upvote_ratio": r.get("upvote_ratio"), "num_comments": r.get("num_comments", 0)},
        ))

    # --- Reddit comments ---
    resp = client.table("reddit_comments").select("*").limit(5000).execute()
    for r in resp.data or []:
        text = (r.get("comment_body") or "").strip()
        if len(text) < 15 or text.startswith("http"):
            continue
        all_mentions.append(NormalizedMention(
            id=r["id"], platform="reddit", content=text,
            author=r.get("comment_author", ""),
            engagement_score=float(r.get("comment_score", 0)),
            published_at=r.get("created_at"),
            source_url="", source_context=f"reddit comment (depth {r.get('comment_depth', 0)})",
            language=detect_language(text),
            original_table="reddit_comments", original_id=r["id"],
            raw_metadata={"post_id": r.get("post_id"), "depth": r.get("comment_depth", 0)},
        ))

    # --- Instagram posts ---
    resp = client.table("instagram_posts").select("*").in_(
        "brand_id", _get_all_brand_ids(brand_id)
    ).limit(2000).execute()
    for r in resp.data or []:
        text = (r.get("caption_text") or "").strip()
        if len(text) < 10:
            continue
        all_mentions.append(NormalizedMention(
            id=r["id"], platform="instagram", content=text,
            author=r.get("account_name", ""),
            engagement_score=float(r.get("like_count", 0)),
            published_at=r.get("published_date"),
            source_url=r.get("post_url", ""),
            source_context=f"IG @{r.get('account_name', '?')}",
            language=detect_language(text),
            original_table="instagram_posts", original_id=r["id"],
            raw_metadata={"media_type": r.get("media_type"), "comment_count": r.get("comment_count", 0),
                          "hashtags": r.get("hashtags", [])},
        ))

    # --- Instagram comments ---
    resp = client.table("instagram_comments").select("*").limit(5000).execute()
    for r in resp.data or []:
        text = (r.get("comment_text") or "").strip()
        if len(text) < 10:
            continue
        all_mentions.append(NormalizedMention(
            id=r["id"], platform="instagram", content=text,
            author=r.get("comment_author", ""),
            engagement_score=0.0,
            published_at=r.get("comment_date"),
            source_url="", source_context=f"IG comment on {r.get('post_id', '?')}",
            language=detect_language(text),
            original_table="instagram_comments", original_id=r["id"],
            raw_metadata={"post_id": r.get("post_id")},
        ))

    # --- YouTube comments ---
    resp = client.table("youtube_comments").select("*").limit(5000).execute()
    for r in resp.data or []:
        text = (r.get("comment_text") or "").strip()
        if len(text) < 10:
            continue
        all_mentions.append(NormalizedMention(
            id=r["id"], platform="youtube", content=text,
            author=r.get("comment_author", ""),
            engagement_score=float(r.get("comment_likes", 0)),
            published_at=r.get("comment_date"),
            source_url="", source_context=f"YT comment on {r.get('video_id', '?')}",
            language=detect_language(text),
            original_table="youtube_comments", original_id=r["id"],
            raw_metadata={"video_id": r.get("video_id")},
        ))

    # --- Telegram messages ---
    resp = client.table("telegram_messages").select("*").eq("brand_id", brand_id).limit(5000).execute()
    for r in resp.data or []:
        text = (r.get("message_text") or "").strip()
        if len(text) < 15 or text.startswith("http"):
            continue
        all_mentions.append(NormalizedMention(
            id=r["id"], platform="telegram", content=text,
            author=r.get("sender_username", ""),
            engagement_score=float(r.get("views", 0)),
            published_at=r.get("message_timestamp"),
            source_url=r.get("message_url", ""),
            source_context=f"TG {r.get('channel_name', '?')}",
            language=detect_language(text),
            original_table="telegram_messages", original_id=r["id"],
            raw_metadata={"channel_name": r.get("channel_name"), "forwards": r.get("forwards_count", 0)},
        ))

    logger.info("Ingested %d mentions across all platforms", len(all_mentions))

    # --- Cross-platform dedup ---
    deduped = deduplicate(all_mentions)
    logger.info("After dedup: %d mentions (%d removed)", len(deduped), len(all_mentions) - len(deduped))

    return deduped


def deduplicate(mentions: list[NormalizedMention]) -> list[NormalizedMention]:
    """Remove near-duplicate content across platforms. Keep highest engagement version."""
    fingerprints: dict[str, NormalizedMention] = {}

    for m in mentions:
        fp = _fingerprint(m.content)
        if fp not in fingerprints:
            fingerprints[fp] = m
        elif m.engagement_score > fingerprints[fp].engagement_score:
            fingerprints[fp] = m

    return list(fingerprints.values())


def _fingerprint(text: str) -> str:
    normalized = text.lower().strip()
    normalized = re.sub(r"https?://\S+", "", normalized)
    normalized = re.sub(r"@\w+", "", normalized)
    normalized = re.sub(r"#\w+", "", normalized)
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    core = normalized[:200]
    return hashlib.md5(core.encode()).hexdigest()


def detect_language(text: str) -> str:
    if len(text) < 15:
        return "unknown"
    words = text.lower().split()
    hinglish_count = sum(1 for w in words if w in HINGLISH_MARKERS)
    hinglish_ratio = hinglish_count / max(len(words), 1)
    devanagari_count = sum(1 for c in text if "\u0900" <= c <= "\u097F")
    devanagari_ratio = devanagari_count / max(len(text), 1)
    if devanagari_ratio > 0.3:
        return "hi"
    if hinglish_ratio > 0.15:
        return "hinglish"
    return "en"


def _get_all_brand_ids(brand_id: str) -> list[str]:
    client = get_service_client()
    resp = client.table("brands").select("id").eq("name", "PhysicsWallah").execute()
    ids = [r["id"] for r in (resp.data or [])]
    if brand_id not in ids:
        ids.append(brand_id)
    return ids
