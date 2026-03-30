# Esha Context Guard (Read First)

## Purpose
This file defines the execution boundary for Codex when working for **Esha** in this repository.

Default rule: Codex should only work in Esha-owned platform areas unless the prompt explicitly says otherwise.

## Product Snapshot
- System: PW Brand Management / PR Intelligence
- Data storage: Supabase
- Runtime/deployment: Railway + ngrok
- UI: React (`frontend/`)

## Ownership Map (Channel End-to-End)
- YouTube Analysis -> Esha
- Telegram Analysis -> Esha
- Facebook (TBD) -> Esha
- LinkedIn (TBD) -> Esha
- Instagram Analysis -> Abhishek
- Reddit Analysis -> Abhishek
- SEO Data (LT KWs and News) -> Abhishek
- X -> Abhishek

Note: in this codebase, X is currently represented as `twitter` (`scrapers/twitter.py`).

## Esha Editable Scope (Default)
Primary Esha platform files:
- `scrapers/youtube.py`
- `scrapers/telegram.py`
- `scrapers/facebook.py`
- `scrapers/linkedin.py`

Allowed supporting files only when required for Esha channels:
- `config/constants.py` (only Esha-platform constants/limits)
- `workers/schedule.py` (only YouTube/Telegram/Facebook/LinkedIn schedule entries)
- `search/filters.py` (only platform-list adjustments tied to Esha channels)
- `config/settings.py` (only Esha-channel env vars)

## Out-of-Scope by Default (Do Not Edit)
Abhishek-owned platform files:
- `scrapers/instagram.py`
- `scrapers/reddit.py`
- `scrapers/seo_news.py`
- `scrapers/twitter.py`

Also out-of-scope unless explicitly requested:
- `analysis/`, `severity/`, `alerts/`, `workers/tasks.py`, `brand/`, `storage/`, `transcription/`, `frontend/`

## Codex Execution Rules for Esha
1. Read this file first before doing any work.
2. Keep changes scoped to Esha-owned files.
3. If a task requires editing Abhishek-owned files, stop and ask for explicit approval.
4. Prefer smallest possible patch in one bounded area.
5. Do not refactor unrelated modules during Esha tasks.
6. Do not run destructive commands.
7. No commit/branch/push unless explicitly requested.

## Low-Context Prompt Pattern
Use this format for future Esha prompts:
- "Read `context.md` first."
- "Edit only: <exact file paths>."
- "Do not touch: <explicit exclusions>."
- "Goal: <single scoped objective>."

Example:
"Read `context.md`. Update only `scrapers/telegram.py` to improve retry handling for Telegram search. Do not edit any Abhishek-owned scraper or shared analysis modules."

## Override Rule
If a future prompt says to work outside Esha scope, that prompt must clearly list the non-Esha file paths to edit.
Without explicit path override, this context file is the source of truth.
