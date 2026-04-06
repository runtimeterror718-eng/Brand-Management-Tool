import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { ragQuery, isRAGEnabled, embedText, searchMentions, searchNegativeMentions, getSupabase } from "@/lib/rag";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY || "";

async function getBrandIds(sb: any): Promise<{ ids: string[]; name: string }> {
  const { data } = await sb.from("brands").select("id, name").eq("name", "PhysicsWallah");
  if (data?.length) return { ids: data.map((b: any) => b.id), name: "PhysicsWallah" };
  const { data: any } = await sb.from("brands").select("id, name").limit(1);
  return { ids: any?.map((b: any) => b.id) || [], name: any?.[0]?.name || "" };
}

export async function GET() {
  if (!url || !key) return NextResponse.json({ live: false });
  const sb = createClient(url, key);

  const { ids: brandIds, name: brandName } = await getBrandIds(sb);
  if (!brandIds.length) return NextResponse.json({ live: false });
  const brandId = brandIds[0];

  // Parallel: traditional data + RAG analysis
  const [mentionsRes, redditRes, igRes, geoRes, embeddingStatsRes, ragNegative, ragPositive] = await Promise.all([
    sb.from("mentions").select("platform, sentiment_label, likes, comments_count, engagement_score, published_at, content_text, author_handle, source_url")
      .in("brand_id", brandIds).order("scraped_at", { ascending: false }).limit(500),
    sb.from("reddit_posts").select("post_title, post_body, score, num_comments, subreddit_name, post_url, author_username, created_at")
      .in("brand_id", brandIds).order("score", { ascending: false }).limit(20),
    sb.from("instagram_posts").select("caption_text, like_count, comment_count, media_type, post_url, account_name, hashtags, published_date")
      .in("brand_id", brandIds).order("like_count", { ascending: false }).limit(20),
    sb.from("geo_aggregates").select("*").in("brand_id", brandIds).order("total_mentions", { ascending: false }),
    // Embedding-based sentiment from classified data
    sb.from("mention_embeddings")
      .select("sentiment_label, platform")
      .eq("brand_id", brandId)
      .not("sentiment_label", "is", null),
    // RAG: negative theme analysis
    isRAGEnabled()
      ? ragQuery("What are the biggest complaints, problems, and negative narratives about Physics Wallah right now? What are students most angry about?", {
          brandId,
          sentiment: "negative",
          mentionLimit: 20,
          rerank: true,
          rerankTopK: 12,
          systemPrompt: `You are OVAL, a brand intelligence AI for Physics Wallah.
Summarize the top 5 negative themes you see in the data. For each:
- Theme name (bold)
- How many mentions relate to it
- A real quote from the data
- Severity: Critical/High/Medium
Keep it punchy — this is an executive briefing.`,
        })
      : Promise.resolve(null),
    // RAG: positive theme analysis
    isRAGEnabled()
      ? ragQuery("What do students love and appreciate most about Physics Wallah? What positive things are people saying?", {
          brandId,
          sentiment: "positive",
          mentionLimit: 15,
          rerank: true,
          rerankTopK: 8,
          systemPrompt: `You are OVAL. Summarize the top 3 positive themes about Physics Wallah. For each: theme name, pattern, real quote. Keep it brief.`,
        })
      : Promise.resolve(null),
  ]);

  const mentions = mentionsRes.data || [];
  const redditPosts = redditRes.data || [];
  const igPosts = igRes.data || [];
  const geo = geoRes.data || [];
  const embeddingStats = embeddingStatsRes.data || [];

  // Sentiment from embeddings (LLM-classified, more accurate)
  const embSentiment = { positive: 0, negative: 0, neutral: 0, total: embeddingStats.length };
  const embPlatforms: Record<string, { total: number; negative: number; positive: number }> = {};
  for (const m of embeddingStats) {
    const s = m.sentiment_label as keyof typeof embSentiment;
    if (s in embSentiment) embSentiment[s]++;
    const p = m.platform || "unknown";
    if (!embPlatforms[p]) embPlatforms[p] = { total: 0, negative: 0, positive: 0 };
    embPlatforms[p].total++;
    if (s === "negative") embPlatforms[p].negative++;
    if (s === "positive") embPlatforms[p].positive++;
  }

  // Legacy sentiment from mentions table
  const total = mentions.length;
  const byPlatform: Record<string, { total: number; negative: number; positive: number }> = {};
  let totalNeg = 0, totalPos = 0;
  for (const m of mentions) {
    const p = m.platform || "unknown";
    if (!byPlatform[p]) byPlatform[p] = { total: 0, negative: 0, positive: 0 };
    byPlatform[p].total++;
    if (m.sentiment_label === "negative") { byPlatform[p].negative++; totalNeg++; }
    if (m.sentiment_label === "positive") { byPlatform[p].positive++; totalPos++; }
  }

  // Use embedding-based stats (LLM-classified) as primary, fall back to mentions table
  const primaryTotal = embSentiment.total || total;
  const primaryNeg = embSentiment.negative || totalNeg;
  const primaryPos = embSentiment.positive || totalPos;
  const negPct = primaryTotal > 0 ? Math.round(primaryNeg / primaryTotal * 100) : 0;
  const posPct = primaryTotal > 0 ? Math.round(primaryPos / primaryTotal * 100) : 0;

  // Health score: weighted by embedding sentiment
  const healthScore = Math.max(0, Math.min(100, Math.round(
    50 + (posPct - negPct * 1.5) * 0.5 + Math.min(primaryTotal / 20, 15)
  )));

  return NextResponse.json({
    live: true,
    brand: { id: brandId, name: brandName },
    stats: {
      totalMentions: primaryTotal,
      healthScore,
      negativePercent: negPct,
      positivePercent: posPct,
      neutralPercent: 100 - negPct - posPct,
      byPlatform: Object.keys(embPlatforms).length > 0 ? embPlatforms : byPlatform,
      sentimentSource: embSentiment.total > 0 ? "llm-classified-embeddings" : "rule-based-mentions",
    },
    topRedditPosts: redditPosts.slice(0, 5),
    topIgPosts: igPosts.slice(0, 4),
    geo,
    recentMentions: mentions.slice(0, 10),
    rag: {
      enabled: isRAGEnabled(),
      negativeAnalysis: ragNegative ? {
        summary: ragNegative.answer,
        confidence: ragNegative.confidence,
        mentionsUsed: ragNegative.metadata.mentionsAfterRerank,
        avgSimilarity: ragNegative.metadata.avgSimilarity,
        platforms: ragNegative.metadata.platforms,
      } : null,
      positiveAnalysis: ragPositive ? {
        summary: ragPositive.answer,
        confidence: ragPositive.confidence,
        mentionsUsed: ragPositive.metadata.mentionsAfterRerank,
        avgSimilarity: ragPositive.metadata.avgSimilarity,
      } : null,
    },
  });
}
