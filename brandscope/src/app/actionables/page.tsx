"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ClipboardCheck, Send, ChevronDown, ChevronUp, Brain, ExternalLink, Filter } from "lucide-react";
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
  "Engineering Team": "#639922",
  "Marketing Team": "#D4537E",
  "Customer Support Team": "#0088CC",
};

const PRIORITY_STYLES: Record<string, { border: string; badge: string }> = {
  high: { border: "border-l-red-500", badge: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
  medium: { border: "border-l-amber-500", badge: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" },
  low: { border: "border-l-green-500", badge: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" },
};

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

  const deptList = Array.from(departments.entries()).map(([name, tasks]) => ({
    name,
    tasks,
    highCount: tasks.filter((t: any) => t.priority === "high").length,
    totalMentions: tasks.reduce((s: number, t: any) => s + t.mentionCount, 0),
    color: DEPT_COLORS[name] || "#9CA3AF",
  })).sort((a, b) => b.highCount - a.highCount || b.tasks.length - a.tasks.length);

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
          {isLive && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Live</span>}
        </div>
        <p className="text-sm text-muted-foreground mt-0.5">Department-wise tasks generated from negative mention analysis</p>
      </motion.div>

      {/* Summary Metrics */}
      <motion.div variants={fadeUp} className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Total Tasks</p>
          <p className="text-xl font-bold mt-0.5"><AnimatedNumber value={stats.totalTasks || actionables.length} /></p>
        </div>
        <div className="rounded-xl border border-red-200 bg-red-50/30 dark:bg-red-950/10 p-3">
          <p className="text-[10px] text-red-600 uppercase tracking-widest font-semibold">High Priority</p>
          <p className="text-xl font-bold mt-0.5 text-red-600"><AnimatedNumber value={stats.highPriority || 0} /></p>
        </div>
        <div className="rounded-xl border border-amber-200 bg-amber-50/30 dark:bg-amber-950/10 p-3">
          <p className="text-[10px] text-amber-600 uppercase tracking-widest font-semibold">Medium</p>
          <p className="text-xl font-bold mt-0.5 text-amber-600"><AnimatedNumber value={stats.mediumPriority || 0} /></p>
        </div>
        <div className="rounded-xl border border-border bg-card p-3">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Departments</p>
          <p className="text-xl font-bold mt-0.5"><AnimatedNumber value={departments.size} /></p>
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
      <motion.div variants={fadeUp} className="space-y-4">
        {filteredDepts.map((dept) => {
          const isExpanded = expandedDept === dept.name;
          return (
            <motion.div key={dept.name} whileHover={{ y: -1 }} transition={{ duration: 0.15 }}
              className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">

              {/* Department Header — always visible */}
              <div className="p-5 cursor-pointer" onClick={() => setExpandedDept(isExpanded ? null : dept.name)}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-1.5 h-10 rounded-full" style={{ backgroundColor: dept.color }} />
                    <div>
                      <h3 className="text-base font-bold">{dept.name}</h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {dept.tasks.length} task{dept.tasks.length !== 1 ? "s" : ""} &middot; {dept.highCount > 0 ? `${dept.highCount} high priority` : "no critical items"} &middot; {formatNumber(dept.totalMentions)} mentions
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {dept.highCount > 0 && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                        {dept.highCount} urgent
                      </span>
                    )}
                    <div className="flex -space-x-1">
                      {dept.tasks.slice(0, 3).map((_: any, i: number) => (
                        <div key={i} className="w-2 h-2 rounded-full border border-white dark:border-gray-900"
                          style={{ backgroundColor: PRIORITY_STYLES[dept.tasks[i]?.priority]?.border?.replace("border-l-", "") === "red-500" ? "#E24B4A" : PRIORITY_STYLES[dept.tasks[i]?.priority]?.border?.includes("amber") ? "#BA7517" : "#639922" }} />
                      ))}
                    </div>
                    {isExpanded ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
                  </div>
                </div>
              </div>

              {/* Expanded Tasks */}
              {isExpanded && (
                <div className="border-t border-border px-5 pb-5 pt-3 space-y-3 animate-in fade-in slide-in-from-top-2 duration-300">
                  {dept.tasks.map((task: any, i: number) => {
                    const ps = PRIORITY_STYLES[task.priority] || PRIORITY_STYLES.medium;
                    return (
                      <div key={i} className={cn("rounded-xl border border-border bg-muted/30 p-4 border-l-4", ps.border)}>
                        <div className="flex items-start justify-between gap-3 mb-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={cn("text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full", ps.badge)}>{task.priority}</span>
                              <span className="text-[10px] text-muted-foreground">{task.rag?.probe_query ? "RAG-generated" : ""}</span>
                            </div>
                            <h4 className="text-sm font-bold">{task.title}</h4>
                            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{task.description}</p>
                          </div>
                          <button onClick={(e) => { e.stopPropagation(); sendToTeam(task); }}
                            className="shrink-0 flex items-center gap-1 text-[10px] font-medium px-2.5 py-1.5 rounded-lg bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 hover:bg-blue-200 transition-colors cursor-pointer">
                            <Send className="w-3 h-3" /> Send
                          </button>
                        </div>

                        {/* Evidence */}
                        {task.evidence?.length > 0 && (
                          <div className="mb-3">
                            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">Evidence</p>
                            <div className="space-y-1">
                              {task.evidence.slice(0, 3).map((e: any, j: number) => (
                                <div key={j} className="text-xs italic text-muted-foreground border-l-2 border-gray-200 dark:border-gray-700 pl-2 line-clamp-2">
                                  &ldquo;{typeof e === "string" ? e.slice(0, 150) : (e.text || "").slice(0, 150)}&rdquo;
                                  {e.platform && <span className="not-italic ml-1 text-[10px]" style={{ color: e.platform === "reddit" ? "#FF5700" : e.platform === "instagram" ? "#E1306C" : "#9CA3AF" }}>— {e.platform}</span>}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Suggested Actions */}
                        {task.suggestedActions?.length > 0 && (
                          <div>
                            <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">Recommended Actions</p>
                            <div className="space-y-1">
                              {task.suggestedActions.map((action: string, j: number) => (
                                <div key={j} className="flex items-start gap-2 text-xs">
                                  <div className="w-4 h-4 rounded border border-border shrink-0 mt-0.5" />
                                  <span>{action}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

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
            </motion.div>
          );
        })}
      </motion.div>

      {/* Insight */}
      <motion.div variants={fadeUp} className="rounded-2xl border border-purple-200/50 dark:border-purple-800/30 bg-purple-50/20 dark:bg-purple-950/10 p-5">
        <div className="flex items-center gap-2 mb-2">
          <Brain className="w-3.5 h-3.5 text-purple-500" />
          <h3 className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-widest">How Actions Are Generated</h3>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Each department receives tasks generated from semantic search across {formatNumber(stats.totalMentionsAnalyzed || 0)} mentions.
          {stats.probesRun} targeted queries identify issues, then negative mentions are retrieved via vector similarity search and analyzed
          to generate specific, evidence-grounded action items with recommended responses.
        </p>
      </motion.div>
    </motion.div>
  );
}
