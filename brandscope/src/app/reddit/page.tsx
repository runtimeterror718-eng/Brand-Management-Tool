"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { MessageCircle, ArrowUp, ExternalLink, Search } from "lucide-react";
import RAGInsight from "@/components/dashboard/rag-insight";
import IndiaMapComponent from "@/components/dashboard/india-map";
import { useLiveData } from "@/lib/use-live-data";
import { formatNumber, cn } from "@/lib/utils";
import { AnimatedChart, AnimatedNumber } from "@/components/ui/animated-chart";
import { MetricCard, MetricRow } from "@/components/ui/metric-card";
import { PageSkeleton } from "@/components/ui/page-skeleton";
import { stagger, fadeUp } from "@/lib/animations";

const ORANGE = "#FF5700";
const COLORS = { positive: "#639922", neutral: "#9CA3AF", negative: "#E24B4A" };

export default function RedditPage() {
  const { data: live, isLive, loading } = useLiveData<any>("/api/reddit", null);
  const [postFilter, setPostFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  if (loading) return <PageSkeleton title="Reddit Intelligence" color={ORANGE} />;

  const stats = live?.stats || {};
  const posts = live?.posts || [];
  const subreddits = live?.subredditBreakdown || [];
  const totalComments = live?.totalComments || 0;
  const posCount = stats.positiveCount || 0;
  const negCount = stats.negativeCount || 0;
  const neuCount = stats.neutralCount || 0;
  const embTotal = posCount + negCount + neuCount;

  const donutData = embTotal > 0 ? [
    { name: "Positive", value: posCount, color: COLORS.positive },
    { name: "Neutral", value: neuCount, color: COLORS.neutral },
    { name: "Negative", value: negCount, color: COLORS.negative },
  ] : [];

  const subChartData = subreddits.slice(0, 8).map((s: any) => ({ name: `r/${s.name}`, posts: s.count }));

  const filteredPosts = posts.filter((p: any) => {
    if (postFilter !== "all" && p.subreddit !== postFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (p.title || "").toLowerCase().includes(q) || (p.snippet || "").toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <motion.div className="max-w-6xl mx-auto px-4 py-6 space-y-6" variants={stagger} initial="hidden" animate="show">
      <motion.div variants={fadeUp}>
        <div className="flex items-center gap-3">
          <MessageCircle className="w-5 h-5" style={{ color: ORANGE }} />
          <h1 className="text-2xl font-bold tracking-tight">Reddit Intelligence</h1>
          {isLive && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Live</span>}
        </div>
        <p className="text-sm text-muted-foreground mt-0.5">What the anonymous internet really thinks about PW</p>
      </motion.div>

      <motion.div variants={fadeUp}>
        <MetricRow>
          <MetricCard label="Posts" value={stats.totalMentions || 0} color={ORANGE} />
          <MetricCard label="Comments" value={totalComments} />
          <MetricCard label="Analyzed" value={embTotal} sparkline={[30, 45, 38, 52, 48, 55, embTotal > 0 ? 60 : 0]} />
          <MetricCard label="Positive" value={posCount} color="#639922" trend={posCount > negCount ? 8 : -5} />
          <MetricCard label="Negative" value={negCount} color="#E24B4A" trend={negCount > posCount ? 12 : -3} />
          <motion.div whileHover={{ y: -2, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }} transition={{ duration: 0.2 }}
            className="rounded-xl border border-border bg-card p-3 cursor-default">
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Top Sub</p>
            <p className="text-sm font-bold mt-0.5">{stats.topSubreddit || "—"}</p>
          </motion.div>
        </MetricRow>
      </motion.div>

      {isLive && live?.rag?.enabled && (
        <motion.div variants={fadeUp}>
          <RAGInsight title="Reddit Analysis" analysis={live.rag.analysis} confidence={live.rag.confidence} mentionsUsed={live.rag.mentionsUsed} avgSimilarity={live.rag.avgSimilarity} sentimentBreakdown={live.rag.sentimentBreakdown} />
        </motion.div>
      )}

      {isLive && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {donutData.length > 0 && (
            <AnimatedChart delay={0} className="rounded-2xl border border-border bg-card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Sentiment Distribution</h3>
              <div className="flex items-center gap-6">
                <ResponsiveContainer width={160} height={160}>
                  <PieChart><Pie data={donutData} cx="50%" cy="50%" innerRadius={40} outerRadius={65} dataKey="value" animationDuration={1500} animationBegin={0}>
                    {donutData.map((d, i) => <Cell key={i} fill={d.color} strokeWidth={0} />)}
                  </Pie></PieChart>
                </ResponsiveContainer>
                <div className="space-y-2 text-sm">
                  {donutData.map(d => (
                    <div key={d.name} className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }} />
                      <span className="text-muted-foreground">{d.name}</span>
                      <span className="font-semibold ml-auto">{d.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </AnimatedChart>
          )}
          {subChartData.length > 0 && (
            <AnimatedChart delay={0.2} className="rounded-2xl border border-border bg-card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Subreddit Activity</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={subChartData} layout="vertical" margin={{ left: 80 }}>
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={75} />
                  <Tooltip />
                  <Bar dataKey="posts" radius={[0, 4, 4, 0]} barSize={14} animationDuration={1500}>
                    {subChartData.map((_: any, i: number) => <Cell key={i} fill={i === 0 ? ORANGE : i < 3 ? "#D85A30" : "#9CA3AF"} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </AnimatedChart>
          )}
        </div>
      )}

      <motion.div variants={fadeUp}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold">Posts ({filteredPosts.length})</h2>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input type="text" placeholder="Search posts..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                className="text-xs pl-7 pr-3 py-1.5 rounded-lg border border-border bg-card focus:outline-none focus:ring-1 focus:ring-purple-500 w-44" />
            </div>
            <select value={postFilter} onChange={(e) => setPostFilter(e.target.value)}
              className="text-xs px-2.5 py-1.5 rounded-lg border border-border bg-card focus:outline-none cursor-pointer">
              <option value="all">All Subreddits</option>
              {subreddits.map((s: any) => <option key={s.name} value={s.name}>r/{s.name} ({s.count})</option>)}
            </select>
          </div>
        </div>
        <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
          {filteredPosts.length === 0 && <p className="text-sm text-muted-foreground py-8 text-center">No posts match your filters</p>}
          {filteredPosts.map((post: any, i: number) => (
            <motion.div key={i} whileHover={{ y: -1, boxShadow: "0 4px 16px rgba(0,0,0,0.08)" }} transition={{ duration: 0.15 }}
              className="rounded-xl border border-border bg-card p-3.5 cursor-pointer">
              <div className="flex items-start gap-3">
                <div className="flex flex-col items-center shrink-0 pt-0.5">
                  <ArrowUp className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-sm font-bold" style={{ color: ORANGE }}>{post.upvotes}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded" style={{ backgroundColor: `${ORANGE}15`, color: ORANGE }}>r/{post.subreddit}</span>
                    <span className={cn("text-[10px] font-medium px-1.5 py-0.5 rounded", post.sentiment === "negative" ? "bg-red-100 text-red-600" : post.sentiment === "positive" ? "bg-green-100 text-green-600" : "bg-gray-100 text-gray-500")}>{post.sentiment}</span>
                  </div>
                  <p className="text-sm font-medium line-clamp-1">{post.title}</p>
                  {post.snippet && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{post.snippet}</p>}
                  <div className="flex items-center gap-3 mt-1.5 text-[10px] text-muted-foreground">
                    <span>{post.comments} comments</span>
                    {post.url && <a href={post.url} target="_blank" rel="noopener noreferrer" className="text-purple-600 hover:underline flex items-center gap-0.5 cursor-pointer">Open <ExternalLink className="w-2.5 h-2.5" /></a>}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      <motion.div variants={fadeUp}><IndiaMapComponent /></motion.div>

    </motion.div>
  );
}

