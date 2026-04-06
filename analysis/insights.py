"""
Tier 3: LLM → structured brand report JSON.
Supports OpenAI (primary) and Anthropic (fallback).
~$0.02–$0.08 per analysis run.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from config.settings import (
    OPENAI_API_KEY, OPENAI_MODEL,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
)
from config.constants import LLM_MAX_TOKENS, LLM_TEMPERATURE

logger = logging.getLogger(__name__)


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


def _build_user_prompt(
    brand_name: str,
    cluster_summaries: list[dict],
    sentiment_stats: dict,
    mention_count: int,
    platform_breakdown: dict[str, int],
) -> str:
    return f"""Analyze brand intelligence for **{brand_name}**.

**Stats:**
- Total mentions analyzed: {mention_count}
- Platform breakdown: {json.dumps(platform_breakdown)}
- Overall sentiment: avg={sentiment_stats.get('avg', 0):.2f}, positive={sentiment_stats.get('positive_pct', 0):.0f}%, negative={sentiment_stats.get('negative_pct', 0):.0f}%

**Cluster Summaries:**
{json.dumps(cluster_summaries, indent=2, default=str)}

Produce the structured JSON report."""


def _call_openai(user_prompt: str) -> dict[str, Any]:
    """Call OpenAI API for insights."""
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        temperature=LLM_TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    text = response.choices[0].message.content or ""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        report = json.loads(text[start:end])
    else:
        report = {"error": "No JSON found in response", "raw": text}

    usage = response.usage
    if usage:
        cost = (usage.prompt_tokens / 1_000_000 * 0.15) + (usage.completion_tokens / 1_000_000 * 0.60)
        report["_llm_cost_usd"] = round(cost, 4)
        report["_tokens"] = {"input": usage.prompt_tokens, "output": usage.completion_tokens}
    report["_provider"] = "openai"

    return report


def _call_anthropic(user_prompt: str) -> dict[str, Any]:
    """Call Anthropic API for insights (fallback)."""
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=LLM_MAX_TOKENS,
        temperature=LLM_TEMPERATURE,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        report = json.loads(text[start:end])
    else:
        report = {"error": "No JSON found in response", "raw": text}

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)
    report["_llm_cost_usd"] = round(cost, 4)
    report["_tokens"] = {"input": input_tokens, "output": output_tokens}
    report["_provider"] = "anthropic"

    return report


def generate_insights(
    brand_name: str,
    cluster_summaries: list[dict],
    sentiment_stats: dict,
    mention_count: int,
    platform_breakdown: dict[str, int],
) -> dict[str, Any]:
    """
    Send clustered data to LLM for structured analysis.
    Tries OpenAI first, falls back to Anthropic.
    """
    user_prompt = _build_user_prompt(
        brand_name, cluster_summaries, sentiment_stats,
        mention_count, platform_breakdown,
    )

    # Try OpenAI first
    if OPENAI_API_KEY:
        try:
            report = _call_openai(user_prompt)
            logger.info("Insights generated via OpenAI (%s)", OPENAI_MODEL)
            return report
        except Exception:
            logger.exception("OpenAI insight generation failed, trying Anthropic...")

    # Fallback to Anthropic
    if ANTHROPIC_API_KEY:
        try:
            report = _call_anthropic(user_prompt)
            logger.info("Insights generated via Anthropic (%s)", ANTHROPIC_MODEL)
            return report
        except Exception:
            logger.exception("Anthropic insight generation failed")

    return {"error": "No LLM provider available", "themes": [], "risks": [], "opportunities": []}
