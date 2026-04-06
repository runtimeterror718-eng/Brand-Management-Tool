# OVAL - Brand Intelligence Platform

> **See what they say before it spreads.**

OVAL is a RAG-powered brand intelligence platform that monitors mentions across **8 platforms** in real-time, classifies each using AI for sentiment, severity, and issue type, and auto-routes action items to the right team -- before a crisis hits Google.

---

## The Problem

A parent searches "physics wallah" on Google. The first autocomplete? **"physics wallah scam."** Enrollment lost before the brand team even knew there was a problem.

- **6,000+ mentions** across 5+ platforms at any given time
- **10-person brand team** can't read them all
- Existing tools (Brandwatch, Meltwater, Google Alerts) **can't understand Hinglish** like "paisa doob gaya" or "quality ghatiya"
- Generic social listening shows mentions but doesn't tell you **what to do** or **which team** should handle it

## What OVAL Does

| Capability | Detail |
|---|---|
| **Multi-Platform Monitoring** | Instagram, Reddit, YouTube, Telegram, X/Twitter, Google SEO, Facebook, LinkedIn |
| **AI Classification** | Every mention scored for sentiment, severity, issue type using GPT-4o + Claude |
| **Hinglish-Native** | 661-term Hindi/Hinglish lexicon for accurate Indian social media analysis |
| **Crisis Detection** | Severity scoring with velocity spike detection -- alerts 6 hours before Google autocomplete changes |
| **Action Routing** | Auto-routes issues to specific departments (PR, Legal, Product, HR) |
| **RAG Insights** | Grounded in real quotes, not LLM hallucinations |
| **Live Dashboard** | Next.js 14 command center with real-time metrics |

---

## Architecture

```
                    Celery Beat (Scheduler)
                           |
                    workers/tasks.py
                           |
              +------------+-------------+
              |                          |
        scrapers/*                 analysis/*
   (8 platform scrapers)     (sentiment, clustering,
              |                 LLM insights)
              |                          |
        search/engine.py          severity/scorer.py
   (fulfillment scoring)      (crisis scoring)
              |                          |
              +--------- Supabase -------+
                     (PostgreSQL)
                           |
                    oval/
                (Next.js 14 Dashboard)
```

### Backend Pipeline
1. **Scrape** - Celery workers collect mentions from 8 platforms
2. **Fulfill** - Search engine scores and filters results
3. **Analyze** - 3-tier pipeline: clean -> sentiment/cluster -> LLM insights
4. **Score** - Severity formula across sentiment, engagement, velocity, keywords
5. **Alert** - Crisis detection triggers Slack/email routing
6. **Serve** - Next.js dashboard reads Supabase directly

### Tech Stack
- **Backend**: Python 3.11+, Celery, Redis
- **Database**: Supabase (PostgreSQL)
- **LLM**: Anthropic Claude + OpenAI GPT-4o-mini + Azure OpenAI
- **NLP**: XLM-RoBERTa (sentiment), SentenceTransformers (embeddings), HDBSCAN (clustering)
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Transcription**: Whisper (audio/video mentions)

---

## Repository Structure

```
.
├── alerts/              # Crisis detection, Slack/email routing
├── analysis/            # 3-tier AI pipeline (clean -> cluster -> insights)
├── brand/               # Brand config, health scores, trends, competitors
├── oval/          # Next.js 14 dashboard (TypeScript + Tailwind)
├── config/              # Settings, constants, Supabase client, Hinglish lexicon
├── design-system/       # UI design tokens
├── docs/                # Product spec, architecture, team ownership
├── scrapers/            # Platform scrapers (IG, Reddit, YT, Telegram, X, SEO)
├── scripts/             # Utility & backfill scripts
├── search/              # Fulfillment scoring + search engine
├── secrets/             # API keys & credentials (gitignored)
├── severity/            # Scoring formula, thresholds, crisis keywords
├── storage/             # Supabase CRUD, dedup (MinHash LSH), Redis cache
│   └── sql/             # Schema definitions & numbered migrations
├── tests/               # Test suite
├── transcription/       # Whisper + YouTube captions
├── workers/             # Celery app, beat schedules, task orchestration
├── .claude/             # Claude Code config (rules, settings, skills)
├── CLAUDE.md            # Project instructions for Claude Code
├── Makefile             # Build targets
└── requirements.txt     # Python dependencies
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Redis (for Celery task queue)

### 1. Install Dependencies
```bash
make setup                # Install Python deps + Playwright + NLP models
cd oval && npm install  # Frontend deps
```

### 2. Configure Environment
```bash
cp .env.example .env                              # Application config (tuning params)
cp secrets/.env.keys.example secrets/.env.keys     # API keys & credentials
cp oval/.env.local.example oval/.env.local  # Frontend env vars

# Fill in your keys:
#   secrets/.env.keys      -> Supabase, OpenAI, YouTube, Telegram, etc.
#   oval/.env.local  -> NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_KEY
```

### 3. Start Redis
```bash
redis-server              # Must be running before workers
```

### 4. Run Services (each in a separate terminal)
```bash
make worker      # Terminal 1: Celery worker (processes scraping/analysis tasks)
make beat        # Terminal 2: Celery beat (schedules recurring tasks)
make frontend    # Terminal 3: Next.js dashboard (localhost:3000)
```

### 5. Run Tests
```bash
make test        # pytest tests/ -v
make lint        # ruff check .
```

---

## Environment Configuration

Environment is split into three files for security:

| File | Purpose | Committed? |
|---|---|---|
| `.env` | Non-secret config: tuning params, model names, service URLs | No (template: `.env.example`) |
| `secrets/.env.keys` | All API keys, passwords, tokens | No (template: `secrets/.env.keys.example`) |
| `oval/.env.local` | Frontend env vars (NEXT_PUBLIC_*) | No (template: `oval/.env.local.example`) |

`config/settings.py` loads `.env` first, then `secrets/.env.keys` overrides with real credentials.

### Required API Keys (minimum to run)
- **Supabase**: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`
- **Supabase (frontend)**: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_KEY`
- **LLM**: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (at least one)
- **Redis**: `REDIS_URL` (defaults to `redis://localhost:6379/0`)

### Optional API Keys (per platform)
- **YouTube**: `YOUTUBE_API_KEY` (Data API v3)
- **Telegram**: `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`
- **Instagram**: `IG_USERNAME`, `IG_PASSWORD` + cookies in `secrets/`
- **Reddit**: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`
- **Google SEO**: `GOOGLE_API_KEY`, `GOOGLE_CSE_ID`
- **Alerts**: `SLACK_WEBHOOK_URL`, `EMAIL_USERNAME`, `EMAIL_PASSWORD`

---

## Platforms Monitored

| Platform | Scraper | Auth | Status |
|---|---|---|---|
| Instagram | `scrapers/instagram.py` | Cookies + Residential Proxy | Live |
| Reddit | `scrapers/reddit.py` | OAuth (client credentials) | Live |
| YouTube | `scrapers/youtube.py` | Data API v3 (4-key rotation) | Live |
| Telegram | `scrapers/telegram.py` | Telethon (MTProto) | Live |
| X / Twitter | `scrapers/twitter.py` | twikit (cookies) | Live |
| Google SEO | `scrapers/seo_news.py` | Google CSE API | Live |
| Facebook | `scrapers/facebook.py` | Meta Graph API | Stub |
| LinkedIn | `scrapers/linkedin.py` | Proxycurl API | Stub |

---

## Data Pipeline

### Supabase Schema (24 tables)
```
brands -> mentions -> {fulfillment_results, transcriptions, severity_scores} -> analysis_runs
```

Platform-specific landing tables: `instagram_posts`, `reddit_posts`, `youtube_videos`, `telegram_messages`, `twitter_tweets`, `google_seo_results`, etc.

### Analysis Pipeline
1. **Cleaning** - Normalization, spam filtering, language detection, dedup (MinHash LSH)
2. **Sentiment** - XLM-RoBERTa multilingual + 661-term Hinglish lexicon blending
3. **Clustering** - SentenceTransformer embeddings + HDBSCAN
4. **Insights** - Anthropic Claude structured report generation (grounded in real quotes)

### Severity Scoring
```
severity = w1*sentiment + w2*engagement + w3*velocity + w4*keywords
```
Components: sentiment polarity, engagement metrics, mention velocity (spike detection), crisis keyword matching (English + Hinglish).

---

## License

Proprietary. All rights reserved.
