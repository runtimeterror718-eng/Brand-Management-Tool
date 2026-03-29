"""
Slack webhook alerting for critical severity.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from config.settings import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)


async def send_slack_alert(
    brand_name: str,
    crisis_data: dict[str, Any],
) -> bool:
    """Send a crisis alert to Slack via webhook."""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not configured, skipping alert")
        return False

    severity = crisis_data.get("severity_summary", {})
    signals = crisis_data.get("signals", [])

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🚨 Brand Crisis Alert: {brand_name}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(f"• {s}" for s in signals),
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Critical:* {severity.get('critical', 0)}"},
                {"type": "mrkdwn", "text": f"*High:* {severity.get('high', 0)}"},
                {"type": "mrkdwn", "text": f"*Medium:* {severity.get('medium', 0)}"},
                {"type": "mrkdwn", "text": f"*Total:* {severity.get('total', 0)}"},
            ],
        },
    ]

    payload = {"blocks": blocks}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SLACK_WEBHOOK_URL,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("Slack alert sent for %s", brand_name)
            return True
    except Exception:
        logger.exception("Failed to send Slack alert for %s", brand_name)
        return False
