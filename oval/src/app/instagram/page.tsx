"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Camera, Heart, MessageCircle as Msg, Play, Search, ExternalLink, AlertTriangle } from "lucide-react";
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
        </div>
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

      {/* Overview Insight Cards */}
      {isLive && (
        <motion.div variants={fadeUp} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {/* Brand Health */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${PINK}15` }}>
                <Camera className="w-3.5 h-3.5" style={{ color: PINK }} />
              </span>
              <h4 className="text-xs font-bold">Brand Health</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {embTotal > 0 && (sentiment.positive || 0) > (sentiment.negative || 0)
                ? `Instagram is PW's safest platform with ${Math.round(((sentiment.positive || 0) / embTotal) * 100)}% positive sentiment. Fan content and student motivation reels drive engagement.`
                : `Sentiment is balanced. Monitor for emerging negative trends in comments.`}
            </p>
            <div className="flex gap-2 mt-2">
              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-green-100 text-green-700">{sentiment.positive || 0} positive</span>
              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700">{sentiment.negative || 0} negative</span>
            </div>
          </div>

          {/* Engagement */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-purple-100 dark:bg-purple-900/30">
                <Heart className="w-3.5 h-3.5 text-purple-600" />
              </span>
              <h4 className="text-xs font-bold">Engagement</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {formatNumber(stats.totalLikes || 0)} total likes across {stats.totalPosts || 0} posts.
              {(stats.totalReelPlays || 0) > 0 ? ` Reels dominate with ${formatNumber(stats.totalReelPlays)} plays — short-form video is the primary engagement driver.` : ""}
              {accounts.length > 0 ? ` Top performer: @${accounts[0]?.name} with ${formatNumber(accounts[0]?.totalLikes || 0)} likes.` : ""}
            </p>
          </div>

          {/* Comment Insights */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-amber-100 dark:bg-amber-900/30">
                <Msg className="w-3.5 h-3.5 text-amber-600" />
              </span>
              <h4 className="text-xs font-bold">Comment Signals</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {stats.storedComments
                ? `${formatNumber(stats.storedComments)} comments captured. Unlike curated captions, comments reveal real student sentiment — refund frustrations, teacher feedback, and app complaints surface here first.`
                : "No comment data available yet."}
            </p>
          </div>

          {/* Content Mix */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-blue-100 dark:bg-blue-900/30">
                <Play className="w-3.5 h-3.5 text-blue-600" />
              </span>
              <h4 className="text-xs font-bold">Content Mix</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {Object.entries(mediaTypes).length > 0
                ? Object.entries(mediaTypes).map(([type, count]) => `${count} ${type}s`).join(", ") + `. ${stats.totalHashtags || 0} unique hashtags tracked across all posts.`
                : "No content type data."}
            </p>
          </div>

          {/* Accounts Monitored */}
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-green-100 dark:bg-green-900/30">
                <Search className="w-3.5 h-3.5 text-green-600" />
              </span>
              <h4 className="text-xs font-bold">Monitoring Scope</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {accounts.length > 0
                ? `Tracking ${accounts.length} accounts: PW official, ${accounts.filter((a: any) => a.name !== "physicswallah").length} external (competitors, ex-PW teachers, fan pages, student influencers). 15 hashtag feeds monitored.`
                : "No accounts tracked."}
            </p>
          </div>

          {/* Key Warning */}
          <div className="rounded-xl border border-amber-200 dark:border-amber-800/40 bg-amber-50/30 dark:bg-amber-950/10 p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-amber-200 dark:bg-amber-900/50">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-700" />
              </span>
              <h4 className="text-xs font-bold text-amber-700 dark:text-amber-400">Watch Out</h4>
            </div>
            <p className="text-xs text-amber-700/80 dark:text-amber-400/80 leading-relaxed">
              Instagram sentiment looks positive, but this is the curated surface. The real complaints live in Reel audio and comment threads — not in captions. Cross-reference with Reddit for the full picture.
            </p>
          </div>
        </motion.div>
      )}

      {/* RAG Analysis */}
      {isLive && live?.rag?.enabled && (
        <motion.div variants={fadeUp}>
          <RAGInsight title="Instagram Analysis" analysis={live.rag.analysis} confidence={live.rag.confidence} mentionsUsed={live.rag.mentionsUsed} avgSimilarity={live.rag.avgSimilarity} sentimentBreakdown={live.rag.sentimentBreakdown} />
        </motion.div>
      )}

      {/* Monitored Accounts */}
      {accounts.length > 0 && (
        <motion.div variants={fadeUp}>
          <h2 className="text-sm font-bold mb-3">Monitored Accounts ({accounts.length})</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {accounts.map((acc: any, i: number) => (
              <div key={i} className="rounded-xl border border-border bg-card p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-bold" style={{ color: PINK }}>@{acc.name}</span>
                      {acc.isOfficial && <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">official</span>}
                      {!acc.isOfficial && <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">external</span>}
                    </div>
                    <p className="text-xs text-muted-foreground">{acc.bio || acc.category || "Instagram account"}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-base font-bold">{formatNumber(acc.followers || acc.totalLikes || 0)}</p>
                    <p className="text-[10px] text-muted-foreground">{acc.followers ? "followers" : "total likes"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                  <span>{acc.posts || 0} posts tracked</span>
                  {acc.totalLikes > 0 && <span>{formatNumber(acc.totalLikes)} likes</span>}
                  {acc.totalComments > 0 && <span>{formatNumber(acc.totalComments)} comments</span>}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Top Posts */}
      {topPosts.length > 0 && (
        <motion.div variants={fadeUp}>
          <h2 className="text-sm font-bold mb-3">Top Posts ({topPosts.length})</h2>
          <div className="space-y-2.5 max-h-[500px] overflow-y-auto pr-1">
            {topPosts.map((post: any, i: number) => (
              <div key={i} className="rounded-xl border border-border bg-card p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[9px] font-medium px-1.5 py-0.5 rounded" style={{ backgroundColor: `${PINK}15`, color: PINK }}>{post.mediaType}</span>
                      <span className="text-xs font-medium text-muted-foreground">@{post.account}</span>
                    </div>
                    <p className="text-sm font-semibold line-clamp-2 leading-snug">{post.caption || "(no caption)"}</p>
                    <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
                      <span className="flex items-center gap-1"><Heart className="w-3 h-3" />{formatNumber(post.likes)}</span>
                      <span className="flex items-center gap-1"><Msg className="w-3 h-3" />{post.comments}</span>
                      {post.reelPlays > 0 && <span className="flex items-center gap-1"><Play className="w-3 h-3" />{formatNumber(post.reelPlays)} plays</span>}
                      {post.url && (
                        <a href={post.url} target="_blank" rel="noopener noreferrer"
                          className="hover:underline cursor-pointer ml-auto flex items-center gap-0.5" style={{ color: PINK }}>
                          View <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Comments */}
      {topComments.length > 0 && (
        <motion.div variants={fadeUp}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-bold">Comments ({filteredComments.length})</h2>
            <div className="relative">
              <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input type="text" placeholder="Search comments..." value={commentSearch} onChange={(e) => setCommentSearch(e.target.value)}
                className="text-xs pl-7 pr-3 py-1.5 rounded-lg border border-border bg-card focus:outline-none focus:ring-1 focus:ring-pink-500 w-48" />
            </div>
          </div>
          <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
            {filteredComments.map((c: any, i: number) => (
              <div key={i} className="rounded-xl border border-border bg-card p-3 hover:shadow-sm transition-shadow">
                <p className="text-sm text-foreground/80 italic leading-relaxed">&ldquo;{c.text}&rdquo;</p>
                <div className="flex items-center gap-2 mt-1.5">
                  <p className="text-[10px] text-muted-foreground font-medium">— @{c.author}</p>
                  {c.likes > 0 && <span className="text-[10px] text-muted-foreground">| {c.likes} likes</span>}
                  {c.sentiment && (
                    <span className={cn("text-[9px] font-medium px-1.5 py-0.5 rounded ml-auto",
                      c.sentiment === "negative" ? "bg-red-100 text-red-600" :
                      c.sentiment === "positive" ? "bg-green-100 text-green-600" :
                      "bg-gray-100 text-gray-500"
                    )}>{c.sentiment}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

    </motion.div>
  );
}
