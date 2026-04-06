"""
Reddit scraper — no-auth JSON API for negative PR detection.

Owner: Abhishek

Pipeline:
  1. Search targeted subreddits for PW mentions via Reddit's public JSON API
  2. Scrape posts + ALL comments (comments = where real criticism lives)
  3. Store to reddit_posts + reddit_comments + mentions

No API key needed — uses Reddit's public .json endpoints.

Usage:
    python -m scrapers.reddit --brand "PhysicsWallah" --max-posts 50 --max-comments 100
"""

from __future__ import annotations

import asyncio
import logging
import time
import random
from datetime import datetime
from typing import Any

import requests as http_requests

from scrapers.base import BaseScraper
from search.engine import register_searcher
from search.filters import SearchParams
from storage import queries as db

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "brand-monitoring-tool/1.0 (contact: dev@example.com)"}

# ---------------------------------------------------------------------------
# Subreddits and queries for PW negative PR
# ---------------------------------------------------------------------------

PW_SUBREDDITS = [
    "JEENEETards",
    "IndianAcademia",
    "btechtards",
    "Indian_Education",
    "CBSE",
    "india",
    "indiasocial",
]

PW_SEARCH_QUERIES = [
    "physicswallah",
    "physics wallah",
    "alakh pandey",
    "PW scam OR fraud OR controversy",
    "PW quality OR teachers leaving OR refund",
    "PW layoffs OR data leak OR IPO",
]


# ---------------------------------------------------------------------------
# Reddit JSON API helpers (no auth needed)
# ---------------------------------------------------------------------------

def _reddit_search(
    subreddit: str,
    query: str,
    sort: str = "relevance",
    time_filter: str = "year",
    limit: int = 25,
) -> list[dict]:
    """Search a subreddit via public JSON API."""
    try:
        resp = http_requests.get(
            f"https://www.reddit.com/r/{subreddit}/search.json",
            params={
                "q": query,
                "sort": sort,
                "t": time_filter,
                "limit": str(limit),
                "restrict_sr": "on",
            },
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code == 429:
            logger.warning("Reddit rate limited, waiting 10s...")
            time.sleep(10)
            return []
        if resp.status_code != 200:
            logger.warning("Reddit search %d for r/%s '%s'", resp.status_code, subreddit, query)
            return []
        return resp.json().get("data", {}).get("children", [])
    except Exception as e:
        logger.warning("Reddit search error for r/%s: %s", subreddit, e)
        return []


def _reddit_get_comments(permalink: str, limit: int = 100) -> list[dict]:
    """Get comments for a post via public JSON API."""
    try:
        url = f"https://www.reddit.com{permalink}.json"
        resp = http_requests.get(
            url,
            params={"limit": str(limit), "sort": "top"},
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        if len(data) < 2:
            return []

        comments = []
        comment_listing = data[1].get("data", {}).get("children", [])
        for child in comment_listing:
            if child.get("kind") != "t1":
                continue
            c = child.get("data", {})
            if not c.get("body") or c["body"] == "[deleted]":
                continue
            created = datetime.utcfromtimestamp(c.get("created_utc", 0))
            comments.append({
                "comment_body": c["body"],
                "comment_author": c.get("author", "[deleted]"),
                "comment_score": c.get("score", 0),
                "comment_parent_id": c.get("parent_id", ""),
                "comment_depth": c.get("depth", 0),
                "created_at": created.isoformat(),
            })

            # Also get replies (1 level deep)
            replies = c.get("replies")
            if isinstance(replies, dict):
                for reply_child in replies.get("data", {}).get("children", []):
                    if reply_child.get("kind") != "t1":
                        continue
                    r = reply_child.get("data", {})
                    if not r.get("body") or r["body"] == "[deleted]":
                        continue
                    r_created = datetime.utcfromtimestamp(r.get("created_utc", 0))
                    comments.append({
                        "comment_body": r["body"],
                        "comment_author": r.get("author", "[deleted]"),
                        "comment_score": r.get("score", 0),
                        "comment_parent_id": r.get("parent_id", ""),
                        "comment_depth": r.get("depth", 1),
                        "created_at": r_created.isoformat(),
                    })

        return comments[:limit]
    except Exception as e:
        logger.warning("Reddit comment scrape error: %s", e)
        return []


def _submission_to_dict(post_data: dict, subreddit: str = "") -> dict[str, Any]:
    """Convert Reddit JSON post to our standard format."""
    d = post_data.get("data", post_data)
    published = datetime.utcfromtimestamp(d.get("created_utc", 0))
    sub = subreddit or d.get("subreddit", "")
    return {
        "post_id": d.get("id", ""),
        "content_text": f"{d.get('title', '')}\n{d.get('selftext', '')}",
        "content_type": "text",
        "author_handle": d.get("author", "[deleted]"),
        "author_name": d.get("author", "[deleted]"),
        "engagement_score": d.get("score", 0),
        "likes": d.get("score", 0),
        "shares": 0,
        "comments_count": d.get("num_comments", 0),
        "source_url": f"https://reddit.com{d.get('permalink', '')}",
        "published_at": published.isoformat(),
        "language": "en",
        "raw_data": {
            "subreddit": sub,
            "id": d.get("id", ""),
            "upvote_ratio": d.get("upvote_ratio", 0),
            "permalink": d.get("permalink", ""),
            "is_self": d.get("is_self", True),
            "num_awards": d.get("total_awards_received", 0),
            "flair": d.get("link_flair_text"),
        },
    }


# ---------------------------------------------------------------------------
# LLM Intelligence Layer
# ---------------------------------------------------------------------------

def _get_llm_client():
    from config.settings import (
        AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION,
        AZURE_OPENAI_DEPLOYMENT_GPT54, AZURE_OPENAI_DEPLOYMENT_GPT53,
        AZURE_OPENAI_DEPLOYMENT_GPT52, OPENAI_API_KEY, OPENAI_MODEL,
    )
    dep = AZURE_OPENAI_DEPLOYMENT_GPT54 or AZURE_OPENAI_DEPLOYMENT_GPT53 or AZURE_OPENAI_DEPLOYMENT_GPT52
    if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and dep:
        from openai import AzureOpenAI
        return AzureOpenAI(api_key=AZURE_OPENAI_API_KEY, api_version=AZURE_OPENAI_API_VERSION, azure_endpoint=AZURE_OPENAI_ENDPOINT), dep
    if OPENAI_API_KEY:
        from openai import OpenAI
        return OpenAI(api_key=OPENAI_API_KEY), OPENAI_MODEL or "gpt-4o-mini"
    return None, None


def _llm_json(system: str, user: str) -> dict:
    import json as _j
    c, m = _get_llm_client()
    if not c: return {}
    try:
        r = c.chat.completions.create(model=m, messages=[{"role":"system","content":system},{"role":"user","content":user}], temperature=0.0, response_format={"type":"json_object"})
        return _j.loads(r.choices[0].message.content or "{}")
    except Exception as e:
        logger.warning("LLM call failed: %s", e)
        return {}


def triage_reddit_post(title: str, body: str, subreddit: str, score: int) -> dict[str, Any]:
    """LLM triage of Reddit post → sentiment, PR risk, issue type, severity."""
    text = f"{title}\n{body[:1500]}" if body else title
    if len(text.strip()) < 10:
        return {"label": "neutral", "is_pr_risk": False, "confidence": 0.3, "issue_type": "none", "severity": "low", "reason": "empty"}
    r = _llm_json(
        "You are a brand PR analyst for Physics Wallah (PW), Indian edtech. Classify this Reddit post. Return JSON: {\"label\":\"positive|negative|neutral|uncertain\",\"is_pr_risk\":true/false,\"confidence\":0.0-1.0,\"issue_type\":\"brand_praise|course_review|refund_complaint|quality_complaint|scam_allegation|teacher_exodus|app_issue|employer_criticism|ipo_discussion|political|student_experience|competitor_comparison|meme|other\",\"severity\":\"low|medium|high|critical\",\"reason\":\"1 sentence\"}",
        f"Subreddit: r/{subreddit}\nScore: {score}\nTitle: {title}\nBody:\n{(body or '')[:2000]}",
    )
    return {"label": r.get("label","neutral"), "is_pr_risk": r.get("is_pr_risk",False), "confidence": min(1.0, max(0.0, r.get("confidence",0.5))), "issue_type": r.get("issue_type","other"), "severity": r.get("severity","low"), "reason": r.get("reason","")}


def classify_reddit_comments_batch(comments: list[dict]) -> dict[int, str]:
    """Batch classify Reddit comments."""
    if not comments: return {}
    items = [f"[{i}] {(c.get('comment_body') or '')[:200]}" for i, c in enumerate(comments)]
    c, m = _get_llm_client()
    if not c: return {}
    try:
        r = c.chat.completions.create(model=m, messages=[
            {"role":"system","content":"Classify each Reddit comment sentiment toward Physics Wallah. Understand Indian slang, Hinglish, sarcasm. Return ONLY index:label, one per line. Labels: positive, negative, neutral."},
            {"role":"user","content":f"Classify all {len(items)}:\n"+"\n".join(items)},
        ], temperature=0.1, max_tokens=800)
        raw = r.choices[0].message.content or ""
        results = {}
        for line in raw.strip().split("\n"):
            if ":" not in line: continue
            parts = line.split(":", 1)
            try:
                idx = int(parts[0].strip())
                lab = parts[1].strip().lower().rstrip(".")
                if lab in ("positive","negative","neutral") and 0 <= idx < len(comments):
                    results[idx] = lab
            except (ValueError, IndexError): pass
        return results
    except Exception as e:
        logger.warning("Reddit comment classification failed: %s", e)
        return {}


def synthesize_reddit_post(triage: dict, comment_stats: dict) -> dict[str, Any]:
    """Final synthesis: combine post triage + comment sentiment → verdict."""
    final = triage.get("label", "neutral")
    severity = triage.get("severity", "low")
    risk = triage.get("is_pr_risk", False)
    issue = triage.get("issue_type", "other")
    action = "ignore"

    neg = comment_stats.get("negative", 0)
    total = comment_stats.get("total", 0)
    if total > 3 and neg / total > 0.5:
        risk = True
        if severity == "low": severity = "medium"
        action = "monitor"

    sev = {"low":0,"medium":1,"high":2,"critical":3}
    if sev.get(severity,0) >= 2:
        action = "escalate" if severity == "critical" else "respond"
    elif risk and action == "ignore":
        action = "monitor"

    return {"final_sentiment": final, "final_severity": severity, "final_is_pr_risk": risk, "final_issue_type": issue, "final_recommended_action": action}


# ---------------------------------------------------------------------------
# Scraper class
# ---------------------------------------------------------------------------

class RedditScraper(BaseScraper):
    platform = "reddit"

    async def search(self, params: SearchParams) -> list[dict[str, Any]]:
        """Search Reddit for PW mentions across targeted subreddits."""
        results = []
        seen_ids = set()

        queries = params.keywords or PW_SEARCH_QUERIES
        subreddits = getattr(params, '_reddit_subreddits', None) or PW_SUBREDDITS
        max_per = max(params.max_results_per_platform // max(len(queries) * len(subreddits), 1), 10)

        def _search():
            for sub in subreddits:
                for query in queries:
                    time.sleep(random.uniform(1, 2))
                    posts = _reddit_search(sub, query, sort="relevance", limit=max_per)
                    for p in posts:
                        pid = p.get("data", {}).get("id", "")
                        if pid and pid not in seen_ids:
                            seen_ids.add(pid)
                            results.append(_submission_to_dict(p, sub))
                logger.info("Searched r/%s: %d queries, %d total posts so far", sub, len(queries), len(results))

            # Also search r/all for top PW content
            for query in queries[:3]:
                time.sleep(random.uniform(1, 2))
                posts = _reddit_search("all", query, sort="top", time_filter="year", limit=max_per)
                for p in posts:
                    pid = p.get("data", {}).get("id", "")
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        results.append(_submission_to_dict(p))

        await asyncio.get_event_loop().run_in_executor(None, _search)
        logger.info("Reddit search complete: %d unique posts", len(results))
        return results

    async def scrape_and_store_post(
        self, submission_data: dict[str, Any], brand_id: str,
    ) -> dict[str, Any]:
        """Store a Reddit post to reddit_posts + mentions."""
        raw = submission_data.get("raw_data", {})
        published = submission_data.get("published_at")

        post_row = {
            "brand_id": brand_id,
            "post_id": submission_data.get("post_id", raw.get("id", "")),
            "post_title": submission_data.get("content_text", "").split("\n")[0],
            "post_body": "\n".join(submission_data.get("content_text", "").split("\n")[1:]),
            "author_username": submission_data.get("author_handle", ""),
            "subreddit_name": raw.get("subreddit", ""),
            "score": submission_data.get("likes", 0),
            "upvote_ratio": raw.get("upvote_ratio"),
            "num_comments": submission_data.get("comments_count", 0),
            "created_at": published,
            "post_url": submission_data.get("source_url", ""),
            "post_flair": raw.get("flair"),
            "is_self_post": raw.get("is_self", True),
            "awards_received": raw.get("num_awards", 0),
            "raw_data": raw,
        }

        stored_post = {}
        try:
            stored_post = db.insert_reddit_post(post_row)
            logger.info(
                "Stored r/%s post [%+d] %s",
                post_row.get("subreddit_name", "?"),
                post_row.get("score", 0),
                post_row["post_id"],
            )
        except Exception:
            logger.exception("Failed to store Reddit post %s", post_row["post_id"])

        try:
            mention = db.insert_mention({
                "brand_id": brand_id,
                "platform": "reddit",
                "platform_ref_id": stored_post.get("id", ""),
                "content_text": submission_data.get("content_text", ""),
                "content_type": "text",
                "author_handle": submission_data.get("author_handle", ""),
                "engagement_score": submission_data.get("likes", 0),
                "likes": submission_data.get("likes", 0),
                "comments_count": submission_data.get("comments_count", 0),
                "source_url": submission_data.get("source_url", ""),
                "published_at": published,
                "raw_data": raw,
            })
            stored_post["_mention_id"] = mention.get("id")
        except Exception:
            logger.exception("Failed to store mention for Reddit post %s", post_row["post_id"])

        return stored_post

    async def scrape_comments(self, source_url: str, limit: int = 200) -> list[dict[str, Any]]:
        """Scrape comments from a Reddit post via public JSON API."""
        raw_permalink = source_url.replace("https://reddit.com", "")
        comments = []

        def _scrape():
            nonlocal comments
            time.sleep(random.uniform(0.5, 1.5))
            raw_comments = _reddit_get_comments(raw_permalink, limit=limit)
            for c in raw_comments:
                c["post_id"] = raw_permalink.split("/comments/")[1].split("/")[0] if "/comments/" in raw_permalink else ""
            comments = raw_comments

        await asyncio.get_event_loop().run_in_executor(None, _scrape)

        if comments:
            try:
                db.insert_reddit_comments_batch(comments)
                logger.info("Stored %d comments for %s", len(comments), source_url.split("/")[-2][:20])
            except Exception:
                logger.exception("Failed to store Reddit comments")

        return comments

    async def run_pipeline(
        self, brand_id: str, keywords: list[str], hashtags: list[str],
        max_comments: int = 100,
        enable_llm_triage: bool = True,
        enable_comment_classification: bool = True,
    ) -> dict:
        """
        Full Reddit pipeline with LLM intelligence:
        1. Search subreddits for PW mentions
        2. LLM triage every post (title + body → sentiment, PR risk, severity)
        3. Store posts with intelligence fields
        4. Scrape comments → LLM batch classify
        5. Final synthesis → risk score + recommended action
        6. Geo inference
        """
        params = SearchParams(
            keywords=keywords,
            hashtags=hashtags,
            platforms=["reddit"],
            brand_id=brand_id,
        )

        search_results = await self.search(params)
        logger.info("Reddit pipeline: %d posts found", len(search_results))
        search_results.sort(key=lambda x: x.get("engagement_score", 0), reverse=True)

        posts_stored = 0
        posts_triaged = 0
        comments_scraped = 0
        comments_classified = 0
        pr_risks_flagged = 0

        for result in search_results:
            raw = result.get("_raw_post", result)
            post_id = result.get("post_id", "")
            title = raw.get("post_title", "") or result.get("content_text", "")
            body = raw.get("post_body", "")
            subreddit = raw.get("subreddit_name", "")
            score = raw.get("score", 0)

            # ── LLM Post Triage ───────────────────────────────
            triage_result = {}
            if enable_llm_triage:
                triage_result = triage_reddit_post(title, body, subreddit, score)
                posts_triaged += 1
                if triage_result.get("is_pr_risk"):
                    logger.warning("REDDIT PR RISK: r/%s [%s] %s — %s",
                        subreddit, triage_result["severity"], triage_result["issue_type"], triage_result["reason"])

            # ── Store post ────────────────────────────────────
            stored = await self.scrape_and_store_post(result, brand_id)
            if stored:
                posts_stored += 1

            # ── Scrape + classify comments ────────────────────
            comment_stats = {"positive": 0, "negative": 0, "neutral": 0, "total": 0}
            if result.get("comments_count", 0) > 0 and max_comments > 0:
                post_comments = await self.scrape_comments(result["source_url"], limit=max_comments)
                comments_scraped += len(post_comments)
                comment_stats["total"] = len(post_comments)

                if enable_comment_classification and post_comments:
                    for batch_start in range(0, len(post_comments), 30):
                        batch = post_comments[batch_start:batch_start + 30]
                        labels = classify_reddit_comments_batch(batch)
                        for idx, label in labels.items():
                            comments_classified += 1
                            comment_stats[label] = comment_stats.get(label, 0) + 1
                            # Update comment in DB
                            cid = batch[idx].get("id") or batch[idx].get("comment_id")
                            if cid:
                                try:
                                    from config.supabase_client import get_service_client
                                    get_service_client().table("reddit_comments").update({"comment_sentiment_label": label}).eq("id", cid).execute()
                                except Exception:
                                    pass

            # ── Final synthesis ────────────────────────────────
            if triage_result:
                synthesis = synthesize_reddit_post(triage_result, comment_stats)
                if synthesis.get("final_is_pr_risk"):
                    pr_risks_flagged += 1

                # Write intelligence fields to reddit_posts
                update_fields = {
                    "post_triage_label": triage_result.get("label"),
                    "post_triage_is_pr_risk": triage_result.get("is_pr_risk", False),
                    "post_triage_confidence": triage_result.get("confidence", 0),
                    "post_triage_issue_type": triage_result.get("issue_type"),
                    "post_triage_severity": triage_result.get("severity"),
                    "post_triage_reason": triage_result.get("reason"),
                    **synthesis,
                }
                if post_id:
                    try:
                        from config.supabase_client import get_service_client
                        get_service_client().table("reddit_posts").update(update_fields).eq("post_id", post_id).execute()
                    except Exception:
                        logger.exception("Failed to update reddit post intelligence for %s", post_id)

        # ── Geo inference ─────────────────────────────────────
        geo_result = {"geo_records_created": 0, "unique_states": 0}
        try:
            from analysis.geo_inference import process_mentions_geo
            geo_result = process_mentions_geo(brand_id)
        except Exception:
            logger.exception("Geo inference failed (non-fatal)")

        summary = {
            "platform": "reddit",
            "brand_id": brand_id,
            "posts_found": len(search_results),
            "posts_stored": posts_stored,
            "posts_triaged": posts_triaged,
            "comments_scraped": comments_scraped,
            "comments_classified": comments_classified,
            "pr_risks_flagged": pr_risks_flagged,
            "geo_records": geo_result.get("geo_records_created", 0),
        }
        logger.info("Reddit pipeline complete: %s", summary)
        return summary


# Register searcher
_scraper = RedditScraper()
register_searcher("reddit", _scraper.search)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Reddit negative PR scraper")
    parser.add_argument("--brand", required=True, help="Brand name to monitor")
    parser.add_argument("--brand-id", help="Existing brand UUID in Supabase")
    parser.add_argument("--keywords", default="",
                        help="Extra search keywords (comma-separated)")
    parser.add_argument("--max-posts", type=int, default=50,
                        help="Max total posts")
    parser.add_argument("--max-comments", type=int, default=50,
                        help="Max comments per post")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords:
        keywords = PW_SEARCH_QUERIES

    print(f"{'='*60}")
    print(f"  Reddit Negative PR Detection")
    print(f"{'='*60}")
    print(f"  Subreddits:   {', '.join(PW_SUBREDDITS)}")
    print(f"  Queries:      {len(keywords)}")
    print(f"  Max posts:    {args.max_posts}")
    print(f"  Max comments: {args.max_comments}/post")
    print(f"{'='*60}")
    print()

    brand_id = args.brand_id
    if not brand_id:
        brand = db.upsert_brand({
            "name": args.brand,
            "keywords": keywords[:5],
            "platforms": ["reddit"],
        })
        brand_id = brand["id"]
        print(f"Brand '{args.brand}' -> {brand_id}")

    loop = asyncio.new_event_loop()
    scraper = RedditScraper()
    try:
        result = loop.run_until_complete(scraper.run_pipeline(
            brand_id=brand_id,
            keywords=keywords,
            hashtags=[],
            max_comments=args.max_comments,
        ))
    finally:
        loop.close()

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Posts found:      {result['posts_found']}")
    print(f"  Posts stored:     {result['posts_stored']}")
    print(f"  Comments scraped: {result['comments_scraped']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
