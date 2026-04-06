# Team Ownership Rules

When modifying platform-specific code, respect ownership boundaries:

- **Team A owns**: `scrapers/instagram.py`, `scrapers/reddit.py`, `scrapers/seo_news.py`, `scrapers/twitter.py`
- **Team B owns**: `scrapers/youtube.py`, `scrapers/telegram.py`, `scrapers/facebook.py`, `scrapers/linkedin.py`
- **Shared**: `brandscope/`, `storage/`, `analysis/`, `severity/`, `alerts/`, `config/`, `workers/`

When in doubt about ownership, check `docs/team-ownership.md` for the detailed boundary map.
Do not make breaking changes to another owner's scraper without explicit coordination.
