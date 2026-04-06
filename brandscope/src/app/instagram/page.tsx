"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Camera, Heart, MessageCircle as Msg, Play, Search, ExternalLink } from "lucide-react";
import RAGInsight from "@/components/dashboard/rag-insight";
import { useLiveData } from "@/lib/use-live-data";
import { formatNumber, cn } from "@/lib/utils";
import { AnimatedChart, AnimatedNumber } from "@/components/ui/animated-chart";
import { PageSkeleton } from "@/components/ui/page-skeleton";
import { stagger, fadeUp } from "@/lib/animations";

const PINK = "#E1306C";
const COLORS = { positive: "#639922", neutral: "#9CA3AF", negative: "#E24B4A" };
const MEDIA_COLORS: Record<string, string> = { reel: "#D4537E", video: "#534AB7", image: "#1D9E75", carousel: "#378ADD", unknown: "#9CA3AF" };

export default function InstagramPage() {
  const { data: live, isLive, loading } = useLiveData<any>("/api/instagram", null);
  const [commentSearch, setCommentSearch] = useState("");

  if (loading) return <PageSkeleton title="Instagram Intelligence" color="#E1306C" />;

  const stats = live?.stats || {};
  const sentiment = stats.sentiment || {};
  const hashtags = live?.topHashtags || [];
  const accounts = live?.topAccounts || [];
  const topPosts = live?.topPosts || [];
  const topComments = live?.topComments || [];
  const mediaTypes = live?.mediaTypes || {};

  const embTotal = (sentiment.positive || 0) + (sentiment.negative || 0) + (sentiment.neutral || 0);
  const donutData = embTotal > 0 ? [
    { name: "Positive", value: sentiment.positive, color: COLORS.positive },
    { name: "Neutral", value: sentiment.neutral, color: COLORS.neutral },
    { name: "Negative", value: sentiment.negative, color: COLORS.negative },
  ] : [];
  const mediaData = Object.entries(mediaTypes).map(([name, value]) => ({ name, value: value as number }));
  const hashtagData = hashtags.slice(0, 8).map((h: any) => ({ name: h.tag, posts: h.posts }));

  const filteredComments = commentSearch
    ? topComments.filter((c: any) => (c.text || "").toLowerCase().includes(commentSearch.toLowerCase()))
    : topComments;

  return (
    <motion.div className="max-w-6xl mx-auto px-4 py-6 space-y-6" variants={stagger} initial="hidden" animate="show">
      <motion.div variants={fadeUp}>
        <div className="flex items-center gap-3">
          <Camera className="w-5 h-5" style={{ color: PINK }} />
          <h1 className="text-2xl font-bold tracking-tight">Instagram Intelligence</h1>
          {isLive && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Live — {stats.totalPosts} posts</span>}
        </div>
        <p className="text-sm text-muted-foreground mt-0.5">The curated surface of brand perception</p>
      </motion.div>

      <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {[
          { l: "Posts", v: stats.totalPosts || 0, c: PINK },
          { l: "Likes", v: stats.totalLikes || 0 },
          { l: "Comments", v: stats.totalComments || 0 },
          { l: "Reel Plays", v: stats.totalReelPlays || 0 },
          { l: "Hashtags", v: stats.totalHashtags || 0 },
          { l: "Stored", v: stats.storedComments || 0 },
        ].map((m, i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-3">
            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">{m.l}</p>
            <p className="text-xl font-bold mt-0.5" style={{ color: m.c }}><AnimatedNumber value={typeof m.v === "number" ? m.v : 0} /></p>
          </div>
        ))}
      </motion.div>

      {isLive && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {donutData.length > 0 && (
            <AnimatedChart delay={0} className="rounded-2xl border border-border bg-card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Sentiment</h3>
              <div className="flex items-center gap-4">
                <ResponsiveContainer width={130} height={130}>
                  <PieChart><Pie data={donutData} cx="50%" cy="50%" innerRadius={35} outerRadius={55} dataKey="value" animationDuration={1500}>
                    {donutData.map((d, i) => <Cell key={i} fill={d.color} strokeWidth={0} />)}
                  </Pie></PieChart>
                </ResponsiveContainer>
                <div className="space-y-1.5 text-sm">
                  {donutData.map(d => <div key={d.name} className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.color }} /><span className="text-muted-foreground text-xs">{d.name}: {d.value}</span></div>)}
                </div>
              </div>
            </AnimatedChart>
          )}
          {mediaData.length > 0 && (
            <AnimatedChart delay={0.15} className="rounded-2xl border border-border bg-card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Content Types</h3>
              <ResponsiveContainer width="100%" height={130}>
                <BarChart data={mediaData} layout="vertical" margin={{ left: 60 }}>
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={16} animationDuration={1500}>
                    {mediaData.map((e: any) => <Cell key={e.name} fill={MEDIA_COLORS[e.name] || "#9CA3AF"} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </AnimatedChart>
          )}
          {hashtagData.length > 0 && (
            <AnimatedChart delay={0.3} className="rounded-2xl border border-border bg-card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Top Hashtags</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={hashtagData} layout="vertical" margin={{ left: 90 }}>
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={85} />
                  <Tooltip />
                  <Bar dataKey="posts" radius={[0, 4, 4, 0]} barSize={12} fill={PINK} animationDuration={1500} />
                </BarChart>
              </ResponsiveContainer>
            </AnimatedChart>
          )}
        </div>
      )}

      {topPosts.length > 0 && (
        <motion.div variants={fadeUp}>
          <h2 className="text-sm font-semibold mb-3">Top Posts ({topPosts.length})</h2>
          <div className="space-y-2 max-h-[400px] overflow-y-auto">
            {topPosts.map((post: any, i: number) => (
              <div key={i} className="rounded-xl border border-border bg-card p-3.5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded" style={{ backgroundColor: `${PINK}15`, color: PINK }}>{post.mediaType}</span>
                    <span className="text-xs text-muted-foreground">@{post.account}</span>
                  </div>
                  <div className="flex gap-3 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-0.5"><Heart className="w-3 h-3" />{formatNumber(post.likes)}</span>
                    <span className="flex items-center gap-0.5"><Msg className="w-3 h-3" />{post.comments}</span>
                    {post.reelPlays > 0 && <span className="flex items-center gap-0.5"><Play className="w-3 h-3" />{formatNumber(post.reelPlays)}</span>}
                  </div>
                </div>
                <p className="text-sm line-clamp-2">{post.caption || "(no caption)"}</p>
                {post.url && <a href={post.url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-pink-600 hover:underline mt-1 inline-flex items-center gap-0.5 cursor-pointer">View <ExternalLink className="w-2.5 h-2.5" /></a>}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {topComments.length > 0 && (
        <motion.div variants={fadeUp}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold">Comments ({filteredComments.length})</h2>
            <div className="relative"><Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input type="text" placeholder="Search comments..." value={commentSearch} onChange={(e) => setCommentSearch(e.target.value)}
                className="text-xs pl-7 pr-3 py-1.5 rounded-lg border border-border bg-card focus:outline-none focus:ring-1 focus:ring-pink-500 w-48" />
            </div>
          </div>
          <div className="space-y-1.5 max-h-[350px] overflow-y-auto">
            {filteredComments.map((c: any, i: number) => (
              <div key={i} className="rounded-lg border border-border p-2.5 text-sm">
                <p className="text-foreground/80 italic">&ldquo;{c.text}&rdquo;</p>
                <p className="text-[10px] text-muted-foreground mt-1">— @{c.author}</p>
              </div>
            ))}
          </div>
        </motion.div>
      )}

    </motion.div>
  );
}
