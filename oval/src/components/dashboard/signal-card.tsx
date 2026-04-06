"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface SignalCardProps {
  title: string;
  description: string;
  trend: "up" | "down" | "stable";
  severity: "red" | "amber" | "green";
}

const borderColors: Record<string, string> = {
  red: "#E24B4A",
  amber: "#BA7517",
  green: "#639922",
};

const TrendIcon = ({ trend }: { trend: "up" | "down" | "stable" }) => {
  if (trend === "up") return <TrendingUp className="h-4 w-4 text-green-600" />;
  if (trend === "down")
    return <TrendingDown className="h-4 w-4 text-red-600" />;
  return <Minus className="h-4 w-4 text-gray-400" />;
};

export default function SignalCard({
  title,
  description,
  trend,
  severity,
}: SignalCardProps) {
  return (
    <div
      className="rounded-xl border border-border bg-card p-5 shadow-sm"
      style={{ borderLeftWidth: 3, borderLeftColor: borderColors[severity] }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="text-sm font-semibold mb-1">{title}</h4>
          <p className="text-xs text-muted-foreground leading-relaxed">
            {description}
          </p>
        </div>
        <TrendIcon trend={trend} />
      </div>
    </div>
  );
}
