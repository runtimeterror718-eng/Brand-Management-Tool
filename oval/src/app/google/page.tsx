"use client";

import { motion } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, BarChart, Bar, Cell } from "recharts";
import { Search, Globe, ExternalLink, AlertTriangle, TrendingUp, Newspaper, Eye } from "lucide-react";
import { useLiveData } from "@/lib/use-live-data";
import { formatNumber, cn } from "@/lib/utils";
import { AnimatedChart, AnimatedNumber } from "@/components/ui/animated-chart";
import { PageSkeleton } from "@/components/ui/page-skeleton";
import { stagger, fadeUp } from "@/lib/animations";

const TREND_COLORS: Record<string, string> = { "Physics Wallah": "#534AB7", "Allen Career Institute": "#1D9E75", "Unacademy": "#378ADD", "BYJU'S": "#9CA3AF" };

export default function GooglePage() {
  const { data: live, isLive, loading } = useLiveData<any>("/api/google", null);

  if (loading) return <PageSkeleton title="Google Intelligence" color="#4285F4" />;
  const stats = live?.stats || {};
  const autocomplete = live?.autocomplete || [];
  const negativeSuggestions = live?.negativeSuggestions || [];
  const trendsChart = live?.trendsChart || [];
  const trendsKeywords = live?.trendsKeywords || [];
  const trendsRegions = live?.trendsRegions || {};
  const serp = live?.serp || {};
  const serpQueries = live?.serpQueries || [];
  const news = live?.news || [];
  const negCount = stats.negativeAutocomplete || 0;
  const regionData = (trendsRegions?.["Physics Wallah"] || []).slice(0, 12);

  return (
    <motion.div className="max-w-6xl mx-auto px-4 py-6 space-y-6" variants={stagger} initial="hidden" animate="show">
      <motion.div variants={fadeUp}>
        <div className="flex items-center gap-3"><Globe className="w-5 h-5 text-[#4285F4]" /><h1 className="text-2xl font-bold tracking-tight">Google Intelligence</h1>
        </div><p className="text-sm text-muted-foreground mt-0.5">What Google shows when someone searches for your brand</p>
      </motion.div>

      <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
        {[{l:"Autocomplete",v:stats.totalAutocomplete||0,s:`${negCount} negative`},{l:"News",v:stats.newsArticles||0},{l:"SERP Queries",v:stats.serpQueries||0},{l:"Trends",v:stats.trendsDataPoints||0},{l:"Regions",v:stats.trendsRegions||0}].map((m,i)=>(
          <div key={i} className="rounded-xl border border-border bg-card p-3"><p className="text-[10px] text-muted-foreground uppercase tracking-widest">{m.l}</p><p className="text-xl font-bold mt-0.5"><AnimatedNumber value={typeof m.v==="number"?m.v:0}/></p>{m.s&&<p className="text-[10px] text-red-500">{m.s}</p>}</div>
        ))}
      </motion.div>

      {autocomplete.length > 0 && (
        <AnimatedChart delay={0} className="rounded-2xl border border-amber-200 dark:border-amber-800 bg-amber-50/30 dark:bg-amber-950/10 p-4">
          <div className="flex items-center gap-2 mb-3"><Search className="w-4 h-4 text-amber-600" /><h3 className="text-xs font-semibold uppercase tracking-widest text-amber-700 dark:text-amber-400">Autocomplete Audit</h3></div>
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
            <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-100 dark:border-gray-800"><div className="w-4 h-4 rounded-full bg-[#4285F4] flex items-center justify-center"><span className="text-white text-[8px] font-bold">G</span></div><span className="text-sm text-gray-400">physics wallah</span></div>
            <div className="space-y-0.5 max-h-[200px] overflow-y-auto">{autocomplete.slice(0, 12).map((a: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-sm py-1 px-1.5 rounded hover:bg-gray-50 dark:hover:bg-gray-800"><Search className="w-3 h-3 text-gray-300 shrink-0" /><span className="flex-1">{a.suggestion || a.highlight}</span>
                {(a.sentiment === "negative" || a.sentiment === "warning") && <span className={cn("text-[9px] px-1 py-0.5 rounded shrink-0", a.sentiment === "negative" ? "bg-red-100 text-red-500" : "bg-amber-100 text-amber-600")}>{a.sentiment}</span>}
              </div>
            ))}</div>
          </div>
        </AnimatedChart>
      )}

      {/* Insight Cards */}
      {isLive && (
        <motion.div variants={fadeUp} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-blue-100 dark:bg-blue-900/30"><Search className="w-3.5 h-3.5 text-blue-600" /></span>
              <h4 className="text-xs font-bold">Autocomplete Audit</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {stats.totalAutocomplete || 0} suggestions scanned (including full a-z alphabet expansion).
              {negCount > 0 ? ` ${negCount} suggestions are negative — including "scam", "fraud", "refund". These appear to every parent searching for PW.` : " No negative suggestions detected."}
              {` ${stats.warningAutocomplete || 0} warning-level suggestions ("review", "comparison", "alternative").`}
            </p>
          </div>

          <div className="rounded-xl border border-red-200 dark:border-red-800/40 bg-red-50/20 dark:bg-red-950/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-red-200 dark:bg-red-900/50"><AlertTriangle className="w-3.5 h-3.5 text-red-700" /></span>
              <h4 className="text-xs font-bold text-red-700 dark:text-red-400">Enrollment Risk</h4>
            </div>
            <p className="text-xs text-red-700/80 dark:text-red-400/80 leading-relaxed">
              Google autocomplete is PW's front door. When a parent types "physics wallah" and sees "scam" as the first suggestion, they never visit your website. This directly impacts enrollment.
              {negCount > 0 ? ` Currently ${Math.round((negCount / Math.max(stats.totalAutocomplete || 1, 1)) * 100)}% of suggestions carry negative sentiment.` : ""}
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-green-100 dark:bg-green-900/30"><TrendingUp className="w-3.5 h-3.5 text-green-600" /></span>
              <h4 className="text-xs font-bold">Trends vs Competitors</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {stats.trendsDataPoints || 0} data points across 90 days. Tracking PW against Allen, Unacademy, and BYJU's.
              {stats.trendsRegions ? ` Search interest mapped across ${stats.trendsRegions} Indian regions — reveals where PW is strong and where competitors dominate.` : ""}
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-purple-100 dark:bg-purple-900/30"><Eye className="w-3.5 h-3.5 text-purple-600" /></span>
              <h4 className="text-xs font-bold">SERP Position</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {stats.serpQueries || 0} queries tracked across brand, risk, and competitor searches.
              {stats.serpResults ? ` ${stats.serpResults} organic results captured. ` : " "}
              When a consumer court article ranks #3 for "physics wallah" — that's a crisis. OVAL tracks what Google shows for every key query.
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-amber-100 dark:bg-amber-900/30"><Newspaper className="w-3.5 h-3.5 text-amber-600" /></span>
              <h4 className="text-xs font-bold">News Radar</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {stats.newsArticles || 0} news articles tracked from Google News RSS.
              Monitoring "Physics Wallah", "Alakh Pandey", "PW IPO", and "edtech scam India". Negative articles from publications like LawChakra, DNA, or Economic Times need immediate PR response.
            </p>
          </div>

          <div className="rounded-xl border border-amber-200 dark:border-amber-800/40 bg-amber-50/30 dark:bg-amber-950/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-amber-200 dark:bg-amber-900/50"><Globe className="w-3.5 h-3.5 text-amber-700" /></span>
              <h4 className="text-xs font-bold text-amber-700 dark:text-amber-400">Why Google Matters Most</h4>
            </div>
            <p className="text-xs text-amber-700/80 dark:text-amber-400/80 leading-relaxed">
              Google is the last touchpoint before enrollment. Reddit creates narratives, Instagram amplifies them, but Google is where parents make the decision. If autocomplete shows "scam" — game over. OVAL monitors this in real-time.
            </p>
          </div>
        </motion.div>
      )}

      {negativeSuggestions?.length > 0 && (
        <motion.div variants={fadeUp} className="rounded-2xl border border-border bg-card p-5">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">Negative & Warning Suggestions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">{negativeSuggestions.map((s: any, i: number) => (
            <div key={i} className="flex items-center gap-2 rounded-lg border border-border p-2"><span className={cn("text-[9px] font-medium px-1 py-0.5 rounded", s.sentiment === "negative" ? "bg-red-100 text-red-600" : "bg-amber-100 text-amber-600")}>{s.sentiment}</span><span className="text-sm">{s.suggestion}</span></div>
          ))}</div>
        </motion.div>
      )}

      {trendsChart.length > 0 && (
        <AnimatedChart delay={0.2} className="rounded-2xl border border-border bg-card p-5">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Search Interest — PW vs Competitors (3 months)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={trendsChart}><CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" /><XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(d: string) => d.slice(5)} /><YAxis tick={{ fontSize: 11 }} domain={[0, 100]} /><Tooltip /><Legend />
              {(trendsKeywords || []).map((kw: string) => <Line key={kw} type="monotone" dataKey={kw} stroke={TREND_COLORS[kw] || "#9CA3AF"} strokeWidth={2} dot={false} animationDuration={1800} />)}
            </LineChart>
          </ResponsiveContainer>
        </AnimatedChart>
      )}

      {regionData.length > 0 && (
        <AnimatedChart delay={0.3} className="rounded-2xl border border-border bg-card p-5">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Search Interest by Indian State</h3>
          <ResponsiveContainer width="100%" height={350}><BarChart data={regionData} layout="vertical" margin={{ left: 110 }}><CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" /><XAxis type="number" tick={{ fontSize: 11 }} domain={[0, 100]} /><YAxis type="category" dataKey="region" tick={{ fontSize: 11 }} width={105} /><Tooltip /><Bar dataKey="interest" radius={[0, 4, 4, 0]} barSize={14} animationDuration={1500}>
            {regionData.map((e: any, i: number) => <Cell key={i} fill={e.interest > 70 ? "#534AB7" : e.interest > 40 ? "#378ADD" : "#9CA3AF"} />)}
          </Bar></BarChart></ResponsiveContainer>
        </AnimatedChart>
      )}

      {serpQueries.length > 0 && (<motion.div variants={fadeUp}><h2 className="text-sm font-semibold mb-3">Search Results</h2><div className="space-y-4 max-h-[500px] overflow-y-auto">{serpQueries.map((query: string) => (<div key={query} className="rounded-2xl border border-border bg-card p-4"><h4 className="text-sm font-semibold mb-2"><span className="text-[#4285F4]">Search:</span> &ldquo;{query}&rdquo;</h4><div className="space-y-2">{(serp[query] || []).slice(0, 5).map((r: any, i: number) => (<div key={i} className="flex gap-2 text-sm"><span className="text-[10px] text-muted-foreground font-mono w-5 shrink-0">#{r.organic_position}</span><div className="flex-1"><a href={r.organic_url} target="_blank" rel="noopener noreferrer" className="text-[#4285F4] hover:underline cursor-pointer font-medium">{r.organic_title}</a><p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{r.organic_snippet}</p></div></div>))}</div></div>))}</div></motion.div>)}

      {news.length > 0 && (<motion.div variants={fadeUp}><h2 className="text-sm font-semibold mb-3">Latest News ({news.length})</h2><div className="space-y-1.5 max-h-[350px] overflow-y-auto">{news.slice(0, 20).map((n: any, i: number) => (<div key={i} className="rounded-lg border border-border p-2.5 hover:shadow-md transition-shadow cursor-pointer"><div className="flex items-center justify-between mb-0.5"><span className="text-[10px] text-muted-foreground">{n.source || "Unknown"}</span><span className="text-[10px] text-muted-foreground">{n.published?.slice(0, 16)}</span></div><p className="text-sm font-medium">{n.title}</p>{n.url && <a href={n.url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-[#4285F4] hover:underline cursor-pointer mt-0.5 inline-flex items-center gap-0.5">Read <ExternalLink className="w-2.5 h-2.5" /></a>}</div>))}</div></motion.div>)}
    </motion.div>
  );
}
