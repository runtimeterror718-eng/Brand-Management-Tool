import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { ragQuery, isRAGEnabled } from "@/lib/rag";
import { getCached, setCache } from "@/lib/api-cache";
import { isDemoMode, demoCommandCenter } from "@/lib/demo-data";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.NEXT_PUBLIC_SUPABASE_KEY || "";

async function getAllBrandIds(sb: any): Promise<string[]> {
  const { data } = await sb.from("brands").select("id").or("name.eq.PhysicsWallah,name.eq.PW Live Smoke");
  return data?.map((b: any) => b.id) || [];
}

export async function GET() {
  const cached = getCached<any>("api:command-center");
  if (cached) return NextResponse.json(cached);

  if (isDemoMode()) return NextResponse.json(demoCommandCenter);
  const sb = createClient(url, key);
  const brandIds = await getAllBrandIds(sb);
  if (!brandIds.length) return NextResponse.json({ live: false });

  const [
    embStatsRes,
    recentSignalsRes,
    ytVideosRes,
    ytCommentsRes,
    tgChannelsRes,
    igPostsRes,
    redditPostsRes,
    autocompleteRes,
    newsRes,
    ragNeg,
    ragPos,
  ] = await Promise.all([
    // Sentiment stats from embeddings (all platforms)
    sb.from("mention_embeddings").select("platform, sentiment_label").in("brand_id", brandIds).not("sentiment_label", "is", null),
    // Recent signals — sample across ALL platforms (not just latest timestamp)
    // Fetch per-platform to ensure diversity
    Promise.all(
      ["reddit", "instagram", "youtube", "telegram"].map((platform) =>
        sb.from("mention_embeddings")
          .select("content_text, platform, sentiment_label, created_at")
          .in("brand_id", brandIds)
          .eq("platform", platform)
          .not("sentiment_label", "is", null)
          .not("content_text", "is", null)
          .limit(8)
          .then((r) => r.data || [])
      )
    ).then((results) => results.flat()),
    // YouTube: flagged videos with PR risk
    sb.from("youtube_videos").select("video_id, video_title, video_views, video_likes, source_url, title_triage_label, title_triage_is_pr_risk, title_triage_severity, title_triage_reason, caption_triage_severity, final_sentiment")
      .in("brand_id", brandIds).order("video_views", { ascending: false }).limit(20),
    // YouTube: top comments
    sb.from("youtube_comments").select("comment_text, comment_author, comment_likes, comment_sentiment_label, video_id")
      .order("comment_likes", { ascending: false }).limit(10),
    // Telegram: suspicious channels
    sb.from("telegram_channels").select("channel_username, channel_title, classification_label, is_fake, participants_count, fake_score_10")
      .in("brand_id", brandIds).order("participants_count", { ascending: false }),
    // Instagram: recent posts with triage
    sb.from("instagram_posts").select("post_id, account_name, caption_text, media_type, post_url, like_count, comment_count, reel_plays, caption_triage_label, caption_triage_is_pr_risk, caption_triage_severity, final_sentiment, final_is_pr_risk")
      .in("brand_id", brandIds).order("like_count", { ascending: false }).limit(20),
    // Reddit: top posts with triage
    sb.from("reddit_posts").select("post_id, post_title, subreddit_name, score, num_comments, post_url, post_triage_label, post_triage_is_pr_risk, post_triage_severity, final_sentiment, final_is_pr_risk")
      .in("brand_id", brandIds).order("score", { ascending: false }).limit(20),
    // Google: negative autocomplete
    sb.from("google_autocomplete").select("suggestion, sentiment, query_text, triage_label, triage_is_pr_risk").limit(100),
    // Google: negative news
    sb.from("google_news").select("title, source, url, published, sentiment, is_pr_risk, severity").limit(30),
    // RAG: negative briefing (use PhysicsWallah brand for RAG, not PW Live Smoke)
    isRAGEnabled()
      ? ragQuery("What are the top 3 most urgent brand threats for Physics Wallah right now? What needs immediate attention?", {
          brandId: brandIds.find((id: string) => id !== "97292c5e-f230-4732-8518-e159349eca07") || brandIds[0],
          sentiment: "negative",
          mentionLimit: 20,
          rerank: true,
          rerankTopK: 10,
          systemPrompt: `You are OVAL Command Center AI. Give an executive briefing in 3-4 short bullet points. Each bullet should be one plain sentence — threat name, where it's from, and what to do. NO markdown, NO headers, NO bold, NO asterisks, NO formatting. Just plain text with dashes for bullets.`,
        })
      : Promise.resolve(null),
    // RAG: positive signals
    isRAGEnabled()
      ? ragQuery("What are the top positive signals for Physics Wallah this week?", {
          brandId: brandIds.find((id: string) => id !== "97292c5e-f230-4732-8518-e159349eca07") || brandIds[0],
          sentiment: "positive",
          mentionLimit: 10,
          rerank: true,
          rerankTopK: 5,
          systemPrompt: `Summarize top 3 positive brand signals in 2-3 short bullet points. NO markdown, NO bold, NO asterisks, NO headers. Just plain text with dashes for bullets.`,
        })
      : Promise.resolve(null),
  ]);

  const embStats = embStatsRes.data || [];
  const ytVideos = ytVideosRes.data || [];
  const igPosts = igPostsRes.data || [];
  const redditPosts = redditPostsRes.data || [];
  const autocomplete = autocompleteRes.data || [];
  const news = newsRes.data || [];
  const tgChannels = tgChannelsRes.data || [];

  // ── Health Score ───────────────────────────────────────────
  const sentiment = { positive: 0, negative: 0, neutral: 0 };
  const platforms: Record<string, { total: number; positive: number; negative: number }> = {};
  for (const m of embStats) {
    const s = m.sentiment_label as keyof typeof sentiment;
    if (s in sentiment) sentiment[s]++;
    const p = m.platform || "unknown";
    if (!platforms[p]) platforms[p] = { total: 0, positive: 0, negative: 0 };
    platforms[p].total++;
    if (s === "positive") platforms[p].positive++;
    if (s === "negative") platforms[p].negative++;
  }
  const total = embStats.length;
  const posRate = total > 0 ? sentiment.positive / total : 0;
  const negRate = total > 0 ? sentiment.negative / total : 0;
  const healthScore = Math.round(Math.max(0, Math.min(100, (posRate * 100) - (negRate * 150) + 50)));

  // ── Critical Alerts ────────────────────────────────────────
  const alerts: any[] = [];

  // PR risk videos
  for (const v of ytVideos.filter((v: any) => v.title_triage_is_pr_risk)) {
    alerts.push({
      type: "youtube_pr_risk",
      severity: v.title_triage_severity || "medium",
      title: v.video_title,
      platform: "youtube",
      url: v.source_url,
      videoId: v.video_id,
      views: v.video_views,
      reason: v.title_triage_reason,
    });
  }

  // PR risk Instagram posts
  for (const p of igPosts.filter((p: any) => p.final_is_pr_risk || p.caption_triage_is_pr_risk)) {
    alerts.push({
      type: "instagram_pr_risk",
      severity: p.caption_triage_severity || "medium",
      title: p.caption_text?.slice(0, 100) || "Instagram post",
      platform: "instagram",
      url: p.post_url,
      account: p.account_name,
      likes: p.like_count,
      mediaType: p.media_type,
    });
  }

  // PR risk Reddit posts
  for (const p of redditPosts.filter((p: any) => p.final_is_pr_risk || p.post_triage_is_pr_risk)) {
    alerts.push({
      type: "reddit_pr_risk",
      severity: p.post_triage_severity || "medium",
      title: p.post_title,
      platform: "reddit",
      url: p.post_url,
      subreddit: p.subreddit_name,
      score: p.score,
    });
  }

  // Fake Telegram channels
  for (const c of tgChannels.filter((c: any) => c.is_fake)) {
    alerts.push({
      type: "telegram_fake_channel",
      severity: "high",
      title: `Fake channel: @${c.channel_username} (${c.channel_title})`,
      platform: "telegram",
      members: c.participants_count,
      fakeScore: c.fake_score_10,
    });
  }

  // Negative autocomplete
  const negAutocomplete = autocomplete.filter((a: any) => a.sentiment === "negative" || a.triage_label === "negative");
  if (negAutocomplete.length > 0) {
    alerts.push({
      type: "google_autocomplete_risk",
      severity: "high",
      title: `${negAutocomplete.length} negative autocomplete suggestions`,
      platform: "google",
      suggestions: negAutocomplete.slice(0, 5).map((a: any) => a.suggestion),
    });
  }

  // Negative news
  const negNews = news.filter((n: any) => n.is_pr_risk || n.sentiment === "negative");
  for (const n of negNews.slice(0, 3)) {
    alerts.push({
      type: "google_negative_news",
      severity: n.severity || "medium",
      title: n.title,
      platform: "google",
      source: n.source,
      url: n.url,
    });
  }

  // Sort alerts by severity
  const sevOrder: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
  alerts.sort((a, b) => (sevOrder[a.severity] ?? 9) - (sevOrder[b.severity] ?? 9));

  // ── Platform Pulse ─────────────────────────────────────────
  const platformPulse = Object.entries(platforms).map(([name, data]) => ({
    name,
    mentions: data.total,
    positiveRatio: data.total > 0 ? Math.round((data.positive / data.total) * 100) : 0,
    negative: data.negative,
  })).sort((a, b) => b.mentions - a.mentions);

  // ── Recent Signals (sampled across all platforms) ───────────
  const allSignals = (recentSignalsRes as any) || [];
  // Shuffle to mix platforms
  for (let i = allSignals.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [allSignals[i], allSignals[j]] = [allSignals[j], allSignals[i]];
  }
  const recentSignals = allSignals.slice(0, 24).map((m: any) => ({
    text: (m.content_text || "").slice(0, 200),
    platform: m.platform,
    sentiment: m.sentiment_label,
    time: m.created_at,
  }));

  // ── Creators (from YouTube channels + IG accounts) ─────────
  const creators: any[] = [];
  // YouTube creators
  for (const v of ytVideos) {
    // Extract channel info from video data
    const existing = creators.find(c => c.name === v.video_title?.split("|")?.[0]?.trim());
    if (!existing && v.video_title) {
      creators.push({
        platform: "youtube",
        videoTitle: v.video_title,
        views: v.video_views,
        url: v.source_url,
        videoId: v.video_id,
        triage: v.title_triage_label,
        isPrRisk: v.title_triage_is_pr_risk,
      });
    }
  }

  // ── Enrollment Risk Signals ─────────────────────────────���──
  const enrollmentRisks = {
    negativeAutocomplete: negAutocomplete.slice(0, 8).map((a: any) => a.suggestion),
    negativeNews: negNews.slice(0, 5).map((n: any) => ({ title: n.title, source: n.source, url: n.url })),
    totalAutocompleteSuggestions: autocomplete.length,
    negativeAutocompletePct: autocomplete.length > 0 ? Math.round((negAutocomplete.length / autocomplete.length) * 100) : 0,
  };

  const response = {
    live: true,
    healthScore,
    sentiment: { ...sentiment, total },
    alerts: alerts.slice(0, 10),
    platformPulse,
    recentSignals,
    enrollmentRisks,
    creators: creators.slice(0, 10),
    rag: {
      negative: ragNeg ? { summary: ragNeg.answer, confidence: ragNeg.confidence, mentions: ragNeg.metadata.mentionsAfterRerank } : null,
      positive: ragPos ? { summary: ragPos.answer, confidence: ragPos.confidence } : null,
    },
    stats: {
      totalMentions: total,
      totalAlerts: alerts.length,
      ragEnabled: isRAGEnabled(),
    },
  };

  setCache("api:command-center", response);
  return NextResponse.json(response);
}
