"use client";

import { motion } from "framer-motion";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import { AnimatedNumber } from "@/components/ui/animated-chart";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: number;
  color?: string;
  trend?: number; // percentage change
  sparkline?: number[]; // 7 data points for mini chart
  suffix?: string;
  small?: boolean;
}

export function MetricCard({ label, value, color, trend, sparkline, suffix, small }: MetricCardProps) {
  const sparkData = sparkline?.map((v, i) => ({ v })) || [];
  const sparkColor = trend && trend > 0 ? "#639922" : trend && trend < 0 ? "#E24B4A" : color || "#9CA3AF";

  return (
    <motion.div
      whileHover={{ y: -2, boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}
      transition={{ duration: 0.2 }}
      className="rounded-xl border border-border bg-card p-3 cursor-default"
    >
      <p className="text-[10px] text-muted-foreground uppercase tracking-widest">{label}</p>
      <div className="flex items-end justify-between mt-0.5">
        <div>
          <p className={cn("font-bold", small ? "text-sm" : "text-xl")} style={{ color }}>
            {typeof value === "number" ? <AnimatedNumber value={value} suffix={suffix} /> : value}
          </p>
          {trend !== undefined && trend !== 0 && (
            <div className={cn("flex items-center gap-0.5 mt-0.5", trend > 0 ? "text-green-600" : "text-red-500")}>
              {trend > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              <span className="text-[10px] font-medium">{trend > 0 ? "+" : ""}{trend}%</span>
            </div>
          )}
        </div>
        {sparkData.length > 2 && (
          <ResponsiveContainer width={56} height={24}>
            <AreaChart data={sparkData}>
              <defs>
                <linearGradient id={`spark-${label}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={sparkColor} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={sparkColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="v" stroke={sparkColor} strokeWidth={1.5} fill={`url(#spark-${label})`} dot={false} animationDuration={1000} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </motion.div>
  );
}

export function MetricRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
      {children}
    </div>
  );
}
