# Team B Changes Log

## Persistent Guardrails
- Cost-control rule: Do not call Apify transcript actor for videos that already have non-empty transcript text in Supabase.
- Test-run logging rule: Every meaningful run (code edits, tests, live backfills, smoke checks) must be appended here with commands and outcomes.

## Step 001 - 2026-03-31 18:52:48 IST

### Files Changed
- `eshachanges.md` (created)

### What Changed
- Created a persistent checkpoint log file for Team B’s YouTube unofficial-analysis MVP.
- Completed deep inspection of current YouTube/search/fulfillment/storage/transcription/worker/config flow.
- Verified live Supabase schema for:
  - `youtube_channels`
  - `youtube_videos`
  - `youtube_comments`
  - `mentions`
  - `fulfillment_results`
  - `transcriptions`
- Verified relevant indexes/uniqueness for YouTube/mentions tables.

### Why It Changed
- You requested disciplined, stepwise delivery with checkpointing after meaningful changes.
- This establishes a source of truth for future prompts and prevents drift during urgent MVP implementation.

### Inspected Files (Prompt 1)
- `context.md`
- `scrapers/youtube.py`
- `search/engine.py`
- `search/fulfillment.py`
- `search/filters.py`
- `scrapers/base.py`
- `storage/queries.py`
- `storage/models.py`
- `storage/dedup.py`
- `transcription/captions.py`
- `transcription/extractor.py`
- `transcription/whisper.py`
- `workers/tasks.py`
- `workers/schedule.py`
- `workers/celery_app.py`
- `config/settings.py`
- `config/constants.py`
- `config/supabase_client.py`
- `brand/monitor.py`
- `Makefile`
- `.env.example`
- `requirements.txt`
- `project.md`
- package `__init__.py` files for `scrapers/` and `search/`

### Open Issues / Blockers
- **Searcher bootstrap reliability gap:** `register_searcher(...)` depends on scraper module import side effects, but no deterministic bootstrap import exists in worker path.
- **No end-to-end YouTube post-fulfillment path yet:** `workers.tasks.scrape_platform` only calls `search_and_fulfill`; no comment/transcript/classification stage is wired.
- **Raw YouTube table helpers missing in code:** `storage/queries.py` has no CRUD/upsert helpers for `youtube_channels`, `youtube_videos`, `youtube_comments`.
- **YouTube API v3 settings missing:** no env/config constants for API key, official blacklist, or query tuning.
- **Azure OpenAI batch path not present:** no `openai` SDK usage, no Azure client abstraction, no batch request lifecycle code.
- **Dependency gap for planned Azure integration:** `requirements.txt` currently has no `openai` package.
- **`tests/` folder missing:** `make test` currently points to `pytest tests/ -v` but `tests/` does not exist.
- **Schema constraint nuance:** `youtube_videos.video_id` is unique, but `youtube_channels.channel_id` is not unique in current DB schema; upsert strategy must account for this.
- **`youtube_comments` schema nuance:** table has no `brand_id`/`mention_id`; linkage is via `video_id` and must be enforced at app layer.

### Exact Commands Run
```bash
pwd; ls -la; sed -n '1,240p' context.md
sed -n '1,260p' scrapers/youtube.py
sed -n '1,260p' search/engine.py
sed -n '1,320p' search/fulfillment.py
sed -n '1,320p' storage/queries.py
sed -n '1,320p' storage/models.py
sed -n '1,320p' transcription/captions.py
sed -n '1,360p' transcription/extractor.py
sed -n '1,360p' transcription/whisper.py
sed -n '1,360p' workers/tasks.py
sed -n '1,320p' workers/schedule.py
sed -n '1,320p' config/settings.py
sed -n '1,360p' config/constants.py
sed -n '1,320p' brand/monitor.py
sed -n '1,240p' Makefile
sed -n '1,240p' .env.example
rg --files tests || true
rg -n "register_searcher|scrapers\.youtube|import scrapers|from scrapers" -S
rg --files | rg -n "test|spec|conftest|pytest|checks" -i
ls -la scrapers; sed -n '1,220p' scrapers/__init__.py
ls -la search; sed -n '1,220p' search/__init__.py
sed -n '1,260p' workers/celery_app.py
sed -n '1,320p' search/filters.py
sed -n '1,320p' scrapers/base.py
rg -n "youtube_channels|youtube_videos|youtube_comments|transcriptions|fulfillment_results|mentions" storage -S
rg -n "scrape_comments|get_transcript|get_captions|download_audio|transcribe_async|insert_transcription|youtube_comments|fulfillment_results|queued_for_transcription|queued_for_scraping" -S
rg -n "search_and_fulfill\(|search_all\(|scrape_platform\(" -S
rg -n "AzureOpenAI|azure|openai|batch|chat.completions|classification|triage" -S
sed -n '1,320p' analysis/sentiment.py
sed -n '1,360p' analysis/pipeline.py
sed -n '1,320p' project.md
wc -l project.md; sed -n '321,520p' project.md
rg -n "youtube_|platform_ref_id|raw_data\[|raw_data\.|mention_id|video_id|channel_id" -S
sed -n '1,260p' requirements.txt
sed -n '1,220p' storage/dedup.py
ls -la transcription; ls -la workers; ls -la storage
set -a; source .env.local; set +a; TOKEN=${SUPABASE_ACCESS_TOKEN:-$SECRET_SUPABASE_ACCESS_TOKEN}; q="select table_name,column_name,data_type,udt_name,is_nullable,column_default,ordinal_position from information_schema.columns where table_schema='public' and table_name in ('youtube_channels','youtube_videos','youtube_comments','mentions','fulfillment_results','transcriptions') order by table_name,ordinal_position;"; q_json=$(printf "%s" "$q" | jq -Rs .); payload="{\"query\":${q_json}}"; curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$payload"
set -a; source .env.local; set +a; TOKEN=${SUPABASE_ACCESS_TOKEN:-$SECRET_SUPABASE_ACCESS_TOKEN}; q="select tablename,indexname,indexdef from pg_indexes where schemaname='public' and tablename in ('youtube_channels','youtube_videos','youtube_comments','mentions') order by tablename,indexname;"; q_json=$(printf "%s" "$q" | jq -Rs .); payload="{\"query\":${q_json}}"; curl -sS "https://api.supabase.com/v1/projects/$SUPABASE_PROJECT_REF/database/query" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$payload"
rg -n "if __name__ == ['\"]__main__['\"]|pytest|unittest|doctest" -S
date '+%Y-%m-%d %H:%M:%S %Z'
```

### Test Results / Smoke-Test Results
- `make test`: **not run** in this prompt (inspection-only prompt).
- Test discovery smoke-check: `tests/` directory missing.
- Searcher registration smoke-check: no deterministic import bootstrap found for scraper registration.
- Live schema smoke-check: successful metadata queries confirmed exact columns + indexes for YouTube/raw and normalized tables.

### Next Recommended Prompt For Codex
"Read `context.md` and `eshachanges.md` first. Implement Phase 1 only: reliable searcher bootstrap + YouTube API/config scaffolding (no full pipeline yet). Edit only `search/engine.py`, `workers/tasks.py`, `config/settings.py`, `config/constants.py`, `.env.example`, and `requirements.txt` if needed. Add official PW YouTube blacklist constants (IDs + handles) and API env placeholders, but do not yet implement transcript/comment enrichment. Update `eshachanges.md` after each meaningful change and run focused smoke checks."

## Step 002.1 - 2026-03-31 18:59:36 IST

### Files Changed
- `search/engine.py`
- `eshachanges.md`

### What Changed
- Added deterministic searcher bootstrap in `search/engine.py` via `ensure_searchers_loaded(...)`.
- Added explicit platform->module mapping and loaded-module tracking to keep bootstrap idempotent.
- Wired bootstrap calls into both `search_all(...)` and `search_and_fulfill(...)` so YouTube registration is guaranteed before lookup.

### Why It Changed
- Searcher registration previously depended on uncertain import side effects.
- This makes YouTube and other platform registration deterministic and safe across repeated task invocations.

### Open Issues / Blockers
- Worker entry path still needs explicit bootstrap invocation + YouTube unofficial pipeline stub for next-phase orchestration.
- YouTube/Azure config scaffolding and blacklist constants are not yet added in this step.

### Exact Commands Run
```bash
sed -n '1,220p' context.md
sed -n '1,320p' eshachanges.md
git status --short
sed -n '1,260p' search/engine.py
sed -n '1,260p' workers/tasks.py
sed -n '1,320p' config/settings.py
sed -n '1,360p' config/constants.py
sed -n '1,260p' .env.example
sed -n '1,260p' requirements.txt
# apply_patch on search/engine.py
date '+%Y-%m-%d %H:%M:%S %Z'
```

### Test Results / Smoke-Test Results
- Not run yet for this checkpoint (smoke checks will run after all Phase-1 edits).

### Next Recommended Prompt For Codex
- Continue Phase 1 in current prompt: patch `workers/tasks.py` for bootstrap-safe entry + YouTube unofficial stub helper.

## Step 002.2 - 2026-03-31 19:00:02 IST

### Files Changed
- `workers/tasks.py`
- `eshachanges.md`

### What Changed
- Updated `scrape_platform(...)` to call `ensure_searchers_loaded([platform])` before running brand searches.
- Added private helper stub `_queue_youtube_unofficial_pipeline_stub(...)` as a Phase-1 placeholder hook for upcoming YouTube unofficial orchestration.
- Added conditional call to that stub only for YouTube scrape runs.

### Why It Changed
- Even with engine-level bootstrap, worker-level bootstrap adds deterministic safety at task entry.
- The stub creates a stable extension point for Prompt 3+ without prematurely implementing enrichment logic.

### Open Issues / Blockers
- YouTube/Azure settings + constants scaffolding still pending.
- Official PW blacklist constants still pending.

### Exact Commands Run
```bash
# apply_patch on workers/tasks.py
date '+%Y-%m-%d %H:%M:%S %Z'
```

### Test Results / Smoke-Test Results
- Not run yet for this checkpoint (smoke checks will run after all Phase-1 edits).

### Next Recommended Prompt For Codex
- Continue Phase 1 in current prompt: add config/constants/.env scaffolding for YouTube unofficial + Azure placeholders + official blacklist.

## Step 002.3 - 2026-03-31 19:01:23 IST

### Files Changed
- `config/settings.py`
- `config/constants.py`
- `.env.example`
- `eshachanges.md`

### What Changed
- Added YouTube unofficial pipeline env settings in `config/settings.py`:
  - `YOUTUBE_API_KEY`
  - `YOUTUBE_UNOFFICIAL_MAX_RESULTS_PER_KEYWORD`
  - `YOUTUBE_UNOFFICIAL_PUBLISHED_AFTER_DAYS`
  - `YOUTUBE_UNOFFICIAL_MAX_COMMENTS_PER_FLAGGED_VIDEO`
- Added Azure OpenAI scaffolding env settings in `config/settings.py`:
  - `AZURE_OPENAI_API_KEY`
  - `AZURE_OPENAI_ENDPOINT`
  - `AZURE_OPENAI_API_VERSION`
  - `AZURE_OPENAI_DEPLOYMENT_GPT52`
  - `AZURE_OPENAI_DEPLOYMENT_GPT53`
  - `AZURE_OPENAI_DEPLOYMENT_GPT54`
  - `AZURE_OPENAI_BATCH_INPUT_DIR`
  - `AZURE_OPENAI_BATCH_OUTPUT_DIR`
- Added YouTube unofficial defaults and official/suspected PW blacklist constants in `config/constants.py`:
  - `YOUTUBE_OFFICIAL_CHANNEL_IDS`
  - `YOUTUBE_OFFICIAL_CHANNEL_HANDLES` (normalized lowercase, no `@`)
  - `YOUTUBE_OFFICIAL_CHANNEL_IDS_SUSPECTED`
  - `YOUTUBE_OFFICIAL_CHANNEL_HANDLES_SUSPECTED`
  - ergonomic merged sets: `YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL`, `YOUTUBE_OFFICIAL_CHANNEL_HANDLES_ALL`
- Added all new placeholders/documentation to `.env.example`.

### Why It Changed
- Provides safe Phase-1 config foundation for upcoming YouTube Data API discovery and Azure batch-oriented triage.
- Blacklist constants are now centralized and ready for deterministic filtering logic in Prompt 3.

### Open Issues / Blockers
- Actual YouTube Data API v3 client/search flow is not implemented yet (by design for this phase).
- Azure batch request creation/polling/ingestion is not implemented yet (by design for this phase).

### Exact Commands Run
```bash
# apply_patch on config/settings.py
# apply_patch on config/constants.py
# apply_patch on .env.example
date '+%Y-%m-%d %H:%M:%S %Z'
```

### Test Results / Smoke-Test Results
- Not run yet for this checkpoint (smoke checks run next in this prompt).

### Next Recommended Prompt For Codex
- Continue in current prompt: run focused smoke checks and record final Phase-1 outcomes.

## Step 002.4 - 2026-03-31 19:02:48 IST

### Files Changed
- `eshachanges.md`

### What Changed
- Ran focused Phase-1 smoke checks for syntax/import/bootstrap/constants.
- Verified new bootstrap hook references are present in both engine and worker paths.
- Captured dependency-related smoke-check constraints and fallback verification used in this environment.

### Why It Changed
- Confirms the Phase-1 foundation is stable before Prompt 3 implementation of actual YouTube discovery + raw persistence.

### Open Issues / Blockers
- Runtime dependencies are not installed in this shell environment (`datasketch`, `supabase`, `celery`), so direct import smoke checks needed stub-based fallback for verification.
- Full YouTube Data API v3 flow and raw-table persistence are still pending by design.
- Azure batch orchestration is still pending by design.

### Exact Commands Run
```bash
python -m py_compile search/engine.py workers/tasks.py config/settings.py config/constants.py
python - <<'PY'
from search.engine import ensure_searchers_loaded, _platform_searchers
ensure_searchers_loaded(["youtube"])
print("youtube_registered", "youtube" in _platform_searchers)
ensure_searchers_loaded(["youtube"])  # idempotency second call
print("registry_size", len(_platform_searchers))
PY
python - <<'PY'
from config.settings import (
    YOUTUBE_API_KEY,
    YOUTUBE_UNOFFICIAL_MAX_RESULTS_PER_KEYWORD,
    YOUTUBE_UNOFFICIAL_PUBLISHED_AFTER_DAYS,
    YOUTUBE_UNOFFICIAL_MAX_COMMENTS_PER_FLAGGED_VIDEO,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_GPT52,
)
from config.constants import (
    YOUTUBE_OFFICIAL_CHANNEL_IDS,
    YOUTUBE_OFFICIAL_CHANNEL_HANDLES,
    YOUTUBE_OFFICIAL_CHANNEL_IDS_SUSPECTED,
    YOUTUBE_OFFICIAL_CHANNEL_HANDLES_SUSPECTED,
    YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL,
    YOUTUBE_OFFICIAL_CHANNEL_HANDLES_ALL,
)
print("youtube_defaults", YOUTUBE_UNOFFICIAL_MAX_RESULTS_PER_KEYWORD, YOUTUBE_UNOFFICIAL_PUBLISHED_AFTER_DAYS, YOUTUBE_UNOFFICIAL_MAX_COMMENTS_PER_FLAGGED_VIDEO)
print("azure_api_version", AZURE_OPENAI_API_VERSION)
print("blacklist_counts", len(YOUTUBE_OFFICIAL_CHANNEL_IDS), len(YOUTUBE_OFFICIAL_CHANNEL_HANDLES), len(YOUTUBE_OFFICIAL_CHANNEL_IDS_SUSPECTED), len(YOUTUBE_OFFICIAL_CHANNEL_HANDLES_SUSPECTED))
print("merged_counts", len(YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL), len(YOUTUBE_OFFICIAL_CHANNEL_HANDLES_ALL))
print("has_vidyapeethpw", "vidyapeethpw" in YOUTUBE_OFFICIAL_CHANNEL_HANDLES)
print("has_at_symbol", any(h.startswith("@") for h in YOUTUBE_OFFICIAL_CHANNEL_HANDLES))
print("has_patna_suspected", "pwvidyapeethpatna" in YOUTUBE_OFFICIAL_CHANNEL_HANDLES_SUSPECTED)
print("keys_present", bool(YOUTUBE_API_KEY), bool(AZURE_OPENAI_API_KEY), bool(AZURE_OPENAI_ENDPOINT), bool(AZURE_OPENAI_DEPLOYMENT_GPT52))
PY
python - <<'PY'
import workers.tasks as wt
print('worker_tasks_import_ok', hasattr(wt, 'scrape_platform'))
print('stub_present', hasattr(wt, '_queue_youtube_unofficial_pipeline_stub'))
PY
python - <<'PY'
import sys
import types

datasketch = types.ModuleType('datasketch')
class MinHash:
    def __init__(self, *args, **kwargs):
        pass
    def update(self, *args, **kwargs):
        pass
class MinHashLSH:
    def __init__(self, *args, **kwargs):
        pass
    def query(self, *args, **kwargs):
        return []
    def insert(self, *args, **kwargs):
        pass

datasketch.MinHash = MinHash
datasketch.MinHashLSH = MinHashLSH
sys.modules['datasketch'] = datasketch

supabase = types.ModuleType('supabase')
class Client:
    pass
def create_client(*args, **kwargs):
    return Client()
supabase.Client = Client
supabase.create_client = create_client
sys.modules['supabase'] = supabase

from search.engine import ensure_searchers_loaded
ensure_searchers_loaded(["youtube"])
ensure_searchers_loaded(["youtube"])
print("bootstrap_callable", True)
PY
python - <<'PY'
import sys
import types

supabase = types.ModuleType('supabase')
class Client:
    pass
def create_client(*args, **kwargs):
    return Client()
supabase.Client = Client
supabase.create_client = create_client
sys.modules['supabase'] = supabase

celery = types.ModuleType('celery')
class Celery:
    def __init__(self, *args, **kwargs):
        self.conf = types.SimpleNamespace(update=lambda **kw: None)
    def task(self, *args, **kwargs):
        def deco(fn):
            return fn
        return deco
celery.Celery = Celery
sys.modules['celery'] = celery

import workers.tasks as wt
print('worker_tasks_import_ok', hasattr(wt, 'scrape_platform'))
print('youtube_stub_ok', hasattr(wt, '_queue_youtube_unofficial_pipeline_stub'))
PY
rg -n "def ensure_searchers_loaded|ensure_searchers_loaded\(" search/engine.py workers/tasks.py
git status --short
date '+%Y-%m-%d %H:%M:%S %Z'
```

### Test Results / Smoke-Test Results
- `python -m py_compile ...`: **PASS**
- Direct import smoke checks:
  - `search.engine` direct import: **FAIL** in this env (`ModuleNotFoundError: datasketch`, then `supabase`)
  - `workers.tasks` direct import: **FAIL** in this env (`ModuleNotFoundError: celery`)
- Config/constants load smoke check: **PASS**
  - YouTube defaults loaded: `25/30/200`
  - Azure API version loaded: `2024-10-21`
  - Blacklist counts: confirmed IDs `56`, handles `9`, suspected ID `1`, suspected handles `2`, merged IDs `57`, merged handles `11`
  - Handle normalization check (`no @`): **PASS**
- Stub-based fallback smoke checks (for dependency-light env only):
  - `ensure_searchers_loaded(["youtube"])` callable and idempotent: **PASS**
  - `workers.tasks` import with celery/supabase stubs and YouTube stub presence: **PASS**
- Bootstrap wiring presence checks via `rg`: **PASS**

### Next Recommended Prompt For Codex
"Read `context.md` and `eshachanges.md` first. Implement Phase 2 (YouTube unofficial discovery + raw persistence) only. Edit only `scrapers/youtube.py`, `storage/queries.py`, `search/engine.py`, and `workers/tasks.py` if strictly required. Build YouTube Data API v3 keyword discovery, apply official/suspected blacklist filtering using `config/constants.py`, persist `youtube_channels` and `youtube_videos` idempotently using verified live columns, and map discovered videos into normalized `mentions` + `fulfillment_results` with `platform_ref_id=video_id`. Do not implement transcript/comment enrichment or Azure batch execution yet. Update `eshachanges.md` after each meaningful change and run focused smoke checks." 

## Step 002.5 - 2026-03-31 19:19:34 IST

### Files Changed
- `eshachanges.md`

### What Changed
- Installed `celery` in the active Python environment for local execution/import support.
- Verified installation by importing Celery and printing version.

### Why It Changed
- You requested Celery installation so task/worker executions can proceed.

### Open Issues / Blockers
- Other runtime dependencies may still be missing (`supabase`, `datasketch`) for full import/runtime flows.

### Exact Commands Run
```bash
python -m pip install celery
python - <<'PY'
import celery
print('celery_version', celery.__version__)
PY
date '+%Y-%m-%d %H:%M:%S %Z'
```

### Test Results / Smoke-Test Results
- `python -m pip install celery`: **PASS** (installed `celery==5.6.3` and required transitive packages)
- `import celery`: **PASS** (`celery_version 5.6.3`)

### Next Recommended Prompt For Codex
- Continue Prompt 3 (Phase 2): YouTube Data API discovery + raw persistence path.

## Step 002.6 - 2026-03-31 19:21:55 IST

### Files Changed
- `eshachanges.md`

### What Changed
- Installed `datasketch` and `supabase` packages in the active Python environment.
- Verified real imports for `datasketch`, `supabase`, `search.engine`, and `workers.tasks` (without stubs).
- Ran Supabase connectivity smoke checks and identified env wiring mismatch as the remaining practical blocker.

### Why It Changed
- You asked to install `datasketch` and clarify Supabase testing with elevated permissions.

### Open Issues / Blockers
- Elevated/network access is **not** the blocker now.
- Runtime config mismatch is the blocker by default:
  - `config/settings.py` loads `.env` and expects `SUPABASE_KEY` / `SUPABASE_SERVICE_KEY`.
  - Local admin credentials currently exist in `.env.local` as `SECRET_SUPABASE_*` names.
- For real DB calls, env vars must be mapped/exported (or `.env` updated accordingly).

### Exact Commands Run
```bash
python -m pip install datasketch supabase
python - <<'PY'
import datasketch
import supabase
print('datasketch_version', datasketch.__version__)
print('supabase_version', supabase.__version__)
PY
python - <<'PY'
import search.engine as se
print('engine_import_ok', hasattr(se, 'search_and_fulfill'))
se.ensure_searchers_loaded(['youtube'])
print('youtube_registered', 'youtube' in se._platform_searchers)
PY
python - <<'PY'
import workers.tasks as wt
print('tasks_import_ok', hasattr(wt, 'scrape_platform'))
print('stub_ok', hasattr(wt, '_queue_youtube_unofficial_pipeline_stub'))
PY
python - <<'PY'
from config.settings import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY
print('has_supabase_url', bool(SUPABASE_URL))
print('has_supabase_key', bool(SUPABASE_KEY))
print('has_supabase_service_key', bool(SUPABASE_SERVICE_KEY))
PY
python - <<'PY'
from storage import queries as db
rows = db.get_all_brands()
print('brands_count', len(rows))
PY
set -a; source .env.local; set +a; export SUPABASE_URL="https://${SUPABASE_PROJECT_REF}.supabase.co"; export SUPABASE_SERVICE_KEY="${SUPABASE_SERVICE_KEY:-$SECRET_SUPABASE_SERVICE_KEY}"; python - <<'PY'
from storage import queries as db
rows = db.get_all_brands()
print('brands_count', len(rows))
PY
date '+%Y-%m-%d %H:%M:%S %Z'
```

### Test Results / Smoke-Test Results
- `pip install datasketch supabase`: **PASS**
  - `datasketch==1.9.0`
  - `supabase==2.28.3`
- `import search.engine`: **PASS**
- `ensure_searchers_loaded(['youtube'])`: **PASS** (`youtube_registered True`)
- `import workers.tasks`: **PASS**
- Direct Supabase query using default loaded env: **FAIL** (`SUPABASE_SERVICE_KEY` missing in `.env`)
- Supabase query with mapped `.env.local` admin vars + elevated permissions: **PASS** (`brands_count 0`)

### Next Recommended Prompt For Codex
- Continue Phase 2 implementation; optionally standardize local runtime env loading strategy (`.env` vs `.env.local`) to avoid manual export mapping during worker/search execution.

## Step 003.1 - 2026-03-31 19:56:25 IST

### Files Changed
- `storage/queries.py`, `search/fulfillment.py`, `transcription/extractor.py`, `transcription/captions.py`
- `scrapers/youtube.py`, `workers/tasks.py`, `config/settings.py`, `requirements.txt`, `eshachanges.md`

### Summary
- Implemented end-to-end unofficial YouTube MVP core:
  - YouTube Data API discovery + official/suspected blacklist filtering
  - Raw persistence helpers (channels/videos/comments) with idempotent behavior
  - Mention + fulfillment upsert path (`platform_ref_id=video_id`)
  - Azure batch-friendly triage abstraction (JSONL input, deterministic custom IDs, parser, direct fallback)
  - Deep enrichment path for flagged videos (transcript fallback + comments + analysis persistence)
- Added `AZURE_OPENAI_BATCH_ENABLED` and `openai` dependency entry.

### Commands
- `apply_patch` on listed files, `cat > scrapers/youtube.py`, `python -m py_compile ...`

### Results
- Compile/import smoke checks: **PASS**

---

## Step 003.2 - 2026-03-31 20:00:05 IST

### Files Changed
- `tests/test_youtube_helpers.py`, `tests/test_fulfillment_youtube.py`, `tests/test_transcript_fallback.py`
- `tests/test_storage_queries_youtube.py`, `tests/test_youtube_pipeline_smoke.py`, `eshachanges.md`

### Summary
- Added focused tests for blacklist, keyword bucketing, mapping, fulfillment flags, transcript fallback order, triage parsing, idempotent video persistence, and mocked end-to-end pipeline run.

### Commands
- `mkdir -p tests`, `cat > tests/...`, `python -m py_compile tests/...`, `python -m pytest tests -v`

### Results
- Test suite: **13 passed**

---

## Step 003.3 - 2026-03-31 20:00:59 IST

### Files Changed
- `eshachanges.md`

### Summary
- Verified wiring symbols and pipeline skip behavior when no API key is present.

### Commands
- `python - <<'PY' ... run_unofficial_youtube_pipeline_for_brand(...) ... PY`
- `rg -n ...`, `git status --short`

### Results
- Pipeline skip path: **PASS** (`missing_youtube_api_key`)

---

## Step 003.4 - 2026-03-31 20:01:43 IST

### Files Changed
- `workers/tasks.py`, `eshachanges.md`

### Summary
- Renamed worker helper to `_run_youtube_unofficial_pipeline(...)` and kept compatibility alias `_queue_youtube_unofficial_pipeline_stub(...)`.

### Commands
- `apply_patch`, `python -m py_compile workers/tasks.py`, `python -m pytest tests -q`

### Results
- Tests: **13 passed**

---

## Step 003.5 - 2026-03-31 20:02:14 IST

### Files Changed
- `scrapers/youtube.py`, `eshachanges.md`

### Summary
- Hardened Azure direct-call parsing for empty `choices` safety.

### Commands
- `apply_patch`, `python -m py_compile scrapers/youtube.py`, `python -m pytest tests -q`

### Results
- Tests: **13 passed**

---

## Step 003.6 - 2026-03-31 22:51:08 IST

### Files Changed
- `eshachanges.md`

### Summary
- First live endpoint probe pass: network reachable but canonical Azure/YouTube env vars not detected at that moment.

### Commands
- Env audits + raw HTTP probes for Azure and YouTube

### Results
- Azure/YouTube not yet returning `200` in this pass (auth/key wiring issue at that time)

---

## Step 003.7 - 2026-03-31 22:55:02 IST

### Files Changed
- `eshachanges.md`

### Summary
- Re-ran live checks after env update; installed missing runtime SDK (`openai`) for Azure SDK validation.

### Commands
- `python -m pip install openai`
- Live YouTube probe + Azure HTTP probe + Azure SDK probe
- `python -m pytest tests -q`

### Results
- YouTube endpoint: **200**
- Azure HTTP endpoint: **200**
- Azure SDK completion: **200** (`pong`)
- Tests: **13 passed**

## Step 004.1 - 2026-03-31 23:08:39 IST
- Files: `config/settings.py`, `eshachanges.md`
- Summary: Added `.env` + `.env.local` loading and canonical-first env fallbacks (YouTube/Azure/Supabase).
- Result: `YOUTUBE_API_KEY`, `AZURE_OPENAI_API_KEY`, `SUPABASE_SERVICE_KEY` resolved.
- Next: Run bounded live YouTube E2E + DB verification.

## Step 004.2 - 2026-03-31 23:11:34 IST
- Files: `scrapers/youtube.py`, `eshachanges.md`
- Summary: Added bounded-run args + richer runtime counters for discovery/persistence/enrichment.
- Result: Tests passed (`13`).
- Next: Execute live direct + worker path run.

## Step 004.3 - 2026-03-31 23:12:35 IST
- Files: `workers/tasks.py`, `eshachanges.md`
- Summary: Worker helper now accepts passthrough kwargs for bounded YouTube runs.
- Result: Tests passed (`13`).
- Next: Run bounded live worker verification.

## Step 004.4 - 2026-03-31 23:18:24 IST
- Files: `scrapers/youtube.py`, `eshachanges.md`
- Summary: Fixed Supabase JSON serialization bug by converting datetime fields to ISO strings.
- Result: Runtime write error fixed; tests passed (`13`).
- Next: Re-run live E2E.

## Step 004.5 - 2026-03-31 23:21:08 IST
- Files: `transcription/captions.py`, `tests/test_transcript_fallback.py`, `eshachanges.md`
- Summary: Whisper fallback failures are non-fatal; enrichment continues with `source_type=none`.
- Result: New test added; tests passed (`14`).
- Next: Re-run live E2E for flagged-video path.

## Step 004.6 - 2026-03-31 23:24:44 IST
- Files: `eshachanges.md`
- Summary: Live bounded E2E verified (direct + worker) for `PW Live Smoke`.
- Result:
  - `youtube_videos=6`, `youtube_channels=6`, `youtube_comments=4`
  - `mentions=6`, `fulfillment_results=6`, `transcriptions=0`
  - flagged/enriched flow executed end-to-end.
- Next: Enable Azure endpoint/deployment + Whisper auth for richer outputs.

## Step 004.7 - 2026-03-31 23:25:08 IST
- Files: `transcription/captions.py`, `eshachanges.md`
- Summary: Reduced whisper fallback log noise (warning instead of traceback spam).
- Result: Tests passed (`14`).
- Next: Continue runtime hardening.

## Step 005.1 - 2026-03-31 23:44:38 IST
- Files: `config/settings.py`, `scrapers/youtube.py`, `transcription/whisper.py`, `.env.example`, `eshachanges.md`
- Summary:
  - Added `channel_owner` write logic (`Owned`/`Not Owned`).
  - Set Azure defaults (endpoint/deployment/api-version) from provided values.
  - Added Whisper proxy submit+poll settings and fallback implementation.
- Result: Tests passed (`14`).
- Next: Apply live schema + run existing-ID backfill test.

## Step 005.2 - 2026-03-31 23:44:38 IST
- Files: `eshachanges.md`
- Summary: Live Supabase migration applied for `youtube_channels.channel_owner`; existing IDs backfilled from live fetch.
- Result:
  - scanned `6`, upserted `6`, owners: `Owned=0`, `Not Owned=6`
  - Azure direct-call smoke succeeded.
- Next: Ensure `WHISPER_API_KEY` is loaded in runtime env.

## Step 005.3 - 2026-03-31 23:46:03 IST
- Files: `.env`, `eshachanges.md`
- Summary: Added Azure endpoint/deployment/api-version entries to `.env`.
- Result: Azure settings resolved at runtime; `WHISPER_API_KEY` still missing from loaded env.
- Next: Save/load `WHISPER_API_KEY` in active env source.

## Step 005.4 - 2026-03-31 23:46:49 IST
- Files: `.vscode/settings.json`, `eshachanges.md`
- Summary: Enabled VS Code Python terminal env-file injection.
- Result: `python.terminal.useEnvFile=true`, `python.envFile=${workspaceFolder}/.env`.

## Step 006.1 - 2026-03-31 23:58:50 IST
- Files: `scrapers/youtube.py`, `storage/queries.py`, `tests/test_youtube_pipeline_smoke.py`, `eshachanges.md`
- Summary:
  - Persisted Azure title triage directly in `youtube_videos`.
  - Added `analysis_artifacts` stage IDs/metadata for future polling.
  - Added `update_youtube_video_by_video_id(...)` helper.
- Live DB schema updates (`youtube_videos`):
  - Added `title_triage_*` columns + `analysis_artifacts jsonb`.
  - Added indexes on `title_triage_label` and `title_triage_custom_id`.
- Result:
  - tests passed (`14`)
  - bounded live run wrote title labels/custom IDs
  - backfill updated `6` existing videos.
- Next: When batch polling is enabled, fill `analysis_artifacts.*.correlation_id` from real provider request IDs.

## Step 007.1 - 2026-04-01 12:07:05 IST
- Files: `storage/queries.py`, `eshachanges.md`
- Summary:
  - Added `get_youtube_videos_for_brand(...)` and `get_youtube_videos_by_video_ids(...)` for phase-based batch polling/ingestion lookup.
  - Added deep-merge helper + `merge_youtube_video_analysis_artifacts(...)` to safely update nested `analysis_artifacts` without clobbering existing stages.
- Why:
  - Azure batch poll/result-ingestion requires merging stage metadata per video and scanning recent videos by brand.
- Commands:
  - `apply_patch` on `storage/queries.py`
  - `date '+%Y-%m-%d %H:%M:%S %Z'`

## Step 007.2 - 2026-04-01 12:07:20 IST
- Files: `config/settings.py`, `eshachanges.md`
- Summary:
  - Added `AZURE_OPENAI_BATCH_POLL_INTERVAL_SECONDS` and `AZURE_OPENAI_BATCH_POLL_TIMEOUT_SECONDS` settings.
- Why:
  - Batch lifecycle now needs explicit runtime control for worker phase-2 poll cadence and bounded waiting.
- Commands:
  - `apply_patch` on `config/settings.py`
  - `date '+%Y-%m-%d %H:%M:%S %Z'`

## Step 007.3 - 2026-04-01 12:17:54 IST
- Files: `scrapers/youtube.py`, `workers/tasks.py`, `transcription/captions.py`, `transcription/extractor.py`, `transcription/whisper.py`, `eshachanges.md`
- Summary:
  - Implemented real Azure batch lifecycle primitives in `AzureYouTubeAnalyzer`:
    - JSONL request building with `/v1/chat/completions`
    - batch input upload + batch create (`submit_batch_stage`)
    - batch status poll (`poll_batch_stage`)
    - output/error file download + parse (`fetch_batch_outputs`, `parse_batch_output_records`, `parse_batch_error_records`)
    - per-result correlation/request-id extraction + metadata propagation.
  - Split YouTube unofficial pipeline into composable phases:
    - `submit_youtube_title_triage_batch_for_brand(...)`
    - `poll_youtube_title_triage_batch_for_brand(...)`
    - `ingest_youtube_title_triage_results_for_brand(...)`
    - `enrich_flagged_youtube_mentions(...)`
    - `run_unofficial_youtube_pipeline_for_brand(...)` now orchestrates submit -> poll -> enrich.
  - Persisted richer `analysis_artifacts.title_triage` metadata (stage, status, batch/file IDs, paths, correlation ID, timestamps, errors) and applied triage outputs back to `youtube_videos`, `mentions`, and `fulfillment_results`.
  - Added phase-specific worker helpers/tasks:
    - `submit_youtube_title_triage_batch`
    - `poll_youtube_title_triage_batch`
    - `ingest_youtube_title_triage_results`
    - `enrich_flagged_youtube_mentions`
  - Hardened transcript metadata handling while keeping non-fatal fallback:
    - whisper proxy no longer fabricates request IDs when missing
    - concise warning when `WHISPER_API_KEY` is missing
    - transcript source metadata now preserved through fallback outputs and enrichment artifacts.
- Commands:
  - `apply_patch` on listed files
  - `python -m py_compile workers/tasks.py transcription/captions.py transcription/extractor.py transcription/whisper.py storage/queries.py config/settings.py scrapers/youtube.py`
  - `rg -n "WHISPER_API_KEY missing|submit_batch_stage|poll_batch_stage|fetch_batch_outputs|merge_youtube_video_analysis_artifacts" -S ...`

## Step 007.4 - 2026-04-01 12:22:16 IST
- Files: `tests/test_youtube_batch_lifecycle.py`, `tests/test_workers_youtube_phases.py`, `tests/test_storage_queries_youtube.py`, `tests/test_transcript_fallback.py`, `tests/test_youtube_pipeline_smoke.py`, `transcription/captions.py`, `eshachanges.md`
- Summary:
  - Added focused tests for:
    - deterministic title-triage `custom_id` generation
    - batch output/error parser behavior
    - mapping/ingestion of batch outputs back to `youtube_videos` + normalized rows
    - `analysis_artifacts` deep-merge update behavior
    - worker phase split tasks (submit vs poll/ingest vs enrich)
    - transcript fallback non-fatal behavior when external provider raises exceptions.
  - Hardened `get_transcript_with_fallback(...)` to catch caption/provider/downloader exceptions and continue fallback chain gracefully.
  - Updated pipeline smoke test to exercise new phased submit->poll->ingest->enrich orchestration.
- Commands:
  - `python -m pytest tests -q`
- Results:
  - `21 passed in 0.91s`

## Step 007.5 - 2026-04-01 12:30:17 IST
- Files: `scrapers/youtube.py`, `eshachanges.md`
- Summary:
  - Tightened title-triage artifact merge behavior to avoid overwriting previously-populated artifact fields with `None` values during later poll/ingest updates.
  - Re-ran compile + full test suite after this patch.
- Commands:
  - `python -m py_compile scrapers/youtube.py && python -m pytest tests -q`
- Results:
  - `21 passed in 0.88s`

## Step 007.6 - 2026-04-01 12:30:17 IST
- Files: `eshachanges.md`
- Summary:
  - Executed bounded live verification using the required constraints:
    - last `7` days
    - keywords: `physics wallah`, `pw arjuna`, `alakh pandey pw`
    - low cap: `max_results_per_keyword_override=2`
    - phased run: submit -> poll loop -> enrich
  - Azure batch live IDs/status observed:
    - `provider_batch_id`: `batch_af6fc21f-7b64-4125-99b5-9802669bfe6f`
    - `input_file_id`: `file-1ae6035ed5ef406790a4196f7a9a71fd`
    - poll statuses: `validating` -> `failed`
    - output/error file IDs: not returned in this run (`None`)
  - Live bounded summary:
    - discovered: `6`
    - excluded official: `0`
    - unofficial candidates: `6`
    - videos updated with batch metadata: `12` (submit `6` + poll `6`)
    - videos updated with triage results: `6`
    - flagged count: `6`
    - comments fetched: `30`
    - transcripts fetched with text: `0` (`source_type=none` for all 6)
    - final analysis updated: `6`
  - Runtime transcript observations:
    - `WHISPER_API_KEY` was missing at runtime in this shell, fallback stayed non-fatal and continued.
    - comments path had one 403 error for a specific video but enrichment continued overall.
- Commands:
  - `AZURE_OPENAI_BATCH_ENABLED=true python - <<'PY' ... submit_youtube_title_triage_batch_for_brand(...) + poll_youtube_title_triage_batch_for_brand(...) + enrich_flagged_youtube_mentions(...) ... PY`
  - `python - <<'PY' ... db.get_youtube_videos_for_brand(...) ... PY`
  - `python - <<'PY' ... db.get_youtube_video_by_video_id('fKKon_t8KWg') ... PY`

## Step 008.1 - 2026-04-01 12:39:54 IST
- Files: `scrapers/youtube.py`, `workers/tasks.py`, `tests/test_workers_youtube_phases.py`, `tests/test_youtube_batch_lifecycle.py`, `eshachanges.md`
- Summary:
  - Implemented independent sync-only title triage ingestion flow:
    - added `run_youtube_title_triage_sync_ingestion_for_brand(...)`
    - processes titles in configurable sync chunks (`triage_batch_size`, default `10`)
    - uses direct GPT call path (`direct_call_with_meta`) and writes results directly to Supabase.
  - Added `queue_followups` switch to `_apply_triage_result_to_rows(...)` and used `queue_followups=False` in sync ingestion so it does not queue downstream enrichment/transcript workflows.
  - Worker wiring update:
    - `scrape_platform("youtube")` now runs sync ingestion only (no submit/poll/enrich chain)
    - added dedicated celery task `run_youtube_title_triage_sync_ingestion(...)`.
  - Test updates:
    - worker test now validates sync-only execution path
    - added sync chunking test verifying 12 titles are processed in `2` chunks with batch size `10`.
- Commands:
  - `apply_patch` on listed files
  - `python -m py_compile scrapers/youtube.py workers/tasks.py tests/test_workers_youtube_phases.py tests/test_youtube_batch_lifecycle.py`
  - `python -m pytest tests/test_workers_youtube_phases.py tests/test_youtube_batch_lifecycle.py -q`
  - `python -m pytest tests -q`
- Results:
  - targeted tests: `7 passed`
  - full tests: `23 passed in 0.98s`

## Step 008.2 - 2026-04-01 12:40:08 IST
- Files: `eshachanges.md`
- Summary:
  - Live-bounded verification for new sync ingestion-only flow completed using:
    - keywords: `physics wallah`, `pw arjuna`, `alakh pandey pw`
    - published window: last `7` days
    - low cap: `max_results_per_keyword_override=2`
    - `triage_batch_size=10`
  - Runtime result:
    - discovered: `4`
    - titles triaged sync: `4`
    - chunks processed: `1`
    - triage writeback applied: `4`
    - enrichment triggered: `False`
  - DB verification:
    - `title_triage_mode=sync_direct` rows found: `4`
    - latest fulfillment flags for sampled rows: `queued_for_scraping=False`, `queued_for_transcription=False`
- Commands:
  - `python - <<'PY' ... run_youtube_title_triage_sync_ingestion_for_brand(...) ... PY`
  - `python - <<'PY' ... db.get_youtube_videos_for_brand(...) + get_latest_fulfillment_result_for_mention(...) ... PY`

## Step 008.3 - 2026-04-01 12:46:26 IST
- Files: `eshachanges.md`
- Summary:
  - Triggered one-time GPT title-triage backfill for all existing Supabase `youtube_videos` entries using sync-direct analysis (chunk size `10`) and follow-ups disabled.
  - Backfill executed over all currently available rows and wrote updated triage outputs to `youtube_videos` + normalized mention/fulfillment rows.
- Commands:
  - `python - <<'PY' ... load all youtube_videos pages ... AzureYouTubeAnalyzer.direct_call_with_meta(...) ... _apply_triage_result_to_rows(..., queue_followups=False) ... PY`
  - `python - <<'PY' ... verify title_triage_mode + queued_for_scraping/queued_for_transcription flags ... PY`
- Results:
  - total rows seen: `12`
  - processed: `12`
  - updated: `12`
  - failed triage: `0`
  - chunks: `2` (batch size `10`)
  - post-check queue flag violations: `0`
  - all checked rows now have `title_triage_mode=sync_direct_backfill`

## Step 008.4 - 2026-04-01 13:07:40 IST
- Files: `scrapers/youtube.py`, `eshachanges.md`
- Summary:
  - Updated title-triage prompt semantics from title-only framing to explicit `title + description` analysis.
  - Hardened triage payload builder to always pass normalized `title` and `description` fields.
  - Updated sync-ingestion flow to set fulfillment queue flags from triage results (`queue_followups_from_triage=True` default), so negative/uncertain now correctly set:
    - `queued_for_scraping=True`
    - `queued_for_transcription=True`
  - Sync ingestion remains independent (does not auto-run enrichment), but queue flags are now accurate for next-stage workers.
- Commands:
  - `apply_patch` on `scrapers/youtube.py`
  - `python -m py_compile ...`
  - `python -m pytest tests -q`
- Results:
  - tests passed: `23 passed`

## Step 008.5 - 2026-04-01 13:07:40 IST
- Files: `eshachanges.md`
- Summary:
  - Re-ran full one-time GPT backfill over all existing `youtube_videos` entries with updated title+description triage logic and follow-up queue flags enabled.
- Commands:
  - `python - <<'PY' ... iterate all youtube_videos ... direct_call_with_meta(title_triage) ... _apply_triage_result_to_rows(..., queue_followups=True) ... PY`
  - `python - <<'PY' ... verify title_triage_mode + queued flags per row ... PY`
- Backfill Results:
  - total rows seen: `12`
  - processed: `12`
  - updated: `12`
  - failed triage: `0`
  - chunks: `2` (batch size `10`)
  - queued_for_scraping=True count: `4`
  - queued_for_transcription=True count: `4`
  - mode marker applied: `title_triage_mode=sync_direct_backfill_v2`
- Validation Snapshot:
  - negative/uncertain rows now show queue flags true (for transcript/comments)
  - positive rows keep queue flags false.

## Step 008.6 - 2026-04-01 14:01:26 IST
- Files: `scrapers/youtube.py`, `workers/tasks.py`, `transcription/extractor.py`, `transcription/captions.py`, `tests/test_youtube_layer2_sync.py`, `tests/test_workers_youtube_phases.py`, `eshachanges.md`
- Summary:
  - Hardened sync layer-2 pipeline for cron/manual operation:
    - Added `include_completed` filter in `_collect_layer2_candidates_for_brand(...)` so already `layer_2=completed` rows are skipped by default.
    - Extended `run_youtube_layer2_fetch_sync_for_brand(...)` with:
      - `include_completed` and `use_fallback_transcript` controls
      - Apify-first transcript metadata tracking (`apify_status`, `actor_id`, `run_id`, `dataset_id`)
      - fallback transcript execution via existing caption/provider/whisper chain when Apify returns no transcript.
  - Worker task wiring updated:
    - `run_youtube_layer2_sync_fetch(...)` now accepts/passes `include_completed` + `use_fallback_transcript`.
  - Transcript provider hardening:
    - `get_apify_transcripts_batch(...)` now always returns actor metadata even on `missing_api_key`/failure states.
    - `get_transcript_with_fallback(...)` now skips expensive whisper audio-download stage immediately when `WHISPER_API_KEY` is missing (non-fatal, concise warning).
  - Added/updated focused tests:
    - layer-2 candidate filtering for completed rows
    - fallback transcript write path when Apify is empty/missing key
    - worker propagation of new layer-2 task args.
- Commands:
  - `apply_patch` on listed files
  - `python -m py_compile transcription/captions.py transcription/extractor.py scrapers/youtube.py workers/tasks.py tests/test_transcript_fallback.py tests/test_youtube_layer2_sync.py tests/test_workers_youtube_phases.py`
  - `python -m pytest tests/test_transcript_fallback.py tests/test_youtube_layer2_sync.py tests/test_workers_youtube_phases.py -q`
  - `python -m pytest tests -q`
- Results:
  - focused tests: `13 passed`
  - full suite: `28 passed in 1.25s`

## Step 008.7 - 2026-04-01 14:01:26 IST
- Files: `eshachanges.md`
- Summary:
  - Ran live Supabase backfill + layer-2 verification on current brand (`PW Live Smoke`, id `97292c5e-f230-4732-8518-e159349eca07`).
  - Backfill (`title + description`, sync-direct) results:
    - rows seen: `12`
    - processed: `12`
    - updated: `12`
    - failed triage: `0`
    - chunks: `2` (size `10`)
    - queued_for_scraping=true: `4`
    - queued_for_transcription=true: `4`
    - mode marker: `sync_direct_backfill_v3`
  - Layer-2 live sync summary (clean final run):
    - total candidates: `4`
    - page candidates processed: `4`
    - transcript success: `0`
    - transcript failed: `4`
    - comments success: `4`
    - comments fetched: `1`
    - comments inserted: `0` (dedupe hit)
    - failures list: empty
  - Verified artifact writeback on sample row `Iy51b8bJtCE`:
    - `analysis_artifacts.layers.layer_2.status=partial_failed`
    - `analysis_artifacts.transcript_fetch.metadata.apify_actor_id=1s7eXiaukVuOr4Ueg`
    - `analysis_artifacts.transcript_fetch.metadata.apify_status=missing_api_key`
    - `analysis_artifacts.comments_fetch.status=completed`
  - Runtime blocker confirmed:
    - `YOUTUBE_TRANSCRIPT_APIFY_KEY` is not loaded in active runtime env, so Apify transcript stage is skipped.
- Commands:
  - `python - <<'PY' ... _apply_triage_result_to_rows(..., queue_followups=True) backfill ... run_youtube_layer2_fetch_sync_for_brand(...) ... PY`
  - `python - <<'PY' ... run_youtube_layer2_fetch_sync_for_brand(...) + per-video comment/transcription checks ... PY`
  - `python - <<'PY' ... db.get_youtube_video_by_video_id('Iy51b8bJtCE') ... PY`
- Notes:
  - One extended diagnostic run looped layer-2 retries on `partial_failed` rows (expected because retries are allowed when not completed). Final clean one-pass run was executed after hardening to capture bounded output.

## Step 008.8 - 2026-04-01 15:09:20 IST
- Files: `config/settings.py`, `eshachanges.md`
- Summary:
  - Updated dotenv precedence so `.env.local` is now the runtime override source for local secrets:
    - kept `.env` load first
    - changed `.env.local` load to `override=True`.
  - Confirmed current on-disk env files in this workspace do not yet contain:
    - `YOUTUBE_TRANSCRIPT_APIFY_KEY`
    - `WHISPER_API_KEY`
    - `YOUTUBE_API_KEY`
    as direct keys (current keys are mostly `SECRET_*` aliases).
  - Confirmed `config.settings.YOUTUBE_TRANSCRIPT_APIFY_KEY` still resolves empty in this shell after precedence change (key still needs to be added in `.env.local` as `YOUTUBE_TRANSCRIPT_APIFY_KEY` or `SECRET_YOUTUBE_TRANSCRIPT_APIFY_KEY`).
- Commands:
  - `apply_patch` on `config/settings.py`
  - `python -m py_compile config/settings.py`
  - `python - <<'PY' ... from config.settings import YOUTUBE_TRANSCRIPT_APIFY_KEY ... PY`

## Step 008.9 - 2026-04-01 15:17:22 IST
- Files: `eshachanges.md`
- Summary:
  - Ran one live Apify actor connectivity smoke test with single-video payload using `.env.local` key resolution.
  - Result: successful end-to-end call and dataset output retrieval.
  - Observed IDs:
    - `run_id`: `ukef3dyJcQ4zXxvd6`
    - `default_dataset_id`: `VfXeCJHxT0WEffC2A`
  - Runtime response:
    - `run_status=SUCCEEDED`
    - `dataset_total=1`
    - `dataset_count=1`
    - preview item keys include `captions`, `videoId`, `title`, `channelID`, `channelName`, `datePublished`.
- Commands:
  - `python - <<'PY' ... ApifyClient(...).actor('1s7eXiaukVuOr4Ueg').call(run_input=...) ... dataset.list_items(limit=3) ... PY`

## Step 009.1 - 2026-04-01 15:26:07 IST
- Files: `transcription/extractor.py`, `tests/test_transcription_apify_parser.py`, `eshachanges.md`
- Summary:
  - Fixed Apify transcript parsing bug:
    - actor returns `captions` as list of strings for this endpoint
    - parser previously handled only list-of-dicts, causing empty transcript text and unintended fallback to Whisper.
  - Updated `_build_transcript_from_apify_item(...)` to accept string caption lines and build transcript text from them.
  - Added focused regression test `test_apify_parser_handles_string_caption_lines`.
- Commands:
  - `apply_patch` on `transcription/extractor.py`
  - `apply_patch` add `tests/test_transcription_apify_parser.py`
  - `python -m py_compile transcription/extractor.py tests/test_transcription_apify_parser.py`
  - `python -m pytest tests/test_transcription_apify_parser.py tests/test_youtube_layer2_sync.py -q`
- Results:
  - focused tests passed: `5 passed`

## Step 009.2 - 2026-04-01 15:26:07 IST
- Files: `eshachanges.md`
- Summary:
  - Executed live transcript+comments backfill for Supabase entries fulfilling queue criteria.
  - Run 1 (`include_completed=False`, fallback enabled):
    - brand: `PW Live Smoke` (`97292c5e-f230-4732-8518-e159349eca07`)
    - eligible before: `4`
    - transcripts success: `4`, failed: `0`
    - comments success: `4`, failed: `0`
    - comments fetched: `1`, inserted: `0` (dedupe)
    - `pending_after`: `0`
    - Apify batch IDs:
      - `run_id`: `gr7fUYteib6PqobrJ`
      - `dataset_id`: `XM4O8g1kKB2U6ecW7`
  - Run 2 (`include_completed=True`, `use_fallback_transcript=False`) to enforce Apify-primary refresh after parser fix:
    - transcripts success: `4`, failed: `0`
    - comments success: `4`, failed: `0`
    - Apify batch IDs:
      - `run_id`: `d0p5NdugVuDXec926`
      - `dataset_id`: `aplsQaajeJL6dXeW1`
  - Source verification from `transcriptions` table confirms latest rows are now `source_type=apify_youtube_actor` for all 4 queued videos, with non-empty text lengths.
- Commands:
  - `python - <<'PY' ... run_youtube_layer2_fetch_sync_for_brand(... include_completed=False ...) ... PY`
  - `python - <<'PY' ... inspect transcriptions per mention/source ... PY`
  - `python - <<'PY' ... run_youtube_layer2_fetch_sync_for_brand(... include_completed=True, use_fallback_transcript=False ...) ... PY`
  - `python -m pytest tests -q`
- Results:
  - full tests passed: `29 passed in 1.77s`

## Step 009.3 - 2026-04-01 15:41:03 IST
- Files: `storage/queries.py`, `scrapers/youtube.py`, `tests/test_youtube_layer2_sync.py`, `tests/test_youtube_pipeline_smoke.py`, `eshachanges.md`
- Summary:
  - Rewired YouTube transcript persistence to `youtube_videos` table (video-level storage) while keeping comments in `youtube_comments`.
  - Added video-level transcript helpers in `storage/queries.py`:
    - `_get_mention_platform_context(...)`
    - `upsert_youtube_video_transcript(video_id, transcript)`
    - `get_youtube_video_transcript(video_id)`
  - Backward-compatible mention API updates:
    - `upsert_transcription_for_mention(...)` now routes YouTube mentions to `youtube_videos` transcript columns.
    - `get_transcription_by_mention(...)` now reads from `youtube_videos` for YouTube mentions.
    - Non-YouTube behavior for `transcriptions` table is unchanged.
  - Updated YouTube code paths to write transcripts directly to `youtube_videos`:
    - `run_youtube_layer2_fetch_sync_for_brand(...)`
    - `enrich_flagged_video_candidate(...)`
  - Updated tests to patch new helper (`upsert_youtube_video_transcript`) and verified suite remains green.
- Commands:
  - `apply_patch` on listed files
  - `python -m py_compile storage/queries.py scrapers/youtube.py tests/test_youtube_layer2_sync.py tests/test_youtube_pipeline_smoke.py`
  - `python -m pytest tests/test_youtube_layer2_sync.py tests/test_youtube_pipeline_smoke.py tests/test_workers_youtube_phases.py -q`
  - `python -m pytest tests -q`
- Results:
  - targeted tests: `9 passed`
  - full suite: `29 passed in 1.59s`

## Step 009.4 - 2026-04-01 15:41:03 IST
- Files: `eshachanges.md`
- Summary:
  - Applied live Supabase schema migration to `public.youtube_videos`:
    - `transcript_source_type text`
    - `transcript_text text`
    - `transcript_language text`
    - `transcript_duration_seconds integer`
    - `transcript_metadata jsonb`
    - `transcript_updated_at timestamptz`
    - indexes:
      - `idx_youtube_videos_transcript_updated_at`
      - `idx_youtube_videos_transcript_source_type`
  - Backfilled existing YouTube transcripts (`transcriptions` + `mentions`) into `youtube_videos` by `video_id`:
    - updated rows: `4`
    - video_ids: `-bhzSJShbY0`, `i5bB8gxmIM4`, `Iy51b8bJtCE`, `KZfAOfFj5pE`
  - Ran live rewired layer-2 pass to validate write path:
    - Apify run: `ve5kley84tpnuYxuT`
    - dataset: `aKildJfaL6WRP63K6`
    - transcript success: `4`
    - comments success: `4`
  - Verified joined view (`youtube_videos` + `youtube_comments` by `video_id`) and confirmed transcript columns populated:
    - `transcript_source_type=apify_youtube_actor`
    - non-zero `transcript_text_len` and fresh `transcript_updated_at` for queued videos
  - Verified no new YouTube transcript writes into `transcriptions` after rewire:
    - latest `transcriptions.created_at` remained at `2026-04-01T09:55:52.605197+00:00` (pre-rewire run).
- Commands:
  - `python - <<'PY' ... supabase database/query ALTER TABLE ... PY`
  - `python - <<'PY' ... supabase database/query UPDATE ... FROM latest ... PY`
  - `python - <<'PY' ... run_youtube_layer2_fetch_sync_for_brand(... include_completed=True, use_fallback_transcript=False) ... PY`
  - `python - <<'PY' ... verify youtube_videos transcript_* + youtube_comments by video_id ... PY`
  - `python - <<'PY' ... verify transcriptions latest timestamps ... PY`

## Step 010.1 - 2026-04-01 16:08:14 IST
- Files: `scrapers/youtube.py`, `workers/tasks.py`, `storage/queries.py`, `tests/test_youtube_layer3_sentiment_sync.py`, `tests/test_workers_youtube_phases.py`, `eshachanges.md`
- Summary:
  - Added new manual/cron-ready sync LLM pathways for layer-3 analysis:
    1. **Transcript sentiment (batch size 1 per video)**:
       - function: `run_youtube_transcript_sentiment_sync_for_brand(...)`
       - prompt stage: `transcript_sentiment_triage`
       - output normalized to: sentiment (`positive|neutral|negative`), priority (`low|medium|high`), monitor (`yes/no` -> bool), reason.
    2. **Comment sentiment (batch size 20 comments per call)**:
       - function: `run_youtube_comment_sentiment_sync_for_brand(...)`
       - prompt stage: `comment_sentiment_batch_triage`
       - payload includes per comment: Comment ID, Video title, Comment String, type of comment.
       - parser preserves exact comment ID case and lowercases sentiment labels.
  - Added parser/normalizer helpers:
    - `normalize_transcript_sentiment_triage(...)`
    - `parse_comment_sentiment_results(...)`
  - Added storage helpers for comment sentiment updates:
    - `update_youtube_comment_by_comment_id(...)`
    - `update_youtube_comment_sentiments(...)`
  - Added worker task wrappers for n8n/manual HTTP-trigger usage:
    - `run_youtube_transcript_sentiment_sync`
    - `run_youtube_comment_sentiment_sync`
- Commands:
  - `apply_patch` on listed files
  - `python -m py_compile scrapers/youtube.py workers/tasks.py storage/queries.py tests/test_youtube_layer3_sentiment_sync.py tests/test_workers_youtube_phases.py`
  - `python -m pytest tests/test_youtube_layer3_sentiment_sync.py tests/test_workers_youtube_phases.py tests/test_youtube_layer2_sync.py -q`
  - `python -m pytest tests -q`
- Results:
  - focused tests: `14 passed`
  - full suite after this step: `35 passed in 1.62s`

## Step 010.2 - 2026-04-01 16:08:14 IST
- Files: `eshachanges.md`
- Summary:
  - Applied Supabase migration for new layer-3 sentiment fields.
  - `youtube_videos` new columns:
    - `transcript_sentiment_label`
    - `transcript_sentiment_priority`
    - `transcript_sentiment_monitor`
    - `transcript_sentiment_reason`
    - `transcript_sentiment_custom_id`
    - `transcript_sentiment_processed_at`
  - `youtube_comments` new columns:
    - `comment_sentiment_label`
    - `comment_sentiment_custom_id`
    - `comment_sentiment_processed_at`
  - Added indexes for sentiment label and processed timestamps on both tables.
- Commands:
  - `python - <<'PY' ... supabase database/query ALTER TABLE youtube_videos + youtube_comments ... PY`
- Results:
  - migration status: `201 Created`

## Step 010.3 - 2026-04-01 16:08:14 IST
- Files: `eshachanges.md`
- Summary:
  - Ran live backfill of both new sync LLM pathways on current Supabase data.
  - Brand: `PW Live Smoke` (`97292c5e-f230-4732-8518-e159349eca07`)
  - Transcript sentiment run:
    - eligible total: `4`
    - processed: `4`
    - updated: `4`
    - failed: `0`
  - Comment sentiment run:
    - eligible videos: `4`
    - videos processed: `4`
    - batches processed: `1`
    - comments seen/classified/updated: `1 / 1 / 1`
    - failures: `0`
  - Verified DB values:
    - `youtube_videos` now has populated `transcript_sentiment_*` for 4 videos.
    - `youtube_comments` has populated `comment_sentiment_*` for comments with comment IDs.
    - join key remains `video_id` between `youtube_videos` and `youtube_comments`.
- Commands:
  - `python - <<'PY' ... run_youtube_transcript_sentiment_sync_for_brand(... force_reprocess=True) + run_youtube_comment_sentiment_sync_for_brand(... comment_batch_size=20, force_reprocess=True) ... PY`
  - `python - <<'PY' ... verify transcript_sentiment_* and comment_sentiment_* in Supabase ... PY`

## Step 010.4 - 2026-04-01 18:38:15 IST
- Files: `scrapers/youtube.py`, `tests/test_youtube_layer3_sentiment_sync.py`, `eshachanges.md`
- Summary:
  - Replaced transcript-analysis prompt with the new PR-risk focused prompt as provided (system semantics + strict output schema expectations).
  - Updated transcript PR normalization logic to align with new response schema fields:
    - `pr_sentiment`
    - `is_pr_risk`
    - `severity`
    - `issue_type`
    - `target_entity`
    - `transcript_summary`
    - `key_claims`
    - `brand_harm_evidence`
    - `protective_context`
    - `recommended_action`
    - `reason`
  - Implemented requested heuristic before save:
    - if `is_pr_risk=false` and `pr_sentiment=negative` and no explicit `brand_harm_evidence`, force sentiment away from negative (`neutral`).
  - Updated transcript sync payload keys to match requested prompt context:
    - `brand_name`, `video_title`, `channel_name`, `speaker_context`, `transcript_text`.
  - Updated layer-3 transcript write path to persist full PR schema and keep backward-compatible mirror fields.
  - Updated tests to validate PR-schema normalization and heuristic behavior.
- Commands:
  - `apply_patch` on `scrapers/youtube.py` + test updates
  - `python -m py_compile scrapers/youtube.py tests/test_youtube_layer3_sentiment_sync.py workers/tasks.py storage/queries.py`
  - `python -m pytest tests/test_youtube_layer3_sentiment_sync.py tests/test_workers_youtube_phases.py -q`
  - `python -m pytest tests -q`
- Results:
  - focused tests: `10 passed`
  - full suite: `35 passed in 1.58s`

## Step 010.5 - 2026-04-01 18:38:15 IST
- Files: `eshachanges.md`
- Summary:
  - Applied Supabase migration to accommodate full transcript PR-analysis response schema in `youtube_videos`.
  - Added columns:
    - `transcript_pr_sentiment`
    - `transcript_pr_is_risk`
    - `transcript_pr_severity`
    - `transcript_pr_issue_type`
    - `transcript_pr_target_entity`
    - `transcript_pr_summary`
    - `transcript_pr_key_claims` (jsonb)
    - `transcript_pr_brand_harm_evidence` (jsonb)
    - `transcript_pr_protective_context` (jsonb)
    - `transcript_pr_recommended_action`
    - `transcript_pr_reason`
    - `transcript_pr_custom_id`
    - `transcript_pr_processed_at`
    - `transcript_pr_raw` (jsonb)
  - Added indexes:
    - `idx_youtube_videos_transcript_pr_sentiment`
    - `idx_youtube_videos_transcript_pr_risk`
    - `idx_youtube_videos_transcript_pr_processed_at`
  - Re-ran live transcript PR-analysis sync with `force_reprocess=True`:
    - brand: `PW Live Smoke`
    - eligible: `4`
    - processed: `4`
    - updated: `4`
    - failed: `0`
  - Live verification confirms `youtube_videos.transcript_pr_*` fields are populated with expected neutral/positive non-risk labels for current sample set, including zero `brand_harm_evidence` where non-risk was inferred.
- Commands:
  - `python - <<'PY' ... supabase database/query ALTER TABLE youtube_videos ... PY`
  - `python - <<'PY' ... run_youtube_transcript_sentiment_sync_for_brand(... force_reprocess=True) ... PY`
  - `python - <<'PY' ... verify transcript_pr_* values ... PY`

## Step 010.6 - 2026-04-01 18:51:27 IST
- Files: `storage/queries.py`, `tests/test_storage_queries_youtube.py`, `eshachanges.md`
- Summary:
  - Fixed `youtube_comments` hydration gap where existing rows with missing `comment_id` were skipped instead of updated.
  - Updated `insert_youtube_comments_batch(...)` to hydrate by deterministic signature `(comment_author, comment_text, comment_date)` when:
    - incoming row has a real `comment_id`, and
    - matching existing row has empty `comment_id`.
  - Hydration now updates existing row fields (`comment_id`, parent/thread IDs, reply flags, counts, payload metadata) via update-by-row-id, while preserving insert behavior for truly new comments.
  - Added focused tests:
    - `test_insert_youtube_comments_batch_hydrates_missing_comment_id`
    - `test_insert_youtube_comments_batch_does_not_overwrite_existing_comment_id`
- Commands:
  - `apply_patch` on `storage/queries.py`
  - `apply_patch` on `tests/test_storage_queries_youtube.py`
  - `pytest -q tests/test_storage_queries_youtube.py` (initial run failed due PYTHONPATH)
  - `PYTHONPATH=. pytest -q tests/test_storage_queries_youtube.py`
  - `PYTHONPATH=. pytest -q tests/test_youtube_layer2_sync.py tests/test_youtube_layer3_sentiment_sync.py`
- Results:
  - `tests/test_storage_queries_youtube.py`: `4 passed`
  - `tests/test_youtube_layer2_sync.py + tests/test_youtube_layer3_sentiment_sync.py`: `8 passed`
  - Net effect: existing Supabase comment rows that were missing `comment_id` can now be hydrated during subsequent fetch cycles, enabling downstream comment-analysis joins by exact comment ID.

## Step 010.7 - 2026-04-01 19:15:47 IST
- Files: `eshachanges.md`
- Summary:
  - Ran live backfill to hydrate missing `youtube_comments.comment_id` values for existing Supabase rows.
  - Executed two passes:
    1. Layer-2 sync fetch backfill (`include_completed=true`) across monitored brands.
    2. Direct comments-only backfill across all `youtube_videos` for brand `PW Live Smoke` to maximize hydration coverage.
  - Hydration verification (brand `97292c5e-f230-4732-8518-e159349eca07`):
    - comments missing `comment_id` before direct pass: `34`
    - comments missing `comment_id` after direct pass: `1`
    - hydrated delta: `33`
  - Remaining missing row is on video `i5bB8gxmIM4` (single unmatched historic row).
  - One video comment fetch returned `403 Forbidden` for `f4ALl368AMk`; processing continued for other videos.
- Commands:
  - `set -a; source .env.local; set +a; PYTHONPATH=. python - <<'PY' ... run_youtube_layer2_fetch_sync_for_brand(... include_completed=True) paged loop ... PY`
  - `set -a; source .env.local; set +a; PYTHONPATH=. python - <<'PY' ... comments-only loop: fetch_comments_with_replies_sync + insert_youtube_comments_batch ... PY`
  - `set -a; source .env.local; set +a; PYTHONPATH=. python - <<'PY' ... verify missing comment_id rows ... PY`
- Results:
  - Layer-2 pass rollup (`PW Live Smoke`):
    - total candidates: `4`
    - processed: `4`
    - comments fetched: `2`
    - comments inserted: `1`
    - comments success/failed: `4/0`
    - transcript success/failed: `4/0`
  - Direct comments-only pass (`PW Live Smoke`):
    - videos attempted: `12`
    - videos failed: `1` (`403`)
    - comments fetched: `63`
    - comments inserted: `28`
    - comments total after: `64`
    - comments missing IDs: `34 -> 1`

## Step 010.8 - 2026-04-01 19:19:44 IST
- Files: `scrapers/youtube.py`, `tests/test_youtube_layer2_sync.py`, `eshachanges.md`
- Summary:
  - Added a transcript cost-control guard to prevent unnecessary Apify runs.
  - Layer-2 candidate collection now carries transcript presence metadata:
    - `has_transcript_text`
    - `existing_transcript_source_type`
  - Layer-2 fetch now sends only transcript-missing videos to Apify.
  - If transcript already exists, pipeline marks transcript step as completed using existing data and skips transcript rewrite.
  - Added summary metrics for visibility:
    - `transcript_requested_count`
    - `transcript_skipped_existing_count`
  - Added persistent guardrail note at top of changelog to keep this context available for every future test run.
- Commands:
  - `apply_patch` on `scrapers/youtube.py`
  - `apply_patch` on `tests/test_youtube_layer2_sync.py`
  - `apply_patch` on `eshachanges.md`
  - `PYTHONPATH=. pytest -q tests/test_youtube_layer2_sync.py`
  - `PYTHONPATH=. pytest -q tests/test_storage_queries_youtube.py tests/test_youtube_layer3_sentiment_sync.py`
- Results:
  - `tests/test_youtube_layer2_sync.py`: `5 passed`
  - `tests/test_storage_queries_youtube.py + tests/test_youtube_layer3_sentiment_sync.py`: `8 passed`
