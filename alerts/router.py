"""
Alert routing — routes by severity: critical → Slack, high → email, etc.
"""

from __future__ import annotations

import logging
from typing import Any

from alerts.detector import check_for_crisis
from alerts.slack import send_slack_alert
from alerts.email_report import send_email_report
from severity.rules import get_alert_channel

logger = logging.getLogger(__name__)


async def route_alerts(brand_id: str, brand_name: str) -> dict[str, Any]:
    """
    Check for crisis and route alerts to appropriate channels.

    Routing:
      - critical → Slack (immediate)
      - high → email
      - medium/low → no alert
    """
    crisis = check_for_crisis(brand_id)

    if not crisis["is_crisis"]:
        return {"alerted": False, "reason": "No crisis detected"}

    results = {"alerted": True, "channels": []}

    # Determine worst severity
    severity = crisis["severity_summary"]
    if severity.get("critical", 0) > 0:
        channel = "slack"
    elif severity.get("high", 0) > 0:
        channel = "email"
    else:
        return {"alerted": False, "reason": "Below alert threshold"}

    if channel == "slack":
        success = await send_slack_alert(brand_name, crisis)
        results["channels"].append({"channel": "slack", "success": success})

    if channel in ("slack", "email"):
        # Also send email for critical
        success = send_email_report(brand_name, crisis, subject=f"🚨 Crisis: {brand_name}")
        results["channels"].append({"channel": "email", "success": success})

    results["crisis_data"] = crisis
    return results
