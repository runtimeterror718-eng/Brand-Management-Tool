"""
Caching layer using Redis.
Falls back to an in-memory dict when Redis is unavailable (dev mode).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis

from config.settings import REDIS_URL

logger = logging.getLogger(__name__)

_redis: redis.Redis | None = None
_fallback: dict[str, str] = {}  # in-memory fallback for dev


def _get_redis() -> redis.Redis | None:
    global _redis
    if _redis is None:
        try:
            _redis = redis.from_url(REDIS_URL, decode_responses=True)
            _redis.ping()
        except Exception:
            logger.warning("Redis unavailable — using in-memory fallback cache")
            _redis = None
    return _redis


def cache_get(key: str) -> Any | None:
    r = _get_redis()
    if r:
        raw = r.get(key)
        return json.loads(raw) if raw else None
    return json.loads(_fallback[key]) if key in _fallback else None


def cache_set(key: str, value: Any, ttl_seconds: int = 3600) -> None:
    raw = json.dumps(value, default=str)
    r = _get_redis()
    if r:
        r.set(key, raw, ex=ttl_seconds)
    else:
        _fallback[key] = raw


def cache_delete(key: str) -> None:
    r = _get_redis()
    if r:
        r.delete(key)
    else:
        _fallback.pop(key, None)
