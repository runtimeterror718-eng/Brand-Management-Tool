import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { ragQuery, isRAGEnabled } from "@/lib/rag";
import { formatNumber } from "@/lib/utils";
import { isDemoMode, demoInstagram } from "@/lib/demo-data";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.NEXT_PUBLIC_SUPABASE_KEY || "";

async function getBrandIds(sb: any): Promise<string[]> {
  const { data } = await sb.from("brands").select("id").eq("name", "PhysicsWallah");
  if (data?.length) return data.map((b: any) => b.id);
  return [];
}

export async function GET() {
  if (isDemoMode()) return NextResponse.json(demoInstagram);
  const sb = createClient(url, key);
  const brandIds = await getBrandIds(sb);
  if (!brandIds.length) return NextResponse.json({ live: false });
  const brandId = brandIds[0];

  const [postsRes, commentsRes, mentionsRes, embStatsRes, ragInsight] = await Promise.all([
    sb.from("instagram_posts").select("*").in("brand_id", brandIds).order("like_count", { ascending: false }).limit(200),
    sb.from("instagram_comments").select("comment_text, comment_author, post_id, comment_date").limit(1000),
    sb.from("mentions").select("sentiment_label, sentiment_score, scraped_at, content_text, author_handle, likes, comments_count, source_url")
      .in("brand_id", brandIds).eq("platform", "instagram").order("scraped_at", { ascending: true }).limit(500),
    // LLM-classified sentiment (Instagram only)
    sb.from("mention_embeddings").select("sentiment_label").eq("brand_id", brandId).eq("platform", "instagram").not("sentiment_label", "is", null),
    // RAG: Instagram-specific analysis
    isRAGEnabled()
      ? ragQuery("What is the Instagram community saying about Physics Wallah? What content performs best? Any complaints visible on Instagram?", {
          brandId,
          platform: "instagram",
          mentionLimit: 20,
          rerank: true,
          rerankTopK: 12,
          systemPrompt: `You are OVAL analyzing Instagram data for Physics Wallah.
Provide:
1. Content themes (what types of posts get engagement)
2. Community sentiment (fan vs critic ratio)
3. Any negative signals visible on Instagram (complaints in comments, order issues)
4. Comparison to Reddit sentiment (is Instagram an echo chamber?)
Be data-grounded — cite real posts/comments.`,
        })
      : Promise.resolve(null),
  ]);

  const posts = postsRes.data || [];
  const comments = commentsRes.data || [];
  const mentions = mentionsRes.data || [];
  const embStats = embStatsRes.data || [];

  // Embedding-based sentiment
  const embSentiment = { positive: 0, negative: 0, neutral: 0 };
  for (const m of embStats) {
    const s = m.sentiment_label as keyof typeof embSentiment;
    if (s in embSentiment) embSentiment[s]++;
  }
  const embTotal = embStats.length;

  // Legacy sentiment
  const negCount = mentions.filter(m => m.sentiment_label === "negative").length;
  const posCount = mentions.filter(m => m.sentiment_label === "positive").length;
  const neuCount = mentions.length - negCount - posCount;

  const totalPosts = posts.length;
  const totalLikes = posts.reduce((s, p) => s + (p.like_count || 0), 0);
  const totalComments = posts.reduce((s, p) => s + (p.comment_count || 0), 0);
  const totalReelPlays = posts.reduce((s, p) => s + (p.reel_plays || 0), 0);

  // Hashtag aggregation
  const hashtagMap: Record<string, { posts: number; totalLikes: number; captions: string[]; accounts: Set<string> }> = {};
  for (const p of posts) {
    for (const tag of (p.hashtags || []) as string[]) {
      const t = tag.startsWith("#") ? tag : `#${tag}`;
      if (!hashtagMap[t]) hashtagMap[t] = { posts: 0, totalLikes: 0, captions: [], accounts: new Set() };
      hashtagMap[t].posts++;
      hashtagMap[t].totalLikes += p.like_count || 0;
      if (p.caption_text && hashtagMap[t].captions.length < 3) hashtagMap[t].captions.push(p.caption_text.slice(0, 120));
      if (p.account_name) hashtagMap[t].accounts.add(p.account_name);
    }
  }
  const topHashtags = Object.entries(hashtagMap)
    .sort((a, b) => b[1].posts - a[1].posts).slice(0, 12)
    .map(([tag, d]) => ({ tag, posts: d.posts, likes: d.totalLikes, quote: d.captions[0] || "", accounts: Array.from(d.accounts).slice(0, 3), sentiment: "positive" as const }));

  // Account breakdown
  const accountMap: Record<string, { posts: number; totalLikes: number; totalComments: number }> = {};
  for (const p of posts) {
    const acc = p.account_name || "unknown";
    if (!accountMap[acc]) accountMap[acc] = { posts: 0, totalLikes: 0, totalComments: 0 };
    accountMap[acc].posts++;
    accountMap[acc].totalLikes += p.like_count || 0;
    accountMap[acc].totalComments += p.comment_count || 0;
  }
  const topAccounts = Object.entries(accountMap)
    .sort((a, b) => b[1].totalLikes - a[1].totalLikes).slice(0, 10)
    .map(([name, d]) => ({ name, ...d, avgLikes: Math.round(d.totalLikes / Math.max(d.posts, 1)) }));

  // Media type breakdown
  const mediaTypes: Record<string, number> = {};
  for (const p of posts) mediaTypes[p.media_type || "unknown"] = (mediaTypes[p.media_type || "unknown"] || 0) + 1;

  // Sentiment trend
  const weeklyScores: { week: string; score: number; count: number }[] = [];
  const now = new Date();
  for (let w = 11; w >= 0; w--) {
    const ws = new Date(now.getTime() - w * 7 * 86400000);
    const we = new Date(ws.getTime() + 7 * 86400000);
    const wm = mentions.filter(m => { const d = new Date(m.scraped_at); return d >= ws && d < we; });
    weeklyScores.push({ week: `W${12 - w}`, score: wm.length > 0 ? Math.round(wm.reduce((s, m) => s + (m.sentiment_score || 0), 0) / wm.length * 100) / 100 : 0, count: wm.length });
  }

  // Top comments
  const topCommentTexts = comments.filter(c => c.comment_text?.length > 20).slice(0, 20)
    .map(c => ({ text: c.comment_text.slice(0, 200), author: c.comment_author || "anonymous" }));

  // Top posts
  const topPosts = posts.slice(0, 10).map(p => ({
    caption: (p.caption_text || "").slice(0, 150), likes: p.like_count, comments: p.comment_count,
    mediaType: p.media_type, url: p.post_url, account: p.account_name,
    videoViews: p.video_views, reelPlays: p.reel_plays, hashtags: (p.hashtags || []).slice(0, 5),
  }));

  return NextResponse.json({
    live: true,
    stats: {
      totalPosts, totalLikes, totalComments, totalReelPlays,
      totalVideoViews: posts.reduce((s, p) => s + (p.video_views || 0), 0),
      totalHashtags: Object.keys(hashtagMap).length,
      storedComments: comments.length,
      sentiment: {
        positive: embTotal > 0 ? embSentiment.positive : posCount,
        negative: embTotal > 0 ? embSentiment.negative : negCount,
        neutral: embTotal > 0 ? embSentiment.neutral : neuCount,
        overall: (embTotal > 0 ? embSentiment.positive : posCount) > (embTotal > 0 ? embSentiment.negative : negCount) ? "Positive-leaning" : "Neutral",
        source: embTotal > 0 ? "llm-classified" : "rule-based",
        totalClassified: embTotal,
      },
    },
    topHashtags, topAccounts, mediaTypes, sentimentTrend: weeklyScores, topComments: topCommentTexts, topPosts,
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
