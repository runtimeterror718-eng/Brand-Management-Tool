# OVAL — Brand Intelligence Platform

## What This Is
Multi-platform brand monitoring system for Physics Wallah (PW). Scrapes 8 platforms, runs AI analysis, scores severity, triggers alerts, and serves a Next.js dashboard.

## Build & Run Commands
```bash
make setup            # Full install (deps + Playwright + NLP models)
make worker           # Celery worker
make beat             # Celery beat scheduler
make frontend         # Next.js dashboard (localhost:3000)
make test             # pytest tests/ -v
make lint             # ruff check .
make clean            # Remove __pycache__ and build artifacts
```

### Frontend (BrandScope - Next.js)
```bash
cd brandscope && npm install && npm run dev   # Dev server on :3000
cd brandscope && npm run build                # Production build
```

## Architecture

### Backend Flow
1. Celery beat triggers `workers.tasks.scrape_platform`
2. Search dispatches via `search.engine.search_and_fulfill`
3. Mentions persisted to Supabase
4. Daily analysis: `workers.tasks.run_full_analysis` -> `analysis.pipeline.run_analysis`
5. Severity scored via `severity.index.score_mentions`
6. Crisis detection via `alerts.detector` + `alerts.router`
7. Dashboard reads Supabase directly

### Services
- **Database**: Supabase (PostgreSQL, ap-south-1)
- **Queue**: Celery + Redis
- **LLM**: Anthropic API (insights generation)
- **Frontend**: Next.js 14 + TypeScript + Tailwind (in `brandscope/`)

## Repository Structure
```
alerts/              # Crisis detection, Slack/email delivery
analysis/            # 3-tier pipeline: clean -> sentiment/cluster -> LLM insights
brand/               # Brand config, health scores, trends, competitor analytics
brandscope/          # Next.js 14 dashboard (TypeScript + Tailwind)
config/              # Settings, constants, Supabase client, Hinglish lexicon
design-system/       # UI design specs (brandscope/)
docs/                # All project documentation
  ├── product-spec.md         # Product vision & requirements
  ├── system-architecture.md  # Full system architecture
  ├── onboarding.md           # Module reference & orientation
  ├── team-ownership.md       # Team ownership boundaries
  ├── changelog-esha.md       # YouTube/Telegram changelog (Team B)
  └── changelog-telegram.md   # Telegram MVP implementation notes
scrapers/            # Platform-specific scrapers (IG, Reddit, YT, Telegram, X, SEO)
scripts/             # Utility scripts, backfills, setup_models.sh
secrets/             # Credentials & session files (gitignored)
search/              # Request parsing, fulfillment scoring, persistence
severity/            # Scoring formula, thresholds, crisis keywords
storage/             # Supabase CRUD, dedup (MinHash LSH), Redis cache
  └── sql/           # Schema definitions & migrations
tests/               # Test suite
transcription/       # Audio extraction, Whisper, YouTube captions
workers/             # Celery app, beat schedules, task orchestration
```

## Coding Standards

### Python
- Python 3.11+ required
- Use type hints for function signatures
- Follow existing patterns in each module (dataclasses in `storage/models.py`, registry pattern in `search/engine.py`)
- Hinglish/Hindi text handling is critical — always consider `config/hinglish_lexicon.py`

### Frontend (brandscope/)
- Next.js 14 App Router with TypeScript
- Tailwind CSS for styling
- Supabase JS client for data access
- Components in `src/app/` following Next.js app directory conventions

### General
- Environment variables loaded via `config/settings.py` — never hardcode secrets
- All platform scrapers must handle rate limiting via `scrapers/base.py`
- Deduplication runs through `storage/dedup.py` (MinHash LSH)

## Data Model
Core pipeline: `brands -> mentions -> {fulfillment_results, transcriptions, severity_scores} -> analysis_runs`

Platform tables (landing/raw): `instagram_posts`, `reddit_posts`, `youtube_videos`, `telegram_messages`, `twitter_tweets`, `google_seo_results`, etc.

## Team Ownership
- **Team A**: Instagram, Reddit, SEO/News, X scrapers
- **Team B**: YouTube, Telegram, Facebook, LinkedIn scrapers
- **Shared**: UI/dashboard, storage layer, analysis pipeline

See `docs/team-ownership.md` for detailed ownership boundaries.

## Environment Configuration
Environment is split into two layers:
- **`.env`** — Non-secret config: tuning params, model names, service URLs, feature flags
- **`secrets/.env.keys`** — All API keys, passwords, tokens (gitignored)
- **`secrets/.env.keys.example`** — Template showing which keys are needed (committed)

`config/settings.py` loads `.env` first, then `secrets/.env.keys` overrides with real credentials.

## Known Caveats
- Facebook/LinkedIn scrapers are stubs (TODO)
- Scraper registration uses import side effects (`register_searcher`)
- `api.py` FastAPI app referenced in Makefile may not exist yet
