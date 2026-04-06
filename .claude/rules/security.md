# Security Rules

- Never commit `secrets/` contents (`.env.keys`, cookies, sessions) — only `.env.keys.example` is committed
- Never commit `.env` with real credentials — config-only values are fine
- Never log or print credentials, tokens, or Supabase service keys
- All API keys and passwords live exclusively in `secrets/.env.keys`
- Session/cookie files (IG cookies, instaloader sessions) live in `secrets/`
- Use `SUPABASE_KEY` (anon) for frontend, `SUPABASE_SERVICE_KEY` (admin) only in backend workers
- Rate limit all external API calls through `scrapers/base.py` retry/backoff
- Validate all user input in API routes before passing to Supabase queries
- When adding a new API key, add it to both `secrets/.env.keys` AND `secrets/.env.keys.example`
