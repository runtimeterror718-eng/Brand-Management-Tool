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

# ---------- Telegram Phase 2 ----------
TELEGRAM_CHANNEL_CLASSIFICATION_LABELS = (
    "official",
    "likely_official",
    "fan_unofficial",
    "suspicious_fake",
    "irrelevant",
)

TELEGRAM_MONITORED_CLASSIFICATION_LABELS = frozenset({
    "official",
    "likely_official",
    "fan_unofficial",
    "suspicious_fake",
})

TELEGRAM_MESSAGE_RISK_LABELS = (
    "safe",
    "suspicious",
    "copyright_infringement",
)

TELEGRAM_MESSAGE_SUSPICIOUS_RISK_LABELS = frozenset({
    "suspicious",
    "copyright_infringement",
})

TELEGRAM_CHANNEL_FULFILMENT_LLM_BATCH_SIZE = 5

TELEGRAM_MESSAGE_ALLOWED_RISK_FLAGS = frozenset(
    {
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
        "irrelevant",
    }
)

# Ordered seed list for discovery. Ambiguous/noisy terms are intentionally later.
TELEGRAM_DISCOVERY_SEED_KEYWORDS = (
    "physics wallah",
    "physics wala",
    "physicswallah",
    "physicswala",
    "pw live",
    "pw arjuna",
    "pw lakshya",
    "pw udaan",
    "pw yakeen",
    "pw prayas",
    "jee wallah",
    "neet wallah",
    "pw vidyapeeth",
    "pw pathshala",
    "alakh pandey",
    "alakh sir",
    "prateek maheshwari",
    "samriddhi maam",
    "samridhi mam",
    "pw",
)

TELEGRAM_AMBIGUOUS_DISCOVERY_TERMS = frozenset({
    "pw",
})

# ---------- YouTube Unofficial Discovery ----------
YOUTUBE_UNOFFICIAL_MAX_RESULTS_PER_KEYWORD_DEFAULT = 25
YOUTUBE_UNOFFICIAL_PUBLISHED_AFTER_DAYS_DEFAULT = 90  # 3 months backfill window
YOUTUBE_UNOFFICIAL_MAX_COMMENTS_PER_FLAGGED_VIDEO_DEFAULT = 10000  # No cap — scrape all comments

# Confirmed official PW channel IDs
YOUTUBE_OFFICIAL_CHANNEL_IDS = frozenset({
    "UCiGyWN6DEbnj2alu7iapuKQ",
    "UCphU2bAGmw304CFAzy0Enuw",
    "UCVJU_IChPMOe8RWkdVQjtfQ",
    "UCD16eo98AXl-9T61Xd711kQ",
    "UCqOy6oOu6RPJNHYQ8f_Ybvg",
    "UCFLdnJ7lV_s64MKTXNGp-EQ",
    "UCw_wyYw3iQs700rj5WHm9lQ",
    "UCmgagjlXOka3jbkMbMfcR7w",
    "UC0CrfC0KPA4zWwRBLVVsJcg",
    "UCVs9oKvZbUe0Mq9zBL62ZSw",
    "UCYlQPz_ONrXppNXZ89P3zyQ",
    "UCQCflB1jT0LitJ6NX9K9bzA",
    "UC8zCnnfhz-dvIpVdZ1CheuA",
    "UCFR8HF5NLtn_8jm7d_zR6fQ",
    "UCF7yooS3ACc57ynnzS1E1GA",
    "UCyxvpKdzvW3qxIabJ2RBPyA",
    "UCNWa2OGtS7X9NggnHlib33g",
    "UCPqeXfZxstA5RzIP4OjuAKw",
    "UCko6jJyo-wUQmWhjGNAIrwg",
    "UClG5nU1WppLzVulRFw4HArQ",
    "UCiNxAFkm3-5hhyJQfeZ6GNA",
    "UCEB_nGXf1l72k3-Jg92MTSw",
    "UCjEIM2LEUt1tz3i6Wx5vEsQ",
    "UC4cVyGXNXdec--qdEJVhdFQ",
    "UCeex8hXWbegjhnWBtiT6I9g",
    "UCG3EvCF6dD2Hc-HddZrt2fQ",
    "UCE3icW9aKl2zYQ8BQj9qYTg",
    "UCt8GXsKNVgThd_R7x7KPskw",
    "UCcaEVV7A47J4k9GFcqOOYkg",
    "UCg5_K50hLTKerLkSE7I1yWQ",
    "UC8OCoGX9tmMneOzIFUTWq2Q",
    "UCXldsq6PYUwRajkYLzbiXVA",
    "UC9PoSJoftLvEnXT-PtQ5Wtw",
    "UCGrrw9x3_B_fItUIBMvqAUw",
    "UCuGWIkiNaWjsCqybgxGuxfg",
    "UCOsV75fSUr8gnMbhx-Qh3Lg",
    "UCOGnjpVWVV2ixP2S9Pq5afQ",
    "UCWWEvCschv0T0rtou4VaKGw",
    "UCFLLwUH0-IbbzpdbHUByYeQ",
    "UCDrf0V4fcBr5FlCtKwvpfwA",
    "UCn5N03prvdzaZxEwq3AtHAw",
    "UCkifxhW4AprsqsiGQWMMVKg",
    "UCwUqDlLUrwhPrnXA5bG5cnw",
    "UC2amkJX5zDyQJ0mDajAWRSA",
    "UCHtjntUA4GPG9mjRe3b0s8Q",
    "UCSlWl53e-KVWc-DKhHqA4IA",
    "UCWy6Jm0FP5fZK2wEDU5WCPA",
    "UCeicdzysLwCglf7W0I9y4kA",
    "UCxQJj0F-N3eSAILu__OR75w",
    "UChXp1WxnWo_Ps-7ybd5OZmQ",
    "UC2-z_9WyFEhzV0XaLhCpNxQ",
    "UCZPJKEqdaXCM9U-x6_1Ik7w",
    "UCP2j7peMYYFgrRnN0yRL_rg",
    "UCj2TV_kFKTy7Vn4vCFO2IJg",
    "UCcXUY9NSMyYbkOvUD97CUmA",
    "UC1AbKK0GztswOiUnbGfu3GQ",
})

# Handles are normalized to lowercase without leading '@'.
YOUTUBE_OFFICIAL_CHANNEL_HANDLES = frozenset({
    "vidyapeethpw",
    "pwvidyapeeth-delhincr",
    "pwvidyapeethtamilnadu",
    "pwvidyapeeth-neet",
    "pwvidyapeethlucknow_",
    "pwvidyapeethbihar",
    "pwvidyapeethup",
    "pw_foundationvp",
    "pwvidyapeethpathshala",
})

# Suspected official channels (kept separate so filters can choose strict/lenient mode).
YOUTUBE_OFFICIAL_CHANNEL_IDS_SUSPECTED = frozenset({
    "UCxXN-T87vvcpFeXKRSvx7MQ",
})

YOUTUBE_OFFICIAL_CHANNEL_HANDLES_SUSPECTED = frozenset({
    "pwvidyapeethpatna",
    "patna.pwvidyapeeth",
})

YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL = (
    YOUTUBE_OFFICIAL_CHANNEL_IDS | YOUTUBE_OFFICIAL_CHANNEL_IDS_SUSPECTED
)
YOUTUBE_OFFICIAL_CHANNEL_HANDLES_ALL = (
    YOUTUBE_OFFICIAL_CHANNEL_HANDLES | YOUTUBE_OFFICIAL_CHANNEL_HANDLES_SUSPECTED
)

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
