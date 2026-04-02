# Telegram Context + Implementation Log

## Telegram MVP Context (Physics Wallah Brand-Risk)
- Scope: discover Telegram public channels by keyword, classify channels, decide `should_monitor`, then ingest new messages and detect suspicious activity.
- Product intent: classification is app logic (not assumed from Telegram metadata alone).
- Required channel labels:
  - `official`
  - `likely_official`
  - `fan_unofficial`
  - `suspicious_fake`
  - `irrelevant`

## Repo Findings Snapshot
- Existing Telegram scraper exists at `scrapers/telegram.py` using Telethon.
- Search registration already wired via `search/engine.py -> _SEARCHER_MODULES["telegram"]`.
- Worker schedule already includes hourly Telegram scrape in `workers/schedule.py`.
- Live DB already had `telegram_messages` but did not have `telegram_channels`.
- Storage query layer had no Telegram raw-table helper functions before this step.
- Existing tests were YouTube-focused; no Telegram storage tests existed.

## Telethon vs Pyrogram Decision (MVP)
- Recommended: **Telethon only** for MVP.
- Why:
  - Already present and integrated in repo (`scrapers/telegram.py`, `requirements.txt`).
  - Avoid dual-client complexity/session drift on day 1.
- Pyrogram can be added later only if a concrete gap appears.

## Auth + Session Requirements
- Required envs already present in settings:
  - `TELEGRAM_API_ID`
  - `TELEGRAM_API_HASH`
  - `TELEGRAM_PHONE`
- Session/auth blockers to address next:
  - persistent session storage path/name strategy (current hardcoded `brand_tool_session`)
  - OTP/2FA flow for first-time login in worker/cron environments
  - session isolation across environments (local/staging/prod)

## Step 001 - 2026-04-01 19:49:27 IST

### Files Inspected
- `context.md`
- `eshachanges.md`
- `scrapers/base.py`
- `scrapers/telegram.py`
- `scrapers/youtube.py`
- `scrapers/reddit.py`
- `scrapers/twitter.py`
- `scrapers/instagram.py`
- `scrapers/facebook.py`
- `scrapers/linkedin.py`
- `scrapers/seo_news.py`
- `workers/tasks.py`
- `workers/schedule.py`
- `workers/celery_app.py`
- `search/engine.py`
- `search/filters.py`
- `search/fulfillment.py`
- `storage/models.py`
- `storage/queries.py`
- `config/settings.py`
- `config/constants.py`
- `.env.example`
- `requirements.txt`
- `brand/monitor.py`
- existing tests under `tests/`

### Files Changed
- `storage/sql/2026-04-01_telegram_mvp_schema.sql` (new)
- `storage/models.py`
- `storage/queries.py`
- `tests/test_storage_queries_telegram.py` (new)
- `telegramcontext.md` (new)

### Summary
- Added an idempotent Telegram MVP schema migration:
  - created `telegram_channels` table for discovery/classification/monitoring state
  - extended `telegram_messages` for channel linkage + risk-analysis fields
  - added Telegram indexes and FK (`telegram_messages.telegram_channel_id -> telegram_channels.id`)
- Applied migration to live Supabase and verified columns/indexes/constraints.
- Added Telegram storage dataclasses and query helpers for channel/message upsert/read paths.
- Added focused unit tests for new Telegram query helpers.

### Blockers / Unknowns
- No centralized migration framework in repo; SQL is currently manual/script-based.
- Telethon session lifecycle is not production-safe yet (OTP/2FA bootstrap + secure persisted session path not finalized).
- `telegram_messages` unique index uses `(brand_id, channel_id, message_id)`:
  - this is good when `brand_id` is populated
  - if `brand_id` is null, Postgres uniqueness semantics can allow duplicates
- LLM channel classification prompt/normalizer and `should_monitor` policy logic are not implemented yet.

### Commands Run
```bash
ls -la
rg --files
sed -n '1,220p' context.md
sed -n '1,260p' eshachanges.md
sed -n '1100,1360p' eshachanges.md
sed -n '1,260p' scrapers/telegram.py
sed -n '1,260p' scrapers/base.py
sed -n '1,260p' search/engine.py
sed -n '1,520p' workers/tasks.py
sed -n '1,220p' workers/schedule.py
sed -n '1,320p' config/settings.py
sed -n '1,260p' config/constants.py
sed -n '1,760p' storage/queries.py
sed -n '1,240p' storage/models.py
sed -n '1,260p' .env.example
sed -n '1,220p' requirements.txt
rg -n "telegram|telegram_messages|platform_ref_id|create table" -S

# Live Supabase schema reads
set -a; source .env.local; set +a; TOKEN=${SUPABASE_ACCESS_TOKEN:-$SECRET_SUPABASE_ACCESS_TOKEN}; ...
curl -sS https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query ...

# Apply migration
set -a; source .env.local; set +a; TOKEN=${SUPABASE_ACCESS_TOKEN:-$SECRET_SUPABASE_ACCESS_TOKEN}; ...
sql=$(cat storage/sql/2026-04-01_telegram_mvp_schema.sql)
curl -sS https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query ...

# Verify indexes/constraints
curl -sS https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query ...

date '+%Y-%m-%d %H:%M:%S %Z'
```

### Test / Smoke Results
- Live schema migration apply: PASS (`[]` response from query API).
- Live schema verification: PASS
  - `telegram_channels` table exists with classification + `should_monitor` + cursor fields.
  - `telegram_messages` has new analysis and linkage columns.
  - indexes created, including unique `(brand_id, channel_id, message_id)`.
  - FK `fk_telegram_messages_channel_row` exists.
- Local tests:
  - `python -m py_compile storage/models.py storage/queries.py tests/test_storage_queries_telegram.py`: PASS
  - `PYTHONPATH=. pytest -q tests/test_storage_queries_telegram.py`: PASS (`2 passed`)

### Next Prompt Recommendation
- "Implement Telegram Phase 2 app logic only (no full monitoring daemon yet): update `scrapers/telegram.py`, `workers/tasks.py`, and `storage/queries.py` to:
  1. run keyword channel discovery into `telegram_channels`,
  2. classify channels into the 5-label taxonomy with stored LLM response,
  3. set `should_monitor`,
  4. ingest new messages for `should_monitor=true` channels into `telegram_messages`,
  5. update channel cursors (`last_message_id`, `last_message_timestamp`, `last_checked_at`).
  Add focused Telegram tests for mapping/classification/upsert behavior."

## Step 002 - 2026-04-01 20:12:53 IST

### Files Changed
- `scrapers/telegram.py`
- `workers/tasks.py`
- `storage/queries.py`
- `config/settings.py`
- `config/constants.py`
- `tests/test_telegram_phase2_logic.py` (new)
- `tests/test_workers_telegram_phase2.py` (new)
- `tests/test_storage_queries_telegram.py`
- `telegramcontext.md`

### Summary
- Implemented Telegram Phase 2 app logic with Telethon-only flow:
  - keyword-based public channel discovery (bounded by keyword + per-keyword limit)
  - normalized channel payload mapping for `telegram_channels`
  - idempotent channel persistence via `upsert_telegram_channels_batch(...)`
  - channel classification into required taxonomy (`official`, `likely_official`, `fan_unofficial`, `suspicious_fake`, `irrelevant`)
  - stored classification payload in `llm_classification_response`
  - deterministic label normalization + `should_monitor` policy mapping
  - monitored-channel message ingestion into `telegram_messages`
  - incremental cursor behavior using `last_message_id` and channel state updates (`last_message_id`, `last_message_timestamp`, `last_checked_at`)
- Classification path is sync/direct (no async batch path) and paginated at pipeline loop level.
- Updated prompt from placeholder wording to a real MVP prompt with strict JSON schema and label rubric.
- Added Telegram config/constants knobs including:
  - `TELEGRAM_DISCOVERY_MAX_RESULTS_PER_KEYWORD` defaulting to `10` for initial tests
  - session name override (`TELEGRAM_SESSION_NAME`)
  - page-size and message-limit controls
- Worker integration:
  - `scrape_platform("telegram")` now routes to Telegram Phase 2 pipeline
  - new callable task `run_telegram_phase2_pipeline(...)` with bounded controls

### Notes On User Constraint Update
- Mid-step adjustment applied:
  - “no async LLM path” honored (sync/direct OpenAI call)
  - “paginated” honored (classification/ingestion loops process in pages)
  - “max discovery limit 10” set as default in settings and used in worker defaults
  - “real prompt” updated to MVP-grade classification prompt

### Commands Run
```bash
# Dependency install (approved)
python -m pip install -r requirements.txt

# Supabase schema verification reads for telegram tables
set -a; source .env.local; set +a; TOKEN=${SUPABASE_ACCESS_TOKEN:-$SECRET_SUPABASE_ACCESS_TOKEN}; ...
curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" ... > /tmp/supabase_columns.json
jq -r '.[] | select(.table_name=="telegram_channels") ...' /tmp/supabase_columns.json
jq -r '.[] | select(.table_name=="telegram_messages") ...' /tmp/supabase_columns.json

# Compile and tests
python -m py_compile scrapers/telegram.py workers/tasks.py storage/queries.py config/settings.py config/constants.py tests/test_telegram_phase2_logic.py tests/test_workers_telegram_phase2.py tests/test_storage_queries_telegram.py
PYTHONPATH=. pytest -q tests/test_telegram_phase2_logic.py tests/test_workers_telegram_phase2.py tests/test_storage_queries_telegram.py

date '+%Y-%m-%d %H:%M:%S %Z'
```

### Test / Smoke Results
- Dependency install: PASS (with pip resolver warnings unrelated to Telegram code path)
- `python -m py_compile ...`: PASS
- `PYTHONPATH=. pytest -q tests/test_telegram_phase2_logic.py tests/test_workers_telegram_phase2.py tests/test_storage_queries_telegram.py`: PASS (`10 passed`)

### Remaining Blockers / Unknowns
- Telethon first-login OTP/2FA bootstrap in non-interactive worker/cron remains unresolved.
- Session storage hardening/isolation strategy still needs finalization across environments.
- Classification prompt is MVP-grade but not yet tuned with production confusion matrix/feedback loop.
- `telegram_messages` uniqueness behavior with nullable `brand_id` still carries duplicate risk if `brand_id` is not set.

### Next Prompt Recommendation
- "Implement Telegram Prompt 3: suspicious-activity / PR-risk analysis over ingested `telegram_messages` (message-level risk labeling + channel-level rollups), including:
  1. message risk prompt + normalization schema,
  2. update `risk_label`, `risk_score`, `is_suspicious`, `risk_flags`, `llm_analysis_response`, `analyzed_at`,
  3. channel-level suspicious-run summary stats,
  4. bounded paginated analyzer task in `workers/tasks.py`,
  5. focused tests for risk parser/normalizer and batch update behavior." 

## Step 003 - 2026-04-01 20:17:33 IST

### Files Changed
- `telegramcontext.md`

### Summary
- Confirmed this run's unit tests/compile checks were local and did not push Telegram rows to Supabase by themselves.
- Per request, pushed a controlled Telegram smoke dataset to Supabase using existing query helpers:
  - inserted/upserted 1 row into `telegram_channels`
  - inserted/upserted 1 row into `telegram_messages`
  - updated channel cursor fields (`last_message_id`, `last_message_timestamp`, `last_checked_at`)
- Verified inserted rows can be read back via storage query helpers.

### Commands Run
```bash
python - <<'PY'
# used storage.queries + brand.monitor to:
# 1) resolve brand
# 2) upsert telegram_channels smoke row
# 3) upsert telegram_messages smoke row
# 4) update cursor fields
# 5) read back inserted rows
PY
```

### Supabase Push Result
- `status`: `ok`
- `brand_id`: `97292c5e-f230-4732-8518-e159349eca07`
- `brand_name`: `PW Live Smoke`
- `inserted_channel_id`: `tg_smoke_20260401144719`
- `inserted_channel_row_id`: `0baa2a20-0f43-412b-8ba1-471079908b93`
- `inserted_message_row_id`: `579d6712-3870-4257-a600-5e01513d5fb5`
- `verified_channel_found`: `true`
- `verified_message_count`: `1`

### Notes
- Discovery/classification/ingestion pipeline task itself was not executed in this step; this was a controlled smoke write for Supabase persistence verification.

## Step 004 - 2026-04-01 20:22:21 IST

### Files Changed
- `telegramcontext.md`

### Summary
- Attempted to run a real Telegram Phase 2 smoke using all configured Telegram discovery keywords with a max insertion cap of 10 channels.
- Run was blocked before discovery started because Telegram API credentials are not configured in runtime env.
- Confirmed missing envs:
  - `TELEGRAM_API_ID`
  - `TELEGRAM_API_HASH`

### Commands Run
```bash
ls -la | rg -n "brand_tool_session|telegram|\.session" -S
python - <<'PY'
# attempted: discover_public_channels(... per_keyword_limit=10),
# classify_channel_row(...), ingest_messages_for_channel(...)
# with max selected channels = 10
PY
rg -n "TELEGRAM|SECRET_TELEGRAM" .env.local .env .env.example -S
env | rg -n "TELEGRAM" -S
```

### Result
- Live discovery/classification/ingestion run: FAIL (blocked)
- Error:
  - `RuntimeError: Missing TELEGRAM_API_ID/TELEGRAM_API_HASH`
- No additional discovery-driven Telegram rows were inserted in this step.

### Blocker
- Telegram credentials are required to run live Telethon discovery and ingestion.

## Step 005 - 2026-04-02 12:11:13 IST

### Files Changed
- `telegramcontext.md`

### Summary
- Completed one-time Telethon session authorization using the provided phone number and OTP.
- Ran live Telegram discovery test using established keyword seed list with:
  - per-keyword request limit: `10`
  - max total channels persisted: `10`
  - random delay between requests: `1` to `5` seconds
- Persisted discovered channel rows to Supabase `telegram_channels` with discovery source `phase2_live_keyword_test`.
- This step focused on channel-name discovery insert only (no message ingestion run in this step).

### Commands Run
```bash
# Authorization check and OTP sign-in
python - <<'PY'
# Telethon connect -> is_user_authorized -> send_code_request/sign_in
PY

# Live discovery run + Supabase upsert
python - <<'PY'
# SearchRequest(q=<keyword>, limit=10)
# random sleep 1..5 sec between requests
# cap unique channels at 10
# upsert_telegram_channels_batch(...)
PY
```

### Live Discovery Insert Result
- `status`: `ok`
- `brand_id`: `97292c5e-f230-4732-8518-e159349eca07`
- `brand_name`: `PW Live Smoke`
- `keywords_considered`: `20`
- `per_keyword_limit`: `10`
- `max_channels_total`: `10`
- `unique_channels_discovered`: `10`
- `channels_persisted`: `10`
- `request_sleep_count`: `1`
- `request_sleep_seconds`: `[2.023]`

### Persisted Channel Name Samples
- `Ummeed Neet Physics Wallah pw` (`@ummeed_neet_pw_physics_wallah`)
- `Mr sir 2026` (`@mr_sir_physics_wallah_neet_2026`)
- `arjuna 2.0 Neet batch physics wallah` (`@arjuna_neet_batch_physics_wallah`)
- `Mr Sir Physics Wallah` (`@pw_mr_sir_neet_physics_wallah`)
- `Physics Wallah - Alakh Pandey (Official)` (`@physics_wallah_official_channel`)
- `@saleemsir_PW` (`@saleem_sir_pw_physics_wallah`)
- `Saleem Sir Physics Wallah PW` (`@saleemsir_physics_wallah_pw`)
- `Physics_Wallah` (`@physics_wallah`)
- `Physics Wala (official)` (`@physics_wala_freelectures`)
- `PW skills physics wala` (`@pwskillshub`)

### Notes
- OTP value was used only for one-time login and is not stored in code.
- Session file `brand_tool_session.session` now exists and is authorized for subsequent non-interactive runs.

## Step 006 - 2026-04-02 12:25:48 IST

### Files Changed
- `scrapers/telegram.py`
- `storage/models.py`
- `storage/sql/2026-04-02_telegram_channel_metadata_split.sql` (new)
- `tests/test_telegram_phase2_logic.py`
- `telegramcontext.md`

### Summary
- Updated discovery-mode channel mapping to write explicit Telegram metadata columns directly:
  - `public_url`
  - `is_verified`
  - `is_scam`
  - `is_fake`
  - `participants_count`
  - `live_test`
  - `live_test_run_at`
- Kept discovery rows free of classification fields:
  - no `classification_label` set during discovery mapping
  - no `llm_classification_response` set during discovery mapping
- Updated classification helpers to read from explicit columns first (with backward compatibility to legacy `channel_metadata` JSON).
- Added a single idempotent SQL migration/backfill for Supabase:
  - adds explicit metadata columns if missing
  - makes `classification_label` nullable with no default
  - backfills new columns from legacy `channel_metadata` JSON
  - clears discovery-only rows (`classification_label`, `llm_classification_response`) where classification was never run

### Commands Run
```bash
# Local validation
python -m py_compile scrapers/telegram.py storage/models.py tests/test_telegram_phase2_logic.py
PYTHONPATH=. pytest -q tests/test_telegram_phase2_logic.py tests/test_storage_queries_telegram.py tests/test_workers_telegram_phase2.py

# Apply Supabase migration/backfill
set -a; source .env.local; set +a
TOKEN=${SUPABASE_ACCESS_TOKEN:-$SECRET_SUPABASE_ACCESS_TOKEN}
PROJECT=${SUPABASE_PROJECT_REF}
sql=$(cat storage/sql/2026-04-02_telegram_channel_metadata_split.sql)
curl -sS "https://api.supabase.com/v1/projects/$PROJECT/database/query" ...

# Verify backfill/column status
curl -sS "https://api.supabase.com/v1/projects/$PROJECT/database/query" ... # aggregate counts
curl -sS "https://api.supabase.com/v1/projects/$PROJECT/database/query" ... # column definitions
curl -sS "https://api.supabase.com/v1/projects/$PROJECT/database/query" ... # sample row values
```

### Test / Smoke Results
- `python -m py_compile scrapers/telegram.py storage/models.py tests/test_telegram_phase2_logic.py`: PASS
- `PYTHONPATH=. pytest -q tests/test_telegram_phase2_logic.py tests/test_storage_queries_telegram.py tests/test_workers_telegram_phase2.py`: PASS (`10 passed`)
- Supabase migration/backfill apply: PASS (`[]` response)
- Supabase verification snapshot:
  - `telegram_channels.total_rows`: `11`
  - `public_url_rows`: `11`
  - `is_verified_rows`: `11`
  - `is_scam_rows`: `11`
  - `is_fake_rows`: `11`
  - `participants_count_rows`: `11`
  - `live_test_rows`: `10`
  - `live_test_run_at_rows`: `10`
  - `classification_label_null_rows`: `10`
  - `llm_response_null_rows`: `10`

### Notes
- One previously classified smoke row remains classified (`classification_label='likely_official'`) as expected.
- Newly discovered rows now show explicit metadata columns populated and classification fields left empty until classification run.

## Step 007 - 2026-04-02 12:32:15 IST

### Files Changed
- `scrapers/telegram.py`
- `storage/models.py`
- `tests/test_telegram_phase2_logic.py`
- `storage/sql/2026-04-02_telegram_drop_channel_metadata_keep_fake_scam_null.sql` (new)
- `telegramcontext.md`

### Summary
- Updated discovery mapping so `is_fake` and `is_scam` are no longer written from Telethon metadata.
- Kept `is_fake` and `is_scam` as nullable DB fields but made them effectively LLM-owned by leaving discovery inserts without those keys.
- Removed backend dependency on legacy `channel_metadata` column in scraper classification helper path.
- Added one idempotent SQL cleanup migration that:
  - sets existing `is_fake` and `is_scam` values to `NULL`
  - drops `telegram_channels.channel_metadata`

### Commands Run
```bash
# Local compile + tests
python -m py_compile scrapers/telegram.py storage/models.py tests/test_telegram_phase2_logic.py
PYTHONPATH=. pytest -q tests/test_telegram_phase2_logic.py tests/test_storage_queries_telegram.py tests/test_workers_telegram_phase2.py

# Apply cleanup migration
set -a; source .env.local; set +a
TOKEN=${SUPABASE_ACCESS_TOKEN:-$SECRET_SUPABASE_ACCESS_TOKEN}
PROJECT=${SUPABASE_PROJECT_REF}
sql=$(cat storage/sql/2026-04-02_telegram_drop_channel_metadata_keep_fake_scam_null.sql)
curl -sS "https://api.supabase.com/v1/projects/$PROJECT/database/query" ...

# Verify schema + null status
curl -sS "https://api.supabase.com/v1/projects/$PROJECT/database/query" ... # information_schema.columns
curl -sS "https://api.supabase.com/v1/projects/$PROJECT/database/query" ... # null-count query
curl -sS "https://api.supabase.com/v1/projects/$PROJECT/database/query" ... # sample rows
```

### Test / Smoke Results
- `python -m py_compile ...`: PASS
- `PYTHONPATH=. pytest -q tests/test_telegram_phase2_logic.py tests/test_storage_queries_telegram.py tests/test_workers_telegram_phase2.py`: PASS (`10 passed`)
- Supabase cleanup migration: PASS (`[]` response)
- Supabase verification:
  - `channel_metadata` column: NOT PRESENT
  - `telegram_channels.total_rows`: `11`
  - `is_fake_null_rows`: `11`
  - `is_scam_null_rows`: `11`

### Notes
- Existing manually classified smoke row remains with `classification_label='likely_official'`.
- Discovery now leaves fake/scam assessment empty for later LLM-based evaluation.

## Step 008 - 2026-04-02 12:44:14 IST

### Files Changed
- `scrapers/telegram.py`
- `config/settings.py`
- `storage/models.py`
- `storage/sql/2026-04-02_telegram_activity_columns.sql` (new)
- `tests/test_telegram_phase2_logic.py`

### Summary
- Added activity fields: `channel_created_at`, `message_count_7d`.
- Added reconnect/auth guard in Telethon client init to fix disconnected-client retries.
- Added activity refresh logic (7-day count + last message timestamp, without using message text).
- Ran one-time backfill for usernames already in Supabase.

### Backfill Result
- Rows considered: `11`
- Refreshed: `10`
- Skipped entity not found: `1` (`pw_smoke_144719`)
- Supabase check: `created_rows=10`, `message_count_rows=10`, `last_msg_rows=11`

## Step 009 - 2026-04-02 12:52:54 IST

### Files Changed
- `scrapers/telegram.py`
- `storage/models.py`
- `storage/sql/2026-04-02_telegram_should_monitor_nullable.sql` (new)

### Summary
- `should_monitor` moved to nullable discovery-default behavior.
- Existing `FALSE` values in Supabase were converted to `NULL`.

### Verification
- `telegram_channels.should_monitor`: nullable, default `NULL`
- counts: `true=1`, `false=0`, `null=10` (total `11`)

## Step 010 - 2026-04-02 13:03:54 IST
- Added discovery fields: `channel_description`, `creator_id`, `creator_username` (+ migration file `2026-04-02_telegram_description_creator_columns.sql`).
- Applied migration on Supabase and ran one live backfill for existing discovered usernames with random sleep `1..5s` between requests.
- Backfill result: `updated=10`, `failed=0`; current DB counts: `description_rows=5`, `creator_id_rows=0`, `creator_username_rows=0` (creator not exposed for these channels in available metadata).

## Step 011 - 2026-04-02 13:14:23 IST
- Removed creator metadata entirely from code/model (`creator_id`, `creator_username`).
- Applied Supabase migration `2026-04-02_telegram_drop_creator_columns.sql`; verification shows only `channel_description` remains.

## Step 012 - 2026-04-02 13:55:41 IST

### Files Changed
- `scrapers/telegram.py`
- `storage/queries.py`
- `workers/tasks.py`
- `tests/test_telegram_fulfilment.py` (new)
- `tests/test_workers_telegram_fulfilment.py` (new)
- `tests/test_storage_queries_telegram.py`
- `telegramcontext.md`

### Summary
- Implemented Telegram channel-level fulfilment pipeline for fake/impersonation/misuse scoring:
  - new fulfilment payload builder with exact required input schema (`brand_name`, `platform`, `task`, `channel` fields).
  - strict fulfilment prompt wiring with synchronous Azure OpenAI request path.
  - strict response normalization for:
    - `classification_label` (required enum)
    - `fake_score_10` (int clamp 0..10)
    - `is_fake`
    - `should_monitor`
    - `confidence`
    - `risk_flags`
    - `reason`
    - `evidence`
  - idempotent writeback to:
    - `llm_classification_response`
    - `classification_label`
    - `should_monitor`
    - `is_fake`
    - optional `fake_score_10` / `confidence` columns when present in row schema.
- Added required verified-account bypass behavior:
  - verified rows are not sent to LLM.
  - fulfilment auto-sets `fake_score_10=0`, `is_fake=false`, and `should_monitor=false`.
  - writeback stores a `verified_auto_bypass` classification record.
- Added manual/cron-safe entrypoints:
  - `run_telegram_channel_fulfilment(...)`
  - `fulfill_discovered_telegram_channels(...)` (alias)
  - worker task: `run_telegram_fulfilment(...)`
- Added storage eligibility query helper:
  - `list_telegram_channels_for_fulfilment(...)` with `brand_id`, `only_unclassified`, `discovered_since_hours`, `limit`, and optional target-channel filters.
- Added focused tests covering payload builder, parser/normalization, score handling, verified bypass, writeback updates, fulfilment summary behavior, worker task arg mapping, and strong-signal fake/fan scenarios.

### Commands Run
```bash
python -m py_compile scrapers/telegram.py storage/queries.py workers/tasks.py tests/test_telegram_fulfilment.py tests/test_workers_telegram_fulfilment.py tests/test_storage_queries_telegram.py
PYTHONPATH=. pytest -q tests/test_telegram_fulfilment.py tests/test_workers_telegram_fulfilment.py tests/test_storage_queries_telegram.py tests/test_telegram_phase2_logic.py tests/test_workers_telegram_phase2.py
date '+%Y-%m-%d %H:%M:%S %Z'
```

### Test / Smoke Results
- `python -m py_compile ...`: PASS
- `PYTHONPATH=. pytest -q tests/test_telegram_fulfilment.py tests/test_workers_telegram_fulfilment.py tests/test_storage_queries_telegram.py tests/test_telegram_phase2_logic.py tests/test_workers_telegram_phase2.py`: PASS (`21 passed`)

### Schema Gaps / Notes
- `telegram_channels` schema in repo migrations does not currently include `fake_score_10` or `confidence` columns.
- Implementation writes those values into `llm_classification_response.normalized` always, and writes to top-level columns only when those columns are present on fetched rows.
- Existing legacy `is_scam` column is not used in this fulfilment pipeline; `is_fake` + `fake_score_10` are used for fake-risk semantics.

### Next Prompt Recommendation
- "Implement Telegram message-level suspicious activity analysis on `telegram_messages` with synchronous LLM risk scoring, strict JSON normalization, `risk_label/risk_score/is_suspicious/risk_flags/llm_analysis_response` writeback, and channel-level risk rollups."

## Step 013 - 2026-04-02 14:32:50 IST

### Files Changed
- `config/constants.py`
- `scrapers/telegram.py`
- `storage/sql/2026-04-02_telegram_channel_fulfilment_score_columns.sql` (new)
- `tests/test_telegram_fulfilment.py`
- `telegramcontext.md`

### Summary
- Updated channel fulfilment execution to process channels in LLM batches of exactly `5`:
  - added batched prompt path (`classify_channels_fulfilment_batch(...)`)
  - added batched fulfilment runner (`classify_telegram_channel_fulfilment_rows_batch(...)`)
  - `run_telegram_channel_fulfilment(...)` now chunks rows in size `5` and reports:
    - `llm_batch_size`
    - `llm_batches_processed`
- Preserved verified-channel bypass in batched mode (verified rows are not sent to LLM and are auto-set to `fake_score_10=0`, `is_fake=false`, `should_monitor=false`).
- Added Supabase schema migration for explicit fulfilment score fields:
  - `telegram_channels.fake_score_10` (`integer`, constrained `0..10`)
  - `telegram_channels.confidence` (`double precision`)
- Ran live Telegram channel fulfilment backfill against Supabase and validated writeback.

### Commands Run
```bash
# Local validation
python -m py_compile scrapers/telegram.py storage/queries.py workers/tasks.py config/constants.py storage/models.py
PYTHONPATH=. pytest -q tests/test_telegram_fulfilment.py tests/test_workers_telegram_fulfilment.py tests/test_storage_queries_telegram.py tests/test_workers_telegram_phase2.py tests/test_telegram_phase2_logic.py
python -m py_compile config/constants.py scrapers/telegram.py storage/queries.py workers/tasks.py storage/models.py tests/test_telegram_fulfilment.py
PYTHONPATH=. pytest -q tests/test_telegram_fulfilment.py tests/test_workers_telegram_fulfilment.py tests/test_storage_queries_telegram.py tests/test_workers_telegram_phase2.py tests/test_telegram_phase2_logic.py

# Supabase schema check + migration + verification
set -a; source .env.local; set +a
curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" ... # check fake_score_10/confidence columns
curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" ... # apply storage/sql/2026-04-02_telegram_channel_fulfilment_score_columns.sql
curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" ... # verify columns exist

# Live backfill run
python - <<'PY'
# run_telegram_channel_fulfilment(... only_unclassified=True ...)
PY
python - <<'PY'
# run_telegram_channel_fulfilment(... only_unclassified=False, force_refulfilment=True ...)
PY

# Supabase post-run verification
curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" ... # aggregate fulfilment counts
curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" ... # sample rows with label/score/status
```

### Live Backfill Result
- Brand: `97292c5e-f230-4732-8518-e159349eca07`
- Explicit re-fulfilment summary:
  - `total_considered`: `10`
  - `classified`: `10`
  - `official`: `1`
  - `fan_unofficial`: `3`
  - `suspicious_fake`: `6`
  - `should_monitor_count`: `9`
  - `failed`: `0`
  - `llm_batch_size`: `5`
  - `llm_batches_processed`: `2`
- Supabase writeback verification:
  - `telegram_channels.total`: `10`
  - `fake_score_10 populated`: `10`
  - `llm_classification_response populated`: `10`
  - `should_monitor=true`: `9`
  - `is_fake=true`: `6`

### Test Results
- Local compile: PASS
- `pytest` suite (Telegram channel fulfilment + related Telegram tests): PASS (`23 passed`)

## Step 014 - 2026-04-02 14:44:29 IST

### Files Changed
- `scrapers/telegram.py`
- `tests/test_telegram_fulfilment.py`
- `telegramcontext.md`

### Summary
- Applied strict business-policy override for channel fulfilment:
  - any **non-verified** channel operating in PW brand/resource naming is force-classified as:
    - `classification_label = suspicious_fake`
    - `fake_score_10 = 10`
    - `is_fake = true`
    - `should_monitor = true`
- Updated fulfilment prompts to include the same hard rule explicitly.
- Re-ran forced live channel re-fulfilment on Supabase.

### Commands Run
```bash
python -m py_compile scrapers/telegram.py tests/test_telegram_fulfilment.py
PYTHONPATH=. pytest -q tests/test_telegram_fulfilment.py tests/test_workers_telegram_fulfilment.py tests/test_storage_queries_telegram.py tests/test_workers_telegram_phase2.py tests/test_telegram_phase2_logic.py

python - <<'PY'
# run_telegram_channel_fulfilment(
#   brand_id='97292c5e-f230-4732-8518-e159349eca07',
#   limit=500,
#   only_unclassified=False,
#   force_refulfilment=True
# )
PY

curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" ... # verify pwskillshub / physics_wala_freelectures rows
```

### Test / Live Results
- `pytest`: PASS (`24 passed`)
- Forced re-fulfilment summary:
  - `total_considered=10`
  - `classified=10`
  - `official=1`
  - `suspicious_fake=9`
  - `fan_unofficial=0`
  - `llm_batch_size=5`
  - `llm_batches_processed=2`
- Verified rows in Supabase now show:
  - `pwskillshub`: `suspicious_fake`, `fake_score_10=10`, `is_fake=true`
  - `physics_wala_freelectures`: `suspicious_fake`, `fake_score_10=10`, `is_fake=true`

## Step 015 - 2026-04-02 15:19:36 IST

### Files Changed
- `scrapers/telegram.py`
- `tests/test_telegram_fulfilment.py`
- `telegramcontext.md`

### Summary
- Reworked fulfilment policy from blanket fake override to social-cue calibration:
  - prompts now explicitly instruct LLM to use PW faculty knowledge and combined cues.
  - non-verified PW-branded channels are no longer auto-10 by default.
  - non-mimic PW-brand channels are calibrated to medium band (`6-7`) and not auto-marked fake.
  - blatant mimicry/reseller channels (`Physics Wala`-style) remain high-risk (`9-10`).
- Updated fallback `is_fake` behavior:
  - defaults to `true` only for higher-confidence high-risk scores (`>=8`) unless explicit.
- Added test coverage for:
  - mimicry high-risk calibration (`>=9`, fake)
  - non-mimic faculty-style channel calibration (`6-7`, not fake)

### Commands Run
```bash
python -m py_compile scrapers/telegram.py tests/test_telegram_fulfilment.py
PYTHONPATH=. pytest -q tests/test_telegram_fulfilment.py tests/test_workers_telegram_fulfilment.py tests/test_storage_queries_telegram.py tests/test_workers_telegram_phase2.py tests/test_telegram_phase2_logic.py

python - <<'PY'
# run_telegram_channel_fulfilment(
#   brand_id='97292c5e-f230-4732-8518-e159349eca07',
#   limit=500,
#   only_unclassified=False,
#   force_refulfilment=True
# )
PY

curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" ... # verify target faculty/mimicry rows
curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" ... # aggregate summary
```

### Test / Live Results
- `pytest`: PASS (`25 passed`)
- Forced re-fulfilment summary:
  - `total_considered=10`
  - `classified=10`
  - `official=1`
  - `fan_unofficial=7`
  - `suspicious_fake=2`
  - `llm_batch_size=5`
  - `llm_batches_processed=2`
- Aggregated Supabase snapshot:
  - `mid_6_7`: `7`
  - `is_fake_true`: `2`
- Verified row outcomes:
  - `mr_sir_physics_wallah_neet_2026`: `fan_unofficial`, `fake_score_10=6`, `is_fake=false`
  - `pw_mr_sir_neet_physics_wallah`: `fan_unofficial`, `fake_score_10=6`, `is_fake=false`
  - `saleemsir_physics_wallah_pw`: `fan_unofficial`, `fake_score_10=6`, `is_fake=false`
  - `physics_wala_freelectures`: `suspicious_fake`, `fake_score_10=10`, `is_fake=true`
  - `pwskillshub` (`PW skills physics wala`): `suspicious_fake`, `fake_score_10=9`, `is_fake=true`

## Step 016 - 2026-04-02 16:02:41 IST

### Files Changed
- `scrapers/telegram.py`
- `workers/tasks.py`
- `storage/sql/2026-04-02_telegram_message_fetch_historical_media.sql` (new)
- `tests/test_telegram_message_fetch.py` (new)
- `tests/test_workers_telegram_message_fetch.py` (new)
- `tests/test_storage_queries_telegram.py`
- `telegramcontext.md`

### Summary
- Implemented Telegram message-fetching pipeline for monitored channels (`should_monitor=true`) with manual + worker/cron-safe entrypoints.
- Added historical-vs-daily windowing policy:
  - `historical_data=false` -> fetch last ~6 months (`historical_6m`)
  - `historical_data=true` -> fetch daily incremental lookback window
- Added channel-level orchestration behavior:
  - message upsert in configurable batches (default `10`)
  - random sleep between batches (default `1-3s`)
  - `5s` gap between consecutive historical channels
- Added media capture path for Telegram messages:
  - attempts media download via Telethon
  - stores base64 payload (`media_base64`) when media is within size limit
  - persists media metadata fields (`mime`, file name, size, downloaded timestamp)
- Added username-join safety:
  - message upsert conflict key now uses `brand_id,channel_username,message_id`
  - fetch path resolves/normalizes channel username from entity and updates channel row when needed
  - channels without resolvable username are skipped with explicit status
- Added worker task:
  - `run_telegram_message_fetch_pipeline(...)` in `workers/tasks.py`
  - supports brand targeting, batch/window/sleep tuning, channel targeting, max media size
- Added SQL migration for schema updates:
  - `telegram_channels.historical_data` boolean + index
  - `telegram_messages` media columns for base64/media metadata
  - switched unique index from `(brand_id, channel_id, message_id)` to `(brand_id, channel_username, message_id)`

### Commands Run
```bash
python -m py_compile scrapers/telegram.py workers/tasks.py storage/queries.py storage/models.py tests/test_telegram_message_fetch.py tests/test_workers_telegram_message_fetch.py tests/test_storage_queries_telegram.py
PYTHONPATH=. pytest -q tests/test_telegram_message_fetch.py tests/test_workers_telegram_message_fetch.py tests/test_storage_queries_telegram.py tests/test_telegram_phase2_logic.py tests/test_workers_telegram_phase2.py tests/test_workers_telegram_fulfilment.py tests/test_telegram_fulfilment.py
```

### Test Results
- `python -m py_compile ...`: PASS
- `pytest` (Telegram-focused suite): PASS (`32 passed`, `2 warnings`)

### Schema Apply Status
- Migration file created locally: `storage/sql/2026-04-02_telegram_message_fetch_historical_media.sql`
- Live Supabase apply not executed in this step.

## Step 017 - 2026-04-02 16:43:12 IST

### Files Changed
- `scrapers/telegram.py`
- `tests/test_telegram_message_fetch.py`
- `telegramcontext.md`

### Summary
- Applied live Supabase migration for Telegram message-fetch schema updates:
  - `telegram_channels.historical_data`
  - media columns in `telegram_messages`
  - unique index moved to `(brand_id, channel_username, message_id)`
- While running first historical backfill, observed runtime JSON serialization failures from Telegram raw payload datetimes.
- Fixed pipeline reliability:
  - added recursive JSON-safe normalization for Telegram raw payloads (`datetime` -> ISO strings)
  - added pre-download media size guard to skip oversized files before download attempt
- Enforced ingestion policy update requested by user:
  - **6-month historical ingestion:** media download disabled
  - **24h daily ingestion:** media download allowed
- Re-ran live pipeline with conservative pacing and completed successfully.

### Commands Run
```bash
# Apply migration to live Supabase
/bin/zsh -lc 'set -a; source .env.local; set +a; ... curl -sS https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query -d "{\"query\": ...storage/sql/2026-04-02_telegram_message_fetch_historical_media.sql ... }"'

# Local patch validation
python -m py_compile scrapers/telegram.py tests/test_telegram_message_fetch.py
PYTHONPATH=. pytest -q tests/test_telegram_message_fetch.py

# Live conservative run
PYTHONPATH=. python - <<'PY'
# asyncio.run(run_telegram_message_fetch_pipeline_for_brand(...))
# batch_size=10, batch_sleep=2..4s, channel_sleep=7s, historical_months=6
PY

# Live post-run verification
# monitored historical status + media checks via Supabase query API
```

### Test Results
- `python -m py_compile ...`: PASS
- `PYTHONPATH=. pytest -q tests/test_telegram_message_fetch.py`: PASS (`7 passed`)

### Live Run Results
- Brand: `PW Live Smoke` (`97292c5e-f230-4732-8518-e159349eca07`)
- Pipeline summary:
  - `channels_considered`: `9`
  - `historical_channels`: `8`
  - `daily_channels`: `1`
  - `channels_completed`: `9`
  - `messages_upserted`: `696`
  - `batches_processed`: `74`
  - `failed`: `0`
- Post-run channel state:
  - `monitored_channels`: `9`
  - `historical_done`: `9`
  - `historical_pending`: `0`
- Media policy verification for this run window:
  - `messages_in_run_window`: `696`
  - `with_media_base64`: `0`
  - `media_skipped_disabled`: `633`

### Notes
- Historical run intentionally skipped media download as requested.
- Future daily 24h runs can retain media capture by keeping `max_media_bytes > 0`.

## Step 018 - 2026-04-02 17:31:42 IST

### Files Changed
- `config/constants.py`
- `config/settings.py`
- `scrapers/telegram.py`
- `workers/tasks.py`
- `storage/sql/2026-04-02_telegram_message_analysis_rollup_columns.sql` (new)
- `tests/test_telegram_message_analysis.py` (new)
- `tests/test_workers_telegram_message_analysis.py` (new)
- `telegramcontext.md`

### Live Supabase Findings
- `telegram_messages` currently contains:
  - core text/message fields
  - channel identifiers/names/usernames
  - `views`, `forwards_count`, `message_timestamp`, `message_url`
  - `media_metadata`
  - raw Telethon payload in `raw_data`
  - analysis fields already available: `risk_label`, `risk_score`, `is_suspicious`, `risk_flags`, `llm_analysis_response`, `analyzed_at`
- Live row count snapshot for `PW Live Smoke`:
  - `total_messages = 697`
  - `unanalyzed_messages = 697`
  - `with_text = 449`
  - `with_message_url = 697`
- Real message patterns seen in data:
  - safe-looking PW promotion with `youtube.com` / `youtu.be`
  - ambiguous off-platform redirects: `c360.me`, `whatsapp.com`, `t.me`, `neet2026.live`
  - clear copyright/piracy signals:
    - `terasharelink.com`
    - `terasharefile.com`
    - `1024terabox.com`
    - “download karlo”, “jaldi”, “deleted soon due to copyright”, “backup alert”
- Important discovery from live samples:
  - risky links are not always visible in plain text
  - some live rows store them inside `raw_data.message.entities[].url` and `raw_data.message.reply_markup.rows[].buttons[].url`

### Summary
- Reworked Telegram message analysis from the old `safe/watch/suspicious` model to the new business taxonomy:
  - `safe`
  - `suspicious`
  - `copyright_infringement`
- Upgraded message-analysis payloads so the LLM now receives:
  - channel name / username / ids
  - channel monitoring context (`classification_label`, `is_fake`, `fake_score_10`, `is_verified`, etc.)
  - message text, views, forwards, reply count, sender username
  - visible links
  - hidden text-URL links
  - button / reply-markup URLs
  - deduped `all_urls`
- Added strong token-saving deterministic rules before LLM:
  - Terabox/Terashare links auto-classify as `copyright_infringement`
  - strong copyright-evasion / competitor-resource patterns auto-classify as `copyright_infringement`
  - clearly PW/YouTube promotional messages can auto-classify as `safe`
- Added batch LLM analysis path with strict JSON schema:
  - historical mode: channel-wise batches (larger default batch size)
  - daily mode: cross-channel batches (smaller default batch size)
- Added manual/cron-safe worker task:
  - `run_telegram_message_analysis(...)`
- Added channel rollup persistence migration and applied it live:
  - `telegram_channels.message_risk_rollup`
  - `telegram_channels.message_risk_rollup_at`
  - `telegram_messages.risk_label` index

### Commands Run
```bash
# Live schema / sample inspection
/bin/zsh -lc 'set -a; source .env.local; set +a; ... curl -sS https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query ...'

# Aggregate live message-domain inspection
PYTHONPATH=. python - <<'PY'
# storage.queries.get_telegram_messages(...)
# extracted outbound links + hidden entity URLs + reply_markup button URLs
PY

# Local validation
python -m py_compile scrapers/telegram.py workers/tasks.py config/constants.py config/settings.py tests/test_telegram_message_analysis.py tests/test_workers_telegram_message_analysis.py
PYTHONPATH=. pytest -q tests/test_telegram_message_analysis.py tests/test_workers_telegram_message_analysis.py tests/test_telegram_message_fetch.py tests/test_workers_telegram_message_fetch.py tests/test_telegram_fulfilment.py tests/test_workers_telegram_fulfilment.py tests/test_telegram_phase2_logic.py tests/test_workers_telegram_phase2.py tests/test_storage_queries_telegram.py

# Live migration apply + verify
/bin/zsh -lc 'set -a; source .env.local; set +a; ... apply storage/sql/2026-04-02_telegram_message_analysis_rollup_columns.sql ...'
/bin/zsh -lc 'set -a; source .env.local; set +a; ... verify telegram_channels message_risk_rollup columns ...'
/bin/zsh -lc 'set -a; source .env.local; set +a; ... verify idx_telegram_messages_risk_label ...'
```

### Test Results
- `python -m py_compile ...`: PASS
- Telegram-focused pytest slice: PASS (`43 passed`, `2 warnings`)

### Live Migration Results
- `telegram_channels.message_risk_rollup`: created
- `telegram_channels.message_risk_rollup_at`: created
- `idx_telegram_messages_risk_label`: created

### Notes
- Message-analysis code is ready for manual runs and cron wiring.
- No paid LLM analysis run was executed in this step; implementation + schema were prepared first to avoid unnecessary token spend before review.

## Step 019 - 2026-04-02 18:08:10 IST

### Files Changed
- `tests/test_telegram_phase2_logic.py`
- `tests/test_telegram_message_analysis.py`
- `telegramcontext.md`

### Summary
- Verified the Telegram message discovery/fetch path already stores the raw Telethon payload intact in `telegram_messages.raw_data.message` using `message.to_dict()` after JSON-safe normalization.
- Added regression coverage to ensure hidden URLs in:
  - `raw_data.message.entities[].url`
  - `raw_data.message.reply_markup.rows[].buttons[].url`
  remain present in stored raw payloads.
- Added regression coverage to ensure AI analysis payloads continue to include the raw fallback structures intact:
  - `message.raw_entities`
  - `message.raw_reply_markup`

### Commands Run
```bash
PYTHONPATH=. pytest -q tests/test_telegram_phase2_logic.py tests/test_telegram_message_analysis.py
```

### Test Results
- Focused Telegram regression slice: PASS (`10 passed`)

### Notes
- No Supabase schema change was needed for this request because the raw message object is already being persisted under `raw_data.message` without truncation.

## Step 020 - 2026-04-02 18:39:20 IST

### Files Changed
- `telegramcontext.md`

### Summary
- Started a live manual Telegram message-analysis backfill run for `PW Live Smoke` in `historical` mode with:
  - `batch_size = 20`
  - `only_unanalyzed = true`
  - `persist_channel_rollup = true`
- Confirmed during the run that writes were happening incrementally to Supabase as chunks completed.
- Per user request, stopped the LLM analysis process gracefully before full completion.

### Commands Run
```bash
/bin/zsh -lc 'set -a; source .env.local; set +a; PYTHONPATH=. python - <<\"PY\"
# run_telegram_message_analysis_pipeline(
#   brand_id=\"97292c5e-f230-4732-8518-e159349eca07\",
#   mode=\"historical\",
#   only_unanalyzed=True,
#   batch_size=20,
#   limit_channels=200,
#   max_messages_per_channel=2000,
#   persist_channel_rollup=True,
# )
PY'

# graceful stop
kill -INT <python_pid>

# post-stop Supabase snapshot
/bin/zsh -lc 'set -a; source .env.local; set +a; PYTHONPATH=. python - <<\"PY\"
# query telegram_messages counts / statuses for brand
PY'
```

### Post-Stop Supabase Snapshot
- `total_messages`: `697`
- `analyzed_at_count`: `225`
- `unanalyzed_count`: `472`
- `status_counts`:
  - `completed`: `213`
  - `policy_rule_bypass`: `12`
  - `missing`: `471`
  - `not_analyzed`: `1`
- `label_counts`:
  - `copyright_infringement`: `121`
  - `suspicious`: `89`
  - `safe`: `15`
  - `missing`: `472`

### Notes
- Completed chunks were preserved because message rows were updated during processing, not only at the very end.
- This run did not include explicit sleep between LLM batches.
- The current historical message-analysis batching was `20` messages per LLM call, not `10`.

## Step 021 - 2026-04-02 18:47:30 IST

### Files Changed
- `scrapers/telegram.py`
- `tests/test_telegram_message_analysis.py`
- `telegramcontext.md`

### Summary
- Hardcoded a `5` second gap between historical Telegram message-analysis LLM requests.
- Implemented the pause in the historical chunk loop only, so:
  - historical mode sleeps `5s` between chunk calls that actually attempt LLM analysis
  - daily mode remains unchanged
- Kept the existing persistence behavior intact:
  - each processed batch still writes message results to `telegram_messages` before the next batch begins
- No live resume run was started in this step.

### Commands Run
```bash
PYTHONPATH=. pytest -q tests/test_telegram_message_analysis.py tests/test_workers_telegram_message_analysis.py
```

### Test Results
- Telegram message-analysis regression slice: PASS (`9 passed`)

### Notes
- The historical throttle is hardcoded in code, not driven from env/config, per request.

## Step 022 - 2026-04-02 19:11:40 IST

### Files Changed
- `telegramcontext.md`

### Summary
- Resumed live Telegram message analysis for `PW Live Smoke` in `historical` mode after introducing the hardcoded `5s` gap between LLM requests.
- The resumed run targeted only pending rows and completed successfully for the real monitored-channel backlog.
- Batch persistence remained incremental: each processed batch was written to `telegram_messages` before the next batch.

### Commands Run
```bash
/bin/zsh -lc 'set -a; source .env.local; set +a; PYTHONPATH=. python - <<\"PY\"
# run_telegram_message_analysis_pipeline(
#   brand_id=\"97292c5e-f230-4732-8518-e159349eca07\",
#   mode=\"historical\",
#   only_unanalyzed=True,
#   batch_size=20,
#   limit_channels=200,
#   max_messages_per_channel=2000,
#   persist_channel_rollup=True,
# )
PY'

/bin/zsh -lc 'set -a; source .env.local; set +a; PYTHONPATH=. python - <<\"PY\"
# inspect remaining rows where _telegram_message_needs_analysis(row) is True
PY'
```

### Resume Run Result
- `phase`: `telegram_message_analysis`
- `mode`: `historical`
- `total_considered`: `471`
- `analyzed`: `471`
- `safe`: `71`
- `suspicious`: `313`
- `copyright_infringement`: `87`
- `is_suspicious_count`: `373`
- `failed`: `0`
- `llm_batches_processed`: `26`
- `batch_size`: `20`
- `channels_considered`: `9`
- `channels_with_messages`: `5`
- `channels_rolled_up`: `5`
- `updated_channel_rows`: `5`

### Post-Resume Snapshot
- `total_messages`: `697`
- `analyzed_at_count`: `696`
- `unanalyzed_messages`: `1`
- `analysis_status_counts`:
  - `completed`: `607`
  - `policy_rule_bypass`: `89`
  - `not_analyzed`: `1`
- `risk_label_counts`:
  - `copyright_infringement`: `208`
  - `suspicious`: `402`
  - `safe`: `86`
  - `missing`: `1`

### Remaining Unanalyzed Row
- The single remaining row is the older manual smoke-test insert:
  - `message_row_id`: `579d6712-3870-4257-a600-5e01513d5fb5`
  - `channel_id`: `tg_smoke_20260401144719`
  - `channel_username`: `pw_smoke_144719`
  - `llm_analysis_response.status`: `not_analyzed`
- This row is not part of the real monitored-channel ingestion set, so the monitored backlog is effectively complete.
