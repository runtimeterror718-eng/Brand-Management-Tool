"""
Deep Topic Clustering Engine — 3-level hierarchical clustering for brand intelligence.

Pipeline:
  Stage 1: Ingest & Normalize (cross-platform dedup, language detection)
  Stage 2: LLM Pre-Enrichment (intent, emotion, complaint category per mention)
  Stage 3: Composite Embedding (text 70% + metadata 30%)
  Stage 4: Multi-Level HDBSCAN (Theme → Topic → Sub-topic)
  Stage 5: LLM Labeling (name each cluster at each level)
  Stage 6: Temporal & Cross-Platform Dynamics
  Stage 7: Store to Supabase

Usage:
    python -m analysis.deep_clustering --brand-id <uuid>
"""
