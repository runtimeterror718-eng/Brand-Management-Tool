"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ClipboardCheck, Send, ChevronDown, ChevronUp, Brain, Filter, AlertTriangle, CheckCircle2 } from "lucide-react";
import { useLiveData } from "@/lib/use-live-data";
import { PageSkeleton } from "@/components/ui/page-skeleton";
import { AnimatedNumber } from "@/components/ui/animated-chart";
import { formatNumber, cn } from "@/lib/utils";
import { stagger, fadeUp } from "@/lib/animations";
import { toast } from "sonner";

const DEPT_COLORS: Record<string, string> = {
  "Product Team": "#534AB7",
  "Finance Team": "#BA7517",
  "Legal Team": "#D85A30",
  "HR Team": "#D4537E",
  "Batch Operations Team": "#378ADD",
  "YouTube Team": "#FF0000",
  "PR Team": "#E24B4A",
  "Vidyapeeth Operations Team": "#1D9E75",
  "Marketing Team": "#639922",
  "Customer Support Team": "#0088CC",
};

const PRIORITY_STYLES: Record<string, { border: string; badge: string; dot: string }> = {
  high: { border: "border-l-red-500", badge: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400", dot: "bg-red-500" },
  medium: { border: "border-l-amber-500", badge: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400", dot: "bg-amber-500" },
  low: { border: "border-l-green-500", badge: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400", dot: "bg-green-500" },
};

// Fixed department order matching the spec
const DEPT_ORDER = [
  "Product Team", "Finance Team", "Legal Team", "HR Team", "Batch Operations Team",
  "YouTube Team", "PR Team", "Vidyapeeth Operations Team", "Marketing Team", "Customer Support Team",
];

export default function ActionablesPage() {
  const { data: raw, isLive, loading } = useLiveData<any>("/api/actionables", null);
  const [expandedDept, setExpandedDept] = useState<string | null>(null);
  const [deptFilter, setDeptFilter] = useState("all");

  if (loading) return <PageSkeleton title="Action Items" color="#534AB7" />;

  const actionables = (raw?.actionables || []).map((a: any) => ({
    id: a.id,
    title: a.task_title || "Review required",
    description: a.task_description || "",
    department: a.department || "General",
    priority: a.priority || "medium",
    area: a.cluster_label || "",
    suggestedActions: a.suggested_actions || [],
    mentionCount: a.mention_count || 0,
    evidence: a.evidence || [],
    rag: a.rag || null,
  }));

  const stats = raw?.stats || {};

  // Group by department
  const departments = new Map<string, typeof actionables>();
  for (const a of actionables) {
    if (!departments.has(a.department)) departments.set(a.department, []);
    departments.get(a.department)!.push(a);
  }

  // Sort by fixed order, then by task count
  const deptList = DEPT_ORDER
    .filter(name => departments.has(name))
    .map(name => {
      const tasks = departments.get(name)!;
      return {
        name,
        tasks,
        highCount: tasks.filter((t: any) => t.priority === "high").length,
        totalMentions: tasks.reduce((s: number, t: any) => s + t.mentionCount, 0),
        color: DEPT_COLORS[name] || "#9CA3AF",
      };
    });

  const filteredDepts = deptFilter === "all" ? deptList : deptList.filter(d => d.name === deptFilter);

  const sendToTeam = async (task: any) => {
    try {
      const res = await fetch("/api/send-action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          actionId: task.id, department: task.department, taskTitle: task.title,
          taskDescription: task.description, evidence: task.evidence,
          suggestedActions: task.suggestedActions, priority: task.priority,
        }),
      });
      const data = await res.json();
      if (data.success) toast.success(`Sent to ${data.sentTo.department}`, { description: `Routed to ${data.sentTo.email}` });
    } catch { toast.error("Failed to send action"); }
  };

  return (
    <motion.div className="max-w-6xl mx-auto px-4 py-6 space-y-6" variants={stagger} initial="hidden" animate="show">

      {/* Header */}
      <motion.div variants={fadeUp}>
        <div className="flex items-center gap-3">
          <ClipboardCheck className="w-5 h-5 text-purple-500" />
          <h1 className="text-2xl font-bold tracking-tight">Action Items</h1>
        </div>
      </motion.div>

      {/* Summary Metrics */}
      <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Tasks</p>
          <p className="text-xl font-bold mt-0.5"><AnimatedNumber value={actionables.length} /></p>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50/30 dark:bg-red-950/10 p-3">
          <p className="text-[10px] text-red-600 uppercase tracking-widest font-semibold">High</p>
          <p className="text-xl font-bold mt-0.5 text-red-600"><AnimatedNumber value={stats.highPriority || 0} /></p>
        </div>
        <div className="rounded-xl border border-amber-200 bg-amber-50/30 dark:bg-amber-950/10 p-3">
          <p className="text-[10px] text-amber-600 uppercase tracking-widest font-semibold">Medium</p>
          <p className="text-xl font-bold mt-0.5 text-amber-600"><AnimatedNumber value={stats.mediumPriority || 0} /></p>
        </div>
        <div className="rounded-xl border border-green-200 bg-green-50/30 dark:bg-green-950/10 p-3">
          <p className="text-[10px] text-green-600 uppercase tracking-widest font-semibold">Low</p>
          <p className="text-xl font-bold mt-0.5 text-green-600"><AnimatedNumber value={stats.lowPriority || 0} /></p>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Departments</p>
          <p className="text-xl font-bold mt-0.5"><AnimatedNumber value={deptList.length} /></p>
        </div>
      </motion.div>

      {/* Department Filter */}
      <motion.div variants={fadeUp} className="flex items-center gap-2 flex-wrap">
        <Filter className="w-3.5 h-3.5 text-muted-foreground" />
        <button onClick={() => setDeptFilter("all")}
          className={cn("text-[11px] px-2.5 py-1 rounded-full font-medium transition-all cursor-pointer border",
            deptFilter === "all" ? "bg-foreground text-background border-transparent" : "border-border text-muted-foreground hover:bg-muted"
          )}>All ({deptList.length})</button>
        {deptList.map(d => (
          <button key={d.name} onClick={() => setDeptFilter(deptFilter === d.name ? "all" : d.name)}
            className={cn("text-[11px] px-2.5 py-1 rounded-full font-medium transition-all cursor-pointer border",
              deptFilter === d.name ? "border-transparent text-white" : "border-border text-muted-foreground hover:bg-muted"
            )}
            style={deptFilter === d.name ? { backgroundColor: d.color } : {}}>
            {d.name.replace(" Team", "")} ({d.tasks.length})
          </button>
        ))}
      </motion.div>

      {/* Department Cards */}
      <motion.div variants={fadeUp} className="space-y-3">
        {filteredDepts.map((dept) => {
          const isExpanded = expandedDept === dept.name;
          return (
            <div key={dept.name} className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">

              {/* Department Header */}
              <div className="px-5 py-4 cursor-pointer flex items-center justify-between" onClick={() => setExpandedDept(isExpanded ? null : dept.name)}>
                <div className="flex items-center gap-3">
                  <div className="w-1 h-8 rounded-full" style={{ backgroundColor: dept.color }} />
                  <h3 className="text-sm font-bold">{dept.name}</h3>
                  <span className="text-[10px] text-muted-foreground">
                    {dept.tasks.length} task{dept.tasks.length !== 1 ? "s" : ""}
                  </span>
                  {dept.highCount > 0 && (
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                      {dept.highCount} urgent
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-muted-foreground">{formatNumber(dept.totalMentions)} mentions</span>
                  {isExpanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
                </div>
              </div>

              {/* Tasks */}
              {isExpanded && (
                <div className="border-t border-border px-5 pb-4 pt-3 space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
                  {dept.tasks.map((task: any, i: number) => {
                    const ps = PRIORITY_STYLES[task.priority] || PRIORITY_STYLES.medium;
                    return (
                      <div key={i} className={cn("rounded-xl border border-border p-4 border-l-4", ps.border)}>

                        {/* Task Header */}
                        <div className="flex items-start justify-between gap-3 mb-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1.5">
                              <span className={cn("w-2 h-2 rounded-full", ps.dot)} />
                              <span className={cn("text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full", ps.badge)}>{task.priority}</span>
                              {task.area && <span className="text-[10px] text-muted-foreground">{task.area}</span>}
                            </div>
                            <h4 className="text-sm font-bold leading-snug">{task.title}</h4>
                          </div>
                          <button onClick={(e) => { e.stopPropagation(); sendToTeam(task); }}
                            className="shrink-0 flex items-center gap-1 text-[10px] font-medium px-2.5 py-1.5 rounded-lg border border-blue-200 text-blue-700 dark:border-blue-800 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/20 transition-colors cursor-pointer">
                            <Send className="w-3 h-3" /> Send to {task.department.replace(" Team", "")}
                          </button>
                        </div>

                        {/* Description */}
                        <p className="text-xs text-muted-foreground leading-relaxed mb-3">{task.description}</p>

                        {/* Two Column: Evidence + Actions */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {/* Evidence */}
                          {task.evidence?.length > 0 && (
                            <div className="rounded-lg bg-muted/30 p-3">
                              <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground mb-2">Evidence ({task.evidence.length} sources)</p>
                              <div className="space-y-2.5">
                                {task.evidence.slice(0, 3).map((e: any, j: number) => {
                                  const text = typeof e === "string" ? e : (e.text || "");
                                  const platform = typeof e === "object" ? e.platform : null;
                                  const url = typeof e === "object" ? e.source_url : null;
                                  const platformColor = platform === "reddit" ? "#FF5700" : platform === "instagram" ? "#E1306C" : platform === "youtube" ? "#FF0000" : platform === "telegram" ? "#0088CC" : "#9CA3AF";
                                  return (
                                    <div key={j} className="rounded-lg border border-border/50 bg-card p-2.5">
                                      <p className="text-[11px] text-foreground/80 italic leading-relaxed">&ldquo;{text}&rdquo;</p>
                                      <div className="flex items-center gap-2 mt-1.5">
                                        {platform && <span className="text-[9px] font-semibold not-italic" style={{ color: platformColor }}>{platform}</span>}
                                        {e.similarity > 0 && <span className="text-[9px] text-muted-foreground">sim: {e.similarity}</span>}
                                        {url && <a href={url} target="_blank" rel="noopener noreferrer" className="text-[9px] text-purple-600 hover:underline ml-auto cursor-pointer flex items-center gap-0.5">View source <span className="text-[8px]">↗</span></a>}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}

                          {/* Recommended Actions */}
                          {task.suggestedActions?.length > 0 && (
                            <div className="rounded-lg bg-muted/30 p-3">
                              <p className="text-[9px] font-bold uppercase tracking-widest text-muted-foreground mb-2">Recommended Actions</p>
                              <div className="space-y-1.5">
                                {task.suggestedActions.map((action: string, j: number) => (
                                  <div key={j} className="flex items-start gap-2 text-[11px]">
                                    <CheckCircle2 className="w-3 h-3 text-muted-foreground mt-0.5 shrink-0" />
                                    <span>{action}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Footer */}
                        <div className="flex items-center justify-between mt-3 pt-2 border-t border-border/50">
                          <span className="text-[10px] text-muted-foreground">{formatNumber(task.mentionCount)} mentions analyzed</span>
                          {task.rag?.matched_keywords?.length > 0 && (
                            <div className="flex gap-1">
                              {task.rag.matched_keywords.slice(0, 4).map((kw: string, j: number) => (
                                <span key={j} className="text-[9px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 dark:bg-purple-900/20 dark:text-purple-400">{kw}</span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </motion.div>

      {/* Footer */}
      <motion.div variants={fadeUp} className="text-center pt-2">
        <p className="text-[10px] text-muted-foreground/60">
          {actionables.length} tasks across {deptList.length} departments — generated from {formatNumber(stats.totalMentionsAnalyzed || 0)} mentions via semantic search
        </p>
      </motion.div>
    </motion.div>
  );
}
