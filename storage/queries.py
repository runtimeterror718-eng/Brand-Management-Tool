"""
Common Supabase queries for all tables.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from config.supabase_client import get_service_client


# ---------------------------------------------------------------------------
# Brands
# ---------------------------------------------------------------------------

def get_brand(brand_id: str) -> dict | None:
    resp = get_service_client().table("brands").select("*").eq("id", brand_id).execute()
    return resp.data[0] if resp.data else None


def get_all_brands() -> list[dict]:
    resp = get_service_client().table("brands").select("*").execute()
    return resp.data


def upsert_brand(brand: dict) -> dict:
    resp = get_service_client().table("brands").upsert(brand).execute()
    return resp.data[0]


# ---------------------------------------------------------------------------
# Mentions
# ---------------------------------------------------------------------------

def insert_mention(mention: dict) -> dict:
    resp = get_service_client().table("mentions").insert(mention).execute()
    return resp.data[0]


def insert_mentions_batch(mentions: list[dict]) -> list[dict]:
    if not mentions:
        return []
    resp = get_service_client().table("mentions").insert(mentions).execute()
    return resp.data


def get_mentions(
    brand_id: str,
    platform: str | None = None,
    since: datetime | None = None,
    limit: int = 500,
) -> list[dict]:
    q = (
        get_service_client()
        .table("mentions")
        .select("*")
        .eq("brand_id", brand_id)
        .order("scraped_at", desc=True)
        .limit(limit)
    )
    if platform:
        q = q.eq("platform", platform)
    if since:
        q = q.gte("scraped_at", since.isoformat())
    return q.execute().data


def get_mention(mention_id: str) -> dict | None:
    resp = (
        get_service_client()
        .table("mentions")
        .select("*")
        .eq("id", mention_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


def update_mention(mention_id: str, updates: dict) -> dict:
    resp = (
        get_service_client()
        .table("mentions")
        .update(updates)
        .eq("id", mention_id)
        .execute()
    )
    return resp.data[0]


# ---------------------------------------------------------------------------
# Transcriptions
# ---------------------------------------------------------------------------

def insert_transcription(transcription: dict) -> dict:
    resp = (
        get_service_client()
        .table("transcriptions")
        .insert(transcription)
        .execute()
    )
    return resp.data[0]


def get_transcription_by_mention(mention_id: str) -> dict | None:
    resp = (
        get_service_client()
        .table("transcriptions")
        .select("*")
        .eq("mention_id", mention_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


# ---------------------------------------------------------------------------
# Severity Scores
# ---------------------------------------------------------------------------

def insert_severity_score(score: dict) -> dict:
    resp = (
        get_service_client()
        .table("severity_scores")
        .insert(score)
        .execute()
    )
    return resp.data[0]


def get_severity_scores(
    brand_id: str,
    level: str | None = None,
    since: datetime | None = None,
    limit: int = 200,
) -> list[dict]:
    q = (
        get_service_client()
        .table("severity_scores")
        .select("*")
        .eq("brand_id", brand_id)
        .order("computed_at", desc=True)
        .limit(limit)
    )
    if level:
        q = q.eq("severity_level", level)
    if since:
        q = q.gte("computed_at", since.isoformat())
    return q.execute().data


# ---------------------------------------------------------------------------
# Fulfillment Results
# ---------------------------------------------------------------------------

def insert_fulfillment_result(result: dict) -> dict:
    resp = (
        get_service_client()
        .table("fulfillment_results")
        .insert(result)
        .execute()
    )
    return resp.data[0]


# ---------------------------------------------------------------------------
# Analysis Runs
# ---------------------------------------------------------------------------

def insert_analysis_run(run: dict) -> dict:
    resp = (
        get_service_client()
        .table("analysis_runs")
        .insert(run)
        .execute()
    )
    return resp.data[0]


def get_latest_analysis(brand_id: str) -> dict | None:
    resp = (
        get_service_client()
        .table("analysis_runs")
        .select("*")
        .eq("brand_id", brand_id)
        .order("ran_at", desc=True)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------

def get_mention_count_since(
    brand_id: str, since: datetime, platform: str | None = None
) -> int:
    q = (
        get_service_client()
        .table("mentions")
        .select("id", count="exact")
        .eq("brand_id", brand_id)
        .gte("scraped_at", since.isoformat())
    )
    if platform:
        q = q.eq("platform", platform)
    return q.execute().count or 0


def get_hourly_mention_rate(brand_id: str, last_hours: int = 2) -> float:
    since = datetime.utcnow().replace(
        microsecond=0
    ) - __import__("datetime").timedelta(hours=last_hours)
    count = get_mention_count_since(brand_id, since)
    return count / max(last_hours, 1)


def get_avg_hourly_rate(brand_id: str, last_days: int = 7) -> float:
    since = datetime.utcnow().replace(
        microsecond=0
    ) - __import__("datetime").timedelta(days=last_days)
    count = get_mention_count_since(brand_id, since)
    total_hours = last_days * 24
    return count / max(total_hours, 1)
