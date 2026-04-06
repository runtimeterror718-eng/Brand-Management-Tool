"""
YouTube Smart Backfill — Grouped keyword search to minimize API quota.

Instead of 250 separate search calls (25K units), groups keywords into
~15 combined queries using YouTube's OR search (1.5K units total).

Usage:
    python scripts/youtube_smart_backfill.py
"""

import os, sys, json, time, hashlib
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

import httpx
from config.supabase_client import get_service_client
from config.constants import YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL

sb = get_service_client()
BASE = "https://www.googleapis.com/youtube/v3"

# ── Load API keys ──────────────────────────────────────────────
KEYS = []
primary = os.environ.get("YOUTUBE_API_KEY", "")
if primary:
    KEYS.append(primary)
for i in range(1, 10):
    k = os.environ.get(f"YOUTUBE_API_KEY_{i}", "")
    if k and k not in KEYS:
        KEYS.append(k)

exhausted = set()


def get_key():
    for k in KEYS:
        if k not in exhausted:
            return k
    return None


def api_get(endpoint, params):
    """GET with key rotation."""
    for _ in range(len(KEYS) + 1):
        key = get_key()
        if not key:
            return None
        params["key"] = key
        try:
            resp = httpx.get(f"{BASE}{endpoint}", params=params, timeout=30)
            if resp.status_code == 403:
                print(f"      Key ...{key[-6:]} exhausted, rotating...")
                exhausted.add(key)
                continue
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError:
            exhausted.add(key)
            continue
    return None


# ── Smart query groups ─────────────────────────────────────────
# Each group becomes ONE API call. YouTube search handles | as OR.
QUERY_GROUPS = [
    {
        "name": "Brand Core",
        "query": '"physics wallah" | "physicswallah" | "alakh pandey" | "alakh sir" | "pw live"',
        "pages": 3,  # fetch up to 75 results for core brand
    },
    {
        "name": "Batches JEE/NEET",
        "query": '"arjuna batch" | "lakshya batch" | "yakeen batch" | "prayas batch" | "udaan batch" | "neev batch"',
        "pages": 2,
    },
    {
        "name": "Negative PR",
        "query": '"pw scam" | "pw fraud" | "pw refund" | "physics wallah scam" | "pw exposed" | "pw controversy"',
        "pages": 2,
    },
    {
        "name": "Teacher Content",
        "query": '"rajwant sir" physics wallah | "saleem sir" pw | "mr sir" pw | "nidhi mam" pw | "anushka mam" pw',
        "pages": 2,
    },
    {
        "name": "Competitors",
        "query": '"physics wallah vs allen" | "pw vs unacademy" | "pw vs byju" | "pw vs vedantu" | "pw vs aakash"',
        "pages": 2,
    },
    {
        "name": "PW Skills / IOI",
        "query": '"pw skills" review | "pw skills" scam | "pw ioi" | "pw institute of innovation" | "pwskills"',
        "pages": 2,
    },
    {
        "name": "IPO / Business",
        "query": '"physics wallah ipo" | "pw ipo" | "pw stock" | "alakh pandey billionaire" | "pw valuation"',
        "pages": 1,
    },
    {
        "name": "Employer Brand",
        "query": '"physics wallah interview" | "sell pen" pw | "pw glassdoor" | "pw salary" | "pw layoffs"',
        "pages": 1,
    },
    {
        "name": "App / Product Reviews",
        "query": '"pw app" review | "pw app" crash | "physics wallah app" | "pw modules" review | "pw books"',
        "pages": 1,
    },
    {
        "name": "Vidyapeeth Offline",
        "query": '"pw vidyapeeth" | "vidyapeeth" physics wallah | "pw offline" coaching | "pw pathshala"',
        "pages": 1,
    },
    {
        "name": "Wallah Brands",
        "query": '"jee wallah" | "neet wallah" | "gate wallah" | "banking wallah" | "upsc wallah" | "competition wallah"',
        "pages": 1,
    },
    {
        "name": "Teacher Exodus",
        "query": '"left pw" | "quit pw" | "resigned pw" | "ex pw teacher" | "pw teachers leaving"',
        "pages": 1,
    },
    {
        "name": "Kashmir / Caste",
        "query": '"pw kashmir" | "pw fir" | "casteist" pw | "chor chamar" pw',
        "pages": 1,
    },
    {
        "name": "Medical / Other Exams",
        "query": '"pw meded" | "pw neet pg" | "pw ugc net" | "pw cuet" | "pw olympiad" | "pw ca"',
        "pages": 1,
    },
    {
        "name": "Motivation / Fan Content",
        "query": '"alakh sir motivation" | "pw motivation" | "pwians" | "#physicswallah" shorts',
        "pages": 2,
    },
]


def get_brand_id():
    resp = sb.table("brands").select("id").or_("name.eq.PhysicsWallah,name.eq.PW Live Smoke").execute()
    return resp.data[0]["id"] if resp.data else None


def search_group(query, max_results=25, published_after_days=90, pages=1):
    """Search with pagination."""
    after = (datetime.now(timezone.utc) - timedelta(days=published_after_days)).isoformat()
    all_items = []
    page_token = ""

    for page in range(pages):
        params = {
            "part": "snippet",
            "type": "video",
            "order": "relevance",
            "q": query,
            "maxResults": max_results,
            "publishedAfter": after,
        }
        if page_token:
            params["pageToken"] = page_token

        data = api_get("/search", params)
        if not data:
            break

        items = data.get("items", [])
        all_items.extend(items)
        page_token = data.get("nextPageToken", "")
        if not page_token:
            break

    return all_items


def fetch_video_details(video_ids):
    """Batch fetch video details (50 per call, 1 unit per video)."""
    all_details = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        data = api_get("/videos", {
            "part": "snippet,contentDetails,statistics",
            "id": ",".join(batch),
            "maxResults": 50,
        })
        if not data:
            break
        for item in data.get("items", []):
            all_details[item["id"]] = item
    return all_details


def parse_duration(duration_str):
    """Parse PT1H23M45S → seconds."""
    if not duration_str:
        return 0
    import re
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    h, m, s = (int(x) if x else 0 for x in match.groups())
    return h * 3600 + m * 60 + s


def store_results(brand_id, video_details, search_items_by_vid):
    """Store videos, channels, and mentions to Supabase."""
    stored_videos = 0
    stored_channels = 0
    seen_channels = set()

    for vid, details in video_details.items():
        snippet = details.get("snippet", {})
        stats = details.get("statistics", {})
        content = details.get("contentDetails", {})
        channel_id = snippet.get("channelId", "")

        # Skip official PW channels
        if channel_id in YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL:
            continue

        # Upsert video
        try:
            sb.table("youtube_videos").upsert({
                "brand_id": brand_id,
                "channel_id": channel_id,
                "video_id": vid,
                "video_title": snippet.get("title", ""),
                "video_description": (snippet.get("description", "") or "")[:2000],
                "video_date": snippet.get("publishedAt", ""),
                "video_views": int(stats.get("viewCount", 0)),
                "video_likes": int(stats.get("likeCount", 0)),
                "video_comment_count": int(stats.get("commentCount", 0)),
                "video_duration": parse_duration(content.get("duration", "")),
                "media_type": "video",
                "source_url": f"https://www.youtube.com/watch?v={vid}",
            }, on_conflict="video_id").execute()
            stored_videos += 1
        except Exception as e:
            print(f"      Video store error: {e}")

        # Upsert channel
        if channel_id and channel_id not in seen_channels:
            seen_channels.add(channel_id)
            try:
                sb.table("youtube_channels").upsert({
                    "brand_id": brand_id,
                    "channel_id": channel_id,
                    "channel_name": snippet.get("channelTitle", ""),
                    "channel_subscribers": 0,
                    "channel_owner": "Not Owned",
                }, on_conflict="channel_id").execute()
                stored_channels += 1
            except Exception:
                pass

    return stored_videos, stored_channels


# ── Main ───────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("YouTube Smart Backfill")
    print(f"  {len(QUERY_GROUPS)} query groups (vs 250+ individual keywords)")
    print(f"  {len(KEYS)} API keys loaded")
    total_pages = sum(g["pages"] for g in QUERY_GROUPS)
    print(f"  Estimated API calls: {total_pages} search + ~10 video detail = ~{total_pages + 10}")
    print(f"  Estimated quota: ~{(total_pages + 10) * 100} units (vs 25,000+ old approach)")
    print("=" * 60)

    brand_id = get_brand_id()
    if not brand_id:
        print("No brand found!")
        sys.exit(1)
    print(f"\nBrand: {brand_id}")

    # Phase 1: Search all groups
    all_video_ids = set()
    search_items = {}  # vid → search snippet

    for i, group in enumerate(QUERY_GROUPS):
        key = get_key()
        if not key:
            print(f"\n  All keys exhausted after group {i}/{len(QUERY_GROUPS)}")
            break

        print(f"\n[{i+1}/{len(QUERY_GROUPS)}] {group['name']} (key ...{key[-6:]})")
        print(f"  Query: {group['query'][:80]}...")

        items = search_group(group["query"], max_results=25, published_after_days=90, pages=group["pages"])
        if items is None:
            print("  All keys exhausted!")
            break

        new_count = 0
        for item in items:
            vid = item.get("id", {}).get("videoId", "")
            cid = item.get("snippet", {}).get("channelId", "")
            if vid and vid not in all_video_ids and cid not in YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL:
                all_video_ids.add(vid)
                search_items[vid] = item
                new_count += 1

        print(f"  Results: {len(items)} | New unique: {new_count} | Total unique: {len(all_video_ids)}")
        time.sleep(0.3)

    print(f"\n{'='*60}")
    print(f"Phase 1 Complete: {len(all_video_ids)} unique videos discovered")
    print(f"{'='*60}")

    if not all_video_ids:
        print("No videos found!")
        sys.exit(0)

    # Phase 2: Fetch video details (cheap — 1 unit per video)
    print(f"\nPhase 2: Fetching details for {len(all_video_ids)} videos...")
    details = fetch_video_details(list(all_video_ids))
    print(f"  Got details for {len(details)} videos")

    if not details:
        # Fallback: store from search snippets
        print("  No details fetched (quota?). Storing from search snippets...")
        for vid, item in search_items.items():
            snippet = item.get("snippet", {})
            try:
                sb.table("youtube_videos").upsert({
                    "brand_id": brand_id,
                    "channel_id": snippet.get("channelId", ""),
                    "video_id": vid,
                    "video_title": snippet.get("title", ""),
                    "video_description": (snippet.get("description", "") or "")[:2000],
                    "video_date": snippet.get("publishedAt", ""),
                    "video_views": 0,
                    "video_likes": 0,
                    "video_comment_count": 0,
                    "video_duration": 0,
                    "media_type": "video",
                    "source_url": f"https://www.youtube.com/watch?v={vid}",
                }, on_conflict="video_id").execute()
            except Exception:
                pass
        print(f"  Stored {len(search_items)} videos from search snippets")
    else:
        # Phase 3: Store everything
        print(f"\nPhase 3: Storing to Supabase...")
        v_count, c_count = store_results(brand_id, details, search_items)
        print(f"  Videos stored: {v_count}")
        print(f"  Channels stored: {c_count}")

    # Verify
    resp = sb.table("youtube_videos").select("video_id").eq("brand_id", brand_id).execute()
    total_in_db = len(resp.data or [])
    print(f"\nTotal videos in Supabase: {total_in_db}")
    print(f"API calls made: ~{total_pages + len(all_video_ids)//50 + 1}")
    print(f"Estimated quota used: ~{(total_pages + len(all_video_ids)//50 + 1) * 100} units")
    print("\nDone!")
