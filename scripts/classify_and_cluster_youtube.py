"""
YouTube Classification + Clustering Pipeline

1. Classify all youtube_comments sentiment via GPT-4o-mini
2. Classify youtube_videos transcript sentiment (where missing)
3. Build video-level enrichment (title + description + keywords → theme, intent, risk)
4. Cluster all YouTube content (videos + comments) using OpenAI embeddings + KMeans
5. Store clusters in cluster_embeddings + backfill youtube_comments.comment_sentiment_label

Usage:
    python scripts/classify_and_cluster_youtube.py
"""

import os, sys, json, time
import numpy as np

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


def get_brand_id():
    resp = sb.table("brands").select("id").eq("name", "PW Live Smoke").limit(1).execute()
    if resp.data:
        return resp.data[0]["id"]
    resp = sb.table("brands").select("id").eq("name", "PhysicsWallah").limit(1).execute()
    return resp.data[0]["id"] if resp.data else None


def embed_batch(texts):
    cleaned = [t[:8000] if t else "empty" for t in texts]
    resp = client.embeddings.create(model=EMBED_MODEL, input=cleaned)
    return [item.embedding for item in resp.data]


# ---------------------------------------------------------------------------
# Step 1: Classify YouTube comments
# ---------------------------------------------------------------------------

def classify_youtube_comments():
    print("\n=== STEP 1: Classify YouTube Comments ===")

    resp = sb.table("youtube_comments").select("id, comment_text, comment_author, comment_sentiment_label").execute()
    comments = [c for c in (resp.data or []) if c.get("comment_text") and len(c["comment_text"]) > 5 and not c.get("comment_sentiment_label")]
    print(f"  {len(comments)} comments need classification")

    if not comments:
        return 0

    # Batch classify
    batch_size = 30
    total = 0
    for i in range(0, len(comments), batch_size):
        batch = comments[i:i+batch_size]
        items = [f"[{j}] {(c['comment_text'] or '')[:200]}" for j, c in enumerate(batch)]

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini", max_tokens=600, temperature=0.1,
                messages=[
                    {"role": "system", "content": "Classify each YouTube comment's sentiment toward Physics Wallah. Return index:label pairs. Labels: positive, negative, neutral."},
                    {"role": "user", "content": f"Classify:\n" + "\n".join(items)},
                ],
            )
            raw = resp.choices[0].message.content or ""

            for line in raw.strip().split("\n"):
                if ":" not in line:
                    continue
                parts = line.split(":", 1)
                try:
                    idx = int(parts[0].strip())
                    label = parts[1].strip().lower()
                    if label not in ("positive", "negative", "neutral"):
                        label = "neutral"
                    if 0 <= idx < len(batch):
                        sb.table("youtube_comments").update({"comment_sentiment_label": label}).eq("id", batch[idx]["id"]).execute()
                        total += 1
                except (ValueError, IndexError):
                    continue
        except Exception as e:
            print(f"  Error: {e}")

        print(f"  Classified {min(i + batch_size, len(comments))}/{len(comments)}")
        time.sleep(0.3)

    print(f"  Done: {total} comments classified")
    return total


# ---------------------------------------------------------------------------
# Step 2: Classify YouTube video transcripts
# ---------------------------------------------------------------------------

def classify_video_transcripts():
    print("\n=== STEP 2: Classify Video Transcripts ===")

    resp = sb.table("youtube_videos").select("id, video_title, transcript_text, transcript_sentiment_label").execute()
    videos = [v for v in (resp.data or []) if v.get("transcript_text") and len(v["transcript_text"]) > 30 and not v.get("transcript_sentiment_label")]
    print(f"  {len(videos)} transcripts need classification")

    if not videos:
        return 0

    total = 0
    for v in videos:
        title = v["video_title"] or ""
        transcript = (v["transcript_text"] or "")[:2000]

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini", max_tokens=200, temperature=0.1,
                messages=[
                    {"role": "system", "content": "Classify this YouTube video transcript's sentiment toward Physics Wallah brand. Return JSON: {\"label\":\"positive|negative|neutral\",\"reason\":\"brief reason\"}"},
                    {"role": "user", "content": f"Title: {title}\nTranscript:\n{transcript}"},
                ],
            )
            raw = resp.choices[0].message.content or ""
            cleaned = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
            label = parsed.get("label", "neutral")
            if label not in ("positive", "negative", "neutral"):
                label = "neutral"

            sb.table("youtube_videos").update({"transcript_sentiment_label": label}).eq("id", v["id"]).execute()
            total += 1
            print(f"  [{label}] {title[:60]}")
        except Exception as e:
            print(f"  Error for {title[:40]}: {e}")
        time.sleep(0.3)

    print(f"  Done: {total} transcripts classified")
    return total


# ---------------------------------------------------------------------------
# Step 3: Video-level enrichment (title + desc + keywords → theme, intent)
# ---------------------------------------------------------------------------

def enrich_videos():
    print("\n=== STEP 3: Video-Level Enrichment ===")

    resp = sb.table("youtube_videos").select("id, video_id, video_title, video_description, title_triage_label, title_triage_is_pr_risk, video_views, video_likes, video_comment_count").execute()
    videos = resp.data or []
    print(f"  {len(videos)} videos to enrich")

    if not videos:
        return []

    # Build enrichment for each video via LLM
    items = []
    for v in videos:
        title = v["video_title"] or ""
        desc = (v["video_description"] or "")[:500]
        # Extract hashtags from title + desc
        import re
        all_text = f"{title} {desc}"
        hashtags = list(set(re.findall(r'#(\w+)', all_text)))[:20]

        items.append({
            "video_id": v["video_id"],
            "title": title,
            "description_preview": desc[:200],
            "hashtags": hashtags,
            "triage_label": v["title_triage_label"],
            "is_pr_risk": v["title_triage_is_pr_risk"],
            "views": v["video_views"],
            "likes": v["video_likes"],
            "comments": v["video_comment_count"],
        })

    # Batch enrich via LLM
    prompt = f"""Analyze these {len(items)} YouTube videos about Physics Wallah.
For each video, classify:
- content_type: one of [fan_edit, motivation, course_review, teacher_appreciation, controversy, meme, news, tutorial, reaction, other]
- theme: one of [teacher_quality, course_marketing, student_motivation, alakh_pandey_persona, brand_controversy, exam_prep, student_life, app_review, other]
- target_audience: one of [jee_student, neet_student, parent, general, investor]

Return JSON array:
[{{"video_id":"...", "content_type":"...", "theme":"...", "target_audience":"..."}}]

Videos:
{json.dumps(items, indent=2, ensure_ascii=False)[:6000]}"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini", max_tokens=1500, temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a YouTube content analyst. Return only valid JSON array."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = resp.choices[0].message.content or ""
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        enrichments = json.loads(cleaned)
        print(f"  Enriched {len(enrichments)} videos")

        for e in enrichments:
            print(f"  [{e.get('content_type','?'):15}] [{e.get('theme','?'):20}] {e.get('video_id','?')}")

        return enrichments
    except Exception as ex:
        print(f"  Enrichment error: {ex}")
        return []


# ---------------------------------------------------------------------------
# Step 4: Cluster all YouTube content
# ---------------------------------------------------------------------------

def cluster_youtube(brand_id, video_enrichments):
    print("\n=== STEP 4: Cluster YouTube Content ===")

    # Gather all YouTube texts from mention_embeddings
    resp = sb.table("mention_embeddings").select("id, content_text, sentiment_label").eq("platform", "youtube").limit(500).execute()
    mentions = [m for m in (resp.data or []) if m.get("content_text")]
    print(f"  {len(mentions)} YouTube mentions")

    if len(mentions) < 5:
        print("  Not enough data to cluster")
        return

    # Embed all texts (use fresh embeddings for clustering consistency)
    texts = [m["content_text"] for m in mentions]
    sentiments = [m["sentiment_label"] for m in mentions]
    print(f"  Embedding {len(texts)} texts...")
    all_embeddings = []
    for i in range(0, len(texts), 100):
        batch = texts[i:i+100]
        all_embeddings.extend(embed_batch(batch))
        time.sleep(0.3)
    embeddings = np.array(all_embeddings)

    # KMeans clustering
    from sklearn.cluster import KMeans

    n_clusters = min(8, max(3, len(mentions) // 8))
    print(f"  Running KMeans with K={n_clusters}")

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    # Group mentions by cluster
    clusters = {}
    for i, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = {"texts": [], "sentiments": [], "ids": []}
        clusters[label]["texts"].append(texts[i])
        clusters[label]["sentiments"].append(sentiments[i])
        clusters[label]["ids"].append(mentions[i]["id"])

    # Label each cluster via LLM
    print(f"\n  Labeling {len(clusters)} clusters via LLM...")
    cluster_records = []

    for cid, data in clusters.items():
        sample_texts = [t[:200] for t in data["texts"][:5]]
        neg_count = sum(1 for s in data["sentiments"] if s == "negative")
        pos_count = sum(1 for s in data["sentiments"] if s == "positive")
        neu_count = len(data["sentiments"]) - neg_count - pos_count

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini", max_tokens=150, temperature=0.1,
                messages=[
                    {"role": "system", "content": "Label this YouTube cluster about Physics Wallah. Return JSON: {\"label\":\"CATEGORY:SUBCATEGORY — Short Description\",\"summary\":\"1-2 sentence summary\"}. Categories: APPRECIATION, NEGATIVE, NEUTRAL, FAN_CONTENT, COURSE_REVIEW, MOTIVATION, CONTROVERSY"},
                    {"role": "user", "content": f"Cluster with {len(data['texts'])} mentions ({pos_count} positive, {neg_count} negative, {neu_count} neutral).\nSamples:\n" + "\n".join(f'- "{t}"' for t in sample_texts)},
                ],
            )
            raw = resp.choices[0].message.content or ""
            cleaned = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
            label = parsed.get("label", f"YOUTUBE_CLUSTER_{cid}")
            summary = parsed.get("summary", "")
        except Exception as e:
            label = f"YOUTUBE_CLUSTER_{cid}"
            summary = f"{len(data['texts'])} mentions"
            print(f"  Label error for cluster {cid}: {e}")

        # Compute cluster centroid embedding
        cluster_indices = [i for i, l in enumerate(labels) if l == cid]
        centroid = embeddings[cluster_indices].mean(axis=0).tolist()

        avg_sentiment = 0
        if neg_count + pos_count > 0:
            avg_sentiment = round((pos_count * 0.6 - neg_count * 0.6) / len(data["sentiments"]), 3)

        record = {
            "brand_id": brand_id,
            "cluster_id": int(100 + cid),
            "cluster_label": label,
            "summary": f"{summary}. {len(data['texts'])} YouTube mentions. Positive: {pos_count}, Negative: {neg_count}, Neutral: {neu_count}.",
            "mention_count": int(len(data["texts"])),
            "avg_sentiment": float(avg_sentiment),
            "platforms": {"youtube": int(len(data["texts"]))},
            "representative_texts": sample_texts[:5],
            "embedding_openai": [float(x) for x in centroid],
        }
        cluster_records.append(record)

        print(f"  Cluster {cid}: [{label[:50]}] — {len(data['texts'])} mentions ({pos_count}P/{neg_count}N/{neu_count}Neu)")

    # Update mention_embeddings with cluster_id
    for cid, data in clusters.items():
        for mid in data["ids"]:
            try:
                sb.table("mention_embeddings").update({"cluster_id": 100 + cid}).eq("id", mid).execute()
            except Exception:
                pass

    # Store clusters in cluster_embeddings
    print(f"\n  Storing {len(cluster_records)} YouTube clusters in Supabase...")
    stored = 0
    for r in cluster_records:
        try:
            sb.table("cluster_embeddings").upsert(r, on_conflict="brand_id,cluster_id").execute()
            stored += 1
        except Exception as e:
            print(f"  Store error: {e}")

    print(f"  Stored: {stored}/{len(cluster_records)} clusters")


# ---------------------------------------------------------------------------
# Step 5: Also cluster Telegram if not done
# ---------------------------------------------------------------------------

def cluster_telegram(brand_id):
    print("\n=== STEP 5: Cluster Telegram Content ===")

    resp = sb.table("mention_embeddings").select("id, content_text, sentiment_label").eq("platform", "telegram").limit(500).execute()
    mentions = [m for m in (resp.data or []) if m.get("content_text")]
    print(f"  {len(mentions)} Telegram mentions")

    if len(mentions) < 10:
        print("  Not enough data to cluster")
        return

    texts = [m["content_text"] for m in mentions]
    sentiments = [m["sentiment_label"] for m in mentions]
    print(f"  Embedding {len(texts)} texts...")
    all_embeddings = []
    for i in range(0, len(texts), 100):
        batch = texts[i:i+100]
        all_embeddings.extend(embed_batch(batch))
        time.sleep(0.3)
    embeddings = np.array(all_embeddings)

    from sklearn.cluster import KMeans

    n_clusters = min(10, max(4, len(mentions) // 30))
    print(f"  Running KMeans with K={n_clusters}")

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    clusters = {}
    for i, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = {"texts": [], "sentiments": [], "ids": []}
        clusters[label]["texts"].append(texts[i])
        clusters[label]["sentiments"].append(sentiments[i])
        clusters[label]["ids"].append(mentions[i]["id"])

    print(f"\n  Labeling {len(clusters)} clusters via LLM...")
    cluster_records = []

    for cid, data in clusters.items():
        sample_texts = [t[:200] for t in data["texts"][:5]]
        neg_count = sum(1 for s in data["sentiments"] if s == "negative")
        pos_count = sum(1 for s in data["sentiments"] if s == "positive")
        neu_count = len(data["sentiments"]) - neg_count - pos_count

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini", max_tokens=150, temperature=0.1,
                messages=[
                    {"role": "system", "content": "Label this Telegram cluster about Physics Wallah. Return JSON: {\"label\":\"CATEGORY:SUBCATEGORY — Short Description\",\"summary\":\"1-2 sentence summary\"}. Categories: OFFICIAL, FAN_CONTENT, STUDY_MATERIAL, MOTIVATION, SUSPICIOUS, SCAM, NEWS, COURSE_PROMO"},
                    {"role": "user", "content": f"Cluster with {len(data['texts'])} messages ({pos_count} positive, {neg_count} negative, {neu_count} neutral).\nSamples:\n" + "\n".join(f'- "{t}"' for t in sample_texts)},
                ],
            )
            raw = resp.choices[0].message.content or ""
            cleaned = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
            label = parsed.get("label", f"TELEGRAM_CLUSTER_{cid}")
            summary = parsed.get("summary", "")
        except Exception as e:
            label = f"TELEGRAM_CLUSTER_{cid}"
            summary = f"{len(data['texts'])} messages"

        cluster_indices = [i for i, l in enumerate(labels) if l == cid]
        centroid = embeddings[cluster_indices].mean(axis=0).tolist()

        avg_sentiment = 0
        if neg_count + pos_count > 0:
            avg_sentiment = round((pos_count * 0.6 - neg_count * 0.6) / len(data["sentiments"]), 3)

        record = {
            "brand_id": brand_id,
            "cluster_id": int(200 + cid),
            "cluster_label": label,
            "summary": f"{summary}. {len(data['texts'])} Telegram messages. Positive: {pos_count}, Negative: {neg_count}, Neutral: {neu_count}.",
            "mention_count": int(len(data["texts"])),
            "avg_sentiment": float(avg_sentiment),
            "platforms": {"telegram": int(len(data["texts"]))},
            "representative_texts": sample_texts[:5],
            "embedding_openai": [float(x) for x in centroid],
        }
        cluster_records.append(record)

        print(f"  Cluster {cid}: [{label[:50]}] — {len(data['texts'])} msgs ({pos_count}P/{neg_count}N/{neu_count}Neu)")

    # Update mention_embeddings
    for cid, data in clusters.items():
        for mid in data["ids"]:
            try:
                sb.table("mention_embeddings").update({"cluster_id": 200 + cid}).eq("id", mid).execute()
            except Exception:
                pass

    # Store
    print(f"\n  Storing {len(cluster_records)} Telegram clusters...")
    stored = 0
    for r in cluster_records:
        try:
            sb.table("cluster_embeddings").upsert(r, on_conflict="brand_id,cluster_id").execute()
            stored += 1
        except Exception as e:
            print(f"  Store error: {e}")

    print(f"  Stored: {stored}/{len(cluster_records)} clusters")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("YouTube + Telegram Classification & Clustering Pipeline")
    print("=" * 60)

    brand_id = get_brand_id()
    if not brand_id:
        print("ERROR: No brand found")
        sys.exit(1)
    print(f"Brand: {brand_id}")

    # Step 1: Classify comments
    classify_youtube_comments()

    # Step 2: Classify transcripts
    classify_video_transcripts()

    # Step 3: Enrich videos
    enrichments = enrich_videos()

    # Step 4: Cluster YouTube
    cluster_youtube(brand_id, enrichments)

    # Step 5: Cluster Telegram
    cluster_telegram(brand_id)

    # Verify
    print("\n=== FINAL VERIFICATION ===")
    resp = sb.table("youtube_comments").select("comment_sentiment_label").execute()
    yt_labels = {}
    for r in (resp.data or []):
        l = r["comment_sentiment_label"] or "null"
        yt_labels[l] = yt_labels.get(l, 0) + 1
    print(f"  YouTube comment sentiments: {json.dumps(yt_labels)}")

    resp = sb.table("cluster_embeddings").select("cluster_id, cluster_label, mention_count, platforms").order("cluster_id").execute()
    all_clusters = resp.data or []
    yt_clusters = [c for c in all_clusters if c.get("platforms", {}).get("youtube")]
    tg_clusters = [c for c in all_clusters if c.get("platforms", {}).get("telegram")]
    print(f"  YouTube clusters: {len(yt_clusters)}")
    for c in yt_clusters:
        print(f"    [{c['cluster_id']}] {c['cluster_label'][:60]} — {c['mention_count']} mentions")
    print(f"  Telegram clusters: {len(tg_clusters)}")
    for c in tg_clusters:
        print(f"    [{c['cluster_id']}] {c['cluster_label'][:60]} — {c['mention_count']} mentions")

    print("\nDone!")
