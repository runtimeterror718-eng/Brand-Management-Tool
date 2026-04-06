"""
Stage 2: LLM Pre-Enrichment — batch classify each mention with intent, emotion, urgency, etc.
Uses Haiku for cost efficiency (~$0.02 per 40 mentions).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from analysis.deep_clustering.ingest import NormalizedMention
from config.settings import OPENAI_API_KEY, OPENAI_MODEL, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

BATCH_PROMPT = """You are analyzing social media mentions about the brand "Physics Wallah" (PW), an Indian edtech company.

For each mention below, extract structured metadata. Return a JSON array with one object per mention, in the same order.

Mentions:
{mentions_block}

For each mention, return:
{{
  "index": <mention number>,
  "intent": "complaint | praise | question | comparison | suggestion | experience_sharing | news_reaction | humor_sarcasm",
  "emotion": "anger | frustration | disappointment | satisfaction | excitement | confusion | indifference | sarcasm | trust | fear",
  "specificity": "general_brand | specific_product | specific_person | specific_event | specific_feature",
  "product_mentioned": "product name or null",
  "person_mentioned": "person name or null",
  "competitor_mentioned": "competitor name or null",
  "complaint_category": "null or: pricing | quality | support | app_bug | content | faculty | refund | access_blocked | misleading_claims",
  "user_segment": "current_student | prospective_student | parent | ex_student | competitor_employee | general_public | educator | investor",
  "urgency": "low | medium | high | crisis",
  "is_actionable": true or false,
  "action_type": "null or: needs_response | needs_fix | needs_investigation | needs_escalation | monitor_only"
}}

Return ONLY the JSON array. No other text."""

DEFAULT_ENRICHMENT = {
    "intent": "unknown", "emotion": "indifference", "specificity": "general_brand",
    "product_mentioned": None, "person_mentioned": None, "competitor_mentioned": None,
    "complaint_category": None, "user_segment": "general_public", "urgency": "low",
    "is_actionable": False, "action_type": None,
}


def enrich_mentions(
    mentions: list[NormalizedMention],
    batch_size: int = 30,
) -> list[dict[str, Any]]:
    """
    Batch-enrich mentions with LLM metadata.
    Tries OpenAI first (gpt-4o-mini), falls back to Anthropic Haiku.
    """
    all_enrichments: list[dict | None] = [None] * len(mentions)
    total_batches = (len(mentions) + batch_size - 1) // batch_size

    for batch_idx in range(total_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(mentions))
        batch = mentions[start:end]

        mentions_block = ""
        for i, m in enumerate(batch):
            mentions_block += f"\n[{i + 1}] Platform: {m.platform} | Context: {m.source_context}\n"
            mentions_block += f'    "{m.content[:250]}"\n'

        prompt = BATCH_PROMPT.format(mentions_block=mentions_block)

        logger.info("Enriching batch %d/%d (%d mentions)...", batch_idx + 1, total_batches, len(batch))

        enrichments = _call_llm(prompt, len(batch))

        for e in enrichments:
            idx = e.get("index", 0) - 1
            if 0 <= idx < len(batch):
                all_enrichments[start + idx] = e

    # Fill gaps with defaults
    result = []
    for i, e in enumerate(all_enrichments):
        if e is None:
            e = dict(DEFAULT_ENRICHMENT)
        e["index"] = i
        result.append(e)

    logger.info("Enrichment complete: %d mentions", len(result))
    return result


def _call_llm(prompt: str, expected_count: int) -> list[dict]:
    """Call LLM for batch enrichment. Returns list of enrichment dicts."""

    # Try OpenAI first (gpt-4o-mini is fast + cheap)
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=4000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.choices[0].message.content or "[]"
            return _parse_json_array(text, expected_count)
        except Exception as e:
            logger.warning("OpenAI enrichment failed: %s", e)

    # Fallback to Anthropic
    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text
            return _parse_json_array(text, expected_count)
        except Exception as e:
            logger.warning("Anthropic enrichment failed: %s", e)

    # No LLM available — return defaults
    logger.warning("No LLM available for enrichment, using defaults")
    return [dict(DEFAULT_ENRICHMENT, index=i + 1) for i in range(expected_count)]


def _parse_json_array(text: str, expected: int) -> list[dict]:
    """Parse JSON array from LLM response, handling common issues."""
    # Find JSON array in response
    start = text.find("[")
    end = text.rfind("]") + 1
    if start < 0 or end <= start:
        return [dict(DEFAULT_ENRICHMENT, index=i + 1) for i in range(expected)]

    try:
        arr = json.loads(text[start:end])
        if isinstance(arr, list):
            return arr
    except json.JSONDecodeError:
        pass

    return [dict(DEFAULT_ENRICHMENT, index=i + 1) for i in range(expected)]
