"""
Stage 5: LLM Labeling — name each cluster at each level with appropriate granularity.
Stage 6: Compute temporal dynamics and cross-platform analysis.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import numpy as np

from analysis.deep_clustering.ingest import NormalizedMention
from config.settings import OPENAI_API_KEY, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# ---- Labeling prompts per level ----

L1_PROMPT = """You are a brand intelligence analyst. Name this broad THEME about Physics Wallah.

Representative content from this theme ({count} mentions, platforms: {platforms}):
{samples}

Rules:
- 2-5 words maximum
- Think like a VP reading a dashboard
- Examples: "Faculty quality concerns", "Founder hero narrative", "Pricing backlash"

Return ONLY the theme name, nothing else."""

L2_PROMPT = """You are a brand intelligence analyst. Name this specific TOPIC within the theme "{parent_theme}" about Physics Wallah.

Representative content from this topic ({count} mentions, platforms: {platforms}):
{samples}

Rules:
- 3-8 words maximum
- Include what differentiates this from sibling topics under "{parent_theme}"
- Think like a product manager

Return ONLY the topic name, nothing else."""

L3_PROMPT = """You are a brand intelligence analyst. Name this micro SUB-TOPIC within "{parent_topic}" about Physics Wallah.

Representative content ({count} mentions):
{samples}

Rules:
- Be specific enough that someone could take action on this exact issue
- Think like a support agent
- 4-10 words

Return ONLY the sub-topic name, nothing else."""

DESC_PROMPT = """Write a 1-2 sentence description of this {level_name} about Physics Wallah based on these representative mentions:

{samples}

The name of this {level_name} is: "{name}"
Platforms: {platforms}
Average sentiment: {sentiment}

Be specific and data-driven. Reference the actual content."""


def label_all_clusters(
    cluster_results: dict,
    mentions: list[NormalizedMention],
    enrichments: list[dict],
) -> dict:
    """Label all clusters at all 3 levels and compute dynamics."""

    labeled = {"level_1": {}, "level_2": {}, "level_3": {}}

    # ---- Level 1: Themes ----
    logger.info("Labeling Level 1 themes...")
    for cid, data in cluster_results["level_1"].items():
        indices = data["mention_indices"]
        cluster_mentions = [mentions[i] for i in indices]
        cluster_enrichments = [enrichments[i] for i in indices]

        samples = _get_samples(cluster_mentions, n=8)
        platforms = _platform_dist(cluster_mentions)
        dynamics = _compute_dynamics(cluster_mentions, cluster_enrichments)

        name = _call_llm_label(L1_PROMPT.format(
            count=len(indices), platforms=_fmt_platforms(platforms), samples=samples
        )) if not data.get("is_misc") else "Miscellaneous / Unclustered"

        desc = _call_llm_label(DESC_PROMPT.format(
            level_name="theme", samples=samples, name=name,
            platforms=_fmt_platforms(platforms), sentiment=f"{dynamics['avg_sentiment']:.2f}"
        )) if not data.get("is_misc") else "Mentions that did not fit into any coherent theme."

        labeled["level_1"][cid] = {
            **data, "name": name, "description": desc,
            "platforms": platforms, **dynamics,
        }
        logger.info("  L1[%d] %s (%d mentions)", cid, name, len(indices))

    # ---- Level 2: Topics ----
    logger.info("Labeling Level 2 topics...")
    for cid, data in cluster_results["level_2"].items():
        indices = data["mention_indices"]
        cluster_mentions = [mentions[i] for i in indices]
        cluster_enrichments = [enrichments[i] for i in indices]

        parent_name = labeled["level_1"].get(data["parent_theme"], {}).get("name", "Unknown")
        samples = _get_samples(cluster_mentions, n=6)
        platforms = _platform_dist(cluster_mentions)
        dynamics = _compute_dynamics(cluster_mentions, cluster_enrichments)

        name = _call_llm_label(L2_PROMPT.format(
            parent_theme=parent_name, count=len(indices),
            platforms=_fmt_platforms(platforms), samples=samples
        )) if not data.get("is_misc") else f"Other {parent_name}"

        desc = _call_llm_label(DESC_PROMPT.format(
            level_name="topic", samples=samples, name=name,
            platforms=_fmt_platforms(platforms), sentiment=f"{dynamics['avg_sentiment']:.2f}"
        )) if not data.get("is_misc") else "Miscellaneous mentions within parent theme."

        labeled["level_2"][cid] = {
            **data, "name": name, "description": desc,
            "platforms": platforms, **dynamics,
        }
        logger.info("  L2[%d] → L1[%d] %s (%d)", cid, data["parent_theme"], name, len(indices))

    # ---- Level 3: Sub-topics ----
    logger.info("Labeling Level 3 sub-topics...")
    for cid, data in cluster_results["level_3"].items():
        indices = data["mention_indices"]
        cluster_mentions = [mentions[i] for i in indices]
        cluster_enrichments = [enrichments[i] for i in indices]

        parent_topic_name = labeled["level_2"].get(data["parent_topic"], {}).get("name", "Unknown")
        samples = _get_samples(cluster_mentions, n=5)
        platforms = _platform_dist(cluster_mentions)
        dynamics = _compute_dynamics(cluster_mentions, cluster_enrichments)

        # Only LLM-label non-misc clusters with enough content
        if not data.get("is_misc") and len(indices) >= 4:
            name = _call_llm_label(L3_PROMPT.format(
                parent_topic=parent_topic_name, count=len(indices), samples=samples
            ))
        else:
            name = f"Other — {parent_topic_name}"

        labeled["level_3"][cid] = {
            **data, "name": name, "description": "",
            "platforms": platforms, **dynamics,
        }

    logger.info("Labeling complete: %d themes, %d topics, %d sub-topics",
                len(labeled["level_1"]), len(labeled["level_2"]), len(labeled["level_3"]))
    return labeled


# ---- Dynamics computation ----

EMOTION_SCORES = {
    "anger": -1.0, "frustration": -0.7, "disappointment": -0.5,
    "confusion": -0.2, "indifference": 0.0, "sarcasm": -0.3,
    "trust": 0.5, "satisfaction": 0.7, "excitement": 0.9, "fear": -0.6,
}


def _compute_dynamics(
    mentions: list[NormalizedMention],
    enrichments: list[dict],
) -> dict:
    """Compute sentiment, velocity, lifecycle, actionability for a cluster."""

    # Sentiment
    sentiments = [EMOTION_SCORES.get(e.get("emotion", "indifference"), 0.0) for e in enrichments]
    avg_sentiment = float(np.mean(sentiments)) if sentiments else 0.0

    # Platform sentiments
    plat_sent: dict[str, list] = {}
    for m, e in zip(mentions, enrichments):
        plat_sent.setdefault(m.platform, []).append(
            EMOTION_SCORES.get(e.get("emotion", "indifference"), 0.0)
        )
    platform_sentiments = {p: round(float(np.mean(s)), 3) for p, s in plat_sent.items()}
    platform_divergence = float(np.std(list(platform_sentiments.values()))) if len(platform_sentiments) >= 2 else 0.0

    # Intent distribution
    intent_dist: dict[str, int] = {}
    emotion_dist: dict[str, int] = {}
    segment_dist: dict[str, int] = {}
    complaint_cats: dict[str, int] = {}
    for e in enrichments:
        intent_dist[e.get("intent", "unknown")] = intent_dist.get(e.get("intent", "unknown"), 0) + 1
        emotion_dist[e.get("emotion", "indifference")] = emotion_dist.get(e.get("emotion", "indifference"), 0) + 1
        segment_dist[e.get("user_segment", "unknown")] = segment_dist.get(e.get("user_segment", "unknown"), 0) + 1
        cat = e.get("complaint_category")
        if cat:
            complaint_cats[cat] = complaint_cats.get(cat, 0) + 1

    # Urgency & actionability
    urg_map = {"crisis": 4, "high": 3, "medium": 2, "low": 1}
    avg_urgency = float(np.mean([urg_map.get(e.get("urgency", "low"), 1) for e in enrichments]))
    actionable_pct = float(np.mean([1 if e.get("is_actionable") else 0 for e in enrichments]))
    complaint_pct = float(np.mean([1 if e.get("intent") == "complaint" else 0 for e in enrichments]))
    avg_engagement = float(np.mean([m.engagement_score for m in mentions]))
    actionability = min(100, (avg_urgency * 0.3 + min(avg_engagement / 100, 1) * 0.2 +
                              complaint_pct * 0.3 + actionable_pct * 0.2) * 25)

    # Dates & velocity
    dates = []
    for m in mentions:
        if m.published_at:
            try:
                dates.append(datetime.fromisoformat(m.published_at.replace("Z", "+00:00")))
            except Exception:
                pass

    velocity = 0.0
    lifecycle = "unknown"
    first_seen = min(dates).isoformat() if dates else None
    last_seen = max(dates).isoformat() if dates else None

    if len(dates) >= 3:
        date_range = (max(dates) - min(dates)).days
        recency = (datetime.now(max(dates).tzinfo) - max(dates)).days if dates else 999
        daily = {}
        for d in dates:
            k = d.strftime("%Y-%m-%d")
            daily[k] = daily.get(k, 0) + 1
        if len(daily) >= 3:
            x = np.arange(len(daily))
            y = np.array(list(daily.values()), dtype=float)
            velocity = float(np.polyfit(x, y, 1)[0])

        if date_range <= 2 and velocity > 0.5:
            lifecycle = "emerging"
        elif velocity > 0.3:
            lifecycle = "active"
        elif velocity > -0.1:
            lifecycle = "peaked"
        elif recency <= 3:
            lifecycle = "fading"
        else:
            lifecycle = "dormant"

    return {
        "avg_sentiment": round(avg_sentiment, 3),
        "platform_sentiments": platform_sentiments,
        "platform_divergence": round(platform_divergence, 3),
        "intent_distribution": intent_dist,
        "emotion_distribution": emotion_dist,
        "user_segment_distribution": segment_dist,
        "complaint_categories": complaint_cats,
        "velocity": round(velocity, 3),
        "lifecycle": lifecycle,
        "actionability_score": round(actionability, 1),
        "first_seen": first_seen,
        "last_seen": last_seen,
    }


# ---- Helpers ----

def _get_samples(mentions: list[NormalizedMention], n: int = 5) -> str:
    """Get top-N representative mentions by engagement."""
    sorted_m = sorted(mentions, key=lambda m: m.engagement_score, reverse=True)
    lines = []
    for m in sorted_m[:n]:
        lines.append(f'[{m.platform}] "{m.content[:200]}"')
    return "\n".join(lines)


def _platform_dist(mentions: list[NormalizedMention]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for m in mentions:
        dist[m.platform] = dist.get(m.platform, 0) + 1
    return dist


def _fmt_platforms(dist: dict[str, int]) -> str:
    return ", ".join(f"{p}: {c}" for p, c in sorted(dist.items(), key=lambda x: -x[1]))


def _call_llm_label(prompt: str) -> str:
    """Call LLM for a single label/description."""
    if OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o-mini", max_tokens=100, temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            return (resp.choices[0].message.content or "").strip().strip('"')
        except Exception as e:
            logger.warning("OpenAI label failed: %s", e)

    if ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001", max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip().strip('"')
        except Exception as e:
            logger.warning("Anthropic label failed: %s", e)

    return "Unlabeled cluster"
