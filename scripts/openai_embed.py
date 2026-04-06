"""
Re-embed all mention_embeddings and cluster_embeddings with OpenAI text-embedding-3-small.
Stores 1536-dim vectors in the embedding_openai column.

Usage:
    python scripts/openai_embed.py

Cost estimate: ~1,500 texts * ~100 tokens avg = 150K tokens = ~$0.003
"""

import os
import sys
import json
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
from config.supabase_client import get_service_client

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    # Try loading from .env
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    OPENAI_API_KEY = line.strip().split("=", 1)[1]
                    break

if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY not found in environment or .env")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)
sb = get_service_client()

MODEL = "text-embedding-3-small"  # 1536 dimensions
BATCH_SIZE = 100  # OpenAI allows up to 2048, but keep batches manageable


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using OpenAI text-embedding-3-small."""
    # Clean texts — OpenAI rejects empty strings
    cleaned = [t[:8000] if t else "empty" for t in texts]
    resp = client.embeddings.create(model=MODEL, input=cleaned)
    return [item.embedding for item in resp.data]


def embed_mentions():
    """Re-embed all mention_embeddings with OpenAI."""
    print("Fetching mentions from mention_embeddings...")

    # Fetch all mentions that need embedding
    resp = sb.table("mention_embeddings").select(
        "id, content_text"
    ).is_("embedding_openai", "null").limit(2000).execute()

    mentions = resp.data or []
    print(f"  Found {len(mentions)} mentions to embed")

    if not mentions:
        print("  All mentions already have OpenAI embeddings!")
        return 0

    total_stored = 0

    for i in range(0, len(mentions), BATCH_SIZE):
        batch = mentions[i:i + BATCH_SIZE]
        texts = [m["content_text"] or "" for m in batch]

        print(f"  Embedding batch {i // BATCH_SIZE + 1}/{(len(mentions) + BATCH_SIZE - 1) // BATCH_SIZE} ({len(batch)} texts)...")

        try:
            embeddings = embed_batch(texts)
        except Exception as e:
            print(f"  ERROR embedding batch: {e}")
            time.sleep(2)
            continue

        # Update each row with the OpenAI embedding
        for j, m in enumerate(batch):
            try:
                sb.table("mention_embeddings").update({
                    "embedding_openai": embeddings[j]
                }).eq("id", m["id"]).execute()
                total_stored += 1
            except Exception as e:
                print(f"  ERROR storing embedding for {m['id']}: {e}")

        print(f"  Stored {total_stored}/{len(mentions)}")
        time.sleep(0.5)  # Rate limit courtesy

    return total_stored


def embed_clusters():
    """Re-embed all cluster_embeddings with OpenAI."""
    print("\nFetching clusters from cluster_embeddings...")

    resp = sb.table("cluster_embeddings").select(
        "id, cluster_label, summary"
    ).is_("embedding_openai", "null").limit(100).execute()

    clusters = resp.data or []
    print(f"  Found {len(clusters)} clusters to embed")

    if not clusters:
        print("  All clusters already have OpenAI embeddings!")
        return 0

    # Build embedding text from label + summary
    texts = [
        f"{c['cluster_label'] or ''}: {c['summary'] or ''}"[:8000]
        for c in clusters
    ]

    print(f"  Embedding {len(clusters)} clusters...")
    try:
        embeddings = embed_batch(texts)
    except Exception as e:
        print(f"  ERROR: {e}")
        return 0

    stored = 0
    for i, c in enumerate(clusters):
        try:
            sb.table("cluster_embeddings").update({
                "embedding_openai": embeddings[i]
            }).eq("id", c["id"]).execute()
            stored += 1
        except Exception as e:
            print(f"  ERROR storing cluster embedding {c['id']}: {e}")

    print(f"  Stored {stored}/{len(clusters)} cluster embeddings")
    return stored


def verify():
    """Quick verification of stored embeddings."""
    print("\nVerification:")

    resp = sb.table("mention_embeddings").select("id").not_.is_("embedding_openai", "null").execute()
    mention_count = len(resp.data or [])

    resp = sb.table("cluster_embeddings").select("id").not_.is_("embedding_openai", "null").execute()
    cluster_count = len(resp.data or [])

    print(f"  Mentions with OpenAI embeddings: {mention_count}")
    print(f"  Clusters with OpenAI embeddings: {cluster_count}")

    # Test a search
    print("\n  Testing vector search...")
    test_embedding = embed_batch(["refund delayed cancel payment"])[0]

    result = sb.rpc("match_mentions_openai", {
        "query_embedding": test_embedding,
        "match_threshold": 0.3,
        "match_count": 3,
    }).execute()

    if result.data:
        print(f"  Search returned {len(result.data)} results:")
        for r in result.data:
            print(f"    sim={r['similarity']:.3f} [{r['platform']}] {(r['content_text'] or '')[:80]}...")
    else:
        print("  WARNING: Search returned 0 results")

    return mention_count, cluster_count


if __name__ == "__main__":
    print("=" * 60)
    print("OpenAI Re-Embedding Pipeline")
    print(f"Model: {MODEL} (1536 dimensions)")
    print("=" * 60)

    n_mentions = embed_mentions()
    n_clusters = embed_clusters()

    print(f"\n{'=' * 60}")
    print(f"DONE: {n_mentions} mentions + {n_clusters} clusters embedded")
    print(f"{'=' * 60}")

    m_count, c_count = verify()

    print(f"\nTotal OpenAI embeddings: {m_count} mentions + {c_count} clusters")
    print("Ready for pure RAG search!")
