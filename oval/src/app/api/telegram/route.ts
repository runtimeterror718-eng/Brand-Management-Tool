import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { ragQuery, isRAGEnabled } from "@/lib/rag";
import { getCached, setCache } from "@/lib/api-cache";
import { isDemoMode, demoTelegram } from "@/lib/demo-data";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.NEXT_PUBLIC_SUPABASE_KEY || "";

async function getBrandIds(sb: any): Promise<string[]> {
  const { data } = await sb.from("brands").select("id").or("name.eq.PhysicsWallah,name.eq.PW Live Smoke");
  if (data?.length) return data.map((b: any) => b.id);
  return [];
}

export async function GET() {
  // Return cached response if available (5 min TTL)
  const cached = getCached<any>("api:telegram");
  if (cached) return NextResponse.json(cached);

  if (isDemoMode()) return NextResponse.json(demoTelegram);
  const sb = createClient(url, key);
  const brandIds = await getBrandIds(sb);
  if (!brandIds.length) return NextResponse.json({ live: false });
  const brandId = brandIds[0];

  const [channelsRes, messagesRes, embStatsRes, ragInsight] = await Promise.all([
    sb.from("telegram_channels").select("channel_username, channel_title, classification_label, should_monitor, participants_count, is_fake, is_scam, is_verified, public_url, fake_score_10, confidence, message_count_7d")
      .in("brand_id", brandIds).order("participants_count", { ascending: false }),
    sb.from("telegram_messages").select("message_text, channel_name, channel_username, views, forwards_count, risk_label, risk_score, is_suspicious, risk_flags, message_timestamp, media_type")
      .in("brand_id", brandIds).not("message_text", "is", null).order("views", { ascending: false }).limit(500),
    sb.from("mention_embeddings").select("sentiment_label").in("brand_id", brandIds).eq("platform", "telegram").not("sentiment_label", "is", null),
    isRAGEnabled()
      ? ragQuery("What is happening on Telegram channels about Physics Wallah? Are there fake channels, scam content, or suspicious activity?", {
          brandId,
          platform: "telegram",
          mentionLimit: 15,
          rerank: true,
          rerankTopK: 10,
          systemPrompt: `You are OVAL analyzing Telegram intelligence for Physics Wallah.
Provide:
1. Channel landscape (official vs fan vs suspicious/fake)
2. Content themes in messages
3. Risk signals (fake channels, scam content, suspicious links)
4. Engagement patterns (views, forwards)
Be specific — this is brand protection intelligence.`,
        })
      : Promise.resolve(null),
  ]);

  const channels = channelsRes.data || [];
  const messages = messagesRes.data || [];
  const embStats = embStatsRes.data || [];

  // Embedding sentiment
  const embSentiment = { positive: 0, negative: 0, neutral: 0 };
  for (const m of embStats) {
    const s = m.sentiment_label as keyof typeof embSentiment;
    if (s in embSentiment) embSentiment[s]++;
  }

  // Channel categories
  const official = channels.filter(c => c.classification_label === "official");
  const fan = channels.filter(c => c.classification_label === "fan_unofficial");
  const suspicious = channels.filter(c => c.classification_label === "suspicious_fake" || c.is_fake);
  const totalMembers = channels.reduce((s, c) => s + (c.participants_count || 0), 0);

  // Message stats
  const totalViews = messages.reduce((s, m) => s + (m.views || 0), 0);
  const totalForwards = messages.reduce((s, m) => s + (m.forwards_count || 0), 0);
  const suspiciousMessages = messages.filter(m => m.is_suspicious || m.risk_label === "suspicious");
  const safeMessages = messages.filter(m => m.risk_label === "safe");

  // Risk breakdown
  const riskBreakdown: Record<string, number> = {};
  for (const m of messages) {
    const label = m.risk_label || "unknown";
    riskBreakdown[label] = (riskBreakdown[label] || 0) + 1;
  }

  // Channel list
  const channelList = channels.map(c => ({
    username: c.channel_username,
    title: c.channel_title,
    label: c.classification_label,
    shouldMonitor: c.should_monitor,
    members: c.participants_count,
    isFake: c.is_fake,
    isScam: c.is_scam,
    isVerified: c.is_verified,
    url: c.public_url,
    fakeScore: c.fake_score_10,
    confidence: c.confidence,
    messagesLast7d: c.message_count_7d,
  }));

  // Top messages by views
  const topMessages = messages.slice(0, 15).map(m => ({
    text: (m.message_text || "").slice(0, 250),
    channel: m.channel_name || m.channel_username,
    views: m.views,
    forwards: m.forwards_count,
    riskLabel: m.risk_label,
    riskScore: m.risk_score,
    isSuspicious: m.is_suspicious,
    date: m.message_timestamp,
    mediaType: m.media_type,
  }));

  // Suspicious messages
  const suspiciousContent = suspiciousMessages.slice(0, 10).map(m => ({
    text: (m.message_text || "").slice(0, 250),
    channel: m.channel_name || m.channel_username,
    views: m.views,
    riskLabel: m.risk_label,
    riskScore: m.risk_score,
    riskFlags: m.risk_flags,
    date: m.message_timestamp,
  }));

  // Weekly message trend
  const weeklyTrend: { week: string; count: number; views: number }[] = [];
  const now = new Date();
  for (let w = 11; w >= 0; w--) {
    const ws = new Date(now.getTime() - w * 7 * 86400000);
    const we = new Date(ws.getTime() + 7 * 86400000);
    const wm = messages.filter(m => {
      const d = new Date(m.message_timestamp);
      return d >= ws && d < we;
    });
    weeklyTrend.push({
      week: `W${12 - w}`,
      count: wm.length,
      views: wm.reduce((s, m) => s + (m.views || 0), 0),
    });
  }

  const response = {
    live: true,
    stats: {
      totalChannels: channels.length,
      officialChannels: official.length,
      fanChannels: fan.length,
      suspiciousChannels: suspicious.length,
      totalMembers,
      totalMessages: messages.length,
      totalViews,
      totalForwards,
      suspiciousCount: suspiciousMessages.length,
      sentiment: {
        ...embSentiment,
        total: embStats.length,
        overall: embSentiment.positive > embSentiment.negative ? "Positive-leaning" : "Neutral",
        source: "llm-classified",
      },
    },
    channels: channelList,
    riskBreakdown,
    topMessages,
    suspiciousContent,
    weeklyTrend,
    rag: ragInsight ? {
      enabled: true,
      analysis: ragInsight.answer,
      confidence: ragInsight.confidence,
      mentionsUsed: ragInsight.metadata.mentionsAfterRerank,
      avgSimilarity: ragInsight.metadata.avgSimilarity,
      sentimentBreakdown: ragInsight.metadata.sentimentBreakdown,
    } : { enabled: false },
  };

  setCache("api:telegram", response);
  return NextResponse.json(response);
}
