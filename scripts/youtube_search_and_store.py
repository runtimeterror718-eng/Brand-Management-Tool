"""
Lightweight YouTube search + store.
Searches one keyword at a time, stores results immediately.
Does NOT do the expensive videos_by_id bulk call — stores search snippet data directly.

Usage:
    python scripts/youtube_search_and_store.py
"""

import os, sys, json, time, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

import httpx
from config.supabase_client import get_service_client

# Load all keys
KEYS = []
primary = os.environ.get("YOUTUBE_API_KEY", "")
if primary:
    KEYS.append(primary)
for i in range(1, 10):
    k = os.environ.get(f"YOUTUBE_API_KEY_{i}", "")
    if k and k not in KEYS:
        KEYS.append(k)

print(f"Loaded {len(KEYS)} YouTube API keys")

sb = get_service_client()
BASE = "https://www.googleapis.com/youtube/v3"
exhausted_keys = set()


def get_key():
    for k in KEYS:
        if k not in exhausted_keys:
            return k
    return None


def yt_search(query, max_results=25, published_after_days=90):
    """Search YouTube, rotate keys on 403."""
    from datetime import datetime, timedelta, timezone
    after = (datetime.now(timezone.utc) - timedelta(days=published_after_days)).isoformat()

    for _ in range(len(KEYS) + 1):
        key = get_key()
        if not key:
            return None

        try:
            resp = httpx.get(f"{BASE}/search", params={
                "part": "snippet",
                "type": "video",
                "order": "date",
                "q": query,
                "maxResults": max_results,
                "publishedAfter": after,
                "key": key,
            }, timeout=30)

            if resp.status_code == 403:
                print(f"    Key ...{key[-6:]} exhausted, rotating...")
                exhausted_keys.add(key)
                continue

            resp.raise_for_status()
            return resp.json().get("items", [])
        except httpx.HTTPStatusError:
            exhausted_keys.add(key)
            continue
        except Exception as e:
            print(f"    Error: {e}")
            return []

    return None


def get_brand_id():
    resp = sb.table("brands").select("id").or_("name.eq.PhysicsWallah,name.eq.PW Live Smoke").execute()
    return resp.data[0]["id"] if resp.data else None


def store_video(brand_id, item):
    """Store a search result as youtube_video + mention."""
    snippet = item.get("snippet", {})
    video_id = item.get("id", {}).get("videoId", "")
    if not video_id:
        return False

    channel_id = snippet.get("channelId", "")
    title = snippet.get("title", "")
    description = snippet.get("description", "")
    published = snippet.get("publishedAt", "")
    channel_title = snippet.get("channelTitle", "")

    # Upsert youtube_video (basic data from search snippet)
    video_row = {
        "brand_id": brand_id,
        "channel_id": channel_id,
        "video_id": video_id,
        "video_title": title,
        "video_description": description[:2000] if description else "",
        "video_date": published,
        "video_views": 0,  # not available from search
        "video_likes": 0,
        "video_comment_count": 0,
        "video_duration": 0,
        "media_type": "video",
        "source_url": f"https://www.youtube.com/watch?v={video_id}",
        "scraped_at": "now()",
    }

    try:
        sb.table("youtube_videos").upsert(video_row, on_conflict="video_id").execute()
    except Exception as e:
        # Might fail on unique constraint — that's fine, video exists
        pass

    # Upsert youtube_channel (basic)
    channel_row = {
        "brand_id": brand_id,
        "channel_id": channel_id,
        "channel_name": channel_title,
        "channel_subscribers": 0,
        "channel_owner": "Not Owned",
        "scraped_at": "now()",
    }
    try:
        sb.table("youtube_channels").upsert(channel_row, on_conflict="channel_id").execute()
    except Exception:
        pass

    return True


# Import keywords
from scrapers.youtube import PRIMARY_PW_QUERY_TERMS, SECONDARY_PW_QUERY_TERMS

# Official channel IDs to skip
from config.constants import YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL

KEYWORDS = list(PRIMARY_PW_QUERY_TERMS) + list(SECONDARY_PW_QUERY_TERMS)

if __name__ == "__main__":
    brand_id = get_brand_id()
    if not brand_id:
        print("No brand found!")
        sys.exit(1)

    print(f"Brand: {brand_id}")
    print(f"Keywords: {len(KEYWORDS)}")
    print(f"Keys: {len(KEYS)}")
    print()

    total_videos = 0
    total_stored = 0
    total_skipped_official = 0
    seen_video_ids = set()

    for i, kw in enumerate(KEYWORDS):
        key = get_key()
        if not key:
            print(f"\n  All keys exhausted after {i}/{len(KEYWORDS)} keywords")
            break

        print(f"[{i+1}/{len(KEYWORDS)}] Searching: '{kw}' (key ...{key[-6:]})")

        items = yt_search(kw, max_results=25, published_after_days=90)
        if items is None:
            print(f"  All keys exhausted!")
            break
        if not items:
            print(f"  No results")
            continue

        stored_this = 0
        for item in items:
            vid = item.get("id", {}).get("videoId", "")
            channel_id = item.get("snippet", {}).get("channelId", "")

            if not vid or vid in seen_video_ids:
                continue
            seen_video_ids.add(vid)

            # Skip official PW channels
            if channel_id in YOUTUBE_OFFICIAL_CHANNEL_IDS_ALL:
                total_skipped_official += 1
                continue

            if store_video(brand_id, item):
                stored_this += 1
                total_stored += 1

        total_videos += len(items)
        print(f"  Found: {len(items)} | New stored: {stored_this} | Total unique: {len(seen_video_ids)}")

        time.sleep(0.2)  # courtesy delay

    print(f"\n{'='*60}")
    print(f"DONE")
    print(f"  Keywords searched: {i+1}/{len(KEYWORDS)}")
    print(f"  Total search results: {total_videos}")
    print(f"  Unique videos found: {len(seen_video_ids)}")
    print(f"  Stored to Supabase: {total_stored}")
    print(f"  Skipped (official PW): {total_skipped_official}")
    print(f"{'='*60}")
