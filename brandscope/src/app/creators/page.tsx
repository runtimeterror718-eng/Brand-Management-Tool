"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Play, Send, AlertTriangle, Heart, ExternalLink, Users, Eye } from "lucide-react";
import { useLiveData } from "@/lib/use-live-data";
import { formatNumber, cn } from "@/lib/utils";
import { AnimatedNumber } from "@/components/ui/animated-chart";
import { stagger, fadeUp } from "@/lib/animations";
import { PageSkeleton } from "@/components/ui/page-skeleton";

const STANCE_CONFIG = {
  threat: { color: "#E24B4A", bg: "border-red-200 dark:border-red-800 bg-red-50/30 dark:bg-red-950/10", icon: AlertTriangle, label: "Threat" },
  friend: { color: "#639922", bg: "border-green-200 dark:border-green-800 bg-green-50/30 dark:bg-green-950/10", icon: Heart, label: "Friend" },
  neutral: { color: "#9CA3AF", bg: "border-border bg-card", icon: Eye, label: "Neutral" },
};
const THREAT_BADGE: Record<string, string> = {
  high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  low: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
};

export default function CreatorsPage() {
  const { data: d, isLive, loading } = useLiveData<any>("/api/creators", null);
  const [filter, setFilter] = useState<"all" | "threat" | "friend" | "neutral">("all");
  const [search, setSearch] = useState("");

  if (loading) return <PageSkeleton title="Creator Intelligence" color="#534AB7" />;

  const creators = d?.creators || [];
  const stats = d?.stats || {};
  const filtered = creators.filter((c: any) => {
    if (filter !== "all" && c.stance !== filter) return false;
    if (search && !(c.name || "").toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <motion.div className="max-w-6xl mx-auto px-4 py-6 space-y-6" variants={stagger} initial="hidden" animate="show">

      <motion.div variants={fadeUp}>
        <div className="flex items-center gap-3">
          <Users className="w-5 h-5 text-purple-500" />
          <h1 className="text-2xl font-bold tracking-tight">Creator Intelligence</h1>
        </div>
        <p className="text-sm text-muted-foreground mt-0.5">Who is making content about PW — friends, threats, and neutrals</p>
      </motion.div>

      {/* Metrics */}
      <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Total Creators</p>
          <p className="text-xl font-bold mt-0.5"><AnimatedNumber value={stats.totalCreators || 0} /></p>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50/30 p-3">
          <p className="text-[10px] text-red-600 uppercase tracking-widest font-semibold">Threats</p>
          <p className="text-xl font-bold mt-0.5 text-red-600"><AnimatedNumber value={stats.threats || 0} /></p>
        </div>
        <div className="rounded-xl border border-green-200 bg-green-50/30 p-3">
          <p className="text-[10px] text-green-600 uppercase tracking-widest font-semibold">Friends</p>
          <p className="text-xl font-bold mt-0.5 text-green-600"><AnimatedNumber value={stats.friends || 0} /></p>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Total Reach</p>
          <p className="text-xl font-bold mt-0.5"><AnimatedNumber value={stats.totalReach || 0} /></p>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div variants={fadeUp} className="flex items-center justify-between">
        <div className="flex gap-1.5">
          {(["all", "threat", "friend", "neutral"] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className={cn("text-xs px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer",
                filter === f ? "bg-foreground text-background" : "bg-muted text-muted-foreground hover:text-foreground"
              )}>
              {f === "all" ? `All (${creators.length})` : f === "threat" ? `Threats (${creators.filter((c: any) => c.stance === "threat").length})` : f === "friend" ? `Friends (${creators.filter((c: any) => c.stance === "friend").length})` : `Neutral (${creators.filter((c: any) => c.stance === "neutral").length})`}
            </button>
          ))}
        </div>
        <input type="text" placeholder="Search creators..." value={search} onChange={(e) => setSearch(e.target.value)}
          className="text-xs px-3 py-1.5 rounded-lg border border-border bg-card focus:outline-none focus:ring-1 focus:ring-purple-500 w-44" />
      </motion.div>

      {/* Creator Cards */}
      <motion.div variants={fadeUp}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {filtered.length === 0 && <p className="text-sm text-muted-foreground py-8 col-span-2 text-center">No creators match your filter</p>}
          {filtered.map((c: any, i: number) => {
            const stance = STANCE_CONFIG[c.stance as keyof typeof STANCE_CONFIG] || STANCE_CONFIG.neutral;
            const StanceIcon = stance.icon;
            const isYT = c.platform === "youtube";
            return (
              <div key={i} className={cn("rounded-xl border p-4 hover:shadow-md transition-shadow cursor-pointer", stance.bg)}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {isYT ? <Play className="w-4 h-4 text-red-500" /> : <Send className="w-4 h-4 text-[#0088CC]" />}
                    <span className="text-sm font-bold">{c.name}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={cn("text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase", THREAT_BADGE[c.threatLevel] || THREAT_BADGE.low)}>{c.threatLevel}</span>
                    <StanceIcon className="w-3.5 h-3.5" style={{ color: stance.color }} />
                  </div>
                </div>
                <div className="flex gap-3 text-xs text-muted-foreground mb-2">
                  {c.subscribers > 0 && <span className="flex items-center gap-1"><Users className="w-3 h-3" />{formatNumber(c.subscribers)} subs</span>}
                  {c.members > 0 && <span className="flex items-center gap-1"><Users className="w-3 h-3" />{formatNumber(c.members)} members</span>}
                  {c.videoCount > 0 && <span>{c.videoCount} videos</span>}
                  {c.totalViews > 0 && <span>{formatNumber(c.totalViews)} views</span>}
                </div>
                {isYT && c.videoCount > 0 && (
                  <div className="flex gap-1.5 text-[10px] mb-2">
                    <span className="px-1.5 py-0.5 rounded bg-green-100 text-green-700">{c.positiveVideos} positive</span>
                    <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-700">{c.negativeVideos} negative</span>
                    {c.prRiskCount > 0 && <span className="px-1.5 py-0.5 rounded bg-red-200 text-red-800 font-bold">{c.prRiskCount} PR RISK</span>}
                  </div>
                )}
                {!isYT && (
                  <div className="flex gap-1.5 text-[10px] mb-2">
                    <span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">{c.label?.replace(/_/g, " ")}</span>
                    {c.isFake && <span className="px-1.5 py-0.5 rounded bg-red-200 text-red-800 font-bold">FAKE</span>}
                  </div>
                )}
                {c.topVideos?.slice(0, 2).map((v: any, j: number) => (
                  <div key={j} className="flex items-center gap-2 text-xs bg-white/50 dark:bg-black/10 rounded-lg p-2 mt-1.5">
                    {v.videoId && <img src={`https://img.youtube.com/vi/${v.videoId}/default.jpg`} alt="" className="w-14 h-8 rounded object-cover shrink-0" />}
                    <div className="flex-1 min-w-0">
                      <p className="line-clamp-1 font-medium text-[11px]">{v.title}</p>
                      <span className="text-[10px] text-muted-foreground">{formatNumber(v.views)} views</span>
                    </div>
                    {v.url && <a href={v.url} target="_blank" rel="noopener noreferrer" className="shrink-0 cursor-pointer"><ExternalLink className="w-3 h-3 text-muted-foreground hover:text-foreground" /></a>}
                  </div>
                ))}
                {c.username && <a href={`https://t.me/${c.username}`} target="_blank" rel="noopener noreferrer" className="text-[10px] text-[#0088CC] hover:underline mt-2 inline-flex items-center gap-0.5 cursor-pointer">Open in Telegram <ExternalLink className="w-2.5 h-2.5" /></a>}
              </div>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
}
