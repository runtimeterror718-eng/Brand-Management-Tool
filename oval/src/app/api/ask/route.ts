import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.SUPABASE_SERVICE_KEY || "";
const openaiKey = process.env.OPENAI_API_KEY || "";

export async function POST(request: Request) {
  const { question, brand_id } = await request.json();

  if (!question) {
    return NextResponse.json({ error: "No question provided" }, { status: 400 });
  }

  if (!url || !key) {
    return NextResponse.json({ error: "Supabase not configured" }, { status: 500 });
  }

  const sb = createClient(url, key);

  // Get brand_id if not provided
  let brandId = brand_id;
  if (!brandId) {
    const { data: brands } = await sb.from("brands").select("id").limit(1);
    brandId = brands?.[0]?.id;
  }

  if (!brandId) {
    return NextResponse.json({ error: "No brand found" }, { status: 404 });
  }

  // Simple keyword search fallback (works without embeddings)
  const keywords = question.toLowerCase().split(/\s+/).filter((w: string) => w.length > 3);
  const searchTerm = keywords.slice(0, 3).join(" | ");

  // Search mentions by text similarity
  const { data: mentions } = await sb
    .from("mentions")
    .select("content_text, platform, sentiment_label, sentiment_score, likes, comments_count, author_handle, source_url")
    .eq("brand_id", brandId)
    .textSearch("content_text", searchTerm, { type: "websearch", config: "english" })
    .limit(15);

  // Also get cluster summaries
  const { data: clusters } = await sb
    .from("cluster_embeddings")
    .select("cluster_id, cluster_label, summary, mention_count, avg_sentiment, representative_texts")
    .eq("brand_id", brandId);

  // Get overall stats
  const { data: allMentions } = await sb
    .from("mentions")
    .select("platform, sentiment_label")
    .eq("brand_id", brandId);

  const stats = {
    total: allMentions?.length || 0,
    negative: allMentions?.filter(m => m.sentiment_label === "negative").length || 0,
    positive: allMentions?.filter(m => m.sentiment_label === "positive").length || 0,
  };

  // Build context
  const context = buildContext(mentions || [], clusters || [], stats);

  // If no OpenAI key, return raw context
  if (!openaiKey) {
    return NextResponse.json({
      answer: `Based on ${mentions?.length || 0} relevant mentions found:\n\n${(mentions || []).slice(0, 5).map(m => `- [${m.platform}] ${m.content_text?.slice(0, 120)}...`).join("\n")}`,
      sources: mentions?.slice(0, 10) || [],
      clusters: clusters || [],
      stats,
      llm: false,
    });
  }

  // Call OpenAI
  try {
    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${openaiKey}`,
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        max_tokens: 800,
        temperature: 0.3,
        messages: [
          {
            role: "system",
            content: `You are a brand intelligence analyst for OVAL. Answer questions using ONLY the provided context from real Reddit/Instagram data. Quote real comments. Be specific with numbers. If data is limited, say so.`,
          },
          {
            role: "user",
            content: `Question: ${question}\n\n--- CONTEXT (real scraped data, ${stats.total} total mentions) ---\n${context}\n--- END ---\n\nAnswer concisely based on the data above.`,
          },
        ],
      }),
    });

    const data = await resp.json();
    const answer = data.choices?.[0]?.message?.content || "Failed to generate answer";

    return NextResponse.json({
      answer,
      sources: mentions?.slice(0, 10) || [],
      clusters: clusters || [],
      stats,
      llm: true,
    });
  } catch {
    return NextResponse.json({
      answer: "LLM call failed. Showing raw data instead.",
      sources: mentions?.slice(0, 10) || [],
      clusters: clusters || [],
      stats,
      llm: false,
    });
  }
}

function buildContext(mentions: any[], clusters: any[], stats: any): string {
  const parts: string[] = [];

  parts.push(`Overall: ${stats.total} mentions, ${stats.positive} positive, ${stats.negative} negative`);

  if (clusters.length > 0) {
    parts.push("\nCLUSTERS:");
    for (const c of clusters) {
      parts.push(`[${c.cluster_label}] ${c.mention_count} mentions, sentiment: ${c.avg_sentiment}`);
      if (c.representative_texts) {
        for (const t of c.representative_texts.slice(0, 2)) {
          parts.push(`  "${t.slice(0, 150)}"`);
        }
      }
    }
  }

  if (mentions.length > 0) {
    parts.push(`\nRELEVANT MENTIONS (${mentions.length}):`);
    for (const m of mentions.slice(0, 10)) {
      parts.push(`[${m.platform}|${m.sentiment_label || "?"}] "${(m.content_text || "").slice(0, 200)}"`);
    }
  }

  return parts.join("\n");
}
