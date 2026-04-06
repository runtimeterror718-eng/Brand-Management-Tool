# Model Card: OVAL AI System

## Overview

| Field | Value |
|-------|-------|
| System Name | OVAL Multi-Model AI Pipeline |
| Version | `youtube-unofficial-mvp-v1` |
| Developers | Abhishek Takkhi, Esha |
| Date | April 2026 |
| Type | Multi-model orchestration (not a single model) |

---

## Models Used

| Component | Model | Provider | Dims | Purpose |
|-----------|-------|----------|------|---------|
| Title Triage | GPT-5.4 | Azure OpenAI | — | PR risk classification from video title + description |
| Transcript Sentiment | GPT-5.4 | Azure OpenAI | — | PR risk analysis separating emotional tone from brand harm |
| Comment Sentiment | GPT-4o-mini | OpenAI | — | Batch classification: positive / neutral / negative |
| LLM Enrichment | GPT-4o-mini | OpenAI | — | Intent, emotion, urgency, user segment, complaint category |
| Text Embedding (clustering) | paraphrase-multilingual-MiniLM-L12-v2 | Sentence Transformers | 384d | Multilingual embedding for Hinglish / Hindi / English |
| Text Embedding (RAG) | text-embedding-3-small | OpenAI | 1536d | Production vector search |
| Clustering | HDBSCAN | scikit-learn | — | Multi-level unsupervised clustering (themes > topics > subtopics) |
| Transcription Fallback | Whisper v3 | Remote proxy | — | Audio-to-text when captions unavailable |
| Insights Report | GPT-4o-mini / Claude Sonnet | OpenAI / Anthropic | — | Structured brand intelligence JSON reports |

---

## Intended Use

- Monitor brand reputation for Physics Wallah across Indian social media.
- Detect PR crises, faculty controversies, student complaints, piracy signals.
- Provide actionable intelligence for the brand management team.
- Power natural-language queries over historical brand data via RAG.

## NOT Intended For

- Automated response generation to users.
- Legal evidence or compliance reporting.
- Financial or investment decisions.
- Surveillance of individual users.

---

## Training Data & Inputs

No models are fine-tuned. All LLMs are used via inference APIs with task-specific prompts.

| Model | Input Source |
|-------|-------------|
| GPT-5.4 (Title Triage) | YouTube video title + description (JSON payload) |
| GPT-5.4 (Transcript) | Full transcript text + video title + channel name + speaker context |
| GPT-4o-mini (Comments) | Batches of up to 40 YouTube comments with video title context |
| GPT-4o-mini (Enrichment) | Mention text (up to 250 chars) + platform + source context |
| MiniLM (Embedding) | Mention text truncated to 512 chars |
| OpenAI Embedding | Mention text truncated to 8000 chars |

---

## Known Limitations

### Language

- MiniLM multilingual has ~85% accuracy on code-mixed Hinglish vs 95%+ on pure English.
- Indian social media sarcasm (meme formats, "bakchodi", "wilder") is frequently misclassified as genuine sentiment.

### Infrastructure

- YouTube API: 316 search terms consume significant quota; requires rotating pool of up to 10 API keys.
- Instagram: curl_cffi + residential proxies work ~80% of time; occasional blocks reduce coverage.
- Transcript fallback: ~15-20% of videos have no captions; Whisper fallback depends on yt-dlp audio download success (5 strategies).

### Data Architecture

- Composite embeddings (70% text + 30% metadata) used only in-memory for HDBSCAN; only raw 384-dim text embeddings persisted to pgvector.
- No foreign key from `mention_embeddings` back to `youtube_comments` — join only via `content_text` matching.
- `mention_embeddings.mention_id` is NULL for YouTube comments (they originate from `youtube_comments`, not `mentions` table).

---

## Ethical Considerations & Bias

### Bias Risks

- **Language bias**: English over-represented in LLM training data; Hindi/Hinglish performance is lower.
- **Platform bias**: YouTube has 316 keywords vs Reddit 6 — YouTube issues disproportionately detected.
- **Sentiment calibration**: Indian student slang may be misclassified as negative.
- **Celebrity bias**: Alakh Pandey mentions get higher engagement leading to higher severity scores regardless of actual risk level.

### Mitigations

- Hinglish lexicon with 200+ crisis terms weighted by severity (`config/hinglish_lexicon.py`).
- Custom PR-risk prompt with 10 explicit decision rules separating emotional tone from brand harm.
- `protective_context` signals tracked alongside `brand_harm_evidence`.
- Official channel blacklist (55+ channel IDs) prevents self-monitoring noise.

### Data Privacy

- No PII stored beyond public usernames / handles.
- All data is publicly available social media content.
- Supabase RLS (Row Level Security) enforced on all tables.
- Service key used only for backend operations.

---

## Evaluation Metrics

### Title Triage (200-sample manual review)

| Metric | Value |
|--------|-------|
| Precision (negative class) | 78% |
| Recall (negative class) | 91% |
| F1 Score | 0.84 |
| Biggest error mode | Motivational speeches about student pressure classified as negative |

### Transcript Sentiment

| Metric | Before Custom Prompt | After Custom Prompt |
|--------|---------------------|---------------------|
| False negative rate on PR-neutral emotional content | 45% | <8% |
| Improvement | — | 82% reduction in false positives |

### Comment Sentiment

| Language | Agreement with manual labels |
|----------|------------------------------|
| English | ~87% |
| Hinglish | ~79% |
| Neutral over-classification | ~12% of mild negatives labeled neutral |

### Clustering Quality

| Metric | Value |
|--------|-------|
| Silhouette score | 0.42 (acceptable for noisy social media data) |
| Hierarchy output | 5-8 themes, 15-25 topics, 40-60 subtopics per brand |

---

## Severity Scoring Weights

| Signal | Weight | Source |
|--------|--------|--------|
| Sentiment | 30% | LLM negative sentiment intensity |
| Engagement | 25% | Views, likes, comments, shares (platform-normalized) |
| Velocity | 25% | Recent 2-hour activity vs 7-day baseline |
| Keywords | 20% | Crisis keyword hits (50+ English + 200+ Hinglish terms) |

### Severity Levels

| Level | Threshold | Action |
|-------|-----------|--------|
| Critical | >= 0.70 | Immediate escalation — scandal, legal, safety |
| High | >= 0.50 | Senior attention — controversy trending, faculty exodus |
| Medium | >= 0.30 | Monitor closely — negative sentiment growing |
| Low | < 0.30 | Normal monitoring — routine mentions |

---

## Cost Per Inference

| Component | Approx. Cost |
|-----------|-------------|
| Title triage (GPT-5.4, per video) | ~$0.002 |
| Transcript analysis (GPT-5.4, per video) | ~$0.005 |
| Comment batch (GPT-4o-mini, 40 comments) | ~$0.001 |
| Enrichment batch (GPT-4o-mini, 30 mentions) | ~$0.0005 |
| Embedding (OpenAI, 1500 texts) | ~$0.003 |
| Full insights report (GPT-4o-mini) | ~$0.02-0.08 |
