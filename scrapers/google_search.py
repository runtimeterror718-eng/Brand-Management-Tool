"""
Google Search & Trends scraper — no API key needed.

Scrapes:
  1. Google Autocomplete suggestions (what people type)
  2. People Also Ask questions
  3. Organic SERP results (title, snippet, URL, position)
  4. Google News results
  5. Google Trends (interest over time, by region in India)

Usage:
    python -m scrapers.google_search --brand "PhysicsWallah" --brand-id <uuid>
"""

from __future__ import annotations

import json
import logging
import re
import time
import random
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from storage import queries as db
from config.supabase_client import get_service_client

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
}

# =============================================================================
# 1. Google Autocomplete
# =============================================================================

def scrape_autocomplete(query: str) -> list[dict[str, Any]]:
    """Scrape Google autocomplete suggestions for a query."""
    url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={quote_plus(query)}&hl=en-IN"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        suggestions = data[1] if len(data) > 1 else []
        results = []
        for s in suggestions:
            # Classify sentiment of suggestion
            neg_words = ["scam", "fraud", "controversy", "fake", "refund", "complaint", "bad", "worst", "fail", "fired", "layoff", "lawsuit"]
            warn_words = ["review", "salary", "worth", "comparison", "vs", "alternative", "cancel"]
            sentiment = "neutral"
            s_lower = s.lower()
            if any(w in s_lower for w in neg_words):
                sentiment = "negative"
            elif any(w in s_lower for w in warn_words):
                sentiment = "warning"
            results.append({"suggestion": s, "sentiment": sentiment, "query": query})
        logger.info("Autocomplete for '%s': %d suggestions", query, len(results))
        return results
    except Exception as e:
        logger.warning("Autocomplete failed for '%s': %s", query, e)
        return []


# =============================================================================
# 2. SERP scraping (organic results + People Also Ask + news)
# =============================================================================

def scrape_serp(query: str) -> dict[str, Any]:
    """Scrape Google search results page for organic results, PAA, and featured snippets."""
    url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en&gl=in&num=10"
    time.sleep(random.uniform(2, 4))

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning("SERP returned %d for '%s'", resp.status_code, query)
            return {"organic": [], "paa": [], "news": [], "featured_snippet": None}

        soup = BeautifulSoup(resp.text, "html.parser")

        # Organic results
        organic = []
        for i, div in enumerate(soup.select("div.g")[:10], 1):
            title_el = div.select_one("h3")
            link_el = div.select_one("a[href]")
            snippet_el = div.select_one("div[data-sncf], span.st, div.VwiC3b")
            if title_el:
                organic.append({
                    "position": i,
                    "title": title_el.get_text(strip=True),
                    "url": link_el.get("href", "") if link_el else "",
                    "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                })

        # People Also Ask
        paa = []
        for div in soup.select("div[data-sgrd], div.related-question-pair, div[jsname='Cpkphb']"):
            text = div.get_text(strip=True)
            if text and len(text) > 10 and "?" in text:
                paa.append(text[:200])
        # Fallback: look for common PAA patterns
        if not paa:
            for span in soup.find_all(string=re.compile(r".+\?")):
                txt = span.strip()
                if 20 < len(txt) < 200 and txt not in paa:
                    paa.append(txt)
                    if len(paa) >= 6:
                        break

        # Featured snippet
        featured = None
        fs_div = soup.select_one("div.xpdopen, div[data-attrid='wa:/description']")
        if fs_div:
            featured = fs_div.get_text(strip=True)[:300]

        # News results
        news = []
        for article in soup.select("div[data-hveid] g-card, div.SoaBEf"):
            title_el = article.select_one("div[role='heading'], h3")
            if title_el:
                news.append({
                    "title": title_el.get_text(strip=True),
                    "source": "",
                })

        logger.info("SERP for '%s': %d organic, %d PAA, %d news", query, len(organic), len(paa), len(news))
        return {"organic": organic, "paa": paa, "news": news, "featured_snippet": featured}

    except Exception as e:
        logger.warning("SERP scrape failed for '%s': %s", query, e)
        return {"organic": [], "paa": [], "news": [], "featured_snippet": None}


# =============================================================================
# 3. Google News RSS
# =============================================================================

def scrape_google_news(query: str, max_results: int = 20) -> list[dict[str, Any]]:
    """Scrape Google News via RSS feed."""
    import feedparser

    rss_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        feed = feedparser.parse(rss_url)
        results = []
        for entry in feed.entries[:max_results]:
            results.append({
                "title": entry.get("title", ""),
                "source": entry.get("source", {}).get("title", ""),
                "url": entry.get("link", ""),
                "published": entry.get("published", ""),
                "snippet": entry.get("summary", "")[:200],
            })
        logger.info("Google News for '%s': %d articles", query, len(results))
        return results
    except Exception as e:
        logger.warning("Google News failed for '%s': %s", query, e)
        return []


# =============================================================================
# 4. Google Trends
# =============================================================================

def scrape_google_trends(keywords: list[str], timeframe: str = "today 3-m", geo: str = "IN") -> dict[str, Any]:
    """Scrape Google Trends data — interest over time and by region."""
    from pytrends.request import TrendReq

    try:
        pytrends = TrendReq(hl="en-IN", tz=330, timeout=(10, 25))

        # Interest over time
        pytrends.build_payload(keywords[:5], cat=0, timeframe=timeframe, geo=geo)
        iot = pytrends.interest_over_time()

        interest_over_time = []
        if not iot.empty:
            for date, row in iot.iterrows():
                point = {"date": date.strftime("%Y-%m-%d")}
                for kw in keywords[:5]:
                    if kw in row:
                        point[kw] = int(row[kw])
                interest_over_time.append(point)

        # Interest by region (Indian states)
        try:
            ibr = pytrends.interest_by_region(resolution="REGION", inc_low_vol=True, inc_geo_code=True)
            by_region = []
            if not ibr.empty:
                for region, row in ibr.iterrows():
                    vals = {kw: int(row[kw]) for kw in keywords[:5] if kw in row}
                    if any(v > 0 for v in vals.values()):
                        by_region.append({"region": region, **vals})
                by_region.sort(key=lambda x: sum(v for k, v in x.items() if k != "region"), reverse=True)
        except Exception:
            by_region = []

        # Related queries
        try:
            related = pytrends.related_queries()
            related_queries = {}
            for kw in keywords[:5]:
                if kw in related and related[kw]["top"] is not None:
                    related_queries[kw] = related[kw]["top"].head(10).to_dict("records")
        except Exception:
            related_queries = {}

        logger.info("Google Trends: %d time points, %d regions", len(interest_over_time), len(by_region))
        return {
            "interest_over_time": interest_over_time,
            "by_region": by_region[:20],
            "related_queries": related_queries,
            "keywords": keywords[:5],
            "timeframe": timeframe,
            "geo": geo,
        }

    except Exception as e:
        logger.warning("Google Trends failed: %s", e)
        return {"interest_over_time": [], "by_region": [], "related_queries": {}, "keywords": keywords[:5]}


# =============================================================================
# 5. Full Pipeline — store everything to Supabase
# =============================================================================

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


def triage_news_batch(articles: list[dict]) -> list[dict]:
    """LLM triage of Google News articles → sentiment, PR risk, severity for each."""
    if not articles: return articles
    c, m = _get_llm_client()
    if not c: return articles

    items = [f"[{i}] {a.get('title','')} — {a.get('source','')}" for i, a in enumerate(articles)]
    try:
        r = c.chat.completions.create(model=m, messages=[
            {"role":"system","content":"Classify each news article about Physics Wallah (PW). For each return index:sentiment:severity:issue_type. Sentiments: positive,negative,neutral. Severity: low,medium,high,critical. Issue types: brand_praise,refund,scam,teacher,ipo,controversy,legal,partnership,results,other. One per line: 0:negative:high:legal"},
            {"role":"user","content":"Classify:\n"+"\n".join(items)},
        ], temperature=0.1, max_tokens=600)
        raw = r.choices[0].message.content or ""
        for line in raw.strip().split("\n"):
            parts = line.strip().split(":")
            if len(parts) >= 4:
                try:
                    idx = int(parts[0])
                    if 0 <= idx < len(articles):
                        articles[idx]["sentiment"] = parts[1].strip()
                        articles[idx]["severity"] = parts[2].strip()
                        articles[idx]["issue_type"] = parts[3].strip()
                        articles[idx]["is_pr_risk"] = parts[1].strip() == "negative" and parts[2].strip() in ("high","critical")
                except (ValueError, IndexError): pass
    except Exception as e:
        logger.warning("News triage failed: %s", e)
    return articles


def triage_autocomplete_batch(suggestions: list[dict]) -> list[dict]:
    """LLM triage of autocomplete suggestions — more accurate than keyword rules."""
    if not suggestions: return suggestions
    c, m = _get_llm_client()
    if not c: return suggestions

    items = [f"[{i}] {s.get('suggestion','')}" for i, s in enumerate(suggestions)]
    try:
        r = c.chat.completions.create(model=m, messages=[
            {"role":"system","content":"Classify each Google autocomplete suggestion for Physics Wallah brand risk. Return index:label:severity:reason. Labels: negative,warning,neutral,positive. Severity: low,medium,high. One per line: 0:negative:high:scam allegation"},
            {"role":"user","content":"Classify:\n"+"\n".join(items)},
        ], temperature=0.1, max_tokens=600)
        raw = r.choices[0].message.content or ""
        for line in raw.strip().split("\n"):
            parts = line.strip().split(":", 3)
            if len(parts) >= 3:
                try:
                    idx = int(parts[0])
                    if 0 <= idx < len(suggestions):
                        suggestions[idx]["triage_label"] = parts[1].strip()
                        suggestions[idx]["triage_severity"] = parts[2].strip()
                        suggestions[idx]["triage_reason"] = parts[3].strip() if len(parts) > 3 else ""
                        suggestions[idx]["triage_is_pr_risk"] = parts[1].strip() == "negative" and parts[2].strip() in ("high","medium")
                except (ValueError, IndexError): pass
    except Exception as e:
        logger.warning("Autocomplete triage failed: %s", e)
    return suggestions


def run_google_pipeline(
    brand_id: str,
    brand_name: str = "Physics Wallah",
    queries: list[str] | None = None,
    enable_llm_triage: bool = True,
) -> dict[str, Any]:
    """
    Google Intelligence Pipeline — 4-tier monitoring system.

    Tier 1: Autocomplete Warfare — what 100M people see before visiting PW
    Tier 2: SERP Position Tracking — what Google shows for brand + risk queries
    Tier 3: News Radar — catch negative articles before they trend
    Tier 4: Competitive Trends — PW vs Allen/Unacademy/BYJU's interest
    """

    # ── Tier 1: Autocomplete Warfare ──────────────────────────
    # MVP: brand name + alphabet expansion (a-z) + risk terms
    autocomplete_queries = [
        # Core brand
        f"{brand_name}",
        # Alphabet expansion — what autocompletes after "physics wallah _"
        *[f"{brand_name} {chr(c)}" for c in range(ord('a'), ord('z') + 1)],
        # Key risk terms
        "pw scam",
        "pw refund",
        "alakh pandey",
        "pw skills",
        "pw vidyapeeth",
    ]

    # ── Tier 2: SERP Tracking ─────────────────────────────────
    # MVP: 3 brand + 3 risk + 2 competitor queries = 8 total
    serp_queries = [
        # Brand queries (what parents/students search)
        f"{brand_name}",
        f"{brand_name} review",
        f"is {brand_name} good",
        # Risk queries (what surfaces during crises)
        f"{brand_name} scam",
        f"{brand_name} refund complaint",
        f"{brand_name} consumer court",
        # Competitor queries (where PW ranks)
        "best coaching for JEE 2026",
        "best coaching for NEET 2026",
    ]

    # ── Tier 3: News Radar ────────────────────────────────────
    news_queries = [
        f"{brand_name}",
        "alakh pandey",
        f"{brand_name} IPO",
        "edtech scam India",
    ]

    # ── Tier 4: Competitive Trends ────────────────────────────
    trends_keywords = [brand_name, "Allen Career Institute", "Unacademy", "BYJU'S"]

    client = get_service_client()

    # --- Tier 1: Autocomplete ---
    print(f"Tier 1: Autocomplete warfare ({len(autocomplete_queries)} queries)...")
    all_autocomplete = []
    for q in autocomplete_queries:
        suggestions = scrape_autocomplete(q)
        all_autocomplete.extend(suggestions)
        time.sleep(random.uniform(0.3, 0.8))

    # Dedup suggestions
    seen = set()
    unique_autocomplete = []
    for s in all_autocomplete:
        key = s["suggestion"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique_autocomplete.append(s)
    all_autocomplete = unique_autocomplete
    print(f"  {len(all_autocomplete)} unique suggestions found")

    # --- Tier 2: SERP ---
    print(f"Tier 2: SERP tracking ({len(serp_queries)} queries)...")
    all_serp = {}
    for q in serp_queries:
        serp = scrape_serp(q)
        all_serp[q] = serp
        time.sleep(random.uniform(3, 5))

    # --- Tier 3: News ---
    print(f"Tier 3: News radar ({len(news_queries)} queries)...")
    all_news = []
    for q in news_queries:
        news = scrape_google_news(q, max_results=15)
        all_news.extend(news)
        time.sleep(random.uniform(1, 2))

    # Dedup news
    seen_titles = set()
    unique_news = []
    for n in all_news:
        key = n["title"].lower().strip()[:80]
        if key not in seen_titles:
            seen_titles.add(key)
            unique_news.append(n)
    all_news = unique_news
    print(f"  {len(all_news)} unique articles found")

    # --- Tier 4: Trends ---
    print(f"Tier 4: Competitive trends ({len(trends_keywords)} keywords)...")
    trends = scrape_google_trends(trends_keywords)

    # --- LLM Intelligence ---
    pr_risks = 0
    if enable_llm_triage:
        print("Running LLM triage on autocomplete...")
        all_autocomplete = triage_autocomplete_batch(all_autocomplete)
        pr_risks += sum(1 for s in all_autocomplete if s.get("triage_is_pr_risk"))

        print("Running LLM triage on news...")
        all_news = triage_news_batch(all_news)
        pr_risks += sum(1 for n in all_news if n.get("is_pr_risk"))

        print(f"LLM triage: {pr_risks} PR risks flagged")

    # --- Store to Supabase ---
    print("Storing to Supabase...")
    stored = 0

    for q, serp in all_serp.items():
        for result in serp["organic"]:
            try:
                client.table("google_seo_results").insert({
                    "brand_id": brand_id,
                    "query_text": q,
                    "organic_title": result["title"],
                    "organic_snippet": result["snippet"],
                    "organic_url": result["url"],
                    "organic_position": result["position"],
                    "people_also_ask": json.dumps(serp["paa"][:5]) if serp["paa"] else None,
                    "featured_snippet_text": serp["featured_snippet"],
                    "news_results": json.dumps([n["title"] for n in all_news[:5]]) if all_news else None,
                    "related_searches": json.dumps([s["suggestion"] for s in all_autocomplete if s["query"] == q]),
                    "autocomplete_suggestion": json.dumps([s["suggestion"] for s in all_autocomplete if s["query"] == q]),
                    "search_result_date": datetime.utcnow().isoformat(),
                    "raw_data": {
                        "serp": serp,
                        "autocomplete": [s for s in all_autocomplete if s["query"] == q],
                        "trends_snapshot": {
                            "latest": trends["interest_over_time"][-1] if trends["interest_over_time"] else None,
                            "top_region": trends["by_region"][0] if trends["by_region"] else None,
                        },
                    },
                }).execute()
                stored += 1
            except Exception:
                logger.exception("Failed to store SERP result")

    # Store negative/warning autocomplete as mentions for RAG
    for s in all_autocomplete:
        is_negative = s.get("sentiment") in ("negative", "warning") or s.get("triage_label") in ("negative", "warning")
        if is_negative:
            try:
                db.insert_mention({
                    "brand_id": brand_id,
                    "platform": "google",
                    "content_text": f"Google autocomplete: {s['suggestion']}",
                    "content_type": "autocomplete",
                    "source_url": f"https://www.google.com/search?q={quote_plus(s['suggestion'])}",
                    "raw_data": s,
                })
            except Exception:
                pass

    # Store People Also Ask as mentions
    all_paa = []
    for q, serp in all_serp.items():
        for paa_text in serp.get("paa", []):
            all_paa.append({"query": q, "question": paa_text})
            # Negative PAA → store as mention
            neg_paa_words = ["scam", "fraud", "complaint", "refund", "fake", "bad", "worst", "controversy"]
            if any(w in paa_text.lower() for w in neg_paa_words):
                try:
                    db.insert_mention({
                        "brand_id": brand_id,
                        "platform": "google",
                        "content_text": f"People Also Ask: {paa_text}",
                        "content_type": "paa",
                        "source_url": f"https://www.google.com/search?q={quote_plus(q)}",
                        "raw_data": {"query": q, "paa": paa_text},
                    })
                except Exception:
                    pass

    # Store negative news articles as mentions
    for n in all_news:
        if n.get("is_pr_risk") or n.get("sentiment") == "negative":
            try:
                db.insert_mention({
                    "brand_id": brand_id,
                    "platform": "google",
                    "content_text": f"[{n.get('source', 'News')}] {n['title']}",
                    "content_type": "news",
                    "source_url": n.get("url", ""),
                    "raw_data": n,
                })
            except Exception:
                pass

    neg_auto = sum(1 for s in all_autocomplete if s.get("sentiment") in ("negative",) or s.get("triage_label") in ("negative",))
    warn_auto = sum(1 for s in all_autocomplete if s.get("sentiment") in ("warning",) or s.get("triage_label") in ("warning",))

    summary = {
        "autocomplete_total": len(all_autocomplete),
        "autocomplete_negative": neg_auto,
        "autocomplete_warning": warn_auto,
        "serp_queries": len(all_serp),
        "serp_organic_results": sum(len(s["organic"]) for s in all_serp.values()),
        "paa_questions": len(all_paa),
        "news_articles": len(all_news),
        "news_pr_risks": sum(1 for n in all_news if n.get("is_pr_risk")),
        "trends_data_points": len(trends.get("interest_over_time", [])),
        "trends_regions": len(trends.get("by_region", [])),
        "stored_in_supabase": stored,
        "pr_risks_total": (pr_risks if enable_llm_triage else 0),
        "llm_triage": enable_llm_triage,
    }

    print(f"\nGoogle pipeline complete: {json.dumps(summary, indent=2)}")
    return {
        "summary": summary,
        "autocomplete": all_autocomplete,
        "serp": all_serp,
        "paa": all_paa,
        "news": all_news,
        "trends": trends,
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Google Search + Trends scraper")
    parser.add_argument("--brand", default="Physics Wallah", help="Brand name")
    parser.add_argument("--brand-id", required=True, help="Brand UUID")
    args = parser.parse_args()

    result = run_google_pipeline(args.brand_id, args.brand)

    print(f"\n{'='*60}")
    print("GOOGLE INTELLIGENCE RESULTS")
    print(f"{'='*60}")
    s = result["summary"]
    print(f"  Autocomplete: {s['autocomplete_suggestions']} suggestions ({s['negative_autocomplete']} negative, {s['warning_autocomplete']} warning)")
    print(f"  SERP: {s['total_organic_results']} organic results across {s['serp_queries']} queries")
    print(f"  PAA: {s['paa_questions']} 'People Also Ask' questions")
    print(f"  News: {s['news_articles']} articles")
    print(f"  Trends: {s['trends_data_points']} time points, {s['trends_regions']} Indian regions")
    print(f"  Stored: {s['stored_in_supabase']} rows in google_seo_results")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
