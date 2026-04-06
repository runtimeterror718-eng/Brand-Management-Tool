"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { GeoMention } from "@/lib/mock-data";

interface SupabaseGeoRow {
  state: string;
  state_code: string;
  lat: number;
  lng: number;
  total_mentions: number;
  negative_mentions: number;
  negative_pct: number;
  top_issue: string;
  reddit_count: number;
  instagram_count: number;
  twitter_count: number;
}

function supabaseToGeoMention(row: SupabaseGeoRow): GeoMention {
  return {
    state: row.state,
    stateCode: row.state_code,
    lat: row.lat,
    lng: row.lng,
    totalMentions: row.total_mentions,
    negativeMentions: row.negative_mentions,
    negativePct: row.negative_pct,
    topIssue: row.top_issue || "",
    platforms: {
      reddit: row.reddit_count,
      instagram: row.instagram_count,
      twitter: row.twitter_count,
    },
  };
}

interface GeoHeatmapProps {
  data: GeoMention[];
  brandId?: string;
  useLiveData?: boolean;
}

const INDIA_VIEWBOX = { x: 68, y: 6, width: 30, height: 30 };

function getColor(negativePct: number): string {
  if (negativePct >= 45) return "#E24B4A";
  if (negativePct >= 38) return "#D85A30";
  if (negativePct >= 30) return "#BA7517";
  if (negativePct >= 25) return "#F59E0B";
  return "#639922";
}

function getBubbleSize(totalMentions: number): number {
  if (totalMentions >= 500) return 1.8;
  if (totalMentions >= 300) return 1.4;
  if (totalMentions >= 150) return 1.1;
  return 0.8;
}

function latLngToSvg(lat: number, lng: number) {
  const x = ((lng - INDIA_VIEWBOX.x) / INDIA_VIEWBOX.width) * 600;
  const y = ((INDIA_VIEWBOX.y + INDIA_VIEWBOX.height - lat) / INDIA_VIEWBOX.height) * 600;
  return { x, y };
}

export default function GeoHeatmap({ data: mockData, brandId, useLiveData = false }: GeoHeatmapProps) {
  const [hovered, setHovered] = useState<GeoMention | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [liveData, setLiveData] = useState<GeoMention[] | null>(null);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    if (!useLiveData) return;
    const url = brandId ? `/api/geo?brand_id=${brandId}` : "/api/geo";
    fetch(url)
      .then((r) => r.json())
      .then((json) => {
        if (json.data && json.data.length > 0) {
          setLiveData(json.data.map(supabaseToGeoMention));
          setIsLive(true);
        }
      })
      .catch(() => {});
  }, [brandId, useLiveData]);

  const data = liveData || mockData;
  const sorted = [...data].sort((a, b) => b.negativePct - a.negativePct);
  const topHotspots = sorted.slice(0, 5);

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-semibold">Geographic Negativity Map</h3>
            {isLive ? (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                LIVE DATA
              </span>
            ) : (
              <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                MOCK DATA
              </span>
            )}
          </div>
          <p className="text-sm text-[var(--muted-foreground)]">
            Where negative sentiment is concentrated across India
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs text-[var(--muted-foreground)]">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#639922]" />
            &lt;25%
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#BA7517]" />
            25-38%
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#D85A30]" />
            38-45%
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#E24B4A]" />
            &gt;45%
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Map */}
        <div className="lg:col-span-2 relative">
          <svg
            viewBox="0 0 600 600"
            className="w-full h-auto"
            style={{ maxHeight: 500 }}
          >
            {/* India outline (simplified) */}
            <path
              d="M260,40 L310,35 L350,50 L380,45 L410,65 L430,90 L450,80 L480,95 L500,120 L510,150 L520,180 L530,220 L525,260 L510,290 L500,320 L480,350 L460,380 L440,400 L420,430 L390,450 L370,470 L350,490 L330,510 L310,520 L290,530 L270,540 L250,535 L230,520 L210,500 L190,470 L170,440 L155,410 L145,380 L140,350 L130,320 L125,290 L120,260 L115,230 L110,200 L115,170 L125,140 L140,115 L160,90 L185,70 L210,55 L240,45 Z"
              fill="var(--muted)"
              stroke="var(--border)"
              strokeWidth="1.5"
              opacity="0.5"
            />

            {/* State bubbles */}
            {data.map((item) => {
              const pos = latLngToSvg(item.lat, item.lng);
              const size = getBubbleSize(item.totalMentions);
              const color = getColor(item.negativePct);
              const r = size * 16;

              return (
                <g key={item.stateCode}>
                  {/* Pulse ring for high negativity */}
                  {item.negativePct >= 40 && (
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={r + 6}
                      fill="none"
                      stroke={color}
                      strokeWidth="1"
                      opacity="0.3"
                    >
                      <animate
                        attributeName="r"
                        values={`${r + 2};${r + 12};${r + 2}`}
                        dur="2s"
                        repeatCount="indefinite"
                      />
                      <animate
                        attributeName="opacity"
                        values="0.4;0.1;0.4"
                        dur="2s"
                        repeatCount="indefinite"
                      />
                    </circle>
                  )}

                  {/* Main bubble */}
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={r}
                    fill={color}
                    opacity="0.85"
                    className="cursor-pointer transition-all duration-200"
                    stroke="white"
                    strokeWidth="1.5"
                    onMouseEnter={(e) => {
                      setHovered(item);
                      const rect = (e.target as SVGElement).closest("svg")!.getBoundingClientRect();
                      setTooltipPos({
                        x: e.clientX - rect.left,
                        y: e.clientY - rect.top - 10,
                      });
                    }}
                    onMouseLeave={() => setHovered(null)}
                  />

                  {/* State label */}
                  <text
                    x={pos.x}
                    y={pos.y + r + 14}
                    textAnchor="middle"
                    className="fill-[var(--foreground)] text-[9px] font-medium"
                  >
                    {item.stateCode}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Tooltip */}
          <AnimatePresence>
            {hovered && (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="absolute pointer-events-none z-50 bg-[var(--card)] border border-[var(--border)] rounded-xl p-4 shadow-lg"
                style={{
                  left: Math.min(tooltipPos.x, 350),
                  top: tooltipPos.y - 120,
                  minWidth: 260,
                }}
              >
                <p className="font-semibold text-sm">{hovered.state}</p>
                <div className="mt-2 space-y-1 text-xs">
                  <div className="flex justify-between">
                    <span className="text-[var(--muted-foreground)]">Total mentions</span>
                    <span className="font-medium">{hovered.totalMentions.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--muted-foreground)]">Negative</span>
                    <span className="font-medium" style={{ color: getColor(hovered.negativePct) }}>
                      {hovered.negativeMentions} ({hovered.negativePct}%)
                    </span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-[var(--muted-foreground)]">Top issue</span>
                    <span className="font-medium text-right">{hovered.topIssue}</span>
                  </div>
                  <div className="flex gap-3 mt-2 pt-2 border-t border-[var(--border)]">
                    <span className="text-[#D85A30]">Reddit {hovered.platforms.reddit}</span>
                    <span className="text-[#D4537E]">IG {hovered.platforms.instagram}</span>
                    <span className="text-[#378ADD]">X {hovered.platforms.twitter}</span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Top hotspots list */}
        <div>
          <h4 className="text-sm font-semibold mb-3">Top Negativity Hotspots</h4>
          <div className="space-y-3">
            {topHotspots.map((item, i) => (
              <motion.div
                key={item.stateCode}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="rounded-lg border border-[var(--border)] p-3 cursor-pointer hover:shadow-md transition-shadow duration-200"
                onMouseEnter={() => setHovered(item)}
                onMouseLeave={() => setHovered(null)}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm">{item.state}</span>
                  <span
                    className="text-xs font-bold px-2 py-0.5 rounded-full"
                    style={{
                      color: getColor(item.negativePct),
                      backgroundColor: `${getColor(item.negativePct)}15`,
                    }}
                  >
                    {item.negativePct}% negative
                  </span>
                </div>

                {/* Negativity bar */}
                <div className="w-full h-1.5 rounded-full bg-[var(--muted)] mt-2 mb-2">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: getColor(item.negativePct) }}
                    initial={{ width: 0 }}
                    animate={{ width: `${item.negativePct}%` }}
                    transition={{ duration: 0.8, delay: i * 0.1 }}
                  />
                </div>

                <p className="text-xs text-[var(--muted-foreground)] italic">
                  {item.topIssue}
                </p>

                <div className="flex gap-2 mt-2 text-[10px] text-[var(--muted-foreground)]">
                  <span>r/ {item.platforms.reddit}</span>
                  <span>IG {item.platforms.instagram}</span>
                  <span>X {item.platforms.twitter}</span>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Insight */}
          <div className="mt-4 p-3 rounded-lg bg-[var(--muted)]">
            <p className="text-xs font-serif italic text-[var(--muted-foreground)] leading-relaxed">
              Rajasthan and J&K have the highest negativity concentration.
              Rajasthan is driven by Allen comparisons in the offline coaching hub.
              J&K spike is entirely from the consumer court refund case where PW didn&apos;t appear.
              UP and Delhi are high-volume states where faculty attrition narrative dominates.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
