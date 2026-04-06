import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { ragQuery, isRAGEnabled } from "@/lib/rag";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY || "";

async function getBrandIds(sb: any): Promise<string[]> {
  const { data } = await sb.from("brands").select("id").eq("name", "PhysicsWallah");
  if (data?.length) return data.map((b: any) => b.id);
  return [];
}

const COMPETITORS = ["Allen", "Unacademy", "BYJU", "Aakash", "Vedantu"];

export async function GET() {
  if (!url || !key) return NextResponse.json({ live: false });
  const sb = createClient(url, key);
  const brandIds = await getBrandIds(sb);
  if (!brandIds.length) return NextResponse.json({ live: false });
  const brandId = brandIds[0];

  const [mentionsRes, ragCompetitor] = await Promise.all([
    sb.from("mention_embeddings")
      .select("content_text, platform, cluster_id, sentiment_label")
      .in("brand_id", brandIds)
      .not("content_text", "is", null)
      .limit(1500),
    // RAG: competitive intelligence
    isRAGEnabled()
      ? ragQuery("How is Physics Wallah compared to Allen, Unacademy, BYJU's, Aakash, Vedantu? What do students say when comparing PW to competitors?", {
          brandId,
          mentionLimit: 20,
          rerank: true,
          rerankTopK: 12,
          systemPrompt: `You are OVAL competitive intelligence analyst.
Analyze how Physics Wallah is compared to each competitor.
For each competitor mentioned in the data:
- How often they're compared to PW
- Is PW seen as better or worse?
- Key comparison point (price, quality, teachers, results)
- A real quote
Also identify: Who is PW's biggest threat based on the data?`,
        })
      : Promise.resolve(null),
  ]);

  const rows = mentionsRes.data || [];
  const totalMentions = rows.length;

  // Track competitor data with LLM-classified sentiment
  const competitorMap = new Map<string, {
    mentions: number;
    sentiments: { positive: number; negative: number; neutral: number };
    quotes: string[];
    platforms: Record<string, number>;
  }>();

  for (const name of COMPETITORS) {
    competitorMap.set(name, { mentions: 0, sentiments: { positive: 0, negative: 0, neutral: 0 }, quotes: [], platforms: {} });
  }

  let competitorMentionCount = 0;

  for (const row of rows) {
    const text = row.content_text || "";
    const lower = text.toLowerCase();
    const platform = row.platform || "unknown";
    const sentiment = row.sentiment_label || "neutral"; // LLM-classified

    for (const name of COMPETITORS) {
      if (lower.includes(name.toLowerCase())) {
        const entry = competitorMap.get(name)!;
        entry.mentions++;
        competitorMentionCount++;

        if (sentiment === "positive" || sentiment === "negative" || sentiment === "neutral") {
          entry.sentiments[sentiment]++;
        }

        if (entry.quotes.length < 5) {
          entry.quotes.push(text.length > 200 ? text.slice(0, 200) + "..." : text);
        }
        entry.platforms[platform] = (entry.platforms[platform] || 0) + 1;
      }
    }
  }

  // Build competitors array
  const competitors = Array.from(competitorMap.entries())
    .filter(([, v]) => v.mentions > 0)
    .map(([name, v]) => {
      const { positive, negative, neutral } = v.sentiments;
      const total = positive + negative + neutral;
      let sentiment: "positive" | "negative" | "neutral" | "mixed" = "neutral";
      if (negative > positive && negative > neutral) sentiment = "negative";
      else if (positive > negative && positive > neutral) sentiment = "positive";
      else if (negative > 0 && positive > 0) sentiment = "mixed";

      return {
        name,
        mentions: v.mentions,
        sentiment,
        sentimentBreakdown: v.sentiments,
        comparison_quotes: v.quotes,
        platforms: v.platforms,
      };
    })
    .sort((a, b) => b.mentions - a.mentions);

  // Negative amplifiers using LLM-classified sentiment
  const negativeAmplifiers: { text: string; platform: string; sentiment: string }[] = [];
  for (const row of rows) {
    if (row.sentiment_label === "negative") {
      const text = row.content_text || "";
      if (text.length > 30 && negativeAmplifiers.length < 20) {
        negativeAmplifiers.push({
          text: text.length > 300 ? text.slice(0, 300) + "..." : text,
          platform: row.platform || "unknown",
          sentiment: "negative",
        });
      }
    }
  }

  // Share of voice
  const shareOfVoice: Record<string, number> = { PW: totalMentions - competitorMentionCount };
  for (const [name, v] of Array.from(competitorMap.entries())) {
    if (v.mentions > 0) shareOfVoice[name] = v.mentions;
  }

  return NextResponse.json({
    live: true,
    competitors,
    negativeAmplifiers,
    shareOfVoice,
    stats: {
      totalMentions,
      competitorMentions: competitorMentionCount,
      sentimentSource: "llm-classified",
    },
    rag: ragCompetitor ? {
      enabled: true,
      analysis: ragCompetitor.answer,
      confidence: ragCompetitor.confidence,
      mentionsUsed: ragCompetitor.metadata.mentionsAfterRerank,
      avgSimilarity: ragCompetitor.metadata.avgSimilarity,
    } : { enabled: false },
  });
}
