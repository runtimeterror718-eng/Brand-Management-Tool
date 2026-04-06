"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, TrendingDown, TrendingUp, Eye, MessageCircle, Camera, Play, Send, Search, Brain, Minus, Activity } from "lucide-react";
import { useLiveData } from "@/lib/use-live-data";
import { formatNumber, cn } from "@/lib/utils";
import { BrandScoreCards, type BrandScoreProps } from "@/components/ui/brand-score-cards";
import { PageSkeleton } from "@/components/ui/page-skeleton";
import { stagger, fadeUp } from "@/lib/animations";

function parseBullets(text: string): string[] {
  if (!text) return [];
  const lines = text.split(/\n/).map(l => l.trim()).filter(Boolean);
  const bullets: string[] = [];
  let current = "";
  for (const line of lines) {
    if (/^[-–•]\s/.test(line) || /^\d+[.)]\s/.test(line)) {
      if (current) bullets.push(current);
      current = line.replace(/^[-–•]\s*/, "").replace(/^\d+[.)]\s*/, "");
    } else if (current) {
      current += " " + line;
    } else {
      current = line;
    }
  }
  if (current) bullets.push(current);
  return bullets.filter(b => b.length > 10).slice(0, 6);
}

function stripMarkdown(text: string): string {
  if (!text) return "";
  return text.replace(/#{1,6}\s+/g, "").replace(/\*\*(.+?)\*\*/g, "$1").replace(/\*(.+?)\*/g, "$1").replace(/__(.+?)__/g, "$1").replace(/_(.+?)_/g, "$1").replace(/`(.+?)`/g, "$1").replace(/^\s*[-*]\s+/gm, "- ").replace(/^\s*\d+\.\s+/gm, "").replace(/\n{3,}/g, "\n\n").trim();
}

const PLATFORM_ICONS: Record<string, any> = { reddit: MessageCircle, instagram: Camera, youtube: Play, telegram: Send, google: Search };
const PLATFORM_COLORS: Record<string, string> = { reddit: "#FF5700", instagram: "#E1306C", youtube: "#FF0000", telegram: "#0088CC", google: "#4285F4" };
const SEV: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  critical: { bg: "bg-red-50 dark:bg-red-950/30", text: "text-red-600", border: "border-red-200 dark:border-red-800", dot: "bg-red-500" },
  high: { bg: "bg-red-50/50 dark:bg-red-950/20", text: "text-red-500", border: "border-red-200 dark:border-red-800", dot: "bg-red-400" },
  medium: { bg: "bg-amber-50/50 dark:bg-amber-950/20", text: "text-amber-600", border: "border-amber-200 dark:border-amber-800", dot: "bg-amber-400" },
  low: { bg: "bg-green-50/50 dark:bg-green-950/20", text: "text-green-600", border: "border-green-200 dark:border-green-800", dot: "bg-green-400" },
};

export default function CommandCenter() {
  const { data: d, isLive, loading } = useLiveData<any>("/api/command-center", null);
  const [signalFilter, setSignalFilter] = useState("all");

  if (loading) return <PageSkeleton title="Command Center" color="#534AB7" />;

  const today = new Date().toLocaleDateString("en-IN", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
  const health = d?.healthScore ?? 50;
  const alerts = d?.alerts || [];
  const platforms = d?.platformPulse || [];
  const signals = d?.recentSignals || [];
  const enrollment = d?.enrollmentRisks || {};
  const sentiment = d?.sentiment || { positive: 0, negative: 0, neutral: 0, total: 0 };
  const highAlerts = alerts.filter((a: any) => a.severity === "high" || a.severity === "critical").length;
  const filteredSignals = signalFilter === "all" ? signals : signals.filter((s: any) => s.platform === signalFilter);

  return (
    <motion.div className="max-w-6xl mx-auto px-4 py-6 space-y-6" variants={stagger} initial="hidden" animate="show">
      <motion.div variants={fadeUp} className="flex items-end justify-between">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-widest mb-1">{today}</p>
          <h1 className="text-2xl font-bold tracking-tight">Command Center</h1>
        </div>
        {isLive && <div className="flex items-center gap-2"><span className="relative flex h-2 w-2"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" /><span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" /></span><span className="text-xs text-green-600 dark:text-green-400 font-medium">Live</span></div>}
      </motion.div>

      {isLive && (
        <motion.div variants={fadeUp}>
          <BrandScoreCards scores={[
            { title: "Brand Health", description: `Measures overall brand perception by weighing positive vs negative mentions across ${platforms.length} platforms. Score above 70 = healthy, below 45 = at risk. Based on ${formatNumber(sentiment.total)} analyzed mentions.`, score: health, linkHref: "/actionables", linkLabel: "Action Items" },
            { title: "Positive Sentiment", description: `Percentage of all mentions classified as positive (praise, appreciation, fan content). Currently ${formatNumber(sentiment.positive)} positive out of ${formatNumber(sentiment.total)} total mentions across Reddit, Instagram, YouTube, and Telegram.`, score: sentiment.total > 0 ? Math.round((sentiment.positive / sentiment.total) * 100) : 0, linkHref: "/instagram", linkLabel: "View Details" },
            { title: "Risk Index", description: `Measures brand safety. Drops when alerts are detected — fake channels, negative news, consumer court cases, or scam allegations. Currently ${alerts.length} active alerts, ${highAlerts} require immediate attention.`, score: Math.max(0, 100 - Math.min(alerts.length * 12, 80)), linkHref: "/creators", linkLabel: "View Threats" },
          ] as BrandScoreProps[]} />
        </motion.div>
      )}

      {/* Key Risks + Bright Spots — full width, detailed pointers with source links */}
      {(d?.rag?.negative || d?.rag?.positive) && (
        <motion.div variants={fadeUp} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {d?.rag?.negative && (
            <div className="rounded-2xl border border-red-200/60 dark:border-red-900/40 bg-red-50/20 dark:bg-red-950/10 p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                    <TrendingDown className="w-4 h-4 text-red-500" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-red-600 dark:text-red-400">Key Risks</h3>
                    <p className="text-[10px] text-muted-foreground">Issues requiring attention</p>
                  </div>
                </div>
                <span className="text-[10px] text-muted-foreground">{d.rag.negative.mentions} sources analyzed</span>
              </div>
              <ul className="space-y-2.5">
                {parseBullets(stripMarkdown(d.rag.negative.summary)).map((bullet, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400 mt-1.5 shrink-0" />
                    <p className="text-sm text-foreground/85 leading-relaxed">{bullet}</p>
                  </li>
                ))}
              </ul>
              <div className="mt-4 pt-3 border-t border-red-200/30 dark:border-red-800/20 flex items-center gap-3">
                <span className="text-[10px] text-muted-foreground">Explore on:</span>
                <a href="/reddit" className="text-[10px] font-medium text-[#FF5700] hover:underline cursor-pointer">Reddit</a>
                <a href="/instagram" className="text-[10px] font-medium text-[#E1306C] hover:underline cursor-pointer">Instagram</a>
                <a href="/youtube" className="text-[10px] font-medium text-[#FF0000] hover:underline cursor-pointer">YouTube</a>
                <a href="/actionables" className="text-[10px] font-medium text-purple-600 hover:underline cursor-pointer ml-auto">View Action Items</a>
              </div>
            </div>
          )}
          {d?.rag?.positive && (
            <div className="rounded-2xl border border-green-200/60 dark:border-green-900/40 bg-green-50/20 dark:bg-green-950/10 p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                    <TrendingUp className="w-4 h-4 text-green-600" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-green-600 dark:text-green-400">Bright Spots</h3>
                    <p className="text-[10px] text-muted-foreground">Positive brand signals</p>
                  </div>
                </div>
                <span className="text-[10px] text-muted-foreground">{d.rag.positive.mentions || ""} sources</span>
              </div>
              <ul className="space-y-2.5">
                {parseBullets(stripMarkdown(d.rag.positive.summary)).map((bullet, i) => (
                  <li key={i} className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-400 mt-1.5 shrink-0" />
                    <p className="text-sm text-foreground/85 leading-relaxed">{bullet}</p>
                  </li>
                ))}
              </ul>
              <div className="mt-4 pt-3 border-t border-green-200/30 dark:border-green-800/20 flex items-center gap-3">
                <span className="text-[10px] text-muted-foreground">Explore on:</span>
                <a href="/instagram" className="text-[10px] font-medium text-[#E1306C] hover:underline cursor-pointer">Instagram</a>
                <a href="/youtube" className="text-[10px] font-medium text-[#FF0000] hover:underline cursor-pointer">YouTube</a>
                <a href="/telegram" className="text-[10px] font-medium text-[#0088CC] hover:underline cursor-pointer">Telegram</a>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Platform Pulse */}
      <motion.div variants={fadeUp}>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-2.5">Platform Overview</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
          {platforms.map((p: any) => {
            const PIcon = PLATFORM_ICONS[p.name] || Eye;
            const pColor = PLATFORM_COLORS[p.name] || "#9CA3AF";
            const ratio = p.positiveRatio;
            const ratioColor = ratio >= 70 ? "#639922" : ratio >= 45 ? "#BA7517" : "#E24B4A";
            return (
              <a key={p.name} href={`/${p.name}`} className="rounded-xl border border-border bg-card p-3.5 hover:shadow-md transition-all cursor-pointer text-center">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <PIcon className="w-4 h-4" style={{ color: pColor }} />
                  <span className="text-xs font-semibold capitalize">{p.name}</span>
                </div>
                <p className="text-2xl font-bold leading-none">{formatNumber(p.mentions)}</p>
                <p className="text-[10px] text-muted-foreground mt-0.5">mentions tracked</p>
                <div className="flex items-center gap-1.5 mt-2.5">
                  <div className="flex-1 h-1.5 rounded-full bg-gray-100 dark:bg-gray-800">
                    <div className="h-full rounded-full transition-all" style={{ width: `${ratio}%`, backgroundColor: ratioColor }} />
                  </div>
                  <span className="text-[10px] font-semibold" style={{ color: ratioColor }}>{ratio}%</span>
                </div>
                <p className="text-[9px] text-muted-foreground mt-1">positive sentiment</p>
                {p.negative > 0 && <p className="text-[9px] text-red-500 mt-0.5">{p.negative} negative</p>}
              </a>
            );
          })}
        </div>
      </motion.div>

      {/* Active Alerts */}
      <motion.div variants={fadeUp} className="rounded-2xl border border-border bg-card p-4">
        <div className="flex items-center gap-2 mb-3"><AlertTriangle className="w-4 h-4 text-red-500" /><h2 className="text-sm font-semibold">Active Alerts</h2>{alerts.length > 0 && <span className="ml-auto text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">{alerts.length}</span>}</div>
        <div className="space-y-2 max-h-[260px] overflow-y-auto">
          {alerts.length === 0 && <p className="text-sm text-muted-foreground py-8 text-center">No active alerts</p>}
          {alerts.slice(0, 8).map((alert: any, i: number) => {
            const s = SEV[alert.severity as keyof typeof SEV] || SEV.medium;
            const PIcon = PLATFORM_ICONS[alert.platform] || Eye;
            return (
              <div key={i} className={cn("flex items-start gap-2.5 rounded-lg border p-2.5", s.border, s.bg)}>
                <span className={cn("w-1.5 h-1.5 rounded-full mt-1.5 shrink-0", s.dot)} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium line-clamp-1">{alert.title}</p>
                  <div className="flex items-center gap-2 mt-0.5"><PIcon className="w-3 h-3" style={{ color: PLATFORM_COLORS[alert.platform] }} /><span className={cn("text-[10px] font-semibold uppercase", s.text)}>{alert.severity}</span></div>
                </div>
              </div>
            );
          })}
        </div>
      </motion.div>

      {enrollment.negativeAutocomplete?.length > 0 && (
        <motion.div variants={fadeUp} className="rounded-2xl border border-amber-200 dark:border-amber-800/50 bg-amber-50/30 dark:bg-amber-950/10 p-4">
          <div className="flex items-center justify-between mb-3"><div className="flex items-center gap-1.5"><Search className="w-3.5 h-3.5 text-amber-600" /><h3 className="text-xs font-semibold uppercase tracking-widest text-amber-700 dark:text-amber-400">What Parents See on Google</h3></div></div>
          <div className="bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 p-3">
            <div className="flex items-center gap-2 mb-1.5 pb-1.5 border-b border-gray-100 dark:border-gray-800"><div className="w-4 h-4 rounded-full bg-[#4285F4] flex items-center justify-center"><span className="text-white text-[8px] font-bold">G</span></div><span className="text-sm text-gray-400">physics wallah</span></div>
            <div className="space-y-0.5">{enrollment.negativeAutocomplete.slice(0, 6).map((s: string, i: number) => (<div key={i} className="flex items-center gap-2 text-sm py-1 px-1 rounded hover:bg-gray-50 dark:hover:bg-gray-800"><Search className="w-3 h-3 text-gray-300 shrink-0" /><span className="flex-1 text-gray-700 dark:text-gray-300">{s}</span><span className="text-[9px] px-1 py-0.5 rounded bg-red-100 text-red-500 shrink-0">risk</span></div>))}</div>
          </div>
        </motion.div>
      )}

      <motion.div variants={fadeUp}>
        <div className="flex items-center justify-between mb-2.5"><div className="flex items-center gap-2"><Activity className="w-3.5 h-3.5 text-muted-foreground" /><h2 className="text-sm font-semibold">Recent Signals</h2></div>
          <div className="flex gap-1">{["all", ...platforms.map((p: any) => p.name)].map((f: string) => (<button key={f} onClick={() => setSignalFilter(f)} className={cn("text-[10px] px-2 py-0.5 rounded-full font-medium transition-colors cursor-pointer", signalFilter === f ? "bg-foreground text-background" : "text-muted-foreground hover:bg-muted")}>{f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}</button>))}</div>
        </div>
        <div className="rounded-xl border border-border bg-card overflow-hidden"><div className="max-h-[320px] overflow-y-auto divide-y divide-border">
          {filteredSignals.length === 0 && <p className="text-sm text-muted-foreground py-8 text-center">No signals</p>}
          {filteredSignals.map((s: any, i: number) => {
            const PIcon = PLATFORM_ICONS[s.platform] || Eye;
            const pColor = PLATFORM_COLORS[s.platform] || "#9CA3AF";
            const sentColor = s.sentiment === "positive" ? "text-green-500" : s.sentiment === "negative" ? "text-red-500" : "text-gray-400";
            return (<div key={i} className="flex items-start gap-3 px-3.5 py-2.5 hover:bg-muted/30 transition-colors"><PIcon className="w-3.5 h-3.5 mt-0.5 shrink-0" style={{ color: pColor }} /><p className="text-sm flex-1 min-w-0 line-clamp-2 text-foreground/80">{s.text}</p><span className={cn("text-[10px] font-medium capitalize shrink-0", sentColor)}>{s.sentiment}</span></div>);
          })}
        </div></div>
      </motion.div>

      <motion.div variants={fadeUp} className="text-center pt-2"><p className="text-[10px] text-muted-foreground/60">Powered by OVAL Intelligence Engine — {formatNumber(sentiment.total)} mentions across {platforms.length} platforms</p></motion.div>
    </motion.div>
  );
}
