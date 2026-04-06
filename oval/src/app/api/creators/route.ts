import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { isDemoMode, demoCreators } from "@/lib/demo-data";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY || "";

async function getAllBrandIds(sb: any): Promise<string[]> {
  const { data } = await sb.from("brands").select("id").or("name.eq.PhysicsWallah,name.eq.PW Live Smoke");
  return data?.map((b: any) => b.id) || [];
}

export async function GET() {
  if (isDemoMode()) return NextResponse.json(demoCreators);
  const sb = createClient(url, key);
  const brandIds = await getAllBrandIds(sb);
  if (!brandIds.length) return NextResponse.json({ live: false });

  const [ytChannelsRes, ytVideosRes, igEmbRes, tgChannelsRes] = await Promise.all([
    sb.from("youtube_channels").select("channel_id, channel_name, channel_subscribers, channel_owner").in("brand_id", brandIds).order("channel_subscribers", { ascending: false }),
    sb.from("youtube_videos").select("video_id, video_title, video_views, video_likes, video_comment_count, source_url, channel_id, title_triage_label, title_triage_is_pr_risk").in("brand_id", brandIds),
    sb.from("mention_embeddings").select("content_text, platform, sentiment_label").in("brand_id", brandIds).eq("platform", "instagram").limit(500),
    sb.from("telegram_channels").select("channel_username, channel_title, classification_label, is_fake, participants_count, fake_score_10, should_monitor").in("brand_id", brandIds),
  ]);

  const ytChannels = ytChannelsRes.data || [];
  const ytVideos = ytVideosRes.data || [];
  const tgChannels = tgChannelsRes.data || [];

  // Build YouTube creator profiles
  const ytCreators = ytChannels.map((ch: any) => {
    const videos = ytVideos.filter((v: any) => v.channel_id === ch.channel_id);
    const totalViews = videos.reduce((s: number, v: any) => s + (v.video_views || 0), 0);
    const totalLikes = videos.reduce((s: number, v: any) => s + (v.video_likes || 0), 0);
    const prRiskCount = videos.filter((v: any) => v.title_triage_is_pr_risk).length;
    const negCount = videos.filter((v: any) => v.title_triage_label === "negative").length;
    const posCount = videos.filter((v: any) => v.title_triage_label === "positive").length;

    let stance: "friend" | "threat" | "neutral" = "neutral";
    if (negCount > posCount && negCount >= 2) stance = "threat";
    else if (posCount > negCount) stance = "friend";

    let threatLevel: "low" | "medium" | "high" = "low";
    if (prRiskCount >= 2 || (negCount >= 3 && totalViews > 10000)) threatLevel = "high";
    else if (prRiskCount >= 1 || negCount >= 2) threatLevel = "medium";

    return {
      platform: "youtube",
      name: ch.channel_name,
      channelId: ch.channel_id,
      subscribers: ch.channel_subscribers || 0,
      isOwned: ch.channel_owner === "Owned",
      videoCount: videos.length,
      totalViews,
      totalLikes,
      prRiskCount,
      negativeVideos: negCount,
      positiveVideos: posCount,
      stance,
      threatLevel,
      topVideos: videos.sort((a: any, b: any) => (b.video_views || 0) - (a.video_views || 0)).slice(0, 3).map((v: any) => ({
        title: v.video_title,
        views: v.video_views,
        url: v.source_url,
        videoId: v.video_id,
        triage: v.title_triage_label,
        isPrRisk: v.title_triage_is_pr_risk,
      })),
    };
  });

  // Build Telegram creator profiles
  const tgCreators = tgChannels.map((ch: any) => {
    let stance: "friend" | "threat" | "neutral" = "neutral";
    if (ch.is_fake) stance = "threat";
    else if (ch.classification_label === "official") stance = "friend";
    else if (ch.classification_label === "fan_unofficial") stance = "friend";

    return {
      platform: "telegram",
      name: ch.channel_title || ch.channel_username,
      username: ch.channel_username,
      members: ch.participants_count || 0,
      label: ch.classification_label,
      isFake: ch.is_fake,
      fakeScore: ch.fake_score_10,
      stance,
      threatLevel: ch.is_fake ? "high" : "low",
      shouldMonitor: ch.should_monitor,
    };
  });

  // Combine and sort by threat level
  const allCreators = [
    ...ytCreators.filter((c: any) => !c.isOwned),
    ...tgCreators,
  ];

  const threatOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };
  allCreators.sort((a, b) => {
    const td = (threatOrder[a.threatLevel] ?? 9) - (threatOrder[b.threatLevel] ?? 9);
    if (td !== 0) return td;
    return (b.subscribers || b.members || 0) - (a.subscribers || a.members || 0);
  });

  const stats = {
    totalCreators: allCreators.length,
    threats: allCreators.filter((c) => c.stance === "threat").length,
    friends: allCreators.filter((c) => c.stance === "friend").length,
    neutral: allCreators.filter((c) => c.stance === "neutral").length,
    totalReach: allCreators.reduce((s, c) => s + (c.subscribers || c.members || 0), 0),
  };

  return NextResponse.json({ live: true, creators: allCreators, stats });
}
