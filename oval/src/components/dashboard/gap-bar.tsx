"use client";

import { cn } from "@/lib/utils";

interface GapBarProps {
  claim: string;
  brandPush: number;
  marketAgreement: number;
  status: string;
  statusColor: "red" | "amber" | "green";
  insight: string;
  sources: { reddit: number; youtube: number; google: number };
}

const statusStyles: Record<string, string> = {
  red: "bg-red-100 text-red-700",
  amber: "bg-amber-100 text-amber-700",
  green: "bg-green-100 text-green-700",
};

export default function GapBar({
  claim,
  brandPush,
  marketAgreement,
  status,
  statusColor,
  insight,
  sources,
}: GapBarProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-sm font-semibold">{claim}</h3>
        <span
          className={cn(
            "inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium shrink-0 ml-3",
            statusStyles[statusColor]
          )}
        >
          {status}
        </span>
      </div>

      <div className="space-y-2 mb-4">
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
              Brand Push
            </span>
            <span className="text-xs font-medium">{brandPush}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-gray-100">
            <div
              className="h-2 rounded-full"
              style={{
                width: `${brandPush}%`,
                backgroundColor: "#534AB7",
              }}
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
              Market Agreement
            </span>
            <span className="text-xs font-medium">{marketAgreement}%</span>
          </div>
          <div className="h-2 w-full rounded-full bg-gray-100">
            <div
              className="h-2 rounded-full"
              style={{
                width: `${marketAgreement}%`,
                backgroundColor: "#1D9E75",
              }}
            />
          </div>
        </div>
      </div>

      <p className="font-serif italic text-sm text-muted-foreground leading-relaxed mb-3">
        {insight}
      </p>

      <div className="flex gap-3 text-[10px] text-muted-foreground">
        <span>Reddit: {sources.reddit}</span>
        <span>YouTube: {sources.youtube}</span>
        <span>Google: {sources.google}</span>
      </div>
    </div>
  );
}
