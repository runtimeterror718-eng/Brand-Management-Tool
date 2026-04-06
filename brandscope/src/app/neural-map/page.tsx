"use client";

import { useState, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { Network, Filter } from "lucide-react";
import { useLiveData } from "@/lib/use-live-data";
import { formatNumber, cn } from "@/lib/utils";
import { stagger, fadeUp } from "@/lib/animations";
import { PageSkeleton } from "@/components/ui/page-skeleton";

const NetworkGraph = dynamic(
  () => import("@ant-design/graphs").then((mod) => mod.NetworkGraph),
  { ssr: false, loading: () => <div className="flex items-center justify-center h-[600px]"><div className="text-center"><Network className="w-8 h-8 text-purple-500 mx-auto mb-3 animate-pulse" /><p className="text-sm text-muted-foreground">Rendering neural map...</p></div></div> }
);

const GROUP_LABELS: Record<string, string> = {
  brand: "Brand", platform: "Platform", competitor: "Competitor",
  topic: "Topic", person: "Person", channel: "Channel", cluster: "Cluster",
};
const GROUP_COLORS: Record<string, string> = {
  brand: "#534AB7", platform: "#378ADD", competitor: "#E24B4A",
  topic: "#BA7517", person: "#1D9E75", channel: "#D4537E", cluster: "#6B7280",
};

export default function NeuralMapPage() {
  const { data: d, isLive, loading } = useLiveData<any>("/api/neural-map", null);
  const [activeGroups, setActiveGroups] = useState<Set<string>>(new Set(Object.keys(GROUP_LABELS)));
  const [selectedNode, setSelectedNode] = useState<any>(null);

  if (loading) return <PageSkeleton title="Neural Map" color="#534AB7" />;

  const allNodes = d?.nodes || [];
  const allLinks = d?.links || [];
  const stats = d?.stats || {};

  const visibleNodeIds = new Set(allNodes.filter((n: any) => activeGroups.has(n.group)).map((n: any) => n.id));

  // Transform to Ant Design G6 format
  const graphData = {
    nodes: allNodes.filter((n: any) => visibleNodeIds.has(n.id)).map((n: any) => ({
      id: n.id,
      data: {
        label: n.label,
        group: n.group,
        cluster: n.group,
        size: Math.max(20, n.size * 2),
        ...n.metadata,
      },
      style: {
        fill: n.color || GROUP_COLORS[n.group] || "#6B7280",
        stroke: n.group === "brand" ? "#fff" : "transparent",
        lineWidth: n.group === "brand" ? 3 : 0,
        labelText: n.label,
        labelFontSize: n.group === "brand" ? 14 : n.size > 10 ? 11 : 9,
        labelFill: "#e5e7eb",
        labelPlacement: "bottom" as const,
        labelOffsetY: 4,
        iconSrc: undefined,
      },
    })),
    edges: allLinks
      .filter((l: any) => visibleNodeIds.has(l.source) && visibleNodeIds.has(l.target))
      .map((l: any, i: number) => ({
        id: `e-${i}`,
        source: l.source,
        target: l.target,
        data: { label: l.label, sentiment: l.sentiment, mentions: l.mentions },
        style: {
          stroke: l.sentiment === "positive" ? "#639922" : l.sentiment === "negative" ? "#E24B4A" : l.sentiment === "mixed" ? "#BA7517" : "#374151",
          lineWidth: Math.max(0.5, Math.min(l.strength * 0.4, 3)),
          opacity: 0.6,
          endArrow: false,
        },
      })),
  };

  const toggleGroup = (group: string) => {
    const next = new Set(activeGroups);
    if (next.has(group)) next.delete(group); else next.add(group);
    setActiveGroups(next);
  };

  return (
    <motion.div className="max-w-[1400px] mx-auto px-4 py-6 space-y-4" variants={stagger} initial="hidden" animate="show">

      <motion.div variants={fadeUp} className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <Network className="w-5 h-5 text-purple-500" />
            <h1 className="text-2xl font-bold tracking-tight">Neural Map</h1>
            {isLive && <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">Live</span>}
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            {stats.totalNodes || 0} entities and {stats.totalLinks || 0} connections — PW&apos;s brand intelligence network
          </p>
        </div>
      </motion.div>

      {/* Filter Tabs */}
      <motion.div variants={fadeUp} className="flex items-center gap-2 flex-wrap">
        <Filter className="w-3.5 h-3.5 text-muted-foreground" />
        {Object.entries(GROUP_LABELS).map(([group, label]) => {
          const count = stats.groups?.[group] || 0;
          const active = activeGroups.has(group);
          return (
            <button key={group} onClick={() => toggleGroup(group)}
              className={cn("text-[11px] px-2.5 py-1 rounded-full font-medium transition-all cursor-pointer border",
                active ? "border-transparent text-white" : "border-border text-muted-foreground bg-transparent hover:bg-muted"
              )}
              style={active ? { backgroundColor: GROUP_COLORS[group] } : {}}>
              {label} ({count})
            </button>
          );
        })}
      </motion.div>

      {/* Graph + Side Panel */}
      <motion.div variants={fadeUp} className="flex gap-4">
        {/* Graph Canvas */}
        <div className="flex-1 rounded-2xl border border-border overflow-hidden bg-[#0f0f14]" style={{ height: 620 }}>
          {graphData.nodes.length > 0 && (
            <NetworkGraph
              data={graphData}
              autoFit
              animation
              layout={{
                type: "d3-force",
                preventOverlap: true,
                nodeStrength: -200,
                linkDistance: 120,
                collide: { radius: 40 },
              }}
              node={{
                type: "circle",
                style: (d: any) => ({
                  size: d.data?.size || 24,
                  fill: d.style?.fill || "#6B7280",
                  stroke: d.style?.stroke || "transparent",
                  lineWidth: d.style?.lineWidth || 0,
                  labelText: d.style?.labelText || d.id,
                  labelFontSize: d.style?.labelFontSize || 10,
                  labelFill: "#e5e7eb",
                  labelPlacement: "bottom",
                  labelOffsetY: 4,
                }),
              }}
              edge={{
                type: "line",
                style: (d: any) => ({
                  stroke: d.style?.stroke || "#374151",
                  lineWidth: d.style?.lineWidth || 1,
                  opacity: d.style?.opacity || 0.5,
                }),
              }}
              behaviors={["drag-canvas", "zoom-canvas", "drag-element", "hover-activate"]}
              onReady={(graph: any) => {
                graph.on("node:click", (evt: any) => {
                  const nodeId = evt.target?.id;
                  const node = allNodes.find((n: any) => n.id === nodeId);
                  if (node) setSelectedNode(node);
                });
              }}
            />
          )}
        </div>

        {/* Side Panel */}
        <div className="w-64 shrink-0 space-y-3">
          {/* Legend */}
          <div className="rounded-xl border border-border bg-card p-3">
            <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">Legend</h4>
            <div className="space-y-1.5">
              {Object.entries(GROUP_LABELS).map(([group, label]) => (
                <div key={group} className="flex items-center gap-2 text-xs">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: GROUP_COLORS[group] }} />
                  <span className="font-medium">{label}</span>
                  <span className="text-muted-foreground ml-auto">{stats.groups?.[group] || 0}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-2 border-t border-border space-y-1">
              <p className="text-[10px] font-semibold text-muted-foreground">Edge Sentiment</p>
              <div className="flex items-center gap-2 text-[10px]"><span className="w-6 h-0.5 rounded bg-[#639922]" />Positive</div>
              <div className="flex items-center gap-2 text-[10px]"><span className="w-6 h-0.5 rounded bg-[#E24B4A]" />Negative</div>
              <div className="flex items-center gap-2 text-[10px]"><span className="w-6 h-0.5 rounded bg-[#BA7517]" />Mixed</div>
            </div>
          </div>

          {/* Selected Node */}
          {selectedNode && (
            <div className="rounded-xl border border-border bg-card p-3 animate-in fade-in duration-300">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-3 h-3 rounded-full" style={{ backgroundColor: selectedNode.color || GROUP_COLORS[selectedNode.group] }} />
                <h4 className="text-sm font-bold">{selectedNode.label}</h4>
              </div>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">{GROUP_LABELS[selectedNode.group]}</p>
              {selectedNode.metadata && (
                <div className="space-y-1 text-xs">
                  {selectedNode.metadata.mentions != null && <div className="flex justify-between"><span className="text-muted-foreground">Mentions</span><span className="font-medium">{selectedNode.metadata.mentions}</span></div>}
                  {selectedNode.metadata.subscribers != null && <div className="flex justify-between"><span className="text-muted-foreground">Subscribers</span><span className="font-medium">{formatNumber(selectedNode.metadata.subscribers)}</span></div>}
                  {selectedNode.metadata.members != null && <div className="flex justify-between"><span className="text-muted-foreground">Members</span><span className="font-medium">{formatNumber(selectedNode.metadata.members)}</span></div>}
                  {selectedNode.metadata.negPct != null && <div className="flex justify-between"><span className="text-muted-foreground">Negative</span><span className="font-medium text-red-500">{selectedNode.metadata.negPct}%</span></div>}
                  {selectedNode.metadata.positivePct != null && <div className="flex justify-between"><span className="text-muted-foreground">Positive</span><span className="font-medium text-green-500">{selectedNode.metadata.positivePct}%</span></div>}
                  {selectedNode.metadata.isFake && <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-red-700">FAKE CHANNEL</span>}
                </div>
              )}
              <div className="mt-3 pt-2 border-t border-border">
                <p className="text-[10px] font-semibold text-muted-foreground mb-1">Connections</p>
                <div className="space-y-1 max-h-[180px] overflow-y-auto">
                  {allLinks.filter((l: any) => l.source === selectedNode.id || l.target === selectedNode.id).slice(0, 10).map((l: any, i: number) => {
                    const otherId = l.source === selectedNode.id ? l.target : l.source;
                    const other = allNodes.find((n: any) => n.id === otherId);
                    const sentColor = l.sentiment === "positive" ? "#639922" : l.sentiment === "negative" ? "#E24B4A" : "#BA7517";
                    return (
                      <div key={i} className="flex items-center gap-1.5 text-[10px]">
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: sentColor }} />
                        <span className="font-medium truncate">{other?.label || otherId}</span>
                        <span className="text-muted-foreground ml-auto">{l.mentions}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="rounded-xl border border-border bg-card p-3">
            <h4 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-2">Network Stats</h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between"><span className="text-muted-foreground">Visible Nodes</span><span className="font-medium">{graphData.nodes.length}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Connections</span><span className="font-medium">{graphData.edges.length}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Negative</span><span className="font-medium text-red-500">{allLinks.filter((l: any) => l.sentiment === "negative").length}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Positive</span><span className="font-medium text-green-500">{allLinks.filter((l: any) => l.sentiment === "positive").length}</span></div>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
