"""
Application settings loaded from environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


# --- Supabase ---
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")

# --- LLM ---
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# --- Telegram ---
TELEGRAM_API_ID: str = os.environ.get("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH: str = os.environ.get("TELEGRAM_API_HASH", "")
TELEGRAM_PHONE: str = os.environ.get("TELEGRAM_PHONE", "")

# --- Twitter / X ---
TWITTER_USERNAME: str = os.environ.get("TWITTER_USERNAME", "")
TWITTER_PASSWORD: str = os.environ.get("TWITTER_PASSWORD", "")

# --- Reddit ---
REDDIT_CLIENT_ID: str = os.environ.get("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET: str = os.environ.get("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT: str = os.environ.get("REDDIT_USER_AGENT", "brand-tool/1.0")

# --- Proxies ---
PROXY_URL: str = os.environ.get("PROXY_URL", "")

# --- Alerts ---
SLACK_WEBHOOK_URL: str = os.environ.get("SLACK_WEBHOOK_URL", "")
EMAIL_SMTP_HOST: str = os.environ.get("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT: int = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
EMAIL_USERNAME: str = os.environ.get("EMAIL_USERNAME", "")
EMAIL_PASSWORD: str = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_FROM: str = os.environ.get("EMAIL_FROM", "")
EMAIL_RECIPIENTS: list[str] = [
    e.strip()
    for e in os.environ.get("EMAIL_RECIPIENTS", "").split(",")
    if e.strip()
]

# --- Redis ---
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# --- Brands ---
MONITORED_BRANDS: list[str] = [
    b.strip()
    for b in os.environ.get("MONITORED_BRANDS", "").split(",")
    if b.strip()
]
