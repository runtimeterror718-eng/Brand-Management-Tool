---
paths:
  - "scrapers/**/*.py"
  - "analysis/**/*.py"
  - "severity/**/*.py"
  - "workers/**/*.py"
  - "storage/**/*.py"
  - "search/**/*.py"
  - "alerts/**/*.py"
  - "brand/**/*.py"
  - "config/**/*.py"
  - "transcription/**/*.py"
---

# Python Backend Rules

- Python 3.11+ — use modern syntax (match/case, type unions with `|`)
- All scrapers must inherit rate limiting from `scrapers/base.py`
- Use `config/settings.py` for env access — never `os.getenv` directly
- Supabase operations go through `storage/queries.py` — no raw client calls in business logic
- Hinglish text is first-class: always consider `config/hinglish_lexicon.py` when touching sentiment/severity
- Register new scrapers via `search.engine.register_searcher`
- Celery tasks live in `workers/tasks.py`, schedules in `workers/schedule.py`
- Use dataclasses from `storage/models.py` for typed data structures
