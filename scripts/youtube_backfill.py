"""
YouTube 3-Month Backfill using Team B's full pipeline.

Key optimization: Instead of 250+ individual search queries (25K units),
we pass pre-grouped OR queries (15 queries, ~2K units) via query_buckets_override.
Team B's pipeline handles everything else: triage, transcripts, comments, sentiment, storage.

Usage:
    python scripts/youtube_backfill.py
"""

import os, sys, asyncio, json, logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("youtube_backfill")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"), override=True)

# ---------------------------------------------------------------------------
# Grouped queries — each string becomes ONE YouTube search API call.
# Uses YouTube's implicit OR when terms are space-separated.
# Quoted phrases for exact match.
# ---------------------------------------------------------------------------
GROUPED_QUERIES = {
    "primary": [
        # Group 1: Core brand (broadest — fetch 3 pages)
        '"physics wallah" | "physicswallah" | "alakh pandey" | "alakh sir"',
        '"pw live" | "pw app" | "pw.live" | "physics wala"',
        # Group 2: Batches
        '"arjuna batch" | "lakshya batch" | "yakeen batch" | "prayas batch" | "udaan batch"',
        '"neev batch" | "sankalp batch" | "umeed batch" | "pw droppers batch"',
        # Group 3: Wallah verticals
        '"jee wallah" | "neet wallah" | "gate wallah" | "banking wallah" | "upsc wallah"',
        '"competition wallah" | "ncert wallah" | "college wallah" | "mba wallah"',
        # Group 4: Vidyapeeth
        '"pw vidyapeeth" | "vidyapeeth" physics wallah | "pw offline" coaching',
        # Group 5: Products
        '"pw skills" | "pwskills" | "pw ioi" | "pw institute of innovation"',
        '"pw meded" | "pw neet pg" | "pw cuet" | "pw ugc net"',
        # Group 6: Negative PR
        '"pw scam" | "pw fraud" | "pw refund" | "physics wallah scam"',
        '"pw exposed" | "pw controversy" | "physics wallah complaint" | "pw consumer court"',
        # Group 7: IPO / Business
        '"physics wallah ipo" | "pw ipo" | "pw stock" | "pw valuation" | "alakh pandey billionaire"',
        # Group 8: Employer
        '"sell pen" physics wallah | "pw interview" | "pw glassdoor" | "pw layoffs" | "pw salary"',
        # Group 9: Competitors
        '"physics wallah vs allen" | "pw vs unacademy" | "pw vs byju"',
        '"pw vs vedantu" | "pw vs aakash" | "best coaching jee neet 2026"',
        # Group 10: Kashmir / Caste / Political
        '"pw kashmir" | "pw fir" | "casteist" physics wallah | "rishi jain pw"',
        # Group 11: App reviews
        '"pw app" crash | "pw app" review | "physics wallah app" | "pw app not working"',
    ],
    "secondary": [
        # Teachers
        '"rajwant sir" physics wallah | "saleem sir" pw | "mr sir" pw',
        '"nidhi mam" pw | "anushka mam" pw | "amit mahajan" pw | "sachin sir" pw',
        '"ritik sir" pw | "pankaj sir" pw | "om sir" pw | "tarun sir" pw',
        # Ex-PW / criticism
        '"left pw" | "quit pw" | "ex pw teacher" | "pw teachers leaving"',
        '"sankalp bharat" pw | "udaan companions" reality | "pw teacher controversy"',
        # Motivation / Fan content
        '"alakh sir motivation" | "pw motivation" | "pwians" | "#physicswallah"',
        # Misspellings
        '"physics walla" | "phisics wallah" | "fisics wallah" | "alakh pande"',
    ],
}


async def run_backfill():
    from config.supabase_client import get_service_client
    from scrapers.youtube import run_unofficial_youtube_pipeline_for_brand
    from config.settings import YOUTUBE_API_KEY, AZURE_OPENAI_API_KEY, OPENAI_API_KEY

    sb = get_service_client()

    # Get brand
    resp = sb.table("brands").select("*").or_("name.eq.PhysicsWallah,name.eq.PW Live Smoke").execute()
    brands = resp.data or []
    if not brands:
        logger.error("No PW brand found")
        return
    brand = brands[0]
    logger.info(f"Brand: {brand['name']} ({brand['id']})")

    # Count queries
    total_queries = sum(len(v) for v in GROUPED_QUERIES.values())
    logger.info(f"Grouped queries: {total_queries} (vs 250+ individual)")
    logger.info(f"Estimated search quota: ~{total_queries * 100} units")

    if not YOUTUBE_API_KEY:
        logger.error("YOUTUBE_API_KEY not set!")
        return
    logger.info(f"YouTube API key: ...{YOUTUBE_API_KEY[-8:]}")
    logger.info(f"LLM: {'Azure OpenAI' if AZURE_OPENAI_API_KEY else 'OpenAI GPT-4o-mini' if OPENAI_API_KEY else 'NONE'}")

    logger.info("=" * 60)
    logger.info("Starting YouTube backfill with Team B's full pipeline...")
    logger.info(f"  Query groups: {total_queries}")
    logger.info(f"  Published after: 90 days")
    logger.info(f"  Max comments per video: 10,000")
    logger.info(f"  Pipeline: discover → triage → transcripts → comments → sentiment → store")
    logger.info("=" * 60)

    try:
        summary = await run_unofficial_youtube_pipeline_for_brand(
            brand=brand,
            include_secondary=True,
            query_buckets_override=GROUPED_QUERIES,
            published_after_days_override=90,
            max_results_per_keyword_override=25,
        )
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        return

    logger.info("=" * 60)
    logger.info("BACKFILL COMPLETE")
    logger.info("=" * 60)

    # Pretty print results
    discovered = summary.get("discovered", summary.get("discovered_video_count", 0))
    flagged = summary.get("flagged", 0)
    enriched = summary.get("enriched", 0)
    comments = summary.get("comments_fetched_total", 0)
    mentions_c = summary.get("mentions_created", 0)
    mentions_u = summary.get("mentions_updated", 0)
    videos_c = summary.get("raw_videos_created", 0)
    videos_u = summary.get("raw_videos_updated", 0)
    channels_c = summary.get("raw_channels_created", 0)

    logger.info(f"  Videos discovered: {discovered}")
    logger.info(f"  Videos stored: {videos_c} new, {videos_u} updated")
    logger.info(f"  Channels stored: {channels_c}")
    logger.info(f"  PR risks flagged: {flagged}")
    logger.info(f"  Videos enriched (transcripts+comments+analysis): {enriched}")
    logger.info(f"  Comments fetched: {comments}")
    logger.info(f"  Mentions: {mentions_c} created, {mentions_u} updated")
    logger.info(f"  Transcript successes: {summary.get('transcript_success_count', 0)}")
    logger.info(f"  Final analyses saved: {summary.get('final_analysis_saved_count', 0)}")

    logger.info(f"\nFull summary:\n{json.dumps(summary, indent=2, default=str)}")


if __name__ == "__main__":
    print("YouTube Backfill — Team B's Full Pipeline + Smart Grouped Queries")
    total = sum(len(v) for v in GROUPED_QUERIES.values())
    print(f"  {total} grouped queries → ~{total * 100} units (vs 25,000+ old approach)")
    print(f"  Pipeline: discover → title triage → transcripts → comments → sentiment → final synthesis")
    print()
    asyncio.run(run_backfill())
