"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Play, ExternalLink, Search, AlertTriangle } from "lucide-react";
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

  return (
    <motion.div className="max-w-6xl mx-auto px-4 py-6 space-y-6" variants={stagger} initial="hidden" animate="show">
      <motion.div variants={fadeUp}>
        <div className="flex items-center gap-3"><Play className="w-5 h-5 text-red-500" /><h1 className="text-2xl font-bold tracking-tight">YouTube Intelligence</h1>
          {isLive && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Live</span>}
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
      <motion.div variants={fadeUp}>
        <div className="flex items-center justify-between mb-3"><h2 className="text-sm font-semibold">Videos ({filteredVideos.length})</h2>
          <div className="relative"><Search className="w-3 h-3 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" /><input type="text" placeholder="Search..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="text-xs pl-7 pr-3 py-1.5 rounded-lg border border-border bg-card focus:outline-none w-44" /></div>
        </div>
        <div className="space-y-2 max-h-[450px] overflow-y-auto">{filteredVideos.map((v: any, i: number) => (
          <div key={i} className={cn("rounded-xl border p-3 hover:shadow-md transition-shadow cursor-pointer", v.isPrRisk ? "border-red-200 bg-red-50/30" : "border-border bg-card")}>
            <div className="flex items-start gap-3">
              {v.videoId && <img src={`https://img.youtube.com/vi/${v.videoId}/default.jpg`} alt="" className="w-24 h-14 rounded object-cover shrink-0" />}
              <div className="flex-1 min-w-0">
                {v.isPrRisk && <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-red-100 text-red-700 mr-1">PR RISK</span>}
                <p className="text-sm font-medium line-clamp-1">{v.title}</p>
                <div className="flex gap-3 mt-1 text-[10px] text-muted-foreground"><span>{formatNumber(v.views)} views</span><span>{formatNumber(v.likes)} likes</span>{v.url && <a href={v.url} target="_blank" rel="noopener noreferrer" className="text-red-500 hover:underline cursor-pointer">Watch</a>}</div>
              </div>
            </div>
          </div>
        ))}</div>
      </motion.div>
      {comments.length > 0 && (<motion.div variants={fadeUp}><h2 className="text-sm font-semibold mb-3">Top Comments</h2><div className="space-y-1.5 max-h-[300px] overflow-y-auto">{comments.map((c: any, i: number) => (<div key={i} className="rounded-lg border border-border p-2.5 text-sm"><p className="text-foreground/80 italic">&ldquo;{c.text}&rdquo;</p><p className="text-[10px] text-muted-foreground mt-1">{c.author} {c.likes > 0 && `| ${c.likes} likes`}</p></div>))}</div></motion.div>)}
    </motion.div>
  );
}
