"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Play, ExternalLink, Search, AlertTriangle, Eye, Users, Shield, TrendingUp } from "lucide-react";
import RAGInsight from "@/components/dashboard/rag-insight";
import { useLiveData } from "@/lib/use-live-data";
import { formatNumber, cn } from "@/lib/utils";
import { AnimatedChart, AnimatedNumber } from "@/components/ui/animated-chart";
import { PageSkeleton } from "@/components/ui/page-skeleton";
import { stagger, fadeUp } from "@/lib/animations";

const COLORS = { positive: "#639922", neutral: "#9CA3AF", negative: "#E24B4A" };

export default function YouTubePage() {
  const { data: live, isLive, loading } = useLiveData<any>("/api/youtube", null);
  const [searchQuery, setSearchQuery] = useState("");

  if (loading) return <PageSkeleton title="YouTube Intelligence" color="#FF0000" />;
  const stats = live?.stats || {};
  const sentiment = stats.sentiment || {};
  const videos = live?.videos || [];
  const channels = live?.channels || [];
  const comments = live?.topComments || [];
  const prRisks = live?.prRiskVideos || [];
  const embTotal = (sentiment.positive || 0) + (sentiment.negative || 0) + (sentiment.neutral || 0);
  const donutData = embTotal > 0 ? [
    { name: "Positive", value: sentiment.positive, color: COLORS.positive },
    { name: "Neutral", value: sentiment.neutral, color: COLORS.neutral },
    { name: "Negative", value: sentiment.negative, color: COLORS.negative },
  ] : [];
  const channelData = channels.slice(0, 8).map((c: any) => ({ name: (c.name || "").slice(0, 18), subs: c.subscribers }));
  const filteredVideos = searchQuery ? videos.filter((v: any) => (v.title || "").toLowerCase().includes(searchQuery.toLowerCase())) : videos;

  // Group videos by triage label for structured display
  const videosByTheme: Record<string, any[]> = {};
  for (const v of filteredVideos) {
    const label = v.isPrRisk
      ? "PR Risk"
      : v.triageLabel === "negative" ? "Negative"
      : v.triageLabel === "positive" ? "Positive"
      : v.triageLabel === "uncertain" ? "Uncertain"
      : "Unclassified";
    if (!videosByTheme[label]) videosByTheme[label] = [];
    videosByTheme[label].push(v);
  }
  const themeOrder = ["PR Risk", "Negative", "Uncertain", "Positive", "Unclassified"];
  const themeColors: Record<string, { bg: string; text: string; border: string; icon: string }> = {
    "PR Risk": { bg: "bg-red-50/40 dark:bg-red-950/15", text: "text-red-700 dark:text-red-400", border: "border-red-200 dark:border-red-800", icon: "#E24B4A" },
    "Negative": { bg: "bg-amber-50/40 dark:bg-amber-950/15", text: "text-amber-700 dark:text-amber-400", border: "border-amber-200 dark:border-amber-800", icon: "#BA7517" },
    "Uncertain": { bg: "bg-blue-50/40 dark:bg-blue-950/15", text: "text-blue-700 dark:text-blue-400", border: "border-blue-200 dark:border-blue-800", icon: "#378ADD" },
    "Positive": { bg: "bg-green-50/40 dark:bg-green-950/15", text: "text-green-700 dark:text-green-400", border: "border-green-200 dark:border-green-800", icon: "#639922" },
    "Unclassified": { bg: "bg-card", text: "text-muted-foreground", border: "border-border", icon: "#9CA3AF" },
  };

  return (
    <motion.div className="max-w-6xl mx-auto px-4 py-6 space-y-6" variants={stagger} initial="hidden" animate="show">
      <motion.div variants={fadeUp}>
        <div className="flex items-center gap-3"><Play className="w-5 h-5 text-red-500" /><h1 className="text-2xl font-bold tracking-tight">YouTube Intelligence</h1>
        </div><p className="text-sm text-muted-foreground mt-0.5">Video content analysis and PR risk detection</p>
      </motion.div>
      <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {[{l:"Channels",v:stats.totalChannels||0},{l:"Videos",v:stats.totalVideos||0},{l:"Views",v:stats.totalViews||0},{l:"Likes",v:stats.totalLikes||0},{l:"Comments",v:stats.totalComments||0},{l:"PR Risks",v:stats.prRiskCount||0,c:stats.prRiskCount>0?"#E24B4A":"#639922"}].map((m,i)=>(
          <div key={i} className="rounded-xl border border-border bg-card p-3"><p className="text-[10px] text-muted-foreground uppercase tracking-widest">{m.l}</p><p className="text-xl font-bold mt-0.5" style={{color:m.c}}><AnimatedNumber value={typeof m.v==="number"?m.v:0}/></p></div>
        ))}
      </motion.div>
      {prRisks.length > 0 && (
        <motion.div variants={fadeUp} className="rounded-2xl border border-red-200 dark:border-red-800 bg-red-50/30 dark:bg-red-950/10 p-4">
          <div className="flex items-center gap-2 mb-3"><AlertTriangle className="w-4 h-4 text-red-500" /><h3 className="text-xs font-semibold uppercase tracking-widest text-red-600">PR Risk Videos</h3></div>
          <div className="space-y-2">{prRisks.map((v: any, i: number) => (
            <div key={i} className="flex items-start gap-3 bg-white/50 dark:bg-black/20 rounded-lg p-2.5">
              {v.videoId && <img src={`https://img.youtube.com/vi/${v.videoId}/default.jpg`} alt="" className="w-20 h-12 rounded object-cover shrink-0" />}
              <div className="flex-1"><p className="text-sm font-medium line-clamp-1">{v.title}</p><p className="text-xs text-muted-foreground mt-0.5">{v.reason}</p></div>
            </div>
          ))}</div>
        </motion.div>
      )}
      {isLive && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {donutData.length > 0 && (
            <AnimatedChart delay={0} className="rounded-2xl border border-border bg-card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Sentiment</h3>
              <div className="flex items-center gap-4">
                <ResponsiveContainer width={130} height={130}><PieChart><Pie data={donutData} cx="50%" cy="50%" innerRadius={35} outerRadius={55} dataKey="value" animationDuration={1500}>{donutData.map((d, i) => <Cell key={i} fill={d.color} strokeWidth={0} />)}</Pie></PieChart></ResponsiveContainer>
                <div className="space-y-1.5 text-sm">{donutData.map(d => <div key={d.name} className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: d.color }} /><span className="text-xs text-muted-foreground">{d.name}: {d.value}</span></div>)}</div>
              </div>
            </AnimatedChart>
          )}
          {channelData.length > 0 && (
            <AnimatedChart delay={0.2} className="rounded-2xl border border-border bg-card p-5">
              <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Channels by Subscribers</h3>
              <ResponsiveContainer width="100%" height={200}><BarChart data={channelData} layout="vertical" margin={{ left: 80 }}><XAxis type="number" tick={{ fontSize: 10 }} /><YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={75} /><Tooltip /><Bar dataKey="subs" radius={[0, 4, 4, 0]} barSize={14} fill="#FF0000" animationDuration={1500} /></BarChart></ResponsiveContainer>
            </AnimatedChart>
          )}
        </div>
      )}
      {/* Insight Cards */}
      {isLive && (
        <motion.div variants={fadeUp} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-red-100 dark:bg-red-900/30"><Play className="w-3.5 h-3.5 text-red-500" /></span>
              <h4 className="text-xs font-bold">Content Landscape</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {stats.totalVideos || 0} unofficial videos discovered across {stats.totalChannels || 0} channels. {formatNumber(stats.totalViews || 0)} total views.
              {stats.prRiskCount > 0 ? ` ${stats.prRiskCount} videos flagged as PR risk — these mention sensitive topics like student suicide, batch mistakes, or fraud allegations.` : " No PR risk videos detected in current scan."}
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-purple-100 dark:bg-purple-900/30"><Shield className="w-3.5 h-3.5 text-purple-600" /></span>
              <h4 className="text-xs font-bold">Brand Protection</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              63 official PW channels are blacklisted — OVAL only tracks unofficial content where real criticism lives.
              {channels.filter((c: any) => c.owner === "Not Owned").length > 0 ? ` ${channels.filter((c: any) => c.owner === "Not Owned").length} third-party channels creating PW content.` : ""}
              {formatNumber(stats.totalSubscribers || 0)} combined subscriber reach.
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-green-100 dark:bg-green-900/30"><TrendingUp className="w-3.5 h-3.5 text-green-600" /></span>
              <h4 className="text-xs font-bold">Sentiment Signal</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              {embTotal > 0 ? `${sentiment.positive || 0} positive vs ${sentiment.negative || 0} negative mentions. ` : ""}
              {(sentiment.positive || 0) > (sentiment.negative || 0) ? "YouTube leans positive — mostly fan edits, motivation clips, and teacher appreciation." : "Negative signal detected — review PR risk videos and comment threads."}
              {` ${stats.totalComments || 0} comments analyzed for sentiment.`}
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-blue-100 dark:bg-blue-900/30"><Eye className="w-3.5 h-3.5 text-blue-600" /></span>
              <h4 className="text-xs font-bold">Discovery Engine</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              250+ search keywords grouped into 15 optimized queries. 4 API keys with automatic rotation — 40K daily quota. 90-day lookback captures 3 months of content. Every title triaged by AI for PR risk.
            </p>
          </div>

          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-amber-100 dark:bg-amber-900/30"><Users className="w-3.5 h-3.5 text-amber-600" /></span>
              <h4 className="text-xs font-bold">Comment Intelligence</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Up to 10,000 comments per video (no cap). Every comment classified by sentiment. Hinglish understood — &ldquo;zabardast sir&rdquo; tagged positive, &ldquo;scam hai&rdquo; tagged negative. Comments often reveal what titles hide.
            </p>
          </div>

          {stats.prRiskCount > 0 && (
            <div className="rounded-xl border border-red-200 dark:border-red-800/40 bg-red-50/30 dark:bg-red-950/10 p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-7 h-7 rounded-lg flex items-center justify-center bg-red-200 dark:bg-red-900/50"><AlertTriangle className="w-3.5 h-3.5 text-red-700" /></span>
                <h4 className="text-xs font-bold text-red-700 dark:text-red-400">PR Alert</h4>
              </div>
              <p className="text-xs text-red-700/80 dark:text-red-400/80 leading-relaxed">
                {stats.prRiskCount} video{stats.prRiskCount > 1 ? "s" : ""} flagged as PR risk. These videos associate PW with sensitive topics and rank in YouTube search. Review and decide: ignore, monitor, respond, or escalate.
              </p>
            </div>
          )}
        </motion.div>
      )}

      {isLive && live?.rag?.enabled && (
        <motion.div variants={fadeUp}>
          <RAGInsight title="YouTube Analysis" analysis={live.rag.analysis} confidence={live.rag.confidence} mentionsUsed={live.rag.mentionsUsed} avgSimilarity={live.rag.avgSimilarity} sentimentBreakdown={live.rag.sentimentBreakdown} />
        </motion.div>
      )}

      <motion.div variants={fadeUp}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold">Content Themes ({filteredVideos.length} videos)</h2>
          <div className="relative">
            <Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input type="text" placeholder="Search videos..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
              className="text-xs pl-7 pr-3 py-1.5 rounded-lg border border-border bg-card focus:outline-none w-48" />
          </div>
        </div>
        <div className="space-y-5">
          {themeOrder.filter(theme => (videosByTheme[theme] || []).length > 0).map(theme => {
            const themeVideos = videosByTheme[theme];
            const colors = themeColors[theme];
            return (
              <div key={theme} className={cn("rounded-2xl border p-4", colors.border, colors.bg)}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: colors.icon }} />
                  <h3 className={cn("text-xs font-bold uppercase tracking-widest", colors.text)}>{theme}</h3>
                  <span className="text-[10px] text-muted-foreground ml-1">({themeVideos.length} video{themeVideos.length > 1 ? "s" : ""})</span>
                </div>
                <div className="space-y-2.5 max-h-[400px] overflow-y-auto pr-1">
                  {themeVideos.map((v: any, i: number) => (
                    <div key={i} className="rounded-xl border border-border bg-card p-4 hover:shadow-md transition-shadow cursor-pointer">
                      <div className="flex items-start gap-4">
                        {v.videoId && (
                          <img src={`https://img.youtube.com/vi/${v.videoId}/mqdefault.jpg`} alt=""
                            className="w-32 h-[72px] rounded-lg object-cover shrink-0" />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-1">
                            {v.isPrRisk && <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">PR RISK</span>}
                            {v.triageLabel && (
                              <span className={cn("text-[9px] font-medium px-1.5 py-0.5 rounded",
                                v.triageLabel === "negative" ? "bg-red-100 text-red-600" :
                                v.triageLabel === "positive" ? "bg-green-100 text-green-600" :
                                "bg-gray-100 text-gray-500"
                              )}>{v.triageLabel}</span>
                            )}
                            {v.transcriptSentiment && v.transcriptSentiment !== v.triageLabel && (
                              <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">transcript: {v.transcriptSentiment}</span>
                            )}
                          </div>
                          <p className="text-sm font-semibold line-clamp-2 leading-snug">{v.title}</p>
                          {v.isPrRisk && v.triageReason && (
                            <p className="text-[11px] text-red-600/80 dark:text-red-400/70 mt-1 line-clamp-1">{v.triageReason}</p>
                          )}
                          <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
                            <span className="flex items-center gap-1"><Eye className="w-3 h-3" />{formatNumber(v.views)}</span>
                            <span>{formatNumber(v.likes)} likes</span>
                            <span>{v.comments || 0} comments</span>
                            {v.url && (
                              <a href={v.url} target="_blank" rel="noopener noreferrer"
                                className="text-red-500 hover:underline cursor-pointer ml-auto flex items-center gap-0.5">
                                Watch <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>
      {comments.length > 0 && (<motion.div variants={fadeUp}><h2 className="text-sm font-semibold mb-3">Top Comments</h2><div className="space-y-1.5 max-h-[300px] overflow-y-auto">{comments.map((c: any, i: number) => (<div key={i} className="rounded-lg border border-border p-2.5 text-sm"><p className="text-foreground/80 italic">&ldquo;{c.text}&rdquo;</p><p className="text-[10px] text-muted-foreground mt-1">{c.author} {c.likes > 0 && `| ${c.likes} likes`}</p></div>))}</div></motion.div>)}
    </motion.div>
  );
}
