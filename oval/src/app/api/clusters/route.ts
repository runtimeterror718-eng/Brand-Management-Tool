import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const key = process.env.NEXT_PUBLIC_SUPABASE_KEY || "";

async function getBrandIds(sb: any): Promise<string[]> {
  const { data } = await sb.from("brands").select("id").eq("name", "PhysicsWallah");
  if (data?.length) return data.map((b: any) => b.id);
  const { data: any } = await sb.from("brands").select("id").limit(1);
  return any?.map((b: any) => b.id) || [];
}

export async function GET() {
  if (!url || !key) return NextResponse.json({ live: false });
  const sb = createClient(url, key);
  const brandIds = await getBrandIds(sb);
  if (!brandIds.length) return NextResponse.json({ live: false });

  const { data: clusters } = await sb
    .from("cluster_embeddings")
    .select("cluster_id, cluster_label, mention_count, avg_sentiment, platforms, representative_texts, summary")
    .in("brand_id", brandIds)
    .order("mention_count", { ascending: false });

  // Group by category
  const categories: Record<string, { clusters: any[]; total: number }> = {};
  for (const c of clusters || []) {
    const cat = c.cluster_label?.split(" — ")[0]?.split(":")[0] || "OTHER";
    if (!categories[cat]) categories[cat] = { clusters: [], total: 0 };
    categories[cat].clusters.push(c);
    categories[cat].total += c.mention_count;
  }

  const totalMentions = (clusters || []).reduce((s: number, c: any) => s + c.mention_count, 0);

  return NextResponse.json({
    live: true,
    totalMentions,
    clusterCount: clusters?.length || 0,
    clusters: clusters || [],
    categories: Object.entries(categories).map(([name, data]) => ({
      name,
      total: data.total,
      percentage: Math.round((data.total / Math.max(totalMentions, 1)) * 100),
      clusters: data.clusters,
    })).sort((a, b) => b.total - a.total),
  });
}
