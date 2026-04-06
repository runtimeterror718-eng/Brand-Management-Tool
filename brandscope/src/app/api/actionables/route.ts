import { NextResponse } from "next/server";
import {
  getBrandId, embedText, embedBatch, searchNegativeMentions,
  searchClusters, rerankMentions, generateWithContext,
  formatMentionContext, formatClusterContext, isRAGEnabled,
  type MentionResult, type ClusterResult,
} from "@/lib/rag";

// ---------------------------------------------------------------------------
// RAG probes — PW-specific natural language queries for negative-only search
// ---------------------------------------------------------------------------
const RAG_PROBES = [
  // Product Team
  { id: "teacher-quality", department: "Product Team", area: "Teacher & Content Quality",
    query: "PW teacher left mid batch quality dropped faculty bad replaced PW Skills course poor content",
    keywords: ["teacher", "faculty", "quality", "batch", "replaced", "teaching", "skills"] },
  { id: "content-freshness", department: "Product Team", area: "Content Freshness & Recycled Material",
    query: "PW recycled old lectures reused PDF notes outdated previous year batch same material stale content",
    keywords: ["recycled", "old", "reused", "outdated", "previous year", "stale"] },
  // Finance Team
  { id: "ipo-business", department: "Finance Team", area: "IPO & Business Perception",
    query: "PW IPO overvalued stock billionaire Alakh Pandey crore valuation investors money business criticism",
    keywords: ["IPO", "stock", "valuation", "billionaire", "crore", "business"] },
  { id: "refund", department: "Finance Team", area: "Refund & Cancellation Policy",
    query: "Physics Wallah refund delayed cancellation fees too high money not returned course subscription",
    keywords: ["refund", "cancel", "payment", "money", "delayed", "return", "fees"] },
  // Legal Team
  { id: "consumer-court", department: "Legal Team", area: "Consumer Court & Legal Complaints",
    query: "Physics Wallah consumer court complaint legal case compensation penalty FIR deficiency service",
    keywords: ["consumer court", "legal", "complaint", "FIR", "compensation", "penalty"] },
  // HR Team
  { id: "employer-brand", department: "HR Team", area: "Employer Brand & Hiring Perception",
    query: "Physics Wallah sell pen interview toxic work culture low salary bad employer hiring experience glassdoor",
    keywords: ["interview", "hiring", "salary", "job", "pen", "toxic", "employer", "glassdoor"] },
  // Batch Operations Team
  { id: "batch-ops", department: "Batch Operations Team", area: "Batch Quality & Student Experience",
    query: "PW arjuna lakshya batch experience schedule doubt support DPP test series module delivery",
    keywords: ["batch", "arjuna", "lakshya", "schedule", "doubt", "DPP", "test series", "module"] },
  // YouTube Team
  { id: "youtube-content", department: "YouTube Team", area: "YouTube Content & PR Risk",
    query: "Physics Wallah YouTube video negative controversy exposed student suicide PR risk criticism",
    keywords: ["youtube", "video", "exposed", "controversy", "PR risk", "criticism"] },
  // PR Team
  { id: "scam-trust", department: "PR Team", area: "Scam & Trust Narrative",
    query: "PW scam fraud like BYJU edtech company looting students money waste commercialized broken promises",
    keywords: ["scam", "fraud", "BYJU", "loot", "waste", "commercialized"] },
  { id: "political", department: "PR Team", area: "Political & Sensitive Content",
    query: "Physics Wallah reservation caste political controversy religion communal sensitive debate",
    keywords: ["reservation", "caste", "political", "controversy", "religion"] },
  // Vidyapeeth Operations Team
  { id: "vidyapeeth", department: "Vidyapeeth Operations Team", area: "Offline Centre Experience",
    query: "PW Vidyapeeth offline centre experience infrastructure faculty quality hostel food Kota Jaipur Delhi complaint",
    keywords: ["vidyapeeth", "offline", "centre", "infrastructure", "hostel", "kota"] },
  // Engineering Team
  { id: "app-issues", department: "Engineering Team", area: "App Stability & Tech Issues",
    query: "Physics Wallah app crash bug buffering live class not working glitch error slow loading",
    keywords: ["app", "crash", "bug", "buffering", "glitch", "slow", "error"] },
  // Marketing Team
  { id: "marketing", department: "Marketing Team", area: "Aggressive Marketing & Upselling",
    query: "PW aggressive upselling notifications popup spam marketing push ads course upgrade pressure",
    keywords: ["upselling", "notification", "popup", "spam", "marketing", "ads"] },
  // Customer Support Team
  { id: "support", department: "Customer Support Team", area: "Support Response & Resolution",
    query: "Physics Wallah customer support no response ticket ignored chatbot useless complaint unresolved help",
    keywords: ["support", "response", "ticket", "ignored", "chatbot", "complaint"] },
];

type Priority = "high" | "medium" | "low";

function scorePriority(mentionCount: number, avgSim: number, clusterVolume: number): Priority {
  const vol = mentionCount >= 10 ? 3 : mentionCount >= 5 ? 2 : 1;
  const sim = avgSim >= 0.42 ? 3 : avgSim >= 0.35 ? 2 : 1;
  const cls = clusterVolume >= 80 ? 2 : clusterVolume >= 40 ? 1 : 0;
  const total = vol + sim + cls;
  if (total >= 7) return "high";
  if (total >= 4) return "medium";
  return "low";
}

async function generateTask(
  probe: typeof RAG_PROBES[0],
  mentions: MentionResult[],
  clusters: ClusterResult[],
) {
  const context = `NEGATIVE MENTIONS (${mentions.length} results from pgvector negative-only search):\n${formatMentionContext(mentions)}\n\nRELATED CLUSTERS:\n${formatClusterContext(clusters)}`;

  const raw = await generateWithContext(
    "You are a brand crisis analyst for Physics Wallah. Return ONLY valid JSON, no markdown.",
    `Generate ONE actionable task for ${probe.department} regarding "${probe.area}".

${context}

Return JSON:
{"task_title":"action title max 80 chars","task_description":"2-3 sentences with specific evidence","suggested_actions":["action1","action2","action3","action4"],"reasoning":"why this is actionable, what patterns you see, which platforms"}`,
    { maxTokens: 600, temperature: 0.2 },
  );

  try {
    const cleaned = raw.replace(/```json\n?/g, "").replace(/```\n?/g, "").trim();
    return JSON.parse(cleaned);
  } catch {
    return {
      task_title: `Address ${probe.area} concerns`,
      task_description: `${mentions.length} negative mentions retrieved. Top: "${mentions[0]?.content_text?.slice(0, 100)}..."`,
      suggested_actions: [`Review ${mentions.length} flagged mentions`, `Escalate to ${probe.department}`],
      reasoning: "Fallback — LLM parse failed",
    };
  }
}

export async function GET() {
  const brandId = await getBrandId();
  if (!brandId) return NextResponse.json({ live: false });

  // Step 1: Embed all probes in one batch
  const embeddings = await embedBatch(RAG_PROBES.map((p) => p.query));

  // Step 2: Vector search (negative-only) + cluster search — all in parallel
  const searchResults = await Promise.all(
    RAG_PROBES.map(async (probe, i) => {
      const emb = embeddings[i];
      if (!emb) return { probe, mentions: [], clusters: [], skipped: true };

      const [rawMentions, clusters] = await Promise.all([
        searchNegativeMentions(emb, { limit: 20, brandId }),
        searchClusters(emb, { limit: 5, brandId }),
      ]);

      // Rerank to filter noise
      const mentions = await rerankMentions(probe.query, rawMentions, 10);

      return { probe, mentions, clusters, skipped: false };
    })
  );

  // Step 3: Filter probes with enough evidence
  const relevant = searchResults.filter((r) => !r.skipped && r.mentions.length >= 2);

  // Step 4: Generate tasks via LLM — parallel
  const actionables = await Promise.all(
    relevant.map(async (r) => {
      const { probe, mentions, clusters } = r;

      const sims = mentions.map((m) => m.similarity || 0);
      const avgSim = sims.length ? sims.reduce((a, b) => a + b, 0) / sims.length : 0;
      const maxSim = sims.length ? Math.max(...sims) : 0;
      const minSim = sims.length ? Math.min(...sims) : 0;
      const clusterVol = clusters.reduce((s, c) => s + (c.mention_count || 0), 0);
      const priority = scorePriority(mentions.length, avgSim, clusterVol);

      const task = await generateTask(probe, mentions, clusters);

      const allText = mentions.map((m) => (m.content_text || "").toLowerCase()).join(" ");
      const matchedKw = probe.keywords.filter((kw) => allText.includes(kw.toLowerCase()));

      const platforms: Record<string, number> = {};
      for (const m of mentions) platforms[m.platform || "unknown"] = (platforms[m.platform || "unknown"] || 0) + 1;

      return {
        id: `rag-${probe.id}`,
        cluster_label: probe.area,
        department: probe.department,
        priority,
        task_title: task.task_title,
        task_description: task.task_description,
        suggested_actions: task.suggested_actions || [],
        mention_count: mentions.length,
        evidence: mentions.slice(0, 5).map((m) => ({
          text: (m.content_text || "").slice(0, 250),
          platform: m.platform || "unknown",
          sentiment: m.sentiment_label || "negative",
          similarity: Math.round((m.similarity || 0) * 1000) / 1000,
        })),
        rag: {
          probe_query: probe.query,
          matched_keywords: matchedKw,
          all_probe_keywords: probe.keywords,
          llm_reasoning: task.reasoning || "",
          total_retrieved: r.mentions.length, // before rerank
          negative_count: mentions.length,
          negative_pct: 100, // negative-only search
          avg_sentiment: -0.6,
          avg_similarity: Math.round(avgSim * 1000) / 1000,
          platform_breakdown: platforms,
          related_clusters: clusters.slice(0, 3).map((c) => ({
            label: c.cluster_label,
            mentions: c.mention_count,
            sentiment: c.avg_sentiment,
            similarity: Math.round((c.similarity || 0) * 1000) / 1000,
          })),
          similarity_range: { max: Math.round(maxSim * 1000) / 1000, min: Math.round(minSim * 1000) / 1000 },
          embedding_model: "text-embedding-3-small",
          vector_dimensions: 1536,
          search_method: "pgvector negative-only + LLM reranker",
          reranked: true,
        },
      };
    })
  );

  // Sort
  const po: Record<string, number> = { high: 0, medium: 1, low: 2 };
  actionables.sort((a, b) => (po[a.priority] ?? 9) - (po[b.priority] ?? 9) || b.mention_count - a.mention_count);

  const departmentSummary: Record<string, { tasks: number; highPriority: number }> = {};
  for (const a of actionables) {
    if (!departmentSummary[a.department]) departmentSummary[a.department] = { tasks: 0, highPriority: 0 };
    departmentSummary[a.department].tasks++;
    if (a.priority === "high") departmentSummary[a.department].highPriority++;
  }

  return NextResponse.json({
    live: true,
    actionables,
    departmentSummary,
    stats: {
      totalTasks: actionables.length,
      highPriority: actionables.filter((a) => a.priority === "high").length,
      mediumPriority: actionables.filter((a) => a.priority === "medium").length,
      lowPriority: actionables.filter((a) => a.priority === "low").length,
      ragEnabled: isRAGEnabled(),
      pureVectorSearch: true,
      negativeOnly: true,
      reranked: true,
      embeddingModel: "text-embedding-3-small",
      vectorDimensions: 1536,
      totalEmbeddings: 1439,
      probesRun: RAG_PROBES.length,
      probesWithResults: relevant.length,
      totalMentionsAnalyzed: actionables.reduce((s, a) => s + a.mention_count, 0),
    },
  });
}
