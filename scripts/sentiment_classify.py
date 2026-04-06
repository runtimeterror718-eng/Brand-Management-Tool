"""
Batch classify sentiment for all mention_embeddings missing labels.
Uses GPT-4o-mini to classify each mention as positive/negative/neutral.
Processes in batches of 30 to minimize API calls.

Cost: ~1,267 mentions / 30 per batch = ~42 API calls = ~$0.05
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

BATCH_SIZE = 30


def classify_batch(mentions: list[dict]) -> list[dict]:
    """Classify a batch of mentions using GPT-4o-mini."""
    items = []
    for i, m in enumerate(mentions):
        text = (m.get("content_text") or "")[:300]
        platform = m.get("platform") or "unknown"
        items.append(f"[{i}] [{platform}] {text}")

    prompt = f"""Classify each mention's sentiment toward Physics Wallah (PW) brand.

Rules:
- "positive": praises PW, teachers, Alakh Pandey, courses, results
- "negative": criticizes PW, scam accusations, refund complaints, teacher quality issues, app problems, hiring criticism
- "neutral": factual, questions, unrelated, memes with no clear sentiment, spam

For each item, return ONLY the index and label. Format:
0:negative
1:positive
2:neutral
...

MENTIONS:
{chr(10).join(items)}

Classify all {len(items)} items:"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=800,
            temperature=0.1,
            messages=[
                {"role": "system", "content": "You are a sentiment classifier for brand mentions. Return only index:label pairs, one per line. Labels: positive, negative, neutral."},
                {"role": "user", "content": prompt},
            ],
        )
        raw = resp.choices[0].message.content or ""

        results = []
        for line in raw.strip().split("\n"):
            line = line.strip()
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
    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def assign_score(label: str) -> float:
    """Convert label to numeric score."""
    if label == "positive": return 0.6
    if label == "negative": return -0.6
    return 0.0


def main():
    print("=" * 60)
    print("Sentiment Classification Pipeline")
    print("Model: gpt-4o-mini | Batch size:", BATCH_SIZE)
    print("=" * 60)

    # Fetch unlabeled mentions
    resp = sb.table("mention_embeddings").select(
        "id, content_text, platform"
    ).is_("sentiment_label", "null").limit(1500).execute()

    mentions = resp.data or []
    print(f"Found {len(mentions)} mentions to classify")

    if not mentions:
        print("All mentions already classified!")
        return

    total_classified = 0
    label_counts = {"positive": 0, "negative": 0, "neutral": 0}

    for i in range(0, len(mentions), BATCH_SIZE):
        batch = mentions[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(mentions) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\n  Batch {batch_num}/{total_batches} ({len(batch)} mentions)...")

        results = classify_batch(batch)

        # Update Supabase
        for r in results:
            try:
                sb.table("mention_embeddings").update({
                    "sentiment_label": r["label"],
                    "sentiment_score": assign_score(r["label"]),
                }).eq("id", r["id"]).execute()
                total_classified += 1
                label_counts[r["label"]] = label_counts.get(r["label"], 0) + 1
            except Exception as e:
                print(f"    ERROR updating {r['id']}: {e}")

        print(f"  Classified: {len(results)}/{len(batch)} | Running total: {total_classified}")
        time.sleep(0.3)  # Rate limit

    print(f"\n{'=' * 60}")
    print(f"DONE: {total_classified} mentions classified")
    print(f"  Positive: {label_counts['positive']}")
    print(f"  Negative: {label_counts['negative']}")
    print(f"  Neutral:  {label_counts['neutral']}")
    print(f"{'=' * 60}")

    # Final verification
    resp = sb.table("mention_embeddings").select("sentiment_label").execute()
    counts = {}
    for r in (resp.data or []):
        l = r["sentiment_label"] or "null"
        counts[l] = counts.get(l, 0) + 1
    print(f"\nFinal distribution: {json.dumps(counts, indent=2)}")


if __name__ == "__main__":
    main()
