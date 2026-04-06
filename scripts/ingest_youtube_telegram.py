"""
Ingest YouTube comments/titles/transcripts and Telegram messages
into mention_embeddings for RAG. Then embed + classify.

Usage:
    python scripts/ingest_youtube_telegram.py
"""

import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from config.supabase_client import get_service_client

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    OPENAI_API_KEY = line.strip().split("=", 1)[1]
                    break

client = OpenAI(api_key=OPENAI_API_KEY)
sb = get_service_client()

EMBED_MODEL = "text-embedding-3-small"
EMBED_BATCH = 100
CLASSIFY_BATCH = 30


def get_brand_id():
    resp = sb.table("brands").select("id").eq("name", "PhysicsWallah").limit(1).execute()
    return resp.data[0]["id"] if resp.data else None


def embed_batch(texts):
    cleaned = [t[:8000] if t else "empty" for t in texts]
    resp = client.embeddings.create(model=EMBED_MODEL, input=cleaned)
    return [item.embedding for item in resp.data]


def classify_batch(mentions):
    items = []
    for i, m in enumerate(mentions):
        text = (m.get("content_text") or "")[:300]
        platform = m.get("platform") or "unknown"
        items.append(f"[{i}] [{platform}] {text}")

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=800,
        temperature=0.1,
        messages=[
            {"role": "system", "content": "You are a sentiment classifier for Physics Wallah brand mentions. Return only index:label pairs, one per line. Labels: positive, negative, neutral."},
            {"role": "user", "content": f"Classify all {len(items)} items:\n" + "\n".join(items)},
        ],
    )
    raw = resp.choices[0].message.content or ""
    results = []
    for line in raw.strip().split("\n"):
        if ":" not in line:
            continue
        parts = line.split(":", 1)
        try:
            idx = int(parts[0].strip())
            label = parts[1].strip().lower()
            if label not in ("positive", "negative", "neutral"):
                label = "neutral"
            if 0 <= idx < len(mentions):
                results.append({"id": mentions[idx]["id"], "label": label})
        except (ValueError, IndexError):
            continue
    return results


def ingest_youtube(brand_id):
    """Pull YouTube comments, titles, transcripts → mention_embeddings."""
    print("\n=== YOUTUBE INGESTION ===")

    # Check what's already in mention_embeddings for youtube
    existing = sb.table("mention_embeddings").select("content_text").eq("brand_id", brand_id).eq("platform", "youtube").limit(5000).execute()
    existing_texts = {(r["content_text"] or "")[:100] for r in (existing.data or [])}
    print(f"  Already have {len(existing_texts)} youtube entries in mention_embeddings")

    new_rows = []

    # 1. YouTube comments
    resp = sb.table("youtube_comments").select("comment_text, comment_author, video_id").not_.is_("comment_text", "null").execute()
    for c in (resp.data or []):
        text = (c["comment_text"] or "").strip()
        if len(text) < 10 or text[:100] in existing_texts:
            continue
        new_rows.append({
            "brand_id": brand_id,
            "content_text": text[:500],
            "platform": "youtube",
            "cluster_id": None,
            "sentiment_label": None,
            "sentiment_score": None,
        })

    # 2. YouTube video titles + descriptions
    resp = sb.table("youtube_videos").select("video_title, video_description, video_id").not_.is_("video_title", "null").execute()
    for v in (resp.data or []):
        title = (v["video_title"] or "").strip()
        desc = (v["video_description"] or "")[:300].strip()
        text = f"{title}. {desc}" if desc else title
        if len(text) < 10 or text[:100] in existing_texts:
            continue
        new_rows.append({
            "brand_id": brand_id,
            "content_text": text[:500],
            "platform": "youtube",
            "cluster_id": None,
            "sentiment_label": None,
            "sentiment_score": None,
        })

    # 3. YouTube transcripts (chunk long ones)
    resp = sb.table("youtube_videos").select("transcript_text, video_title, video_id").not_.is_("transcript_text", "null").execute()
    for v in (resp.data or []):
        transcript = (v["transcript_text"] or "").strip()
        if len(transcript) < 50:
            continue
        # Chunk into ~500 char segments
        title = (v["video_title"] or "")
        for i in range(0, len(transcript), 400):
            chunk = transcript[i:i+400].strip()
            if len(chunk) < 30:
                continue
            text = f"[Transcript: {title}] {chunk}"
            if text[:100] in existing_texts:
                continue
            new_rows.append({
                "brand_id": brand_id,
                "content_text": text[:500],
                "platform": "youtube",
                "cluster_id": None,
                "sentiment_label": None,
                "sentiment_score": None,
            })

    print(f"  New YouTube rows to insert: {len(new_rows)}")

    # Insert
    inserted = 0
    for i in range(0, len(new_rows), 50):
        batch = new_rows[i:i+50]
        try:
            sb.table("mention_embeddings").insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            print(f"  Insert error: {e}")
    print(f"  Inserted: {inserted}")
    return inserted


def ingest_telegram(brand_id):
    """Pull Telegram messages → mention_embeddings."""
    print("\n=== TELEGRAM INGESTION ===")

    existing = sb.table("mention_embeddings").select("content_text").eq("brand_id", brand_id).eq("platform", "telegram").limit(5000).execute()
    existing_texts = {(r["content_text"] or "")[:100] for r in (existing.data or [])}
    print(f"  Already have {len(existing_texts)} telegram entries in mention_embeddings")

    resp = sb.table("telegram_messages").select("message_text, channel_name, channel_username, sender_username, views, message_timestamp").not_.is_("message_text", "null").execute()

    new_rows = []
    for m in (resp.data or []):
        text = (m["message_text"] or "").strip()
        if len(text) < 10 or text[:100] in existing_texts:
            continue
        channel = m.get("channel_name") or m.get("channel_username") or "unknown"
        new_rows.append({
            "brand_id": brand_id,
            "content_text": f"[Telegram @{channel}] {text}"[:500],
            "platform": "telegram",
            "cluster_id": None,
            "sentiment_label": None,
            "sentiment_score": None,
        })

    print(f"  New Telegram rows to insert: {len(new_rows)}")

    inserted = 0
    for i in range(0, len(new_rows), 50):
        batch = new_rows[i:i+50]
        try:
            sb.table("mention_embeddings").insert(batch).execute()
            inserted += len(batch)
        except Exception as e:
            print(f"  Insert error: {e}")
    print(f"  Inserted: {inserted}")
    return inserted


def embed_new():
    """Embed all mention_embeddings missing OpenAI embeddings."""
    print("\n=== EMBEDDING (OpenAI text-embedding-3-small) ===")

    resp = sb.table("mention_embeddings").select("id, content_text").is_("embedding_openai", "null").limit(2000).execute()
    mentions = resp.data or []
    print(f"  {len(mentions)} mentions need embedding")

    if not mentions:
        return 0

    total = 0
    for i in range(0, len(mentions), EMBED_BATCH):
        batch = mentions[i:i+EMBED_BATCH]
        texts = [m["content_text"] or "" for m in batch]
        print(f"  Embedding batch {i//EMBED_BATCH + 1}/{(len(mentions)+EMBED_BATCH-1)//EMBED_BATCH}...")

        try:
            embeddings = embed_batch(texts)
        except Exception as e:
            print(f"  Embed error: {e}")
            time.sleep(2)
            continue

        for j, m in enumerate(batch):
            try:
                sb.table("mention_embeddings").update({"embedding_openai": embeddings[j]}).eq("id", m["id"]).execute()
                total += 1
            except Exception as e:
                print(f"  Store error: {e}")

        time.sleep(0.5)

    print(f"  Embedded: {total}")
    return total


def classify_new():
    """Classify sentiment for all mention_embeddings missing labels."""
    print("\n=== SENTIMENT CLASSIFICATION (GPT-4o-mini) ===")

    resp = sb.table("mention_embeddings").select("id, content_text, platform").is_("sentiment_label", "null").limit(2000).execute()
    mentions = resp.data or []
    print(f"  {len(mentions)} mentions need classification")

    if not mentions:
        return 0

    total = 0
    for i in range(0, len(mentions), CLASSIFY_BATCH):
        batch = mentions[i:i+CLASSIFY_BATCH]
        print(f"  Classifying batch {i//CLASSIFY_BATCH + 1}/{(len(mentions)+CLASSIFY_BATCH-1)//CLASSIFY_BATCH}...")

        results = classify_batch(batch)

        for r in results:
            score = 0.6 if r["label"] == "positive" else -0.6 if r["label"] == "negative" else 0.0
            try:
                sb.table("mention_embeddings").update({
                    "sentiment_label": r["label"],
                    "sentiment_score": score,
                }).eq("id", r["id"]).execute()
                total += 1
            except Exception as e:
                print(f"  Update error: {e}")

        time.sleep(0.3)

    print(f"  Classified: {total}")
    return total


def verify():
    print("\n=== VERIFICATION ===")
    resp = sb.table("mention_embeddings").select("platform, sentiment_label").execute()
    rows = resp.data or []

    by_platform = {}
    by_sentiment = {}
    for r in rows:
        p = r["platform"] or "unknown"
        s = r["sentiment_label"] or "unclassified"
        by_platform[p] = by_platform.get(p, 0) + 1
        by_sentiment[s] = by_sentiment.get(s, 0) + 1

    print(f"  Total: {len(rows)}")
    print(f"  By platform: {json.dumps(by_platform, indent=2)}")
    print(f"  By sentiment: {json.dumps(by_sentiment, indent=2)}")


if __name__ == "__main__":
    print("=" * 60)
    print("YouTube + Telegram → RAG Ingestion Pipeline")
    print("=" * 60)

    brand_id = get_brand_id()
    if not brand_id:
        print("ERROR: No PhysicsWallah brand found")
        sys.exit(1)
    print(f"Brand ID: {brand_id}")

    yt_count = ingest_youtube(brand_id)
    tg_count = ingest_telegram(brand_id)
    print(f"\nIngested: {yt_count} YouTube + {tg_count} Telegram = {yt_count + tg_count} new rows")

    embed_new()
    classify_new()
    verify()

    print("\nDone! YouTube + Telegram data is now in the RAG system.")
