# Alpha Test Log

**Period:** April 2–3, 2026
**Environment:** Staging Supabase instance + sandbox API keys
**Testers:** Abhishek Takkhi, Esha
**Objective:** Validate all scrapers, AI pipeline, and integration before production deployment.

---

## April 2, 2026 — Scraper & AI Pipeline Validation

### Scraper Health (09:00–13:00)

| Time | Test Case | Platform | Result | Notes |
|------|-----------|----------|--------|-------|
| 09:00 | YouTube search executes all 3 query buckets (primary 203 + secondary 73 + expanded 40) | YouTube | PASS | 316 terms across 10 rotating API keys; 0 quota exhaustion events |
| 09:30 | Official channel blacklist (55 IDs + 9 handles) filters owned content | YouTube | PASS | Verified against `YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL` — no owned-channel leakage |
| 10:00 | Instagram curl_cffi + Decodo proxy session initializes and fetches | Instagram | PASS | Chrome fingerprint accepted; session TTL 3600s; 35 keywords + 13 hashtags queried |
| 10:30 | Reddit JSON API searches 6 queries x 7 subreddits | Reddit | PASS | 42 search combos completed in ~3 min; no 429 rate limits |
| 11:00 | Telegram discovery across 20 seed keywords | Telegram | PASS | "pw" filtered via `AMBIGUOUS_DISCOVERY_TERMS`; 148 channels indexed |
| 11:30 | Google SEO scraper returns autocomplete + PAA + organic results | SEO/News | PASS | Autocomplete suggestions + People Also Ask captured |
| 12:00 | Transcript fallback chain: YouTube captions > Apify > Whisper | YouTube | PASS | Tested on 50 videos: 38 captions, 7 Apify, 3 Whisper, 2 no-audio shorts |
| 12:30 | yt-dlp download strategies (Chrome/Safari/iOS/Android/plain) | YouTube | PASS | iOS client most reliable; all 5 strategies exercised without failure |

### AI Pipeline (13:00–17:00)

| Time | Test Case | Component | Result | Notes |
|------|-----------|-----------|--------|-------|
| 13:00 | Title triage on 50 sample videos | Azure GPT-5.4 | PASS | 41/50 correct; 9 "uncertain" on ambiguous titles (expected) |
| 13:45 | Transcript sentiment: 10 motivational videos | Azure GPT-5.4 | PASS | 0/10 misclassified as negative — 10-rule PR-risk prompt working |
| 14:30 | Comment batch: 200 Hinglish comments | GPT-4o-mini | PASS | 87% agreement (English), 81% (Hinglish) |
| 15:00 | LLM enrichment: 100 mentions (intent/emotion/urgency) | GPT-4o-mini | PASS | 4 batches of 30, completed in ~45 seconds |
| 15:45 | Deep clustering on 1,200 staging mentions | HDBSCAN | PASS | 6 themes, 19 topics, 43 subtopics; silhouette 0.44 |
| 16:15 | Composite embedding 70/30 text/metadata split | MiniLM | PASS | Pricing complaints clustered separately from pricing questions |
| 16:45 | RAG query: "What are students saying about refunds?" | pgvector + LLM | PASS | 8/10 top results relevant; answer cited 4 specific comments |

**Issues:** None critical.

---

## April 3, 2026 — Integration & Storage Validation

### Storage & Dedup (09:00–12:00)

| Time | Test Case | Result | Notes |
|------|-----------|--------|-------|
| 09:00 | Upsert 500 duplicate YouTube videos | PASS | `on_conflict="video_id"` prevents duplicates; metadata updated |
| 09:30 | Cross-platform dedup: identical content on Reddit + Telegram | PASS | MD5 fingerprint (first 200 chars, normalized) — higher-engagement version retained |
| 10:00 | Embedding storage: verify 384d (MiniLM) + 1536d (OpenAI) columns | PASS | Both `embedding` and `embedding_openai` populated in `mention_embeddings` |
| 10:30 | pgvector search: `match_mentions_openai` RPC | PASS | 0.3 cosine threshold, 10 results in <200ms |
| 11:00 | Hinglish crisis keywords: 200+ terms on 100 sample texts | PASS | Severity-weighted matching from `config/hinglish_lexicon.py` correct |

### Severity & Alerting (12:00–15:00)

| Time | Test Case | Result | Notes |
|------|-----------|--------|-------|
| 12:00 | Severity scoring on 50 flagged mentions | PASS | Distribution: 3 critical, 8 high, 21 medium, 18 low — reasonable |
| 12:30 | Slack webhook: simulate critical alert | PASS | Delivered in <2 seconds with video URL + title + severity + issue_type |
| 13:00 | Email weekly report generation | PASS | Monday 9 AM Celery schedule verified via manual trigger |
| 13:30 | Celery Beat: all 8 platform schedules fire correctly | PASS | YT/IG 6h, Reddit 4h, Telegram 1h, Twitter 2h, SEO 3h, alerts 30m |

### End-to-End Pipeline (15:00–16:00)

| Time | Test Case | Result | Notes |
|------|-----------|--------|-------|
| 15:00 | Full YouTube pipeline for 1 video: discovery > triage > transcript > comments > severity > storage | PASS | Completed in ~4 minutes end-to-end |
| 15:30 | Full Reddit pipeline: search > scrape > triage > mention > severity | PASS | Completed in ~2 minutes |
| 16:00 | Telegram: channel discovery > classification > message fetch > risk analysis | PASS | Completed in ~3 minutes |

### Known Issue (Accepted)

`mention_embeddings.mention_id` is NULL for YouTube comments because they originate from `youtube_comments` table, not `mentions`. Back-join only possible via `content_text` matching. Accepted for MVP.

---

## Alpha Sign-Off

All scraper, AI pipeline, and integration tests pass. **Cleared for beta deployment on production environment.**

Signed: Abhishek Takkhi, Esha — April 3, 2026
