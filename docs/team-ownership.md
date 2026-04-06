# Team B Context Guard (Read First)

## Purpose
This file defines the execution boundary for Codex when working for **Team B** in this repository.

Default rule: Codex should only work in Team B-owned platform areas unless the prompt explicitly says otherwise.

## Product Snapshot
- System: PW Brand Management / PR Intelligence
- Data storage: Supabase (project ref: `bieocyzyybjetzornlfw`, region: ap-south-1)
- Runtime/deployment: Railway + ngrok
- UI: React (`frontend/`)
- Task queue: Celery + Redis

## Current State (updated 2026-03-31)
- Supabase schema deployed: 24 tables (brands + 8 platform tables + mentions + severity + analysis)
- Instagram pipeline: LIVE — full scrape→store pipeline in `scrapers/instagram.py` with dedicated Celery task
- Reddit pipeline: LIVE — full scrape→store pipeline in `scrapers/reddit.py` with dedicated Celery task
- YouTube/Telegram/X/SEO: generic scrape path via `scrape_platform` task (no platform-specific table storage yet)
- Facebook/LinkedIn: stub scrapers (TBD)
- Hinglish lexicon: 350+ terms integrated into severity + sentiment

## Ownership Map (Channel End-to-End)
- YouTube Analysis -> Team B
- Telegram Analysis -> Team B
- Facebook (TBD) -> Team B
- LinkedIn (TBD) -> Team B
- Instagram Analysis -> Team A
- Reddit Analysis -> Team A
- SEO Data (LT KWs and News) -> Team A
- X -> Team A

Note: in this codebase, X is currently represented as `twitter` (`scrapers/twitter.py`).

## Supabase Tables by Owner
Team A tables: `instagram_accounts`, `instagram_posts`, `instagram_comments`, `reddit_posts`, `reddit_comments`, `google_seo_results`, `twitter_tweets`
Team B tables: `youtube_channels`, `youtube_videos`, `youtube_comments`, `telegram_messages`, `facebook_pages`, `facebook_posts`, `facebook_comments`, `facebook_page_insights`, `facebook_post_insights`, `facebook_groups`, `linkedin_posts`
Shared tables: `brands`, `mentions`, `transcriptions`, `severity_scores`, `fulfillment_results`, `analysis_runs`

## Celery Tasks by Owner
Team A tasks: `scrape_instagram`, `scrape_reddit`, `scrape_platform("twitter")`, `scrape_platform("seo_news")`
Team B tasks: `scrape_platform("youtube")`, `scrape_platform("telegram")`
Shared tasks: `run_full_analysis`, `check_alerts`, `send_weekly_report`

## Team B Editable Scope (Default)
Primary Team B platform files:
- `scrapers/youtube.py`
- `scrapers/telegram.py`
- `scrapers/facebook.py`
- `scrapers/linkedin.py`

Allowed supporting files only when required for Team B channels:
- `config/constants.py` (only Team B-platform constants/limits)
- `workers/schedule.py` (only YouTube/Telegram/Facebook/LinkedIn schedule entries)
- `search/filters.py` (only platform-list adjustments tied to Team B channels)
- `config/settings.py` (only Team B-channel env vars)

## Out-of-Scope by Default (Do Not Edit)
Team A-owned platform files:
- `scrapers/instagram.py`
- `scrapers/reddit.py`
- `scrapers/seo_news.py`
- `scrapers/twitter.py`

Also out-of-scope unless explicitly requested:
- `analysis/`, `severity/`, `alerts/`, `workers/tasks.py`, `brand/`, `storage/`, `transcription/`, `frontend/`

## Codex Execution Rules for Team B
1. Read this file first before doing any work.
2. Keep changes scoped to Team B-owned files.
3. If a task requires editing Team A-owned files, stop and ask for explicit approval.
4. Prefer smallest possible patch in one bounded area.
5. Do not refactor unrelated modules during Team B tasks.
6. Do not run destructive commands.
7. No commit/branch/push unless explicitly requested.

## Low-Context Prompt Pattern
Use this format for future Team B prompts:
- "Read `context.md` first."
- "Edit only: <exact file paths>."
- "Do not touch: <explicit exclusions>."
- "Goal: <single scoped objective>."

Example:
"Read `context.md`. Update only `scrapers/telegram.py` to improve retry handling for Telegram search. Do not edit any Team A-owned scraper or shared analysis modules."

## Override Rule
If a future prompt says to work outside Team B scope, that prompt must clearly list the non-Team B file paths to edit.
Without explicit path override, this context file is the source of truth.
