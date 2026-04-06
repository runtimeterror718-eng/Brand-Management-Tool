"""
RAG (Retrieval Augmented Generation) engine for brand intelligence.

Pipeline:
  1. Embed all mentions + cluster summaries → store in Supabase pgvector
  2. On query: embed question → similarity search → retrieve top-K context
  3. Feed context to LLM → grounded answer with real quotes

Usage:
    # Build embeddings (run once after scraping)
    python -m analysis.rag --build --brand-id <uuid>

    # Ask a question
    python -m analysis.rag --ask "What are students saying about PW teachers?" --brand-id <uuid>
"""

from __future__ import annotations

import json
import logging
from typing import Any

from config.supabase_client import get_service_client
from config.settings import OPENAI_API_KEY, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, OPENAI_MODEL

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding model (same MiniLM used in clustering)
# ---------------------------------------------------------------------------

_embed_model = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model for RAG...")
        _embed_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _embed_model


def embed_text(text: str) -> list[float]:
    """Embed a single text string. Returns 384-dim vector."""
    model = _get_embed_model()
    vec = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts."""
    model = _get_embed_model()
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return [v.tolist() for v in vecs]


# ---------------------------------------------------------------------------
# Step 1: Build embeddings from existing mentions + clusters
# ---------------------------------------------------------------------------

def build_mention_embeddings(brand_id: str) -> int:
    """Embed all mentions for a brand and store in mention_embeddings."""
    client = get_service_client()

    # Fetch mentions that don't have embeddings yet
    resp = client.table("mentions").select(
        "id, brand_id, content_text, platform, cluster_id, sentiment_label, sentiment_score"
    ).eq("brand_id", brand_id).not_.is_("content_text", "null").limit(2000).execute()

    mentions = resp.data
    if not mentions:
        logger.info("No mentions to embed")
        return 0

    # Filter out already embedded
    existing = client.table("mention_embeddings").select("mention_id").eq(
        "brand_id", brand_id
    ).execute()
    existing_ids = {r["mention_id"] for r in (existing.data or [])}
    new_mentions = [m for m in mentions if m["id"] not in existing_ids]

    if not new_mentions:
        logger.info("All mentions already embedded")
        return 0

    logger.info("Embedding %d new mentions...", len(new_mentions))

    texts = [m.get("content_text", "")[:500] for m in new_mentions]
    embeddings = embed_batch(texts)

    # Store in batches of 50
    stored = 0
    for i in range(0, len(new_mentions), 50):
        batch = []
        for j, m in enumerate(new_mentions[i:i + 50]):
            batch.append({
                "mention_id": m["id"],
                "brand_id": m["brand_id"],
                "content_text": (m.get("content_text") or "")[:500],
                "platform": m.get("platform"),
                "cluster_id": m.get("cluster_id"),
                "sentiment_label": m.get("sentiment_label"),
                "sentiment_score": m.get("sentiment_score"),
                "embedding": embeddings[i + j],
            })
        try:
            client.table("mention_embeddings").insert(batch).execute()
            stored += len(batch)
        except Exception:
            logger.exception("Failed to store embedding batch")

    logger.info("Stored %d mention embeddings", stored)
    return stored


def build_cluster_embeddings(brand_id: str) -> int:
    """Build cluster summary embeddings from clustered mentions."""
    client = get_service_client()

    # Get cluster data
    resp = client.table("mentions").select(
        "cluster_id, content_text, platform, sentiment_label, sentiment_score"
    ).eq("brand_id", brand_id).not_.is_("cluster_id", "null").execute()

    mentions = resp.data or []
    if not mentions:
        return 0

    # Group by cluster
    clusters: dict[int, list[dict]] = {}
    for m in mentions:
        cid = m["cluster_id"]
        if cid == -1:
            continue
        if cid not in clusters:
            clusters[cid] = []
        clusters[cid].append(m)

    logger.info("Building embeddings for %d clusters", len(clusters))

    records = []
    for cid, members in clusters.items():
        # Build summary from representative texts
        sorted_members = sorted(members, key=lambda x: len(x.get("content_text", "")), reverse=True)
        rep_texts = [m["content_text"][:200] for m in sorted_members[:5]]

        platforms = {}
        sentiments = []
        for m in members:
            p = m.get("platform", "unknown")
            platforms[p] = platforms.get(p, 0) + 1
            if m.get("sentiment_score") is not None:
                sentiments.append(m["sentiment_score"])

        avg_sent = sum(sentiments) / len(sentiments) if sentiments else 0

        # Create summary text for embedding
        summary = f"Cluster {cid}: {len(members)} mentions. "
        summary += f"Platforms: {json.dumps(platforms)}. "
        summary += f"Avg sentiment: {avg_sent:.2f}. "
        summary += "Representative content: " + " | ".join(rep_texts[:3])

        # Auto-label based on content
        label = _auto_label_cluster(rep_texts, avg_sent)

        embedding = embed_text(summary)

        records.append({
            "brand_id": brand_id,
            "cluster_id": cid,
            "cluster_label": label,
            "summary": summary,
            "mention_count": len(members),
            "avg_sentiment": round(avg_sent, 3),
            "platforms": platforms,
            "representative_texts": rep_texts,
            "embedding": embedding,
        })

    # Upsert
    stored = 0
    for r in records:
        try:
            client.table("cluster_embeddings").upsert(
                r, on_conflict="brand_id,cluster_id"
            ).execute()
            stored += 1
        except Exception:
            logger.exception("Failed to store cluster embedding %d", r["cluster_id"])

    logger.info("Stored %d cluster embeddings", stored)
    return stored


def _auto_label_cluster(texts: list[str], avg_sentiment: float) -> str:
    """Auto-generate a cluster label from content."""
    combined = " ".join(texts).lower()

    if any(w in combined for w in ["topper", "rank 1", "result", "cleared"]):
        return "Results & Toppers"
    if any(w in combined for w in ["donate", "lakh", "farmer", "crpf", "charity"]):
        return "Alakh Pandey Charity & Goodwill"
    if any(w in combined for w in ["batch", "arjuna", "yakeen", "lakshya", "neev", "join"]):
        return "Course Queries & Comparisons"
    if any(w in combined for w in ["bakchodi", "wilder", "kya hai", "💀"]):
        return "Memes & Student Criticism"
    if any(w in combined for w in ["kota", "factory", "aadhya", "sam"]):
        return "Kota Factory Fandom"
    if any(w in combined for w in ["ritik", "aarushi", "teacher", "sir"]):
        return "Teacher Fan Content"
    if any(w in combined for w in ["motivation", "#success", "#dream", "neet_jee"]):
        return "JEE/NEET Motivation"
    if avg_sentiment < -0.3:
        return "Negative Sentiment"
    if avg_sentiment > 0.5:
        return "Positive Sentiment"
    return "General Discussion"


# ---------------------------------------------------------------------------
# Step 2: Retrieval — find relevant context for a query
# ---------------------------------------------------------------------------

def retrieve(
    query: str,
    brand_id: str,
    top_k_mentions: int = 10,
    top_k_clusters: int = 3,
    threshold: float = 0.3,
) -> dict[str, Any]:
    """
    Retrieve relevant mentions + clusters for a query.

    Returns context dict ready to feed to LLM.
    """
    client = get_service_client()
    query_vec = embed_text(query)

    # Search mentions
    mention_results = client.rpc("match_mentions", {
        "query_embedding": query_vec,
        "match_threshold": threshold,
        "match_count": top_k_mentions,
        "filter_brand_id": brand_id,
    }).execute()

    # Search clusters
    cluster_results = client.rpc("match_clusters", {
        "query_embedding": query_vec,
        "match_count": top_k_clusters,
        "filter_brand_id": brand_id,
    }).execute()

    mentions = mention_results.data or []
    clusters = cluster_results.data or []

    return {
        "query": query,
        "mentions": mentions,
        "clusters": clusters,
        "mention_count": len(mentions),
        "cluster_count": len(clusters),
    }


# ---------------------------------------------------------------------------
# Step 3: Generate — feed context to LLM
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a brand intelligence analyst for OVAL, a brand monitoring tool.
You answer questions about brand perception based ONLY on real scraped data from Reddit and Instagram.

Rules:
- Only use information from the provided context (real mentions and cluster summaries)
- Quote actual student comments in italics when relevant
- Be specific with numbers: mention counts, sentiment scores, engagement
- If the data doesn't cover the question, say so clearly
- Distinguish between Reddit sentiment (anonymous, more critical) and Instagram (fan community, more positive)
- Flag when a finding is based on limited data"""


def generate_answer(query: str, brand_id: str) -> dict[str, Any]:
    """
    Full RAG pipeline: retrieve context → generate grounded answer.
    """
    # Step 1: Retrieve
    context = retrieve(query, brand_id)

    if not context["mentions"] and not context["clusters"]:
        return {
            "answer": "I don't have enough data to answer this question. Try running the scrapers first to collect more mentions.",
            "sources": [],
            "context": context,
        }

    # Step 2: Build prompt with context
    context_text = _format_context(context)

    user_prompt = f"""Question: {query}

--- RETRIEVED CONTEXT (real scraped data) ---

{context_text}

--- END CONTEXT ---

Answer the question based ONLY on the context above. Be specific, cite real quotes, and mention sentiment scores."""

    # Step 3: Call LLM
    answer = _call_llm(user_prompt)

    return {
        "answer": answer,
        "sources": [
            {"type": "mention", "text": m["content_text"][:100], "platform": m["platform"],
             "sentiment": m["sentiment_label"], "similarity": round(m["similarity"], 3)}
            for m in context["mentions"]
        ],
        "clusters_used": [
            {"id": c["cluster_id"], "label": c["cluster_label"],
             "mentions": c["mention_count"], "similarity": round(c["similarity"], 3)}
            for c in context["clusters"]
        ],
        "context": context,
    }


def _format_context(context: dict) -> str:
    """Format retrieved context into a prompt-friendly string."""
    parts = []

    if context["clusters"]:
        parts.append("CLUSTER SUMMARIES:")
        for c in context["clusters"]:
            parts.append(f"\n[Cluster {c['cluster_id']}: {c.get('cluster_label', 'Unknown')}]")
            parts.append(f"  Mentions: {c['mention_count']}, Avg sentiment: {c['avg_sentiment']}")
            parts.append(f"  Summary: {c['summary'][:300]}")
            if c.get("representative_texts"):
                for t in c["representative_texts"][:3]:
                    parts.append(f"  Quote: \"{t[:150]}\"")

    if context["mentions"]:
        parts.append("\nRELEVANT MENTIONS:")
        for m in context["mentions"]:
            parts.append(f"\n[{m['platform']}] (sentiment: {m['sentiment_label']}, similarity: {m['similarity']:.2f})")
            parts.append(f"  \"{m['content_text'][:200]}\"")

    return "\n".join(parts)


def _call_llm(user_prompt: str) -> str:
    """Call OpenAI or Anthropic for answer generation."""
    # Try OpenAI first
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                max_tokens=1024,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content or ""
        except Exception:
            logger.exception("OpenAI RAG call failed, trying Anthropic...")

    # Fallback to Anthropic
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=1024,
                temperature=0.3,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return resp.content[0].text
        except Exception:
            logger.exception("Anthropic RAG call failed")

    return "No LLM provider configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="RAG engine for brand intelligence")
    parser.add_argument("--brand-id", required=True, help="Brand UUID")
    parser.add_argument("--build", action="store_true", help="Build embeddings from existing data")
    parser.add_argument("--ask", type=str, help="Ask a question about the brand")
    parser.add_argument("--retrieve-only", type=str, help="Retrieve context without LLM")
    args = parser.parse_args()

    if args.build:
        print("Building mention embeddings...")
        n_mentions = build_mention_embeddings(args.brand_id)
        print(f"  Mention embeddings: {n_mentions}")

        print("Building cluster embeddings...")
        n_clusters = build_cluster_embeddings(args.brand_id)
        print(f"  Cluster embeddings: {n_clusters}")

        print(f"\nDone. Total: {n_mentions} mention + {n_clusters} cluster embeddings.")

    if args.retrieve_only:
        context = retrieve(args.retrieve_only, args.brand_id)
        print(f"\nRetrieved {context['mention_count']} mentions, {context['cluster_count']} clusters")
        for m in context["mentions"]:
            print(f"  [{m['platform']}] sim={m['similarity']:.3f} | {m['content_text'][:80]}...")
        for c in context["clusters"]:
            print(f"  [Cluster {c['cluster_id']}: {c.get('cluster_label', '?')}] sim={c['similarity']:.3f}")

    if args.ask:
        print(f"\nQuestion: {args.ask}")
        print("Retrieving context + generating answer...\n")
        result = generate_answer(args.ask, args.brand_id)

        print("=" * 60)
        print("ANSWER:")
        print("=" * 60)
        print(result["answer"])
        print(f"\n--- Sources: {len(result['sources'])} mentions, {len(result['clusters_used'])} clusters ---")
        for s in result["sources"][:5]:
            print(f"  [{s['platform']}] sim={s['similarity']} | {s['text'][:80]}...")


if __name__ == "__main__":
    main()
