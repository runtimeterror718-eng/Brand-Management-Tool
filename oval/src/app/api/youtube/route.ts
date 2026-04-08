import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { ragQuery, isRAGEnabled } from "@/lib/rag";
import { isDemoMode, demoYoutube } from "@/lib/demo-data";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.NEXT_PUBLIC_SUPABASE_KEY || "";

async function getBrandIds(sb: any): Promise<string[]> {
  const { data } = await sb.from("brands").select("id").or("name.eq.PhysicsWallah,name.eq.PW Live Smoke");
  if (data?.length) return data.map((b: any) => b.id);
  return [];
}

export async function GET() {
  if (isDemoMode()) return NextResponse.json(demoYoutube);
  const sb = createClient(url, key);
  const brandIds = await getBrandIds(sb);
  if (!brandIds.length) return NextResponse.json({ live: false });
  const brandId = brandIds[0];

  const [channelsRes, videosRes, commentsRes, embStatsRes, ragInsight] = await Promise.all([
    sb.from("youtube_channels").select("*").in("brand_id", brandIds).order("channel_subscribers", { ascending: false }),
    sb.from("youtube_videos").select("video_id, video_title, video_views, video_likes, video_comment_count, video_duration, video_date, source_url, title_triage_label, title_triage_is_pr_risk, title_triage_reason, transcript_sentiment_label, transcript_pr_severity, transcript_pr_summary")
      .in("brand_id", brandIds).order("video_views", { ascending: false }),
    sb.from("youtube_comments").select("comment_text, comment_author, comment_likes, comment_sentiment_label, video_id")
      .order("comment_likes", { ascending: false }).limit(200),
    sb.from("mention_embeddings").select("sentiment_label").in("brand_id", brandIds).eq("platform", "youtube").not("sentiment_label", "is", null),
    isRAGEnabled()
      ? ragQuery("What are people saying about Physics Wallah on YouTube? What are the main themes in comments and video content?", {
          brandId,
          platform: "youtube",
          mentionLimit: 15,
          rerank: true,
          rerankTopK: 10,
          systemPrompt: `You are OVAL analyzing YouTube data for Physics Wallah.
Provide:
1. Content themes (what types of videos exist about PW)
2. Comment sentiment (what students say in comments)
3. Any PR risks flagged in video titles or transcripts
4. Key channels creating PW content
Be data-grounded — cite real comments/titles.`,
        })
      : Promise.resolve(null),
  ]);

  const channels = channelsRes.data || [];
  const videos = videosRes.data || [];
  const comments = commentsRes.data || [];
  const embStats = embStatsRes.data || [];

  // Embedding-based sentiment
  const embSentiment = { positive: 0, negative: 0, neutral: 0 };
  for (const m of embStats) {
    const s = m.sentiment_label as keyof typeof embSentiment;
    if (s in embSentiment) embSentiment[s]++;
  }

  // Stats
  const totalViews = videos.reduce((s, v) => s + (v.video_views || 0), 0);
  const totalLikes = videos.reduce((s, v) => s + (v.video_likes || 0), 0);
  const totalComments = videos.reduce((s, v) => s + (v.video_comment_count || 0), 0);
  const totalSubscribers = channels.reduce((s, c) => s + (c.channel_subscribers || 0), 0);

  // PR Risk videos
  const prRiskVideos = videos.filter(v => v.title_triage_is_pr_risk);

  // Channel breakdown
  const channelList = channels.map(c => ({
    name: c.channel_name,
    subscribers: c.channel_subscribers,
    owner: c.channel_owner,
  }));

  // Top comments
  const topComments = comments.filter(c => c.comment_text?.length > 10).slice(0, 20).map(c => ({
    text: c.comment_text?.slice(0, 200),
    author: c.comment_author,
    likes: c.comment_likes,
    sentiment: c.comment_sentiment_label,
  }));

  // Video list
  const videoList = videos.slice(0, 50).map(v => ({
    videoId: v.video_id,
    title: v.video_title,
    views: v.video_views,
    likes: v.video_likes,
    comments: v.video_comment_count,
    duration: v.video_duration,
    date: v.video_date,
    url: v.source_url,
    triageLabel: v.title_triage_label,
    isPrRisk: v.title_triage_is_pr_risk,
    triageReason: v.title_triage_reason,
    transcriptSentiment: v.transcript_sentiment_label,
    prSeverity: v.transcript_pr_severity,
    prSummary: v.transcript_pr_summary,
  }));

  return NextResponse.json({
    live: true,
    stats: {
      totalChannels: channels.length,
      totalVideos: videos.length,
      totalViews,
      totalLikes,
      totalComments,
      totalSubscribers,
      prRiskCount: prRiskVideos.length,
      sentiment: {
        ...embSentiment,
        total: embStats.length,
        overall: embSentiment.positive > embSentiment.negative ? "Positive-leaning" : embSentiment.negative > embSentiment.positive ? "Negative-leaning" : "Neutral",
        source: "llm-classified",
      },
    },
    channels: channelList,
    videos: videoList,
    prRiskVideos: prRiskVideos.slice(0, 5).map(v => ({
      videoId: v.video_id,
      title: v.video_title,
      views: v.video_views,
      reason: v.title_triage_reason,
      severity: v.transcript_pr_severity,
      summary: v.transcript_pr_summary,
      url: v.source_url,
    })),
    topComments,
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
