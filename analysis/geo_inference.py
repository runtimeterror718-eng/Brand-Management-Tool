"""
Geographic inference engine — extracts location signals from Reddit & Instagram data.

Methods:
  1. Subreddit mapping (r/mumbai → Maharashtra, r/JEENEETards → Rajasthan-heavy)
  2. Instagram location tags (when available in raw_data)
  3. Keyword extraction (city/state names in comment text)
  4. PW centre mentions ("Vidyapeeth Bhopal" → Madhya Pradesh)

Stores results to geo_mentions + aggregates to geo_aggregates in Supabase.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from storage import queries as db
from config.supabase_client import get_service_client

logger = logging.getLogger(__name__)

# =============================================================================
# India geography database
# =============================================================================

STATES: dict[str, dict[str, Any]] = {
    "DL": {"name": "Delhi", "lat": 28.6, "lng": 77.2},
    "RJ": {"name": "Rajasthan", "lat": 26.9, "lng": 75.8},
    "UP": {"name": "Uttar Pradesh", "lat": 26.8, "lng": 80.9},
    "MH": {"name": "Maharashtra", "lat": 19.1, "lng": 72.9},
    "KA": {"name": "Karnataka", "lat": 12.97, "lng": 77.6},
    "TN": {"name": "Tamil Nadu", "lat": 13.1, "lng": 80.3},
    "WB": {"name": "West Bengal", "lat": 22.6, "lng": 88.4},
    "GJ": {"name": "Gujarat", "lat": 23.0, "lng": 72.6},
    "BR": {"name": "Bihar", "lat": 25.6, "lng": 85.1},
    "MP": {"name": "Madhya Pradesh", "lat": 23.3, "lng": 77.4},
    "HR": {"name": "Haryana", "lat": 29.1, "lng": 76.1},
    "PB": {"name": "Punjab", "lat": 31.1, "lng": 75.3},
    "JK": {"name": "Jammu & Kashmir", "lat": 34.1, "lng": 74.8},
    "JH": {"name": "Jharkhand", "lat": 23.6, "lng": 85.3},
    "CG": {"name": "Chhattisgarh", "lat": 21.3, "lng": 81.6},
    "AS": {"name": "Assam", "lat": 26.1, "lng": 91.7},
    "KL": {"name": "Kerala", "lat": 10.0, "lng": 76.3},
    "TS": {"name": "Telangana", "lat": 17.4, "lng": 78.5},
    "AP": {"name": "Andhra Pradesh", "lat": 15.9, "lng": 79.7},
    "OR": {"name": "Odisha", "lat": 20.9, "lng": 85.1},
    "UK": {"name": "Uttarakhand", "lat": 30.1, "lng": 79.0},
    "HP": {"name": "Himachal Pradesh", "lat": 32.1, "lng": 77.2},
    "GA": {"name": "Goa", "lat": 15.3, "lng": 74.0},
}

# City → State mapping (major Indian cities)
CITY_TO_STATE: dict[str, str] = {
    # Metros
    "delhi": "DL", "new delhi": "DL", "noida": "UP", "gurgaon": "HR",
    "gurugram": "HR", "faridabad": "HR", "ghaziabad": "UP", "greater noida": "UP",
    "mumbai": "MH", "pune": "MH", "nagpur": "MH", "thane": "MH", "navi mumbai": "MH",
    "bangalore": "KA", "bengaluru": "KA", "mysore": "KA", "mysuru": "KA",
    "chennai": "TN", "madurai": "TN", "coimbatore": "TN",
    "kolkata": "WB", "howrah": "WB",
    "hyderabad": "TS", "secunderabad": "TS",
    "ahmedabad": "GJ", "surat": "GJ", "vadodara": "GJ", "rajkot": "GJ",
    # Coaching hubs
    "kota": "RJ", "jaipur": "RJ", "jodhpur": "RJ", "udaipur": "RJ", "ajmer": "RJ",
    "patna": "BR", "ranchi": "JH", "jamshedpur": "JH",
    "lucknow": "UP", "varanasi": "UP", "allahabad": "UP", "prayagraj": "UP",
    "kanpur": "UP", "agra": "UP", "meerut": "UP",
    "bhopal": "MP", "indore": "MP", "jabalpur": "MP", "gwalior": "MP",
    "chandigarh": "PB", "ludhiana": "PB", "amritsar": "PB",
    "dehradun": "UK", "haridwar": "UK",
    "raipur": "CG", "bhilai": "CG",
    "bhubaneswar": "OR", "cuttack": "OR",
    "guwahati": "AS", "dibrugarh": "AS",
    "thiruvananthapuram": "KL", "kochi": "KL", "cochin": "KL",
    "visakhapatnam": "AP", "vijayawada": "AP",
    "shimla": "HP", "dharamshala": "HP",
    "srinagar": "JK", "jammu": "JK", "baramulla": "JK",
    "panaji": "GA",
}

# Subreddit → State mapping (where the community is primarily from)
SUBREDDIT_TO_STATE: dict[str, str] = {
    # City subreddits
    "mumbai": "MH", "pune": "MH",
    "delhi": "DL", "newdelhi": "DL",
    "bangalore": "KA", "bengaluru": "KA",
    "chennai": "TN",
    "kolkata": "WB",
    "hyderabad": "TS",
    "ahmedabad": "GJ",
    "jaipur": "RJ", "kota": "RJ",
    "lucknow": "UP",
    "chandigarh": "PB",
    "indore": "MP", "bhopal": "MP",
    "patna": "BR",
    "kerala": "KL",
    "goa": "GA",
    # JEE/NEET subreddits — mapped to Kota/Rajasthan as primary hub
    "jeeneetards": "RJ",
    "jeeadvanced": "RJ",
    "jee": "RJ",
    "neet": "RJ",
    # General India subreddits — cannot infer, skip
    "india": "",
    "indiasocial": "",
    "indianteenagers": "",
    "indian_education": "",
    "indianacademia": "",
    "btechtards": "",
    "cbse": "",
}

# PW Vidyapeeth centre locations (extract "Vidyapeeth <city>" from text)
PW_CENTRES: dict[str, str] = {
    "vidyapeeth kota": "RJ",
    "vidyapeeth jaipur": "RJ",
    "vidyapeeth delhi": "DL",
    "vidyapeeth noida": "UP",
    "vidyapeeth lucknow": "UP",
    "vidyapeeth patna": "BR",
    "vidyapeeth bhopal": "MP",
    "vidyapeeth indore": "MP",
    "vidyapeeth pune": "MH",
    "vidyapeeth mumbai": "MH",
    "vidyapeeth bangalore": "KA",
    "vidyapeeth hyderabad": "TS",
    "vidyapeeth chandigarh": "PB",
    "vidyapeeth ranchi": "JH",
    "vidyapeeth kolkata": "WB",
    "vidyapeeth ahmedabad": "GJ",
    "vidyapeeth surat": "GJ",
    "vidyapeeth dehradun": "UK",
}


# =============================================================================
# Inference methods
# =============================================================================

def infer_from_subreddit(subreddit: str) -> tuple[str, float] | None:
    """Infer state from subreddit name. Returns (state_code, confidence)."""
    sub_lower = subreddit.lower().strip()
    code = SUBREDDIT_TO_STATE.get(sub_lower, None)
    if code:
        # City subreddits = high confidence, JEE/NEET subs = lower
        confidence = 0.85 if code not in ("RJ",) else 0.45
        return code, confidence
    return None


def infer_from_text(text: str) -> list[tuple[str, float, str]]:
    """
    Infer state(s) from text content.
    Returns list of (state_code, confidence, matched_keyword).
    """
    if not text:
        return []

    text_lower = text.lower()
    results = []
    seen_codes = set()

    # Method 1: PW centre mentions (highest confidence)
    for phrase, code in PW_CENTRES.items():
        if phrase in text_lower and code not in seen_codes:
            results.append((code, 0.90, phrase))
            seen_codes.add(code)

    # Method 2: City name mentions
    for city, code in CITY_TO_STATE.items():
        if code in seen_codes:
            continue
        # Word boundary match to avoid partial matches ("pune" in "punishment")
        pattern = rf"\b{re.escape(city)}\b"
        if re.search(pattern, text_lower):
            results.append((code, 0.75, city))
            seen_codes.add(code)

    # Method 3: State name mentions (lower confidence — could be discussing, not from there)
    for code, info in STATES.items():
        if code in seen_codes:
            continue
        state_name = info["name"].lower()
        if state_name in text_lower:
            results.append((code, 0.50, info["name"]))
            seen_codes.add(code)

    return results


def infer_from_instagram_location(raw_data: dict) -> tuple[str, float] | None:
    """Infer state from Instagram post location tag if available."""
    location = raw_data.get("location") or {}
    if isinstance(location, dict):
        loc_name = (location.get("name") or "").lower()
        loc_city = (location.get("city") or "").lower()

        # Try city first
        for city, code in CITY_TO_STATE.items():
            if city in loc_city or city in loc_name:
                return code, 0.95

        # Try state name
        for code, info in STATES.items():
            if info["name"].lower() in loc_name:
                return code, 0.90

    return None


# =============================================================================
# Main extraction function
# =============================================================================

def extract_geo_from_mention(mention: dict) -> list[dict[str, Any]]:
    """
    Extract geographic signals from a single mention.
    Returns list of geo records to store.
    """
    platform = mention.get("platform", "")
    content = mention.get("content_text", "")
    raw_data = mention.get("raw_data", {})
    if isinstance(raw_data, str):
        import json
        try:
            raw_data = json.loads(raw_data)
        except Exception:
            raw_data = {}

    results = []

    # Method 1: Reddit subreddit mapping
    if platform == "reddit":
        subreddit = raw_data.get("subreddit", "")
        sub_result = infer_from_subreddit(subreddit)
        if sub_result:
            code, conf = sub_result
            results.append(_build_geo_record(
                mention, code, conf, "subreddit_mapping",
                f"r/{subreddit}"
            ))

    # Method 2: Instagram location tag
    if platform == "instagram":
        ig_result = infer_from_instagram_location(raw_data)
        if ig_result:
            code, conf = ig_result
            results.append(_build_geo_record(
                mention, code, conf, "instagram_location_tag",
                raw_data.get("location", {}).get("name", "")
            ))

    # Method 3: Text keyword extraction (all platforms)
    text_results = infer_from_text(content)
    seen_in_results = {r["state_code"] for r in results}
    for code, conf, keyword in text_results:
        if code not in seen_in_results:
            results.append(_build_geo_record(
                mention, code, conf, "keyword_extraction", keyword
            ))
            seen_in_results.add(code)

    return results


def _build_geo_record(
    mention: dict, state_code: str, confidence: float,
    method: str, source_text: str
) -> dict[str, Any]:
    state_info = STATES.get(state_code, {})
    return {
        "brand_id": mention.get("brand_id"),
        "mention_id": mention.get("id"),
        "platform": mention.get("platform", ""),
        "state": state_info.get("name", state_code),
        "state_code": state_code,
        "lat": state_info.get("lat"),
        "lng": state_info.get("lng"),
        "inference_method": method,
        "confidence": confidence,
        "source_text": source_text[:200] if source_text else "",
        "sentiment_label": mention.get("sentiment_label"),
    }


# =============================================================================
# Batch processing + Supabase storage
# =============================================================================

def process_mentions_geo(brand_id: str, mentions: list[dict] | None = None) -> dict:
    """
    Process mentions for geographic signals and store to Supabase.
    If mentions not provided, fetches from Supabase.
    """
    client = get_service_client()

    if mentions is None:
        mentions = db.get_mentions(brand_id, limit=2000)

    logger.info("Processing %d mentions for geo inference (brand %s)", len(mentions), brand_id)

    all_geo_records = []
    for mention in mentions:
        records = extract_geo_from_mention(mention)
        all_geo_records.extend(records)

    # Store geo_mentions
    stored = 0
    if all_geo_records:
        # Batch insert in chunks of 100
        for i in range(0, len(all_geo_records), 100):
            chunk = all_geo_records[i:i + 100]
            try:
                client.table("geo_mentions").insert(chunk).execute()
                stored += len(chunk)
            except Exception:
                logger.exception("Failed to store geo_mentions batch")

    logger.info("Stored %d geo records for brand %s", stored, brand_id)

    # Rebuild aggregates
    _rebuild_aggregates(brand_id)

    return {
        "brand_id": brand_id,
        "mentions_processed": len(mentions),
        "geo_records_created": stored,
        "unique_states": len({r["state_code"] for r in all_geo_records}),
    }


def _rebuild_aggregates(brand_id: str):
    """Rebuild geo_aggregates from geo_mentions for a brand."""
    client = get_service_client()

    # Fetch all geo_mentions for this brand
    resp = (
        client.table("geo_mentions")
        .select("*")
        .eq("brand_id", brand_id)
        .execute()
    )
    records = resp.data

    if not records:
        return

    # Aggregate by state
    state_data: dict[str, dict] = {}
    for r in records:
        code = r["state_code"]
        if code not in state_data:
            state_data[code] = {
                "brand_id": brand_id,
                "state": r["state"],
                "state_code": code,
                "lat": r.get("lat"),
                "lng": r.get("lng"),
                "total_mentions": 0,
                "negative_mentions": 0,
                "positive_mentions": 0,
                "neutral_mentions": 0,
                "reddit_count": 0,
                "instagram_count": 0,
                "twitter_count": 0,
                "issues": {},
            }

        d = state_data[code]
        d["total_mentions"] += 1

        sentiment = r.get("sentiment_label", "neutral")
        if sentiment == "negative":
            d["negative_mentions"] += 1
        elif sentiment == "positive":
            d["positive_mentions"] += 1
        else:
            d["neutral_mentions"] += 1

        platform = r.get("platform", "")
        if platform == "reddit":
            d["reddit_count"] += 1
        elif platform == "instagram":
            d["instagram_count"] += 1
        elif platform == "twitter":
            d["twitter_count"] += 1

        # Track issues from source_text
        source = r.get("source_text", "")
        if source:
            d["issues"][source] = d["issues"].get(source, 0) + 1

    # Build final aggregates
    aggregates = []
    for code, d in state_data.items():
        total = d["total_mentions"]
        neg = d["negative_mentions"]
        top_issue = ""
        if d["issues"]:
            top_issue = max(d["issues"], key=d["issues"].get)

        aggregates.append({
            "brand_id": brand_id,
            "state": d["state"],
            "state_code": code,
            "lat": d["lat"],
            "lng": d["lng"],
            "total_mentions": total,
            "negative_mentions": neg,
            "positive_mentions": d["positive_mentions"],
            "neutral_mentions": d["neutral_mentions"],
            "negative_pct": round((neg / total * 100) if total > 0 else 0, 1),
            "top_issue": top_issue[:200],
            "reddit_count": d["reddit_count"],
            "instagram_count": d["instagram_count"],
            "twitter_count": d["twitter_count"],
        })

    # Upsert aggregates
    try:
        client.table("geo_aggregates").upsert(
            aggregates, on_conflict="brand_id,state_code"
        ).execute()
        logger.info("Updated %d geo aggregates for brand %s", len(aggregates), brand_id)
    except Exception:
        logger.exception("Failed to update geo_aggregates")


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Run geo inference on mentions")
    parser.add_argument("--brand-id", required=True, help="Brand UUID")
    args = parser.parse_args()

    result = process_mentions_geo(args.brand_id)
    print(f"\nGeo Inference Results:")
    print(f"  Mentions processed: {result['mentions_processed']}")
    print(f"  Geo records created: {result['geo_records_created']}")
    print(f"  Unique states found: {result['unique_states']}")


if __name__ == "__main__":
    main()
