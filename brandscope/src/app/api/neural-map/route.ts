import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { getCached, setCache } from "@/lib/api-cache";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.SUPABASE_SERVICE_KEY || process.env.NEXT_PUBLIC_SUPABASE_KEY || "";

interface Node { id: string; label: string; group: string; size: number; color: string; metadata?: any }
interface Link { source: string; target: string; label: string; strength: number; sentiment: "positive" | "negative" | "neutral" | "mixed"; mentions: number }

const COMPETITORS = ["Allen", "Unacademy", "BYJU", "Aakash", "Vedantu"];
const TOPICS = [
  { keywords: ["refund", "cancel", "money back", "payment"], label: "Refund & Cancellation" },
  { keywords: ["teacher", "faculty", "sir", "mam", "left pw", "quit"], label: "Teacher Quality" },
  { keywords: ["scam", "fraud", "loot", "waste", "byju"], label: "Scam Narrative" },
  { keywords: ["app", "crash", "bug", "glitch", "slow"], label: "App Issues" },
  { keywords: ["ipo", "stock", "valuation", "crore", "billionaire"], label: "IPO & Business" },
  { keywords: ["interview", "sell pen", "salary", "job", "hiring"], label: "Employer Brand" },
  { keywords: ["reservation", "caste", "political", "bjp"], label: "Political" },
  { keywords: ["vidyapeeth", "offline", "centre", "kota"], label: "Offline Centres" },
  { keywords: ["pw skills", "placement", "devops", "data science"], label: "PW Skills" },
  { keywords: ["arjuna", "lakshya", "yakeen", "udaan", "batch"], label: "Batches & Courses" },
];
const PEOPLE = [
  { keywords: ["alakh pandey", "alakh sir", "alakhpandey"], label: "Alakh Pandey" },
  { keywords: ["rajwant", "rj sir"], label: "Rajwant Sir" },
  { keywords: ["saleem sir"], label: "Saleem Sir" },
  { keywords: ["prateek"], label: "Prateek Maheshwari" },
];
const GROUP_COLORS: Record<string, string> = {
  brand: "#534AB7", competitor: "#E24B4A", platform: "#378ADD", topic: "#BA7517",
  person: "#1D9E75", channel: "#D4537E", cluster: "#9CA3AF",
};

export async function GET() {
  const cached = getCached<any>("api:neural-map");
  if (cached) return NextResponse.json(cached);

  if (!url || !key) return NextResponse.json({ nodes: [], links: [] });
  const sb = createClient(url, key);

  const [mentionsRes, ytChannelsRes, tgChannelsRes, clustersRes] = await Promise.all([
    sb.from("mention_embeddings").select("content_text, platform, sentiment_label").not("content_text", "is", null).limit(2000),
    sb.from("youtube_channels").select("channel_name, channel_subscribers").order("channel_subscribers", { ascending: false }).limit(20),
    sb.from("telegram_channels").select("channel_username, channel_title, classification_label, participants_count, is_fake").order("participants_count", { ascending: false }),
    sb.from("cluster_embeddings").select("cluster_label, mention_count, platforms").order("mention_count", { ascending: false }).limit(15),
  ]);

  const mentions = mentionsRes.data || [];
  const ytChannels = ytChannelsRes.data || [];
  const tgChannels = tgChannelsRes.data || [];
  const clusters = clustersRes.data || [];

  const nodes: Node[] = [];
  const links: Link[] = [];
  const linkMap = new Map<string, Link>();

  function addLink(src: string, tgt: string, label: string, sentiment: string) {
    const key = [src, tgt].sort().join("||");
    const existing = linkMap.get(key);
    if (existing) {
      existing.mentions++;
      existing.strength = Math.min(existing.strength + 0.3, 10);
      if (sentiment === "negative" && existing.sentiment !== "negative") existing.sentiment = "mixed";
      if (sentiment === "positive" && existing.sentiment !== "positive") existing.sentiment = "mixed";
    } else {
      const link: Link = { source: src, target: tgt, label, strength: 1, sentiment: sentiment as any, mentions: 1 };
      linkMap.set(key, link);
    }
  }

  // ── Node: PW (center) ──
  nodes.push({ id: "pw", label: "Physics Wallah", group: "brand", size: 30, color: GROUP_COLORS.brand });

  // ── Nodes: Platforms ──
  const platformCounts: Record<string, { total: number; neg: number; pos: number }> = {};
  for (const m of mentions) {
    const p = m.platform || "unknown";
    if (!platformCounts[p]) platformCounts[p] = { total: 0, neg: 0, pos: 0 };
    platformCounts[p].total++;
    if (m.sentiment_label === "negative") platformCounts[p].neg++;
    if (m.sentiment_label === "positive") platformCounts[p].pos++;
  }
  for (const [platform, counts] of Object.entries(platformCounts)) {
    nodes.push({ id: `platform:${platform}`, label: platform.charAt(0).toUpperCase() + platform.slice(1), group: "platform", size: 8 + Math.sqrt(counts.total) * 2, color: GROUP_COLORS.platform, metadata: counts });
    addLink("pw", `platform:${platform}`, `${counts.total} mentions`, counts.neg > counts.pos ? "negative" : counts.pos > counts.neg ? "positive" : "neutral");
  }

  // ── Nodes: Competitors ──
  for (const comp of COMPETITORS) {
    let compMentions = 0; let compNeg = 0; let compPos = 0;
    for (const m of mentions) {
      if ((m.content_text || "").toLowerCase().includes(comp.toLowerCase())) {
        compMentions++;
        if (m.sentiment_label === "negative") compNeg++;
        if (m.sentiment_label === "positive") compPos++;
      }
    }
    if (compMentions > 0) {
      nodes.push({ id: `comp:${comp}`, label: comp, group: "competitor", size: 6 + compMentions * 1.5, color: GROUP_COLORS.competitor, metadata: { mentions: compMentions, negative: compNeg, positive: compPos } });
      addLink("pw", `comp:${comp}`, `${compMentions} comparisons`, compNeg > compPos ? "negative" : "mixed");
    }
  }

  // ── Nodes: Topics ──
  for (const topic of TOPICS) {
    let topicMentions = 0; let topicNeg = 0;
    const topicPlatforms: Record<string, number> = {};
    for (const m of mentions) {
      const text = (m.content_text || "").toLowerCase();
      if (topic.keywords.some(kw => text.includes(kw))) {
        topicMentions++;
        if (m.sentiment_label === "negative") topicNeg++;
        const p = m.platform || "unknown";
        topicPlatforms[p] = (topicPlatforms[p] || 0) + 1;
      }
    }
    if (topicMentions >= 3) {
      const negPct = topicMentions > 0 ? topicNeg / topicMentions : 0;
      nodes.push({ id: `topic:${topic.label}`, label: topic.label, group: "topic", size: 5 + Math.sqrt(topicMentions) * 2, color: GROUP_COLORS.topic, metadata: { mentions: topicMentions, negPct: Math.round(negPct * 100) } });
      addLink("pw", `topic:${topic.label}`, `${topicMentions} mentions`, negPct > 0.4 ? "negative" : negPct > 0.2 ? "mixed" : "neutral");

      // Connect topics to platforms
      for (const [platform, count] of Object.entries(topicPlatforms)) {
        if (count >= 2) addLink(`topic:${topic.label}`, `platform:${platform}`, `${count}`, "neutral");
      }

      // Connect topics to competitors if co-mentioned
      for (const comp of COMPETITORS) {
        let coMentions = 0;
        for (const m of mentions) {
          const text = (m.content_text || "").toLowerCase();
          if (topic.keywords.some(kw => text.includes(kw)) && text.includes(comp.toLowerCase())) coMentions++;
        }
        if (coMentions >= 2) addLink(`topic:${topic.label}`, `comp:${comp}`, `${coMentions}`, "negative");
      }
    }
  }

  // ── Nodes: People ──
  for (const person of PEOPLE) {
    let personMentions = 0; let personPos = 0;
    for (const m of mentions) {
      const text = (m.content_text || "").toLowerCase();
      if (person.keywords.some(kw => text.includes(kw))) {
        personMentions++;
        if (m.sentiment_label === "positive") personPos++;
      }
    }
    if (personMentions >= 3) {
      nodes.push({ id: `person:${person.label}`, label: person.label, group: "person", size: 5 + Math.sqrt(personMentions) * 1.5, color: GROUP_COLORS.person, metadata: { mentions: personMentions, positivePct: Math.round((personPos / personMentions) * 100) } });
      addLink("pw", `person:${person.label}`, `${personMentions}`, personPos > personMentions / 2 ? "positive" : "mixed");
    }
  }

  // ── Nodes: YouTube Channels ──
  for (const ch of ytChannels.slice(0, 8)) {
    if (!ch.channel_name) continue;
    nodes.push({ id: `yt:${ch.channel_name}`, label: ch.channel_name, group: "channel", size: 4 + Math.sqrt(ch.channel_subscribers || 0) * 0.02, color: "#FF0000", metadata: { subscribers: ch.channel_subscribers } });
    addLink(`platform:youtube`, `yt:${ch.channel_name}`, "channel", "neutral");
  }

  // ── Nodes: Telegram Channels ──
  for (const ch of tgChannels.slice(0, 8)) {
    const label = ch.channel_title || ch.channel_username;
    if (!label) continue;
    nodes.push({ id: `tg:${ch.channel_username}`, label, group: "channel", size: 4 + Math.sqrt(ch.participants_count || 0) * 0.01, color: ch.is_fake ? "#E24B4A" : "#0088CC", metadata: { members: ch.participants_count, isFake: ch.is_fake, label: ch.classification_label } });
    addLink(`platform:telegram`, `tg:${ch.channel_username}`, ch.classification_label || "", ch.is_fake ? "negative" : "neutral");
  }

  // ── Nodes: Top Clusters ──
  for (const cl of clusters.slice(0, 8)) {
    const shortLabel = (cl.cluster_label || "").split("—")[0].trim().slice(0, 25);
    nodes.push({ id: `cluster:${cl.cluster_label}`, label: shortLabel, group: "cluster", size: 4 + Math.sqrt(cl.mention_count) * 1.2, color: GROUP_COLORS.cluster, metadata: { mentions: cl.mention_count, platforms: cl.platforms } });
    // Connect to platforms
    for (const [p, count] of Object.entries(cl.platforms || {})) {
      if ((count as number) >= 3) addLink(`cluster:${cl.cluster_label}`, `platform:${p}`, `${count}`, "neutral");
    }
  }

  for (const link of linkMap.values()) links.push(link);

  const response = {
    nodes,
    links,
    stats: {
      totalNodes: nodes.length,
      totalLinks: links.length,
      groups: {
        brand: nodes.filter(n => n.group === "brand").length,
        platform: nodes.filter(n => n.group === "platform").length,
        competitor: nodes.filter(n => n.group === "competitor").length,
        topic: nodes.filter(n => n.group === "topic").length,
        person: nodes.filter(n => n.group === "person").length,
        channel: nodes.filter(n => n.group === "channel").length,
        cluster: nodes.filter(n => n.group === "cluster").length,
      },
    },
  };

  setCache("api:neural-map", response, 10 * 60 * 1000);
  return NextResponse.json(response);
}
