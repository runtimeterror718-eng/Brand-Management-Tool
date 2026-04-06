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

export async function GET() {
  if (!url || !key) return NextResponse.json({ live: false });
  const sb = createClient(url, key);
  const brandIds = await getBrandIds(sb);
  if (!brandIds.length) return NextResponse.json({ live: false });
  const brandId = brandIds[0];

  const [postsRes, commentsRes, mentionsRes, embStatsRes, ragInsight] = await Promise.all([
    sb.from("reddit_posts").select("*").in("brand_id", brandIds).order("score", { ascending: false }).limit(50),
    sb.from("reddit_comments").select("comment_body, comment_author, comment_score, post_id, comment_depth").order("comment_score", { ascending: false }).limit(200),
    sb.from("mentions").select("sentiment_label, sentiment_score, scraped_at").in("brand_id", brandIds).eq("platform", "reddit").order("scraped_at", { ascending: true }).limit(500),
    // LLM-classified sentiment from embeddings (Reddit only)
    sb.from("mention_embeddings").select("sentiment_label").eq("brand_id", brandId).eq("platform", "reddit").not("sentiment_label", "is", null),
    // RAG: Reddit-specific analysis
    isRAGEnabled()
      ? ragQuery("What are the main themes and narratives about Physics Wallah on Reddit? What do JEENEETards and Indian students discuss most?", {
          brandId,
          platform: "reddit",
          mentionLimit: 20,
          rerank: true,
          rerankTopK: 12,
          systemPrompt: `You are OVAL analyzing Reddit sentiment for Physics Wallah.
Provide:
1. Top 3 negative narratives (with real quotes)
2. Top 2 positive narratives (with real quotes)
3. Overall Reddit sentiment verdict (1 sentence)
4. Key subreddit themes
Be specific — this is data-driven intelligence, not speculation.`,
        })
      : Promise.resolve(null),
  ]);

  const posts = postsRes.data || [];
  const comments = commentsRes.data || [];
  const mentions = mentionsRes.data || [];
  const embStats = embStatsRes.data || [];

  // Use embedding-based sentiment (more accurate)
  const embSentiment = { positive: 0, negative: 0, neutral: 0 };
  for (const m of embStats) {
    const s = m.sentiment_label as keyof typeof embSentiment;
    if (s in embSentiment) embSentiment[s]++;
  }
  const embTotal = embStats.length;

  // Legacy sentiment
  const negCount = mentions.filter(m => m.sentiment_label === "negative").length;
  const posCount = mentions.filter(m => m.sentiment_label === "positive").length;

  const subCounts: Record<string, number> = {};
  for (const p of posts) {
    const s = p.subreddit_name || "unknown";
    subCounts[s] = (subCounts[s] || 0) + 1;
  }
  const topSub = Object.entries(subCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "N/A";

  // Weekly sentiment trend
  const weeklyScores: { week: string; score: number }[] = [];
  const now = new Date();
  for (let w = 11; w >= 0; w--) {
    const weekStart = new Date(now.getTime() - w * 7 * 86400000);
    const weekEnd = new Date(weekStart.getTime() + 7 * 86400000);
    const weekMentions = mentions.filter(m => {
      const d = new Date(m.scraped_at);
      return d >= weekStart && d < weekEnd;
    });
    const avg = weekMentions.length > 0
      ? weekMentions.reduce((s, m) => s + (m.sentiment_score || 0), 0) / weekMentions.length
      : 0;
    weeklyScores.push({ week: `W${12 - w}`, score: Math.round(avg * 100) / 100 });
  }

  return NextResponse.json({
    live: true,
    stats: {
      totalMentions: posts.length,
      negativeCount: embTotal > 0 ? embSentiment.negative : negCount,
      positiveCount: embTotal > 0 ? embSentiment.positive : posCount,
      neutralCount: embSentiment.neutral,
      sentiment: (embTotal > 0 ? embSentiment.negative : negCount) > (embTotal > 0 ? embSentiment.positive : posCount)
        ? "Mixed-negative" : "Positive-leaning",
      topSubreddit: `r/${topSub}`,
      sentimentSource: embTotal > 0 ? "llm-classified" : "rule-based",
      totalEmbeddings: embTotal,
    },
    posts: posts.slice(0, 10).map(p => ({
      subreddit: p.subreddit_name,
      title: p.post_title,
      snippet: (p.post_body || "").slice(0, 150),
      upvotes: p.score,
      comments: p.num_comments,
      sentiment: p.score < 0 ? "negative" : "mixed",
      url: p.post_url,
    })),
    sentimentTrend: weeklyScores,
    totalComments: comments.length,
    subredditBreakdown: Object.entries(subCounts).sort((a, b) => b[1] - a[1]).map(([name, count]) => ({ name, count })),
    rag: ragInsight ? {
      enabled: true,
      analysis: ragInsight.answer,
      confidence: ragInsight.confidence,
      mentionsUsed: ragInsight.metadata.mentionsAfterRerank,
      avgSimilarity: ragInsight.metadata.avgSimilarity,
      sentimentBreakdown: ragInsight.metadata.sentimentBreakdown,
    } : { enabled: false },
  });
}
