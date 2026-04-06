"""
BACKFILL + AUTOMATION PIPELINE

1. Pulls ALL missing data from platform tables into mention_embeddings
2. Embeds with OpenAI text-embedding-3-small
3. Classifies with GPT-4o-mini (sentiment + issue_type + severity + reason)
4. Stores full classification in enriched mention_embeddings columns
5. Sets up automated pipeline function for future scrapes

Usage:
    python scripts/backfill_automate.py
"""

import os, sys, json, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

from openai import OpenAI
from config.supabase_client import get_service_client

OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=OPENAI_KEY)
sb = get_service_client()

EMBED_MODEL = "text-embedding-3-small"
CLASSIFY_MODEL = "gpt-4o-mini"
BATCH_SIZE = 25


def content_hash(platform: str, text: str) -> str:
    return hashlib.sha256(f"{platform}:{(text or '')[:500]}".encode()).hexdigest()[:32]


def embed_batch(texts: list[str]) -> list[list[float]]:
    cleaned = [t[:8000] if t else "empty" for t in texts]
    resp = client.embeddings.create(model=EMBED_MODEL, input=cleaned)
    return [item.embedding for item in resp.data]


def classify_batch(items: list[dict]) -> list[dict]:
    """Full classification: sentiment + issue_type + severity + reason."""
    entries = []
    for i, item in enumerate(items):
        text = (item.get("content_text") or "")[:300]
        platform = item.get("platform") or "unknown"
        entries.append(f"[{i}] [{platform}] {text}")

    prompt = f"""Classify each mention about Physics Wallah (PW). Return a JSON array.
For each item return:
{{"idx": 0, "sentiment": "positive|negative|neutral", "issue_type": "brand_praise|refund|teacher_quality|scam|app_issue|ipo|employer|political|course_review|meme|spam|other", "severity": "low|medium|high|critical", "is_pr_risk": true/false, "reason": "one sentence why"}}

Mentions:
{chr(10).join(entries)}

Return ONLY a valid JSON array, no markdown:"""

    try:
        resp = client.chat.completions.create(
            model=CLASSIFY_MODEL, max_tokens=2000, temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a brand analyst for Physics Wallah. Return ONLY valid JSON array. No markdown fences."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = resp.choices[0].message.content or "[]"
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        results = json.loads(cleaned)
        if isinstance(results, list):
            return results
        return []
    except Exception as e:
        print(f"    Classification error: {e}")
        return []


def get_brand_ids() -> list[str]:
    resp = sb.table("brands").select("id").or_("name.eq.PhysicsWallah,name.eq.PW Live Smoke").execute()
    return [b["id"] for b in (resp.data or [])]


def get_existing_hashes() -> set:
    """Get content_hash of already ingested rows."""
    resp = sb.table("mention_embeddings").select("content_hash").limit(10000).execute()
    return {r["content_hash"] for r in (resp.data or []) if r.get("content_hash")}


def get_existing_texts() -> set:
    """Get first 100 chars of existing content for dedup. Paginated to avoid timeout."""
    existing = set()
    offset = 0
    page_size = 500
    while True:
        resp = sb.table("mention_embeddings").select("content_text").range(offset, offset + page_size - 1).execute()
        rows = resp.data or []
        if not rows:
            break
        for r in rows:
            if r.get("content_text"):
                existing.add(r["content_text"][:100])
        offset += page_size
        if len(rows) < page_size:
            break
    return existing


# ═══════════════════════════════════════════════════════════
# PULL MISSING DATA FROM EACH PLATFORM TABLE
# ═══════════════════════════════════════════════════════════

def pull_reddit(brand_ids: list, existing: set) -> list[dict]:
    print("  Pulling Reddit...")
    rows = []

    # Posts
    resp = sb.table("reddit_posts").select("post_id, post_title, post_body, author_username, subreddit_name, score, num_comments, post_url, created_at, brand_id").in_("brand_id", brand_ids).execute()
    for r in (resp.data or []):
        text = f"{r.get('post_title', '')} {r.get('post_body', '')}".strip()
        if not text or len(text) < 10 or text[:100] in existing:
            continue
        rows.append({
            "brand_id": r["brand_id"], "platform": "reddit", "content_type": "post",
            "content_text": text[:2000], "platform_ref_id": r.get("post_id"),
            "source_url": r.get("post_url"), "author_handle": r.get("author_username"),
            "upvotes": r.get("score", 0), "comments_count": r.get("num_comments", 0),
            "parent_post_id": None,
        })

    # Comments
    resp = sb.table("reddit_comments").select("id, post_id, comment_body, comment_author, comment_score").limit(5000).execute()
    brand_id = brand_ids[0] if brand_ids else None
    for r in (resp.data or []):
        text = (r.get("comment_body") or "").strip()
        if not text or len(text) < 10 or text[:100] in existing:
            continue
        rows.append({
            "brand_id": brand_id, "platform": "reddit", "content_type": "comment",
            "content_text": text[:2000], "platform_ref_id": r.get("id"),
            "author_handle": r.get("comment_author"),
            "upvotes": r.get("comment_score", 0),
            "parent_post_id": r.get("post_id"),
        })

    print(f"    Found {len(rows)} missing Reddit rows")
    return rows


def pull_instagram(brand_ids: list, existing: set) -> list[dict]:
    print("  Pulling Instagram...")
    rows = []

    resp = sb.table("instagram_posts").select("post_id, caption_text, account_name, like_count, comment_count, media_type, post_url, reel_plays, brand_id").in_("brand_id", brand_ids).execute()
    for r in (resp.data or []):
        text = (r.get("caption_text") or "").strip()
        if not text or len(text) < 5 or text[:100] in existing:
            continue
        rows.append({
            "brand_id": r["brand_id"], "platform": "instagram", "content_type": r.get("media_type", "post"),
            "content_text": text[:2000], "platform_ref_id": r.get("post_id"),
            "source_url": r.get("post_url"), "author_handle": r.get("account_name"),
            "likes": r.get("like_count", 0), "comments_count": r.get("comment_count", 0),
            "views": r.get("reel_plays", 0),
        })

    resp = sb.table("instagram_comments").select("id, post_id, comment_text, comment_author").limit(5000).execute()
    brand_id = brand_ids[0] if brand_ids else None
    for r in (resp.data or []):
        text = (r.get("comment_text") or "").strip()
        if not text or len(text) < 5 or text[:100] in existing:
            continue
        rows.append({
            "brand_id": brand_id, "platform": "instagram", "content_type": "comment",
            "content_text": text[:2000], "platform_ref_id": r.get("id"),
            "author_handle": r.get("comment_author"),
            "parent_post_id": r.get("post_id"),
        })

    print(f"    Found {len(rows)} missing Instagram rows")
    return rows


def pull_youtube(brand_ids: list, existing: set) -> list[dict]:
    print("  Pulling YouTube...")
    rows = []

    resp = sb.table("youtube_videos").select("video_id, video_title, video_description, video_views, video_likes, video_comment_count, source_url, brand_id, title_triage_label, title_triage_is_pr_risk, title_triage_issue_type, title_triage_reason, transcript_text").in_("brand_id", brand_ids).execute()
    for r in (resp.data or []):
        title = (r.get("video_title") or "").strip()
        desc = (r.get("video_description") or "")[:300].strip()
        text = f"{title}. {desc}" if desc else title
        if not text or len(text) < 10 or text[:100] in existing:
            continue
        rows.append({
            "brand_id": r["brand_id"], "platform": "youtube", "content_type": "video",
            "content_text": text[:2000], "platform_ref_id": r.get("video_id"),
            "source_url": r.get("source_url"),
            "views": r.get("video_views", 0), "likes": r.get("video_likes", 0),
            "comments_count": r.get("video_comment_count", 0),
            "has_audio": bool(r.get("transcript_text")),
            "transcript_text": (r.get("transcript_text") or "")[:3000] or None,
            # Pre-existing triage from Team B's pipeline
            "_pre_sentiment": r.get("title_triage_label"),
            "_pre_pr_risk": r.get("title_triage_is_pr_risk"),
            "_pre_issue_type": r.get("title_triage_issue_type"),
            "_pre_reason": r.get("title_triage_reason"),
        })

    resp = sb.table("youtube_comments").select("comment_id, video_id, comment_text, comment_author, comment_likes, comment_sentiment_label").limit(5000).execute()
    brand_id = brand_ids[0] if brand_ids else None
    for r in (resp.data or []):
        text = (r.get("comment_text") or "").strip()
        if not text or len(text) < 5 or text[:100] in existing:
            continue
        rows.append({
            "brand_id": brand_id, "platform": "youtube", "content_type": "comment",
            "content_text": text[:2000], "platform_ref_id": r.get("comment_id"),
            "author_handle": r.get("comment_author"),
            "likes": r.get("comment_likes", 0),
            "parent_post_id": r.get("video_id"),
            "_pre_sentiment": r.get("comment_sentiment_label"),
        })

    print(f"    Found {len(rows)} missing YouTube rows")
    return rows


def pull_telegram(brand_ids: list, existing: set) -> list[dict]:
    print("  Pulling Telegram...")
    rows = []

    resp = sb.table("telegram_messages").select("message_id, message_text, channel_name, channel_username, sender_username, views, forwards_count, risk_label, risk_score, is_suspicious, brand_id").in_("brand_id", brand_ids).execute()
    for r in (resp.data or []):
        text = (r.get("message_text") or "").strip()
        if not text or len(text) < 10 or text[:100] in existing:
            continue
        rows.append({
            "brand_id": r["brand_id"], "platform": "telegram", "content_type": "message",
            "content_text": text[:2000], "platform_ref_id": str(r.get("message_id", "")),
            "author_handle": r.get("sender_username") or r.get("channel_username"),
            "views": r.get("views", 0), "forwards": r.get("forwards_count", 0),
            "_pre_severity": "high" if r.get("is_suspicious") else "low",
            "_pre_issue_type": r.get("risk_label"),
        })

    print(f"    Found {len(rows)} missing Telegram rows")
    return rows


# ═══════════════════════════════════════════════════════════
# PROCESS AND STORE
# ═══════════════════════════════════════════════════════════

def process_and_store(all_rows: list[dict], brand_ids: list):
    print(f"\n{'='*60}")
    print(f"Processing {len(all_rows)} rows: embed + classify + store")
    print(f"{'='*60}")

    total_stored = 0
    total_classified = 0

    for batch_start in range(0, len(all_rows), BATCH_SIZE):
        batch = all_rows[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(all_rows) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\n  Batch {batch_num}/{total_batches} ({len(batch)} items)...")

        # Step 1: Embed
        texts = [r["content_text"] for r in batch]
        try:
            embeddings = embed_batch(texts)
        except Exception as e:
            print(f"    Embed error: {e}")
            time.sleep(2)
            continue

        # Step 2: Classify (full classification)
        classifications = classify_batch(batch)
        cls_by_idx = {c.get("idx", i): c for i, c in enumerate(classifications)}

        # Step 3: Store
        for j, row in enumerate(batch):
            cls = cls_by_idx.get(j, {})

            # Use pre-existing classification if available, else use GPT result
            sentiment = row.get("_pre_sentiment") or cls.get("sentiment", "neutral")
            if sentiment not in ("positive", "negative", "neutral"):
                sentiment = "neutral"
            score = 0.6 if sentiment == "positive" else -0.6 if sentiment == "negative" else 0.0

            issue_type = row.get("_pre_issue_type") or cls.get("issue_type", "other")
            severity = row.get("_pre_severity") or cls.get("severity", "low")
            is_pr_risk = row.get("_pre_pr_risk") or cls.get("is_pr_risk", False)
            reason = row.get("_pre_reason") or cls.get("reason", "")

            chash = content_hash(row["platform"], row["content_text"])

            record = {
                "brand_id": row["brand_id"],
                "content_text": row["content_text"],
                "content_hash": chash,
                "platform": row["platform"],
                "content_type": row.get("content_type"),
                "platform_ref_id": row.get("platform_ref_id"),
                "source_url": row.get("source_url"),
                "author_handle": row.get("author_handle"),
                "parent_post_id": row.get("parent_post_id"),
                "likes": row.get("likes", 0),
                "comments_count": row.get("comments_count", 0),
                "views": row.get("views", 0),
                "upvotes": row.get("upvotes", 0),
                "forwards": row.get("forwards", 0),
                "sentiment_label": sentiment,
                "sentiment_score": score,
                "is_pr_risk": bool(is_pr_risk),
                "severity": severity,
                "issue_type": issue_type,
                "classification_reason": reason[:500] if reason else None,
                "recommended_action": cls.get("recommended_action"),
                "is_actionable": severity in ("high", "critical") or is_pr_risk,
                "has_audio": row.get("has_audio", False),
                "transcript_text": row.get("transcript_text"),
                "classification_model": CLASSIFY_MODEL,
                "classification_provider": "openai",
                "classified_at": "now()",
                "embedding_openai": embeddings[j],
            }

            # Remove None values
            record = {k: v for k, v in record.items() if v is not None}

            try:
                sb.table("mention_embeddings").upsert(record, on_conflict="content_hash").execute()
                total_stored += 1
                if cls:
                    total_classified += 1
            except Exception as e:
                # If content_hash conflict, try without it (fallback insert)
                try:
                    record.pop("content_hash", None)
                    sb.table("mention_embeddings").insert(record).execute()
                    total_stored += 1
                except Exception as e2:
                    print(f"    Store error: {e2}")

        print(f"    Stored: {total_stored} | Classified: {total_classified}")
        time.sleep(0.3)

    return total_stored, total_classified


# ═══════════════════════════════════════════════════════════
# BACKFILL EXISTING mention_embeddings WITH NEW COLUMNS
# ═══════════════════════════════════════════════════════════

def backfill_existing_rows():
    """Fill classification columns for existing 1,907 rows that only have sentiment_label."""
    print("\n  Backfilling existing rows with enriched classification...")

    resp = sb.table("mention_embeddings").select("id, content_text, platform, sentiment_label").is_("issue_type", "null").limit(2000).execute()
    rows = [r for r in (resp.data or []) if r.get("content_text")]
    print(f"    {len(rows)} existing rows need enrichment")

    if not rows:
        return 0

    total = 0
    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start:batch_start + BATCH_SIZE]
        classifications = classify_batch([{"content_text": r["content_text"], "platform": r["platform"]} for r in batch])
        cls_by_idx = {c.get("idx", i): c for i, c in enumerate(classifications)}

        for j, row in enumerate(batch):
            cls = cls_by_idx.get(j, {})
            if not cls:
                continue

            chash = content_hash(row["platform"], row["content_text"])
            update = {
                "content_hash": chash,
                "issue_type": cls.get("issue_type", "other"),
                "severity": cls.get("severity", "low"),
                "is_pr_risk": bool(cls.get("is_pr_risk", False)),
                "classification_reason": (cls.get("reason") or "")[:500] or None,
                "is_actionable": cls.get("severity") in ("high", "critical") or cls.get("is_pr_risk", False),
                "classification_model": CLASSIFY_MODEL,
                "classification_provider": "openai",
                "classified_at": "now()",
                "updated_at": "now()",
            }
            update = {k: v for k, v in update.items() if v is not None}

            try:
                sb.table("mention_embeddings").update(update).eq("id", row["id"]).execute()
                total += 1
            except Exception:
                pass

        print(f"    Enriched {min(batch_start + BATCH_SIZE, len(rows))}/{len(rows)}")
        time.sleep(0.3)

    print(f"    Total enriched: {total}")
    return total


# ═══════════════════════════════════════════════════════════
# AUTOMATED PIPELINE FUNCTION
# ═══════════════════════════════════════════════════════════

def create_automation_script():
    """Create the automated pipeline that scrapers call after ingestion."""
    script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "auto_enrich.py")

    script_content = '''"""
AUTO-ENRICH PIPELINE
Called after any scraper runs. Finds new unembedded records
in platform tables and ingests them into mention_embeddings.

Usage:
    python scripts/auto_enrich.py

Can also be imported and called programmatically:
    from scripts.auto_enrich import enrich_new_mentions
    enrich_new_mentions()
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def enrich_new_mentions():
    """Find and process any new mentions not yet in mention_embeddings."""
    from scripts.backfill_automate import (
        get_brand_ids, get_existing_texts,
        pull_reddit, pull_instagram, pull_youtube, pull_telegram,
        process_and_store
    )

    brand_ids = get_brand_ids()
    if not brand_ids:
        print("No brands found")
        return

    existing = get_existing_texts()
    print(f"Existing records: {len(existing)}")

    new_rows = []
    new_rows.extend(pull_reddit(brand_ids, existing))
    new_rows.extend(pull_instagram(brand_ids, existing))
    new_rows.extend(pull_youtube(brand_ids, existing))
    new_rows.extend(pull_telegram(brand_ids, existing))

    if not new_rows:
        print("No new records to process")
        return

    stored, classified = process_and_store(new_rows, brand_ids)
    print(f"\\nDone: {stored} stored, {classified} classified")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)
    enrich_new_mentions()
'''

    with open(script_path, "w") as f:
        f.write(script_content)
    print(f"\n  Created auto_enrich.py at {script_path}")


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("OVAL — Full Backfill & Enrichment Pipeline")
    print("=" * 60)

    brand_ids = get_brand_ids()
    if not brand_ids:
        print("ERROR: No brands found")
        sys.exit(1)
    print(f"Brands: {brand_ids}")

    # Step 1: Get existing data for dedup
    existing = get_existing_texts()
    print(f"Existing records in mention_embeddings: {len(existing)}")

    # Step 2: Pull ALL missing data from platform tables
    print(f"\n{'='*60}")
    print("Phase 1: Pull missing data from platform tables")
    print(f"{'='*60}")

    all_new = []
    all_new.extend(pull_reddit(brand_ids, existing))
    all_new.extend(pull_instagram(brand_ids, existing))
    all_new.extend(pull_youtube(brand_ids, existing))
    all_new.extend(pull_telegram(brand_ids, existing))

    print(f"\nTotal new records to process: {len(all_new)}")

    # Step 3: Process new records (embed + classify + store)
    if all_new:
        stored, classified = process_and_store(all_new, brand_ids)
        print(f"\nPhase 1 complete: {stored} stored, {classified} classified")

    # Step 4: Backfill existing rows with enriched classification
    print(f"\n{'='*60}")
    print("Phase 2: Enrich existing rows with full classification")
    print(f"{'='*60}")
    backfill_existing_rows()

    # Step 5: Create automation script
    print(f"\n{'='*60}")
    print("Phase 3: Create automation pipeline")
    print(f"{'='*60}")
    create_automation_script()

    # Step 6: Verify
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")

    resp = sb.table("mention_embeddings").select("platform, sentiment_label, issue_type, is_pr_risk").execute()
    rows = resp.data or []

    by_platform = {}
    by_sentiment = {}
    by_issue = {}
    pr_risks = 0
    has_issue = 0

    for r in rows:
        p = r.get("platform") or "unknown"
        s = r.get("sentiment_label") or "unclassified"
        i = r.get("issue_type") or "none"
        by_platform[p] = by_platform.get(p, 0) + 1
        by_sentiment[s] = by_sentiment.get(s, 0) + 1
        if i != "none":
            by_issue[i] = by_issue.get(i, 0) + 1
            has_issue += 1
        if r.get("is_pr_risk"):
            pr_risks += 1

    print(f"\n  Total rows: {len(rows)}")
    print(f"  By platform: {json.dumps(by_platform, indent=4)}")
    print(f"  By sentiment: {json.dumps(by_sentiment, indent=4)}")
    print(f"  With issue_type: {has_issue}")
    print(f"  PR risks flagged: {pr_risks}")
    print(f"  Top issues: {json.dumps(dict(sorted(by_issue.items(), key=lambda x: -x[1])[:8]), indent=4)}")

    print(f"\n{'='*60}")
    print("DONE — mention_embeddings is now the single source of truth")
    print(f"{'='*60}")
    print(f"\nTo process future scrapes automatically:")
    print(f"  python scripts/auto_enrich.py")
    print(f"\nOr import in your scraper:")
    print(f"  from scripts.auto_enrich import enrich_new_mentions")
    print(f"  enrich_new_mentions()  # call after scraping")
