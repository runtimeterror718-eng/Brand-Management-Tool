"""
Data models mirroring Supabase tables.
These are plain dataclasses used across the codebase — not an ORM.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Brand:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    keywords: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    created_at: datetime | None = None


@dataclass
class Mention:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str = ""
    platform: str = ""
    content_text: str = ""
    content_type: str = "text"
    author_handle: str = ""
    author_name: str = ""
    engagement_score: int = 0
    likes: int = 0
    shares: int = 0
    comments_count: int = 0
    sentiment_score: float | None = None
    sentiment_label: str | None = None
    language: str | None = None
    cluster_id: int | None = None
    theme: str | None = None
    source_url: str = ""
    published_at: datetime | None = None
    scraped_at: datetime | None = None
    duplicate_of: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Transcription:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mention_id: str = ""
    source_type: str = ""
    transcript_text: str = ""
    language: str = ""
    duration_seconds: int = 0
    brand_mentions: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass
class SeverityScore:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mention_id: str = ""
    brand_id: str = ""
    severity_level: str = "low"
    severity_score: float = 0.0
    sentiment_component: float = 0.0
    engagement_component: float = 0.0
    velocity_component: float = 0.0
    keyword_component: float = 0.0
    computed_at: datetime | None = None


@dataclass
class FulfillmentResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    search_query: dict[str, Any] = field(default_factory=dict)
    mention_id: str = ""
    passed: bool = False
    score: float = 0.0
    criteria_met: dict[str, bool] = field(default_factory=dict)
    queued_for_scraping: bool = False
    queued_for_transcription: bool = False
    evaluated_at: datetime | None = None


@dataclass
class AnalysisRun:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str = ""
    total_mentions: int = 0
    overall_sentiment: float = 0.0
    cluster_count: int = 0
    themes: dict[str, Any] = field(default_factory=dict)
    risks: dict[str, Any] = field(default_factory=dict)
    opportunities: dict[str, Any] = field(default_factory=dict)
    severity_summary: dict[str, Any] = field(default_factory=dict)
    llm_cost_usd: float = 0.0
    ran_at: datetime | None = None


@dataclass
class TelegramChannel:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str | None = None
    channel_id: str = ""
    channel_username: str | None = None
    channel_title: str | None = None
    channel_type: str | None = None
    discovery_keyword: str | None = None
    discovery_source: str = "keyword_search"
    public_url: str | None = None
    is_verified: bool | None = None
    is_scam: bool | None = None
    is_fake: bool | None = None
    participants_count: int | None = None
    live_test: bool | None = None
    live_test_run_at: datetime | None = None
    channel_created_at: datetime | None = None
    channel_description: str | None = None
    message_count_7d: int | None = None
    llm_classification_response: dict[str, Any] | None = None
    classification_label: str | None = None
    should_monitor: bool | None = None
    historical_data: bool | None = None
    last_checked_at: datetime | None = None
    last_message_id: str | None = None
    last_message_timestamp: datetime | None = None
    message_risk_rollup: dict[str, Any] = field(default_factory=dict)
    message_risk_rollup_at: datetime | None = None
    first_discovered_at: datetime | None = None
    updated_at: datetime | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TelegramMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    brand_id: str | None = None
    telegram_channel_id: str | None = None
    channel_id: str | None = None
    channel_name: str | None = None
    channel_username: str | None = None
    message_id: str | None = None
    message_text: str | None = None
    media_type: str | None = None
    media_base64: str | None = None
    media_mime_type: str | None = None
    media_file_name: str | None = None
    media_file_size_bytes: int | None = None
    media_downloaded_at: datetime | None = None
    media_metadata: dict[str, Any] = field(default_factory=dict)
    sender_username: str | None = None
    sender_id: str | None = None
    views: int = 0
    forwards_count: int = 0
    reply_to_message_id: str | None = None
    reactions: dict[str, Any] = field(default_factory=dict)
    message_timestamp: datetime | None = None
    message_url: str | None = None
    is_pinned: bool = False
    discovery_keyword: str | None = None
    discovery_source: str = "keyword_search"
    llm_analysis_response: dict[str, Any] = field(default_factory=dict)
    risk_label: str | None = None
    risk_score: float | None = None
    is_suspicious: bool = False
    risk_flags: dict[str, Any] = field(default_factory=dict)
    analyzed_at: datetime | None = None
    scraped_at: datetime | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)
