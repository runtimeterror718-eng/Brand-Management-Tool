# OVAL — Product Specification Document

> **Version**: 1.0 (MVP)
> **Date**: April 6, 2026
> **Team**: Abhishek Takkhi, Esha
> **Status**: MVP Submission Round

---

## 1. Executive Summary

OVAL is a real-time brand intelligence platform built for Physics Wallah (PW), India's largest edtech company (13M+ Instagram followers, $3.5B IPO valuation). It monitors brand mentions across 5 platforms, classifies every piece of content using LLMs, and generates department-wise action items grounded in real evidence — giving PW's brand team a 6-hour head start on PR crises.

**Tagline**: *See what they say before it spreads.*

---

## 2. Problem Statement

### The Business Problem
- PW gets mentioned **1,900+ times** across social media platforms daily
- A negative Reddit post reaches 10K views in 12 hours
- Google autocomplete shows "physics wallah scam" to every searching parent
- Consumer court ordered ₹50K compensation in March 2026 — PW's team found out from news, not from monitoring
- Teacher exodus narrative spreading across Reddit → Instagram → YouTube pipeline
- 2 fake Telegram channels impersonating PW with combined 1,400 members

### Why Existing Tools Fail
| Tool | Limitation |
|------|-----------|
| Brandwatch / Meltwater | No Hinglish understanding, no Indian platform coverage, $5K+/month |
| Google Alerts | Text-only, no sentiment, no Reels audio, 24hr delay |
| Manual monitoring | 3-person team can't cover 5 platforms × 1,900 mentions/day |
| Social listening tools | Show mentions, don't tell you what to DO about them |

### OVAL's Advantage
- **Understands Hinglish**: "paisa doob gaya" and "refund nahi diya" correctly classified as negative
- **Listens to Reel audio**: 90% of Instagram Reels have empty captions — the complaint is in the spoken Hindi
- **Routes to departments**: Doesn't just show data — generates specific tasks for HR, Product, PR, Legal, Engineering
- **Evidence-grounded**: Every insight cites real scraped quotes, not LLM hallucinations (RAG architecture)

---

## 3. Product Architecture

### 3.1 System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        DATA COLLECTION                           │
│                                                                  │
│  Instagram ─┐                                                    │
│  (curl_cffi │                                                    │
│   + proxies)│                                                    │
│             ├──→ Supabase PostgreSQL                             │
│  Reddit ────┤    (platform tables + unified mentions table)      │
│  (JSON API) │                                                    │
│             │                                                    │
│  YouTube ───┤                                                    │
│  (Data API  │                                                    │
│   4-key     │                                                    │
│   rotation) │                                                    │
│             │                                                    │
│  Telegram ──┤                                                    │
│  (Telethon) │                                                    │
│             │                                                    │
│  Google ────┘                                                    │
│  (Autocomplete                                                   │
│   + News RSS                                                     │
│   + Trends                                                       │
│   + Custom                                                       │
│   Search API)                                                    │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                     PROCESSING LAYER                             │
│                                                                  │
│  1. Sentiment Classification (GPT-4o-mini / Azure GPT-5.4)      │
│     → positive / negative / neutral per mention                  │
│                                                                  │
│  2. OpenAI Embedding (text-embedding-3-small, 1536d)             │
│     → every mention converted to searchable vector               │
│                                                                  │
│  3. KMeans Clustering (paraphrase-multilingual-MiniLM-L12-v2)    │
│     → 32 topic clusters from 1,907 mentions                     │
│                                                                  │
│  4. Reel Audio Transcription (yt-dlp → Whisper proxy)            │
│     → Hindi/Hinglish audio → text                               │
│                                                                  │
│  5. Geographic Inference                                         │
│     → subreddit mapping + keyword extraction + IG location tags  │
│                                                                  │
│  6. Hinglish Lexicon (350+ terms, 10 categories)                 │
│     → crisis detection for Indian social media slang             │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                        RAG ENGINE                                │
│                                                                  │
│  Query → Embed (OpenAI 1536d)                                    │
│       → pgvector HNSW cosine similarity search                   │
│       → LLM Reranker (filter noise)                              │
│       → GPT generates grounded answer                            │
│       → Confidence scoring                                       │
│                                                                  │
│  5 search functions:                                             │
│    match_mentions_openai (all)                                   │
│    match_mentions_negative (negative-only)                       │
│    match_mentions_by_sentiment (filtered)                        │
│    match_mentions_by_platform (platform + sentiment)             │
│    match_clusters_openai (cluster summaries)                     │
└───────────────────────────┬──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                     OVAL DASHBOARD                               │
│                                                                  │
│  Landing Page      → Hero animation with tagline                 │
│  Command Center    → Health score, alerts, risks, signals        │
│  Platform Intel    → Reddit, Instagram, YouTube, Telegram, Google│
│  Neural Map        → Force-directed graph (G6 engine)            │
│  Creator Intel     → Friend vs Threat classification             │
│  Competitors       → Share of voice, sentiment comparison        │
│  Action Items      → Department-wise tasks with team routing     │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Database Schema

**Core Tables (Supabase PostgreSQL)**:

| Table | Records | Purpose |
|-------|---------|---------|
| `brands` | 4 | Brand definitions |
| `mentions` | 728 | Unified cross-platform mentions |
| `mention_embeddings` | 1,907 | Embedded mentions with OpenAI 1536d vectors + sentiment |
| `cluster_embeddings` | 32 | Cluster summaries with vectors |
| `instagram_posts` | 144 | IG posts with triage fields |
| `instagram_comments` | 1,000+ | IG comments with sentiment |
| `reddit_posts` | 50 | Reddit posts with triage |
| `reddit_comments` | 200 | Reddit comments with sentiment |
| `youtube_videos` | 84 | YT videos (52 columns — triage, transcript, PR analysis) |
| `youtube_channels` | 74 | YT channels tracked |
| `youtube_comments` | 115 | YT comments with sentiment |
| `telegram_channels` | 10 | TG channels (classification, fake detection) |
| `telegram_messages` | 697 | TG messages with risk scoring |
| `google_autocomplete` | 79 | Autocomplete suggestions with sentiment |
| `google_news` | 30 | News articles |
| `google_trends` | — | Trend time series + regional data |
| `google_seo_results` | — | SERP organic results |
| `geo_mentions` | — | Per-mention geographic signals |
| `geo_aggregates` | — | State-level aggregated stats |

**pgvector Functions**:

| Function | Purpose |
|----------|---------|
| `match_mentions_openai` | Cosine similarity search across all mentions |
| `match_mentions_negative` | Negative-only vector search |
| `match_mentions_by_sentiment` | Filtered by sentiment label |
| `match_mentions_by_platform` | Filtered by platform + sentiment |
| `match_clusters_openai` | Cluster summary similarity search |

---

## 4. Frontend Specification

### 4.1 Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Next.js | 14.2.35 | App Router, SSR, API routes |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 3.x | Utility-first styling |
| Recharts | 3.8.1 | Charts (Pie, Bar, Area, Line) with animation |
| Framer Motion | 12.38 | Page entrance animations, stagger, hover effects |
| react-simple-maps | — | India geographic map with GeoJSON |
| @ant-design/graphs | — | NetworkGraph for neural map (G6 engine) |
| react-loading-skeleton | — | Skeleton loading screens |
| sonner | — | Toast notifications |
| cmdk | — | Cmd+K command palette |
| lucide-react | — | Icon library |

### 4.2 Pages

| Page | Route | Purpose |
|------|-------|---------|
| Hero Landing | `/` | Animated landing with tagline, no sidebar |
| Command Center | `/command-center` | Executive briefing — health score, alerts, risks |
| Reddit Intel | `/reddit` | Posts, sentiment, subreddits, India map |
| Instagram Intel | `/instagram` | Posts, hashtags, accounts, comments |
| YouTube Intel | `/youtube` | Videos, PR risk flags, channels, comments |
| Telegram Intel | `/telegram` | Channels, fake detection, risk scoring |
| Google Intel | `/google` | Autocomplete, trends, SERP, news |
| Neural Map | `/neural-map` | Interactive force-directed network graph |
| Creator Intel | `/creators` | Friend/threat/neutral classification |
| Competitors | `/competitors` | Share of voice, sentiment per competitor |
| Action Items | `/actionables` | Department-wise tasks with "Send to Team" |

### 4.3 Key UI Components

| Component | File | Purpose |
|-----------|------|---------|
| `BrandScoreCards` | `components/ui/brand-score-cards.tsx` | Animated half-circle gauges with info tooltip |
| `AnimatedChart` | `components/ui/animated-chart.tsx` | IntersectionObserver scroll-triggered chart animation |
| `AnimatedNumber` | `components/ui/animated-chart.tsx` | Count-up number animation on scroll |
| `MetricCard` | `components/ui/metric-card.tsx` | Metric card with sparkline + trend arrow + hover |
| `PageSkeleton` | `components/ui/page-skeleton.tsx` | Skeleton loading screen (metrics, charts, posts) |
| `RAGInsight` | `components/dashboard/rag-insight.tsx` | AI analysis card with bullet parsing + markdown stripping |
| `IndiaMap` | `components/dashboard/india-map.tsx` | react-simple-maps India map with state bubbles |
| `CommandPalette` | `components/ui/command-palette.tsx` | Cmd+K search across all pages |
| `AppShell` | `components/layout/app-shell.tsx` | Conditional sidebar (hidden on landing page) |
| `HeroLanding` | `components/ui/hero-landing.tsx` | Animated landing page with grid, particles, ripples |

### 4.4 Design System

| Element | Value |
|---------|-------|
| Primary accent | #534AB7 (purple) |
| Positive/safe | #639922 (green) |
| Negative/danger | #E24B4A (red) |
| Warning | #BA7517 (amber) |
| Reddit | #FF5700 |
| Instagram | #E1306C |
| YouTube | #FF0000 |
| Telegram | #0088CC |
| Google | #4285F4 |
| Font (UI) | DM Sans (Inter fallback) |
| Font (editorial) | Merriweather |
| Card style | Solid bg, border-border, shadow-sm, hover:shadow-md |
| Metric labels | text-[10px] uppercase tracking-widest |
| Animation | Framer Motion fadeUp with stagger 0.12s |
| Chart animation | Recharts animationDuration={1500} |

---

## 5. Backend Specification

### 5.1 Tech Stack

| Technology | Purpose |
|-----------|---------|
| Python 3.9 | Primary backend language |
| Celery | Distributed task queue |
| Redis | Message broker for Celery |
| Supabase Python SDK | Database operations |
| OpenAI SDK | Embeddings + GPT calls |
| httpx | Async HTTP client (YouTube API) |
| curl_cffi | Chrome TLS fingerprinting (Instagram) |
| Telethon | Telegram client |
| yt-dlp | Audio download (YouTube/Instagram) |
| BeautifulSoup | HTML parsing (Google SERP) |
| pytrends | Google Trends |
| feedparser | Google News RSS |
| sentence-transformers | MiniLM embeddings (clustering) |
| scikit-learn | KMeans clustering |

### 5.2 Scraper Specifications

#### Instagram Scraper (`scrapers/instagram.py`)

| Feature | Detail |
|---------|--------|
| Method | Reverse-engineered web API via curl_cffi Chrome fingerprinting |
| Auth | Burner account with stored session cookies |
| Proxies | 10 Decodo Indian residential proxy IPs |
| Rate limiting | Adaptive: 2-5s delay, exponential backoff on 429 |
| Sessions | Pool of 5 concurrent authenticated sessions |
| Accounts monitored | 48 (10 own brand + 8 competitor + 6 ex-PW + 10 ecosystem + 14 influencers) |
| Hashtags monitored | 15 (#physicswallah, #pwscam, #pwexposed, etc.) |
| LLM triage | Every caption classified by Azure GPT-5.4 |
| Reel audio | yt-dlp download → Whisper proxy → Hindi transcript → GPT analysis |
| Comment classification | Batch of 30 → GPT sentiment labels |
| Final synthesis | Caption + transcript + comments → severity + recommended action |
| New Supabase columns | 22 intelligence fields (triage label, PR risk, severity, transcript, etc.) |

#### Reddit Scraper (`scrapers/reddit.py`)

| Feature | Detail |
|---------|--------|
| Method | Public JSON API (no auth required) |
| Subreddits | JEENEETards, IndianAcademia, btechtards, Indian_Education, CBSE, india, indiasocial |
| Queries | "physicswallah", "alakh pandey", "PW scam OR fraud", "PW teachers leaving OR refund" |
| Rate limiting | 1-2s random delay, 10s sleep on 429 |
| LLM triage | Every post (title + body) classified by GPT |
| Comment classification | Batch of 30 → sentiment labels |
| Final synthesis | Post triage + comment sentiment → verdict + recommended action |

#### YouTube Scraper (`scrapers/youtube.py` — Esha's pipeline)

| Feature | Detail |
|---------|--------|
| Method | YouTube Data API v3 |
| API keys | 4 keys with auto-rotation (thread-safe `_KeyPool` class) |
| Keywords | 250+ terms grouped into 15 OR-queries (saves 90% quota) |
| Lookback | 90 days (3 months) |
| Comment cap | 10,000 per video (effectively unlimited) |
| Official blacklist | 63 channel IDs + 11 handles filtered out |
| Layer 1 | Title triage — Azure GPT-5.4 classifies title as PR risk |
| Layer 2 | Transcript fetch — YouTube captions → Whisper fallback |
| Layer 3 | Transcript sentiment + comment batch sentiment + final synthesis |
| Issue types | 13 categories: brand_attack, faculty_criticism, pricing, refund, controversy, etc. |
| Recommended actions | ignore / monitor / respond / escalate |
| Schema | 52 columns on youtube_videos |

#### Telegram Scraper (`scrapers/telegram.py` — Esha's pipeline)

| Feature | Detail |
|---------|--------|
| Method | Telethon client (requires API_ID + API_HASH + phone OTP) |
| Channels discovered | 10 (1 official, 7 fan, 2 suspicious/fake) |
| Channel classification | LLM classifies as official / fan_unofficial / suspicious_fake |
| Fake detection | 2 channels flagged (pwskillshub, physics_wala_freelectures) |
| Message risk scoring | Each message scored: safe / suspicious / copyright_infringement |
| Messages analyzed | 697 (Oct 2025 — Apr 2026) |

#### Google Scraper (`scrapers/google_search.py`)

| Feature | Detail |
|---------|--------|
| Autocomplete | 32 queries (brand + a-z alphabet expansion + risk terms) |
| SERP | 8 queries (3 brand + 3 risk + 2 competitor) via Custom Search API |
| News | 4 queries via Google News RSS |
| Trends | PW vs Allen vs Unacademy vs BYJU's (90 days, by Indian state) |
| LLM triage | Autocomplete batch + news batch classified by GPT |
| People Also Ask | Negative PAA stored as mentions for RAG |

### 5.3 Celery Task Schedule

| Task | Frequency |
|------|-----------|
| Instagram scrape | Every 6 hours |
| Reddit scrape | Every 4 hours |
| YouTube scrape | Every 6 hours |
| Telegram scrape | Every 1 hour |
| SEO/News scrape | Every 3 hours |
| Full analysis | Daily at 2 AM |
| Alert check | Every 30 minutes |
| Weekly report | Monday 9 AM |

---

## 6. LLM & AI Specification

### 6.1 Models Used

| Model | Provider | Purpose | Cost |
|-------|----------|---------|------|
| `gpt-4o-mini` | OpenAI | Sentiment classification, RAG generation, reranking | $0.15/1M input |
| `gpt-5.4-marketing-southcentralus` | Azure OpenAI | YouTube/Telegram triage, Instagram caption triage | Via Azure deployment |
| `text-embedding-3-small` | OpenAI | 1536-dim embeddings for all mentions | $0.02/1M tokens |
| `paraphrase-multilingual-MiniLM-L12-v2` | HuggingFace (local) | 384-dim embeddings for clustering | Free (local) |
| Whisper v3 | Yotta proxy | Hindi/Hinglish audio transcription | Via proxy endpoint |

### 6.2 RAG Pipeline

```
Query: "What are students complaining about?"
    ↓
Step 1: Embed query → OpenAI text-embedding-3-small → [1536 floats]
    ↓
Step 2: pgvector search → match_mentions_negative(embedding, threshold=0.25, limit=20)
         HNSW index returns 20 most similar negative mentions in <50ms
    ↓
Step 3: LLM Reranker → GPT reads 20 candidates, returns indices of 10 most relevant
    ↓
Step 4: Generate → GPT reads 10 verified mentions + cluster context → grounded answer
    ↓
Step 5: Confidence = (count_score × 0.4) + (similarity_score × 0.6)
    ↓
Step 6: Cache result (30 min TTL) → next request returns in <50ms
```

### 6.3 Actionables Generation

14 semantic probes across 10 PW departments:

| Department | Probes | Search Query |
|-----------|--------|-------------|
| Product Team | 2 | Teacher quality, content freshness |
| Finance Team | 2 | IPO perception, refund policy |
| Legal Team | 1 | Consumer court, legal complaints |
| HR Team | 1 | Employer brand, sell-a-pen interviews |
| Batch Operations Team | 1 | Batch quality, DPP, test series |
| YouTube Team | 1 | YouTube PR risk, controversy videos |
| PR Team | 2 | Scam narrative, political content |
| Vidyapeeth Operations Team | 1 | Offline centre experience |
| Engineering Team | 1 | App crashes, buffering |
| Marketing Team | 1 | Aggressive upselling |
| Customer Support Team | 1 | Ticket response, chatbot complaints |

Each probe: embed → negative-only search → rerank → GPT generates task → priority scored → routed to department.

### 6.4 Hinglish Lexicon

350+ terms across 10 categories with sentiment weights (-1.0 to +1.0):

| Category | Examples | Weight |
|----------|---------|--------|
| Crisis | "boycott karo", "scam hai", "paisa doob gaya" | -0.7 to -1.0 |
| Positive | "zabardast", "legend hai", "goat" | +0.6 to +0.9 |
| Profanity | Full forms + abbreviations + leetspeak | -0.7 to -1.0 |
| Brand complaints | "refund nahi diya", "quality ghatiya" | -0.5 to -0.8 |
| Political flags | "sanghi", "librandu", "paid troll" | -0.3 to -0.7 |
| Instagram spam | "follow back", "f4f", "dm for collab" | 0.0 |

---

## 7. Clustering Specification

### 7.1 Method

| Parameter | Value |
|-----------|-------|
| Algorithm | KMeans (switched from HDBSCAN due to 64-87% noise on mixed-language data) |
| Embedding | paraphrase-multilingual-MiniLM-L12-v2 (384d) for clustering |
| Embedding (RAG) | text-embedding-3-small (1536d) for search |
| Total clusters | 32 (20 cross-platform + 8 YouTube + 10 Telegram) |
| Noise | 0% (KMeans assigns every point) |

### 7.2 Cluster Distribution

| Category | Clusters | Mentions | % |
|----------|----------|----------|---|
| NEGATIVE | 7 | 375 | 26% |
| APPRECIATION | 5 | 345 | 24% |
| REQUEST | 3 | 337 | 23% |
| MIXED/NEUTRAL | 2 | 211 | 15% |
| SPAM | 2 | 102 | 7% |
| POLITICAL | 1 | 69 | 5% |

---

## 8. Geographic Intelligence

### 8.1 Inference Methods

| Method | Source | Confidence |
|--------|--------|-----------|
| Subreddit → State | r/mumbai → Maharashtra | 0.85 |
| Instagram location tag | Post metadata | 0.95 |
| Text keyword extraction | City/state names in text | 0.75 |
| PW Vidyapeeth centres | "vidyapeeth bhopal" → MP | 0.90 |
| Comment keyword fallback | State names in comments | 0.65 |

### 8.2 Coverage
- 23 Indian states mapped with lat/lng
- 80+ cities → state mappings
- 15 PW Vidyapeeth campus locations
- India GeoJSON with 36 states/UTs for map visualization

---

## 9. Performance & Cost

### 9.1 Response Times

| Operation | Time |
|-----------|------|
| pgvector search (1,907 vectors) | <50ms |
| API response (cached) | <50ms |
| API response (cold, no RAG) | 200-500ms |
| API response (cold, with RAG) | 5-15s (first load, then cached 30 min) |
| Full page load (cached) | <1s |
| OpenAI embedding (single text) | ~200ms |
| Whisper transcription | 5-10s per video |

### 9.2 API Costs

| Operation | Cost |
|-----------|------|
| Embed 1,907 mentions | $0.006 |
| Classify 1,907 mentions | $0.08 |
| Single dashboard page load (RAG) | ~$0.02 |
| Full actionables (14 probes) | ~$0.05 |
| Monthly estimate (moderate use) | ~$10-15 |
| At 1 lakh mentions/day | ~$36/month |

### 9.3 Caching Strategy

| Cache | TTL | What |
|-------|-----|------|
| RAG query results | 30 min | Embedding + search + rerank + generation |
| API route responses | 5 min | Full JSON response for each endpoint |
| In-memory (Next.js) | Session | State between page navigations |

---

## 10. Security

### 10.1 Credential Management
- All API keys in `.env` (gitignored)
- `.env.example` has placeholders only
- `.gitignore` covers: `.env`, `.env.local`, `.ig-cookies.json`, `.instaloader-session-*`, `.mcp.json`, `.claude/`
- Supabase service key used server-side only (never exposed to frontend)

### 10.2 Data Access
- Supabase Row Level Security (RLS) available but not enforced in MVP
- API routes use service key (bypasses RLS)
- Frontend uses `NEXT_PUBLIC_SUPABASE_KEY` (anon key, read-only)

---

## 11. Go-To-Market Strategy

### 11.1 Target Users

**Primary**: Physics Wallah's internal brand/PR team (5-10 people)

**Expansion targets**:
- Other edtech companies (Allen, Unacademy, Aakash)
- Indian D2C brands with large social media presence
- IPO-stage startups needing brand monitoring
- PR agencies managing Indian brands

### 11.2 Value Proposition by Persona

| Persona | Pain Point | OVAL's Answer |
|---------|-----------|---------------|
| CEO (Alakh Pandey) | "Am I safe this week?" | Command Center — 30-second health check |
| PR Lead | "What fires need putting out?" | Action Items — department-routed tasks with evidence |
| Platform Manager | "What's happening on MY platform?" | Platform Intel — filterable, searchable, with charts |
| Product Manager | "What are users complaining about?" | Actionables — issue → evidence → action pipeline |
| Legal Team | "Are there court cases we don't know about?" | Google Intel — consumer court mentions, legal autocomplete |
| Investor Relations | "How does market perceive our IPO?" | IPO probe — stock discussion sentiment from Reddit/YouTube |

### 11.3 Competitive Positioning

| Feature | Brandwatch | Sprinklr | Meltwater | OVAL |
|---------|-----------|---------|----------|------|
| Hinglish understanding | No | Limited | No | Yes (350+ term lexicon) |
| Reel audio transcription | No | No | No | Yes (Whisper) |
| Fake channel detection | No | No | No | Yes (Telegram) |
| RAG-grounded insights | No | No | No | Yes (pgvector) |
| Department routing | Manual | Manual | Manual | Automated (14 probes) |
| India-specific geo mapping | No | Limited | No | Yes (23 states) |
| Price | $5K+/mo | $10K+/mo | $3K+/mo | ~$15/mo (AI costs) |

### 11.4 Pricing Strategy (Post-MVP)

| Tier | Price | Includes |
|------|-------|----------|
| Starter | $99/mo | 1 brand, 3 platforms, 10K mentions/mo, daily scraping |
| Growth | $299/mo | 3 brands, 5 platforms, 50K mentions/mo, 4hr scraping, team routing |
| Enterprise | $799/mo | Unlimited brands, all platforms, unlimited mentions, real-time, Slack/WhatsApp alerts, custom probes |

### 11.5 Launch Roadmap

**Phase 1 — MVP (Current)**
- 5 platforms monitored
- RAG-powered insights
- Department action items
- Manual scrape triggers

**Phase 2 — Production (Month 2-3)**
- Real-time Slack/WhatsApp alerts
- Automated scraping on schedule (Celery + Redis)
- XLM-RoBERTa for local sentiment (replace GPT for cost savings)
- Redis caching layer for 10x faster responses

**Phase 3 — Scale (Month 4-6)**
- 100K+ mentions/day support
- Multi-brand dashboard
- Competitor ad tracking
- Automated response drafting
- Parent sentiment tracking (pre-enrollment pipeline)
- API access for integration with existing tools

**Phase 4 — Platform (Month 7-12)**
- Self-serve onboarding for new brands
- White-label for PR agencies
- Custom RAG probes builder (no-code)
- Predictive crisis modeling (narrative velocity + historical patterns)

---

## 12. Key Metrics

### 12.1 Current MVP Numbers

| Metric | Value |
|--------|-------|
| Mentions embedded | 1,907 |
| Platforms covered | 5 |
| YouTube channels tracked | 74 |
| YouTube videos analyzed | 84 |
| Telegram channels monitored | 10 |
| Telegram fake channels detected | 2 |
| Topic clusters | 32 |
| RAG probes (actionables) | 14 across 10 departments |
| Sentiment classification coverage | 100% |
| API response (cached) | <50ms |
| Dashboard pages | 11 |
| Hinglish lexicon terms | 350+ |
| YouTube keywords | 250+ |
| Instagram accounts monitored | 48 |
| Google autocomplete queries | 32 (including a-z expansion) |

### 12.2 Success Metrics (Post-Launch)

| Metric | Target |
|--------|--------|
| Time to detect crisis | <3 hours (vs 24-48 hours currently) |
| False positive rate | <15% (RAG reranker filters noise) |
| Department response time | <4 hours from alert |
| Enrollment impact correlation | Track autocomplete sentiment vs enrollment numbers |
| Platform coverage | >95% of PW-related content captured |

---

## 13. File Index

### Frontend (`brandscope/`)
```
src/app/
  page.tsx                    → Hero landing page
  command-center/page.tsx     → Command Center dashboard
  reddit/page.tsx             → Reddit Intelligence
  instagram/page.tsx          → Instagram Intelligence
  youtube/page.tsx            → YouTube Intelligence
  telegram/page.tsx           → Telegram Intelligence
  google/page.tsx             → Google Intelligence
  neural-map/page.tsx         → Neural Map (G6 network graph)
  creators/page.tsx           → Creator Intelligence
  competitors/page.tsx        → Competitive Intelligence
  actionables/page.tsx        → Department Action Items
  api/command-center/route.ts → Command Center API
  api/reddit/route.ts         → Reddit API
  api/instagram/route.ts      → Instagram API
  api/youtube/route.ts        → YouTube API
  api/telegram/route.ts       → Telegram API
  api/google/route.ts         → Google API
  api/neural-map/route.ts     → Neural Map graph data API
  api/creators/route.ts       → Creator data API
  api/competitors/route.ts    → Competitor data API
  api/actionables/route.ts    → RAG-powered actionables API
  api/send-action/route.ts    → Email routing API
src/lib/
  rag.ts                      → RAG utility (embed, search, rerank, generate, cache)
  api-cache.ts                → In-memory API response cache
  animations.ts               → Shared Framer Motion animation variants
  use-live-data.ts            → Data fetching hook with loading state
  utils.ts                    → formatNumber, cn utility
src/components/
  ui/brand-score-cards.tsx    → Animated gauge cards
  ui/animated-chart.tsx       → Scroll-triggered chart wrapper + AnimatedNumber
  ui/metric-card.tsx          → Metric card with sparkline
  ui/page-skeleton.tsx        → Skeleton loading screens
  ui/hero-landing.tsx         → Animated landing page
  ui/command-palette.tsx      → Cmd+K search
  dashboard/rag-insight.tsx   → AI analysis card (markdown stripping, bullet parsing)
  dashboard/india-map.tsx     → India map (react-simple-maps)
  layout/app-shell.tsx        → Conditional sidebar
  layout/sidebar.tsx          → Navigation sidebar
```

### Backend (Python)
```
scrapers/
  instagram.py                → Instagram scraper (3-layer intelligence)
  reddit.py                   → Reddit scraper (LLM triage)
  youtube.py                  → YouTube scraper (Esha's 3-layer pipeline)
  telegram.py                 → Telegram scraper (Esha's channel classification)
  google_search.py            → Google 4-tier monitoring
analysis/
  rag.py                      → Python RAG pipeline (MiniLM embeddings)
  geo_inference.py            → Geographic state inference
  deep_clustering/            → 7-stage clustering pipeline
config/
  settings.py                 → All environment variables
  constants.py                → YouTube blacklists, defaults
  hinglish_lexicon.py         → 350+ Hinglish sentiment terms
scripts/
  embed_openai.py             → Batch embed mentions with OpenAI
  classify_sentiment.py       → Batch classify sentiment with GPT
  classify_and_cluster_youtube.py → YouTube/Telegram clustering
  ingest_youtube_telegram.py  → Ingest YT/TG data into RAG
  youtube_backfill.py         → YouTube 3-month backfill
workers/
  tasks.py                    → 16 Celery tasks
  schedule.py                 → Celery Beat schedule
storage/
  queries.py                  → Supabase CRUD operations
transcription/
  captions.py                 → YouTube captions + Whisper fallback
  extractor.py                → Audio download (yt-dlp)
  whisper.py                  → Whisper proxy transcription
```

---

## 14. Team

| Member | Ownership |
|--------|-----------|
| **Abhishek Takkhi** | Instagram scraper, Reddit scraper, Google scraper, RAG system, embeddings, clustering, dashboard frontend, Command Center, all API routes, LLM classification, geographic inference |
| **Esha** | YouTube scraper (3,711 lines), Telegram scraper (4,200 lines), Azure OpenAI integration, Whisper proxy, 15 test files, 8 SQL migrations, Celery task orchestration |

---

*Built in 5 days. 1,907 mentions. 5 platforms. 14 department probes. One truth.*

**OVAL — See what they say before it spreads.**
