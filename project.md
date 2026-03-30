# Brand Management Tool - Project Context for LLMs

Last updated: 2026-03-30

## 1) What this project is

This repository is a multi-platform brand intelligence system. It:
- Collects brand mentions from social/news platforms.
- Filters and stores mentions in Supabase.
- Runs a 3-tier analysis pipeline (cleaning, sentiment + clustering, LLM insights).
- Scores mention severity and triggers crisis alerts.
- Exposes data to a React dashboard (directly via Supabase in frontend code).

Core runtime is Python (workers + pipelines) with a React/Vite frontend.

## 2) High-level architecture

Main backend flow:
1. Celery scheduled task triggers `workers.tasks.scrape_platform`.
2. Search runs through `search.engine.search_and_fulfill`.
3. Mentions + fulfillment results are persisted to Supabase.
4. Daily analysis runs via `workers.tasks.run_full_analysis` -> `analysis.pipeline.run_analysis`.
5. Severity is computed and stored via `severity.index.score_mentions`.
6. Crisis detection + routing run via `alerts.detector` and `alerts.router`.
7. Frontend reads Supabase tables (`brands`, `mentions`, `severity_scores`, `analysis_runs`) for dashboard views.

Supporting services:
- Supabase (primary DB)
- Redis (Celery broker/backend + cache fallback logic)
- Anthropic API (insight generation)
- External platform/APIs/libraries per scraper (YouTube, Telegram, Reddit, etc.)

## 3) Repository structure

Top-level:
- `alerts/` crisis detection and Slack/email delivery
- `analysis/` 3-tier analysis pipeline
- `brand/` brand config, health, trend, competitor analytics
- `config/` env settings, constants, Supabase client, Hinglish lexicon
- `scrapers/` platform-specific search/comment extraction
- `search/` request parsing + fulfillment scoring + persistence glue
- `severity/` scoring formula, thresholds, keyword logic
- `storage/` Supabase queries, deduplication, cache
- `transcription/` audio extraction, Whisper transcription, captions
- `workers/` Celery app, schedules, async task orchestration
- `frontend/` React app (Vite + Tailwind + Recharts + Supabase JS)
- `context.md` ownership/scope guardrails used by team workflow

## 4) Key modules and roles

### `workers/`
- `workers/celery_app.py`: Celery app config (Redis broker/result backend).
- `workers/schedule.py`: beat schedules for scrape/analysis/alert/report jobs.
- `workers/tasks.py`: task entrypoints:
  - `scrape_platform`
  - `run_full_analysis`
  - `check_alerts`
  - `send_weekly_report`

### `search/`
- `search/filters.py`: defines `SearchParams` and raw->validated conversion.
- `search/engine.py`:
  - platform searcher registry (`register_searcher`)
  - concurrent search dispatch (`search_all`)
  - persistence + fulfillment in `search_and_fulfill`
- `search/fulfillment.py`: pass/fail scoring criteria and queue flags.

### `scrapers/`
Implemented (at least partially):
- `scrapers/youtube.py`
- `scrapers/telegram.py`
- `scrapers/twitter.py`
- `scrapers/reddit.py`
- `scrapers/instagram.py`
- `scrapers/seo_news.py`

Stub/TODO:
- `scrapers/facebook.py`
- `scrapers/linkedin.py`

Shared infra:
- `scrapers/base.py`: rate limiter, retry/backoff, proxy rotation.

### `analysis/`
- `analysis/pipeline.py`: orchestrates all analysis tiers and persists `analysis_runs`.
- `analysis/cleaner.py`: normalization, spam filtering, language detection, dedup.
- `analysis/sentiment.py`: XLM-RoBERTa sentiment + Hinglish lexicon blending.
- `analysis/clustering.py`: SentenceTransformer embeddings + HDBSCAN clustering.
- `analysis/insights.py`: Anthropic-powered structured report generation.

### `severity/`
- `severity/scorer.py`: formula across sentiment, engagement, velocity, keywords.
- `severity/rules.py`: threshold classification and alert channel rules.
- `severity/keywords.py`: English + Hinglish crisis terms + competitors.
- `severity/index.py`: scoring persistence and brand-level aggregation helpers.

### `alerts/`
- `alerts/detector.py`: crisis signal detection from severity + velocity.
- `alerts/router.py`: channel routing (Slack/email) and orchestration.
- `alerts/slack.py`: Slack webhook payload sender.
- `alerts/email_report.py`: SMTP HTML report sender.

### `storage/`
- `storage/queries.py`: Supabase CRUD/query helpers for all major tables.
- `storage/dedup.py`: MinHash LSH duplicate detection.
- `storage/cache.py`: Redis cache with in-memory fallback.
- `storage/models.py`: dataclass mirrors of table-shaped entities.

### `brand/`
- `brand/monitor.py`: fetch/seed monitored brands.
- `brand/health.py`: weighted health score.
- `brand/trends.py`: weekly trends + velocity spike detection.
- `brand/competitors.py`: mention/sentiment comparison against competitors.

### `transcription/`
- `transcription/extractor.py`: media/audio extraction helpers.
- `transcription/whisper.py`: local Whisper transcription wrapper.
- `transcription/captions.py`: YouTube captions/transcripts.

### `frontend/`
- Routing and pages:
  - `frontend/src/App.jsx`
  - `frontend/src/pages/Dashboard.jsx`
  - `frontend/src/pages/BrandView.jsx`
  - `frontend/src/pages/Search.jsx`
  - `frontend/src/pages/Alerts.jsx`
- Data access:
  - `frontend/src/lib/supabase.js` (direct Supabase reads)
- Visual components:
  - `MentionCard`, `SeverityBadge`, `SentimentChart`, `PlatformBreakdown`

## 5) Data model context (Supabase tables referenced)

Based on storage queries and frontend usage, primary tables are:
- `brands`
- `mentions`
- `fulfillment_results`
- `transcriptions`
- `severity_scores`
- `analysis_runs`

Critical mention fields used across modules:
- identity: `id`, `brand_id`, `platform`
- content: `content_text`, `content_type`, `source_url`, `raw_data`
- author: `author_handle`, `author_name`
- metrics: `engagement_score`, `likes`, `shares`, `comments_count`
- analysis: `language`, `sentiment_score`, `sentiment_label`, `cluster_id`
- timestamps: `published_at`, `scraped_at`

## 6) Configuration and environment

Main config files:
- `config/settings.py` (env loading + typed settings)
- `config/constants.py` (platform list, thresholds, weights, defaults)
- `config/supabase_client.py` (anon + service clients)
- `config/hinglish_lexicon.py` (661-line Hinglish sentiment/crisis lexicon)

Important env vars (from `.env.example` + settings):
- Supabase: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`
- LLM: `ANTHROPIC_API_KEY`, optional `ANTHROPIC_MODEL`
- Platform creds: Telegram, Twitter, Reddit
- Alerts: Slack webhook + SMTP credentials
- Infra: `REDIS_URL`, optional `PROXY_URL`
- Bootstrap: `MONITORED_BRANDS`

## 7) Dev and runtime commands

From `Makefile`:
- Install deps: `make install`
- Download models: `make setup-models`
- Run API (expects `api:app`): `make dev`
- Run worker: `make worker`
- Run beat scheduler: `make beat`
- Run frontend: `make frontend`
- Test target (expects `tests/`): `make test`
- Lint: `make lint`

Also:
- `setup_models.sh` downloads fastText model and pre-caches HF models.

## 8) Ownership and collaboration context

Team guardrails currently live in `context.md`. It defines:
- Platform ownership split (Esha vs Abhishek)
- Default editable scope constraints
- Out-of-scope modules unless explicitly requested

If using this repo context for assisted coding, read `context.md` first when ownership scope matters.

## 9) Current caveats and known gaps (important for LLM reasoning)

1. API server file appears missing:
- `Makefile` references `python -m uvicorn api:app --reload --port 8000`.
- No `api.py` / FastAPI app file was found in current tree.

2. Searcher registration depends on import side effects:
- `register_searcher(...)` is called inside scraper modules.
- There is no obvious bootstrap import of all scrapers in the task flow.
- If scraper modules are not imported before search, `_platform_searchers` can stay empty.

3. Some scrapers are placeholders:
- Facebook and LinkedIn scrapers are TODO stubs returning empty results.

4. Frontend Search page expects backend endpoint:
- `frontend/src/pages/Search.jsx` posts to `/api/search`.
- Without API layer, this path will fail even though dashboard pages can still read Supabase directly.

5. Test scaffold mismatch:
- `make test` expects a `tests/` folder, but none currently exists.

6. A few implementation details likely need review before production hardening:
- Cost math in `analysis/insights.py` uses `LLM_TEMPERATURE` in token cost formula.
- Telegram scraper retry call in `scrapers/telegram.py` passes arguments in a pattern that may not match `_retry` expectations.

## 10) Fast orientation guide for future LLM sessions

If you are a new LLM/session agent, start here:
1. Read `context.md` for scope/ownership boundaries.
2. Read `workers/tasks.py` to see execution entrypoints.
3. Read `search/engine.py` and `analysis/pipeline.py` for core data flow.
4. Read `storage/queries.py` to understand persistence contract.
5. Read `frontend/src/lib/supabase.js` + page files for UI data dependencies.
6. Check caveats in section 9 before implementing new features.

## 11) Practical change map (where to edit for common tasks)

- New platform integration:
  - Add scraper in `scrapers/`
  - Register via `register_searcher`
  - Add platform constants/rate limits in `config/constants.py`
  - Include in schedules (`workers/schedule.py`) as needed

- Fulfillment logic tweaks:
  - `search/fulfillment.py`
  - optionally `search/filters.py` + `config/constants.py`

- Sentiment/analysis improvements:
  - `analysis/sentiment.py`, `analysis/cleaner.py`, `analysis/clustering.py`, `analysis/insights.py`
  - Hinglish behavior lives in `config/hinglish_lexicon.py`

- Severity/alerting policy:
  - `severity/scorer.py`, `severity/rules.py`, `severity/keywords.py`
  - `alerts/detector.py`, `alerts/router.py`

- Dashboard/UI updates:
  - `frontend/src/pages/*`
  - `frontend/src/components/*`
  - `frontend/src/lib/supabase.js`

