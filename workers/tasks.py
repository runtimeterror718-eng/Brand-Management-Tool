"""
Celery task wrappers — the glue between workers and business logic.
"""

from __future__ import annotations

import asyncio
import logging

from workers.celery_app import app
from brand.monitor import get_monitored_brands
from storage import queries as db

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code from sync Celery tasks."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def scrape_platform(self, platform: str):
    """Scrape a specific platform for all monitored brands."""
    from search.engine import search_and_fulfill
    from search.filters import SearchParams

    brands = get_monitored_brands()
    for brand in brands:
        try:
            params = {
                "keywords": brand.get("keywords", []),
                "hashtags": brand.get("hashtags", []),
                "platforms": [platform],
                "brand_id": brand["id"],
            }
            results = _run_async(search_and_fulfill(params))
            logger.info(
                "Scraped %s for brand %s: %d results passed fulfillment",
                platform, brand["name"], len(results),
            )
        except Exception as exc:
            logger.exception("Scrape failed: %s / %s", platform, brand["name"])
            raise self.retry(exc=exc)


@app.task(bind=True, max_retries=2)
def run_full_analysis(self):
    """Run the full 3-tier analysis pipeline for all monitored brands."""
    from analysis.pipeline import run_analysis
    from severity.index import score_mentions
    from datetime import datetime, timedelta

    brands = get_monitored_brands()
    since = datetime.utcnow() - timedelta(days=1)

    for brand in brands:
        try:
            mentions = db.get_mentions(brand["id"], since=since)
            if not mentions:
                continue

            # Run analysis
            report = _run_async(run_analysis(
                brand["id"], brand["name"], mentions
            ))

            # Score severity
            score_mentions(mentions, brand)

            logger.info(
                "Analysis complete for %s: %d mentions, %d clusters",
                brand["name"],
                report.get("mention_count", 0),
                report.get("cluster_count", 0),
            )
        except Exception as exc:
            logger.exception("Analysis failed for %s", brand["name"])
            raise self.retry(exc=exc)


@app.task
def check_alerts():
    """Check all brands for crisis alerts."""
    from alerts.router import route_alerts

    brands = get_monitored_brands()
    for brand in brands:
        try:
            result = _run_async(route_alerts(brand["id"], brand["name"]))
            if result.get("alerted"):
                logger.warning("Alert sent for %s: %s", brand["name"], result)
        except Exception:
            logger.exception("Alert check failed for %s", brand["name"])


@app.task
def send_weekly_report():
    """Send weekly email summary for all brands."""
    from alerts.email_report import send_email_report
    from brand.health import compute_health_score
    from severity.index import aggregate_severity

    brands = get_monitored_brands()
    for brand in brands:
        try:
            health = compute_health_score(brand["id"])
            severity = aggregate_severity(brand["id"])
            latest = db.get_latest_analysis(brand["id"])

            report = {
                "health": health,
                "severity_summary": severity,
                "themes": latest.get("themes", []) if latest else [],
                "risks": latest.get("risks", []) if latest else [],
            }
            send_email_report(brand["name"], report)
        except Exception:
            logger.exception("Weekly report failed for %s", brand["name"])
