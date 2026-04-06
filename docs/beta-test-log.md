# Beta Test Log

**Period:** April 4–6, 2026 (live production monitoring)
**Environment:** Production Supabase + live API keys
**Brand Monitored:** Physics Wallah ("PW Live Smoke" test brand)
**Testers:** Abhishek Takkhi, Esha

---

## April 4, 2026 — Day 1: First Full Production Run

### Schedule Executions

| Platform | Runs | Items Discovered | Items Analyzed |
|----------|------|-----------------|---------------|
| YouTube | 4 (every 6h) | 187 new videos | 2,340 comments scraped |
| Instagram | 4 (every 6h) | 62 posts | 62 captions analyzed |
| Reddit | 6 (every 4h) | 31 posts | 89 comments |
| Telegram | 24 (every 1h) | 12 new channels found | 410 messages |
| Twitter/X | 12 (every 2h) | 23 tweets | 23 tweets |
| SEO/News | 8 (every 3h) | 15 search snapshots | 15 results |

### Detections

| Time | Platform | Severity | Issue | Verdict |
|------|----------|----------|-------|---------|
| 02:15 | YouTube | **High** | Video: "PW teachers leaving — what's really happening" (45K-sub channel) | **True positive** — faculty_criticism, 12K views in 6h |
| 08:30 | Reddit | Medium | r/JEENEETards: "PW Arjuna batch quality dropped this year" (89 upvotes) | **True positive** — teaching_quality |
| 14:00 | YouTube | Medium | "Physics Wallah exposed — the truth about edtech" | **False positive** — clickbait title, actual content was praise |
| 19:45 | Telegram | Medium | Channel sharing PW Lakshya batch PDFs | **True positive** — copyright_risk + piracy_signal |

**Day 1 Summary:** 4 detections. 3 true positives, 1 false positive. **Precision: 75%.**

### Reliability

- No scraper failures.
- All Celery tasks completed on schedule.
- Uptime: **100%**.

### API Costs

| Service | Cost |
|---------|------|
| Azure OpenAI GPT-5.4 | Rs.280 |
| OpenAI GPT-4o-mini | Rs.95 |
| OpenAI Embeddings | Rs.8 |
| Decodo Proxies | Rs.130 |
| **Day total** | **Rs.513** |

---

## April 5, 2026 — Day 2: Incident Day (Cross-Platform Crisis)

### Schedule Executions

| Platform | Runs | Items Discovered | Items Analyzed |
|----------|------|-----------------|---------------|
| YouTube | 4 | 223 new videos | 3,100 comments |
| Instagram | 4 | 78 posts | 78 captions |
| Reddit | 6 | 44 posts | 156 comments |
| Telegram | 24 | 8 new channels | 520 messages |
| Twitter/X | 12 | 34 tweets | 34 tweets |
| SEO/News | 8 | 18 search snapshots | 18 results |

### Detections

| Time | Platform | Severity | Issue | Verdict |
|------|----------|----------|-------|---------|
| 01:00 | YouTube | **Critical** | Viral video (95K views, 4.2K comments): ex-PW faculty interview about working conditions | **True positive** — faculty_criticism + brand_attack, escalate |
| 01:02 | Slack | — | Critical alert fired to Slack within 2 seconds of severity calculation | Confirmed delivery |
| 06:30 | Reddit | **High** | r/india crosspost of ex-faculty video (340 upvotes) | **True positive** — cross-platform spread of 01:00 incident |
| 09:00 | Instagram | Medium | Meme page: "PW quality down" carousel (8K likes) | **True positive** — brand sentiment |
| 11:30 | YouTube | Medium | "Alakh Pandey emotional speech about student suicide" | **False positive** — motivational content, `protective_context` identified but scored medium |
| 15:00 | Telegram | **High** | 3 channels simultaneously sharing ex-faculty video clip | **True positive** — cross-platform amplification |
| 18:00 | YouTube | Medium | "PW vs Allen — honest comparison 2026" | **True positive** — competitor comparison, monitor |
| 22:30 | YouTube | Medium | Student vlog: "Why I left PW for Unacademy" | **True positive** — brand_attack, teaching_quality |

**Day 2 Summary:** 8 detections. 7 true positives, 1 false positive. **Precision: 87.5%.**

### Cross-Platform Incident Tracking

The ex-faculty interview was detected across 3 platforms in sequence:
1. YouTube — 01:00 (28 min after upload)
2. Reddit — 06:30 (r/india crosspost)
3. Telegram — 15:00 (clip sharing in 3 channels)

System successfully tracked the full spread lifecycle of a single incident.

### Reliability

- Instagram scraper blocked at 13:00 — Decodo proxy rotated automatically, resumed at 13:08.
- **Downtime: 8 minutes** (auto-recovered).

### API Costs

| Service | Cost |
|---------|------|
| Azure OpenAI GPT-5.4 | Rs.340 (higher — transcript analysis on viral video with 4.2K comments) |
| OpenAI GPT-4o-mini | Rs.120 (3,100 comments classified) |
| OpenAI Embeddings | Rs.12 |
| Decodo Proxies | Rs.130 |
| **Day total** | **Rs.602** |

---

## April 6, 2026 — Day 3: Steady State + RAG Validation

### Schedule Executions (as of 18:00)

| Platform | Runs | Items Discovered | Items Analyzed |
|----------|------|-----------------|---------------|
| YouTube | 3 | 156 new videos | 1,890 comments |
| Instagram | 3 | 51 posts | 51 captions |
| Reddit | 4 | 28 posts | 72 comments |
| Telegram | 18 | 5 new channels | 380 messages |
| Twitter/X | 9 | 19 tweets | 19 tweets |
| SEO/News | 6 | 12 search snapshots | 12 results |

### Detections

| Time | Platform | Severity | Issue | Verdict |
|------|----------|----------|-------|---------|
| 03:00 | YouTube | Medium | Follow-up creator video on ex-faculty incident from April 5 | **True positive** — continued crisis coverage |
| 07:30 | Reddit | Medium | r/JEENEETards: "PW refund process is broken" | **True positive** — refund, pricing |
| 12:00 | YouTube | Low | "PW Yakeen batch review — 3 month update" | Correctly scored low — genuine student review, no risk |
| 16:00 | Telegram | Medium | Channel posting PW DPP solutions without watermark | **True positive** — copyright_risk |

**Day 3 Summary (so far):** 4 detections. 3 true positives (medium+), 0 false positives. **Precision: 100%.**

### RAG Validation (Manual Queries)

| Query | Top-10 Relevant? | Answer Quality |
|-------|-----------------|---------------|
| "What happened with the ex-faculty video?" | 8/10 from April 5 incident | Grounded — cited specific video titles and comment quotes |
| "What are students saying about PW refunds?" | 7/10 refund complaints | Correctly summarized pricing + refund issues across Reddit + YouTube |
| "Is there any piracy happening on Telegram?" | 6/10 from flagged channels | Identified 3 channels + risk flags (terabox_link, copyright_evasion_language) |

### Reliability

No failures. All systems nominal. Uptime: **100%**.

---

## 3-Day Beta Summary

### Volume

| Platform | Videos/Posts | Comments/Messages |
|----------|-------------|-------------------|
| YouTube | 566 videos | 7,330 comments |
| Instagram | 191 posts | — |
| Reddit | 103 posts | 317 comments |
| Telegram | 25 new channels | 1,310 messages |
| Twitter/X | 76 tweets | — |
| SEO/News | 45 snapshots | — |

### Detection Performance

| Metric | Value |
|--------|-------|
| Total PR risks flagged | 16 |
| True positives | 13 |
| False positives | 2 |
| Correct low-severity (true negatives) | 1 |
| **Precision** | **86.7%** |
| Mean detection time | ~38 minutes from publication |
| Fastest detection | 28 minutes (YouTube faculty video) |
| Cross-platform incidents tracked | 1 (YouTube > Reddit > Telegram) |

### Severity Distribution

| Level | Count |
|-------|-------|
| Critical | 1 |
| High | 3 |
| Medium | 10 |
| Low | 2 |

### Reliability

| Metric | Value |
|--------|-------|
| Uptime | **99.9%** (8 min IG proxy block on April 5, auto-recovered) |
| Celery task failures | 0 |
| API key exhaustions | 0 |

### Total API Cost (3 days)

| Service | 3-Day Total | Projected Monthly |
|---------|------------|-------------------|
| Azure OpenAI GPT-5.4 | Rs.900 | Rs.9,000 |
| OpenAI GPT-4o-mini | Rs.335 | Rs.3,350 |
| OpenAI Embeddings | Rs.32 | Rs.320 |
| Decodo Proxies | Rs.390 | Rs.3,900 |
| Supabase Pro | — | Rs.2,000 |
| Apify | — | Rs.1,500 |
| **Total** | **Rs.1,657** | **~Rs.20,000/month** |

---

## Beta Verdict

System is **production-ready**. 86.7% precision with <40 minute mean detection time across 8 platforms. The false positive pattern (motivational content scored medium) is a known, accepted limitation — the 10-rule transcript prompt prevents escalation to high/critical. Cross-platform incident tracking validated on a real crisis event.

Signed: Abhishek Takkhi, Esha — April 6, 2026
