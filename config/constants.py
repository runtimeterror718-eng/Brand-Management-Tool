"""
Constants: rate limits, fulfillment thresholds, severity weights, platform configs.
"""

# ---------- Platforms ----------
PLATFORMS = [
    "youtube",
    "telegram",
    "instagram",
    "reddit",
    "twitter",
    "facebook",
    "linkedin",
    "seo_news",
]

# ---------- Rate Limits (requests per minute) ----------
RATE_LIMITS = {
    "youtube": 60,
    "telegram": 30,
    "instagram": 10,       # aggressive anti-bot
    "reddit": 60,
    "twitter": 50,
    "facebook": 30,
    "linkedin": 10,
    "seo_news": 60,
}

# ---------- Fulfillment Thresholds ----------
FULFILLMENT_PASS_THRESHOLD = 0.6       # minimum score to pass fulfillment
FULFILLMENT_DEFAULT_LANGUAGES = ["en", "hi"]
FULFILLMENT_MIN_ENGAGEMENT = 0         # overridable per search

# ---------- Severity Weights ----------
SEVERITY_WEIGHTS = {
    "sentiment_max": 0.30,
    "engagement_max": 0.25,
    "velocity_max": 0.25,
    "keyword_max": 0.20,
}

SEVERITY_LEVELS = {
    "critical": 0.70,
    "high": 0.50,
    "medium": 0.30,
    "low": 0.0,
}

# ---------- Velocity ----------
VELOCITY_RECENT_HOURS = 2
VELOCITY_BASELINE_DAYS = 7
VELOCITY_SPIKE_DIVISOR = 10

# ---------- Analysis ----------
ANALYSIS_BATCH_SIZE = 500
CLUSTERING_MIN_CLUSTER_SIZE = 5
CLUSTERING_MIN_SAMPLES = 3

# ---------- LLM ----------
LLM_MAX_TOKENS = 4096
LLM_TEMPERATURE = 0.2
LLM_COST_PER_1K_INPUT = 0.003    # Claude Sonnet pricing
LLM_COST_PER_1K_OUTPUT = 0.015

# ---------- Scraper Defaults ----------
SCRAPER_MAX_RETRIES = 3
SCRAPER_BACKOFF_BASE = 2          # seconds, exponential
SCRAPER_REQUEST_TIMEOUT = 30      # seconds
SCRAPER_PROXY_ROTATION_AFTER = 50  # requests before rotating proxy

# ---------- Content Types ----------
CONTENT_TYPES_REQUIRING_TRANSCRIPTION = ("video", "audio", "reel", "voice")
