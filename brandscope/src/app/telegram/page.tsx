"use client";

import { motion } from "framer-motion";
import { PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { Send, ExternalLink, AlertTriangle } from "lucide-react";
import RAGInsight from "@/components/dashboard/rag-insight";
import { useLiveData } from "@/lib/use-live-data";
import { formatNumber, cn } from "@/lib/utils";
import { AnimatedChart, AnimatedNumber } from "@/components/ui/animated-chart";
import { PageSkeleton } from "@/components/ui/page-skeleton";
import { stagger, fadeUp } from "@/lib/animations";

const BLUE = "#0088CC";
const COLORS = { positive: "#639922", neutral: "#9CA3AF", negative: "#E24B4A" };
const RISK_COLORS: Record<string, string> = { safe: "#639922", suspicious: "#E24B4A", copyright_infringement: "#BA7517" };
const LABEL_COLORS: Record<string, string> = { official: "#639922", fan_unofficial: "#378ADD", suspicious_fake: "#E24B4A" };

export default function TelegramPage() {
  const { data: live, isLive, loading } = useLiveData<any>("/api/telegram", null);

  if (loading) return <PageSkeleton title="Telegram Intelligence" color="#0088CC" />;

  const stats = live?.stats || {};
  const sentiment = stats.sentiment || {};
  const channels = live?.channels || [];
  const riskBreakdown = live?.riskBreakdown || {};
  const suspiciousContent = live?.suspiciousContent || [];
  const weeklyTrend = live?.weeklyTrend || [];
  const embTotal = (sentiment.positive || 0) + (sentiment.negative || 0) + (sentiment.neutral || 0);
  const sentDonut = embTotal > 0 ? [
    { name: "Positive", value: sentiment.positive, color: COLORS.positive },
    { name: "Neutral", value: sentiment.neutral, color: COLORS.neutral },
    { name: "Negative", value: sentiment.negative, color: COLORS.negative },
  ] : [];
  const riskDonut = Object.entries(riskBreakdown).map(([name, value]) => ({ name, value: value as number, color: RISK_COLORS[name] || "#9CA3AF" }));

  return (
    <motion.div className="max-w-6xl mx-auto px-4 py-6 space-y-6" variants={stagger} initial="hidden" animate="show">
      <motion.div variants={fadeUp}>
        <div className="flex items-center gap-3"><Send className="w-5 h-5" style={{ color: BLUE }} /><h1 className="text-2xl font-bold tracking-tight">Telegram Intelligence</h1>
          {isLive && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Live</span>}
        </div><p className="text-sm text-muted-foreground mt-0.5">Channel monitoring, fake detection, and risk analysis</p>
      </motion.div>
      <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {[{l:"Channels",v:stats.totalChannels||0,c:BLUE},{l:"Members",v:stats.totalMembers||0},{l:"Messages",v:stats.totalMessages||0},{l:"Views",v:stats.totalViews||0},{l:"Suspicious",v:stats.suspiciousCount||0,c:"#E24B4A"},{l:"Fake",v:stats.suspiciousChannels||0,c:"#E24B4A"}].map((m,i)=>(
          <div key={i} className="rounded-xl border border-border bg-card p-3"><p className="text-[10px] text-muted-foreground uppercase tracking-widest">{m.l}</p><p className="text-xl font-bold mt-0.5" style={{color:m.c}}><AnimatedNumber value={typeof m.v==="number"?m.v:0}/></p></div>
        ))}
      </motion.div>
      {isLive && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {sentDonut.length > 0 && (<AnimatedChart delay={0} className="rounded-2xl border border-border bg-card p-5"><h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Sentiment</h3><div className="flex items-center gap-4"><ResponsiveContainer width={130} height={130}><PieChart><Pie data={sentDonut} cx="50%" cy="50%" innerRadius={35} outerRadius={55} dataKey="value" animationDuration={1500}>{sentDonut.map((d,i)=><Cell key={i} fill={d.color} strokeWidth={0}/>)}</Pie></PieChart></ResponsiveContainer><div className="space-y-1.5 text-sm">{sentDonut.map(d=><div key={d.name} className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full" style={{backgroundColor:d.color}}/><span className="text-xs text-muted-foreground">{d.name}: {d.value}</span></div>)}</div></div></AnimatedChart>)}
          {riskDonut.length > 0 && (<AnimatedChart delay={0.2} className="rounded-2xl border border-border bg-card p-5"><h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Message Risk</h3><div className="flex items-center gap-4"><ResponsiveContainer width={130} height={130}><PieChart><Pie data={riskDonut} cx="50%" cy="50%" innerRadius={35} outerRadius={55} dataKey="value" animationDuration={1500}>{riskDonut.map((d,i)=><Cell key={i} fill={d.color} strokeWidth={0}/>)}</Pie></PieChart></ResponsiveContainer><div className="space-y-1.5 text-sm">{riskDonut.map(d=><div key={d.name} className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full" style={{backgroundColor:d.color}}/><span className="text-xs text-muted-foreground">{d.name}: {d.value}</span></div>)}</div></div></AnimatedChart>)}
        </div>
      )}
      {weeklyTrend.some((w: any) => w.count > 0) && (<AnimatedChart delay={0.1} className="rounded-2xl border border-border bg-card p-5"><h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-4">Message Activity</h3><ResponsiveContainer width="100%" height={180}><AreaChart data={weeklyTrend}><defs><linearGradient id="tgGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={BLUE} stopOpacity={0.3}/><stop offset="95%" stopColor={BLUE} stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb"/><XAxis dataKey="week" tick={{fontSize:10}}/><YAxis tick={{fontSize:10}}/><Tooltip/><Area type="monotone" dataKey="count" stroke={BLUE} strokeWidth={2} fill="url(#tgGrad)" animationDuration={1500}/></AreaChart></ResponsiveContainer></AnimatedChart>)}
      {channels.length > 0 && (<motion.div variants={fadeUp}><h2 className="text-sm font-semibold mb-3">Channels ({channels.length})</h2><div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">{channels.map((ch: any, i: number) => (<div key={i} className={cn("rounded-xl border p-3.5 hover:shadow-md transition-shadow cursor-pointer", ch.isFake ? "border-red-200 bg-red-50/30" : ch.label === "official" ? "border-green-200 bg-green-50/30" : "border-border bg-card")}><div className="flex items-start justify-between mb-1.5"><div><div className="flex items-center gap-1.5"><span className="text-sm font-semibold" style={{color:BLUE}}>@{ch.username}</span><span className="text-[9px] font-medium px-1.5 py-0.5 rounded" style={{backgroundColor:`${LABEL_COLORS[ch.label]||"#9CA3AF"}20`,color:LABEL_COLORS[ch.label]||"#9CA3AF"}}>{ch.label?.replace(/_/g," ")}</span>{ch.isFake && <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-red-100 text-red-700">FAKE</span>}</div><p className="text-xs text-muted-foreground mt-0.5">{ch.title}</p></div><div className="text-right"><p className="text-sm font-bold">{formatNumber(ch.members)}</p><p className="text-[10px] text-muted-foreground">members</p></div></div>{ch.url && <a href={ch.url} target="_blank" rel="noopener noreferrer" className="text-[10px] hover:underline cursor-pointer" style={{color:BLUE}}>Open in Telegram</a>}</div>))}</div></motion.div>)}
      {suspiciousContent.length > 0 && (<motion.div variants={fadeUp} className="rounded-2xl border border-red-200 bg-red-50/30 p-4"><div className="flex items-center gap-2 mb-3"><AlertTriangle className="w-4 h-4 text-red-500"/><h3 className="text-xs font-semibold uppercase tracking-widest text-red-600">Suspicious Content</h3></div><div className="space-y-2 max-h-[300px] overflow-y-auto">{suspiciousContent.map((m: any, i: number) => (<div key={i} className="bg-white/50 dark:bg-black/20 rounded-lg p-2.5 text-sm"><div className="flex items-center gap-2 mb-1"><span className="text-[9px] font-bold px-1 py-0.5 rounded bg-red-100 text-red-700">{m.riskLabel}</span><span className="text-[10px] text-muted-foreground">@{m.channel}</span><span className="text-[10px] text-muted-foreground ml-auto">{formatNumber(m.views)} views</span></div><p className="text-foreground/80 italic line-clamp-2">&ldquo;{m.text}&rdquo;</p></div>))}</div></motion.div>)}
    </motion.div>
  );
}
