import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

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

  const [autoRes, newsRes, trendsTimeRes, trendsRegionRes, serpRes] = await Promise.all([
    sb.from("google_autocomplete").select("*").in("brand_id", brandIds).order("scraped_at", { ascending: false }).limit(200),
    sb.from("google_news").select("*").in("brand_id", brandIds).order("scraped_at", { ascending: false }).limit(100),
    sb.from("google_trends").select("keyword, date, interest_value").in("brand_id", brandIds).not("date", "is", null).order("date", { ascending: true }).limit(500),
    sb.from("google_trends").select("keyword, region, region_interest").in("brand_id", brandIds).not("region", "is", null).order("region_interest", { ascending: false }).limit(200),
    sb.from("google_seo_results").select("query_text, organic_title, organic_snippet, organic_url, organic_position").in("brand_id", brandIds).order("organic_position", { ascending: true }).limit(100),
  ]);

  const autocomplete = autoRes.data || [];
  const news = newsRes.data || [];
  const trendsTime = trendsTimeRes.data || [];
  const trendsRegion = trendsRegionRes.data || [];
  const serp = serpRes.data || [];

  // Group SERP by query
  const serpByQuery: Record<string, any[]> = {};
  for (const r of serp) {
    if (!serpByQuery[r.query_text]) serpByQuery[r.query_text] = [];
    serpByQuery[r.query_text].push(r);
  }

  // Autocomplete stats
  const negSuggestions = autocomplete.filter(a => a.sentiment === "negative");
  const warnSuggestions = autocomplete.filter(a => a.sentiment === "warning");
  const uniqueSuggestions = Array.from(new Map(autocomplete.map(a => [a.suggestion, a])).values());

  // Group trends by date for chart
  const trendsByDate: Record<string, Record<string, number>> = {};
  for (const t of trendsTime) {
    if (!t.date) continue;
    if (!trendsByDate[t.date]) trendsByDate[t.date] = { date: t.date } as any;
    (trendsByDate[t.date] as any)[t.keyword] = t.interest_value;
  }
  const trendsChart = Object.values(trendsByDate).sort((a: any, b: any) => a.date.localeCompare(b.date));

  // Group regions by keyword
  const regionsByKeyword: Record<string, { region: string; interest: number }[]> = {};
  for (const t of trendsRegion) {
    if (!regionsByKeyword[t.keyword]) regionsByKeyword[t.keyword] = [];
    regionsByKeyword[t.keyword].push({ region: t.region, interest: t.region_interest });
  }

  // Unique news
  const uniqueNews = Array.from(new Map(news.map(n => [n.title, n])).values()).slice(0, 30);

  return NextResponse.json({
    live: true,
    stats: {
      totalAutocomplete: uniqueSuggestions.length,
      negativeAutocomplete: negSuggestions.length,
      warningAutocomplete: warnSuggestions.length,
      newsArticles: uniqueNews.length,
      trendsDataPoints: trendsChart.length,
      trendsRegions: Object.keys(regionsByKeyword).length > 0 ? trendsRegion.length : 0,
      serpResults: serp.length,
      serpQueries: Object.keys(serpByQuery).length,
    },
    autocomplete: uniqueSuggestions.slice(0, 50),
    negativeSuggestions: negSuggestions.slice(0, 20),
    news: uniqueNews,
    trendsChart,
    trendsRegions: regionsByKeyword,
    trendsKeywords: Array.from(new Set(trendsTime.map(t => t.keyword))),
    serp: serpByQuery,
    serpQueries: Object.keys(serpByQuery),
  });
}
