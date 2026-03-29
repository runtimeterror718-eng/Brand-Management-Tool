"""
Severity rules engine — thresholds → critical/high/medium/low.
"""

from __future__ import annotations

from config.constants import SEVERITY_LEVELS


def classify_severity(score: float) -> str:
    """Map a severity score [0, 1] to a level label."""
    if score >= SEVERITY_LEVELS["critical"]:
        return "critical"
    elif score >= SEVERITY_LEVELS["high"]:
        return "high"
    elif score >= SEVERITY_LEVELS["medium"]:
        return "medium"
    return "low"


def should_alert(level: str) -> bool:
    """Return True if severity level warrants an alert."""
    return level in ("critical", "high")


def get_alert_channel(level: str) -> str:
    """Determine alert routing based on severity level."""
    if level == "critical":
        return "slack"
    elif level == "high":
        return "email"
    return "none"
