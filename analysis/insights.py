"""
Tier 3: Claude API → structured brand report JSON.
~$0.08 per analysis run.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from config.settings import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from config.constants import LLM_MAX_TOKENS, LLM_TEMPERATURE

logger = logging.getLogger(__name__)


def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


SYSTEM_PROMPT = """You are a brand intelligence analyst. Given clustered mention data with sentiment scores, produce a structured JSON report.

Your output must be valid JSON with exactly these keys:
{
  "themes": [{"name": str, "description": str, "mention_count": int, "avg_sentiment": float}],
  "risks": [{"title": str, "description": str, "severity": "critical"|"high"|"medium"|"low", "evidence": [str]}],
  "opportunities": [{"title": str, "description": str, "potential_impact": str, "evidence": [str]}],
  "severity_overview": {"critical": int, "high": int, "medium": int, "low": int},
  "executive_summary": str
}

Be specific, data-driven, and actionable. Reference actual mention content as evidence."""


def generate_insights(
    brand_name: str,
    cluster_summaries: list[dict],
    sentiment_stats: dict,
    mention_count: int,
    platform_breakdown: dict[str, int],
) -> dict[str, Any]:
    """
    Send clustered data to Claude for structured analysis.

    Returns the parsed JSON report.
    """
    client = _get_client()

    user_prompt = f"""Analyze brand intelligence for **{brand_name}**.

**Stats:**
- Total mentions analyzed: {mention_count}
- Platform breakdown: {json.dumps(platform_breakdown)}
- Overall sentiment: avg={sentiment_stats.get('avg', 0):.2f}, positive={sentiment_stats.get('positive_pct', 0):.0f}%, negative={sentiment_stats.get('negative_pct', 0):.0f}%

**Cluster Summaries:**
{json.dumps(cluster_summaries, indent=2, default=str)}

Produce the structured JSON report."""

    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = response.content[0].text

        # Extract JSON from response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            report = json.loads(text[start:end])
        else:
            report = {"error": "No JSON found in response", "raw": text}

        # Calculate cost
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (
            input_tokens * LLM_TEMPERATURE / 1000 * 0.003
            + output_tokens / 1000 * 0.015
        )
        report["_llm_cost_usd"] = round(cost, 4)
        report["_tokens"] = {"input": input_tokens, "output": output_tokens}

        return report

    except Exception:
        logger.exception("Claude insight generation failed")
        return {"error": "LLM call failed", "themes": [], "risks": [], "opportunities": []}
