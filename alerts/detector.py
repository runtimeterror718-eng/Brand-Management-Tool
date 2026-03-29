"""
Crisis detection based on severity index.
"""

from __future__ import annotations

import logging
from typing import Any

from severity.index import aggregate_severity, get_critical_mentions
from brand.trends import detect_velocity_spike

logger = logging.getLogger(__name__)


def check_for_crisis(brand_id: str) -> dict[str, Any]:
    """
    Check if a brand is currently experiencing a crisis.

    Triggers on:
      - Multiple critical severity mentions
      - Velocity spike above threshold
      - Sudden sentiment drop
    """
    severity_agg = aggregate_severity(brand_id)
    spike = detect_velocity_spike(brand_id)

    is_crisis = False
    signals = []

    # Signal 1: Multiple critical mentions
    if severity_agg.get("critical", 0) >= 3:
        is_crisis = True
        signals.append(f"{severity_agg['critical']} critical mentions detected")

    # Signal 2: Velocity spike
    if spike:
        is_crisis = True
        signals.append(
            f"Velocity spike: {spike['ratio']}x above baseline"
        )

    # Signal 3: High volume of high-severity mentions
    high_count = severity_agg.get("high", 0) + severity_agg.get("critical", 0)
    total = severity_agg.get("total", 1)
    if total > 10 and high_count / total > 0.3:
        is_crisis = True
        signals.append(
            f"{high_count}/{total} mentions are high/critical severity"
        )

    critical_mentions = get_critical_mentions(brand_id, limit=10) if is_crisis else []

    return {
        "is_crisis": is_crisis,
        "signals": signals,
        "severity_summary": severity_agg,
        "velocity_spike": spike,
        "critical_mentions": critical_mentions,
    }
