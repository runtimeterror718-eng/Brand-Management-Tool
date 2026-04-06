"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface HealthGaugeProps {
  score: number;
  label: string;
  color: string;
  trend: number;
  trendLabel: string;
}

export default function HealthGauge({
  score,
  label,
  color,
  trend,
  trendLabel,
}: HealthGaugeProps) {
  const clampedScore = Math.max(0, Math.min(100, score));

  const getColor = () => {
    if (clampedScore > 70) return "#639922";
    if (clampedScore >= 50) return "#BA7517";
    return "#E24B4A";
  };

  const arcColor = color || getColor();

  const radius = 80;
  const strokeWidth = 14;
  const cx = 100;
  const cy = 95;
  const startAngle = Math.PI;
  const totalArc = Math.PI;

  const describeArc = (fraction: number) => {
    const angle = startAngle - totalArc * fraction;
    const x1 = cx + radius * Math.cos(startAngle);
    const y1 = cy - radius * Math.sin(startAngle);
    const x2 = cx + radius * Math.cos(angle);
    const y2 = cy - radius * Math.sin(angle);
    const largeArc = fraction > 0.5 ? 1 : 0;
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`;
  };

  const circumference = Math.PI * radius;
  const bgPath = describeArc(1);

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width="200" height="115" viewBox="0 0 200 115">
        <path
          d={bgPath}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <motion.path
          d={bgPath}
          fill="none"
          stroke={arcColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference}
          animate={{
            strokeDashoffset:
              circumference - (circumference * clampedScore) / 100,
          }}
          transition={{ duration: 1.2, ease: "easeOut" }}
        />
      </svg>

      <div className="flex flex-col items-center -mt-4">
        <span className="text-4xl font-bold" style={{ color: arcColor }}>
          {clampedScore}
        </span>
        <span className="text-sm text-muted-foreground mt-0.5">{label}</span>
      </div>

      <div
        className={cn(
          "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
          trend < 0
            ? "bg-red-100 text-red-700"
            : "bg-green-100 text-green-700"
        )}
      >
        <span>{trend > 0 ? "+" : ""}{trend}%</span>
        <span>{trendLabel}</span>
      </div>
    </div>
  );
}
