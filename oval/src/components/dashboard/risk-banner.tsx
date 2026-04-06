"use client";

import { cn } from "@/lib/utils";

interface RiskBannerProps {
  title: string;
  tags: { label: string; color: "red" | "amber" | "green" }[];
  body: string;
}

const tagStyles: Record<string, string> = {
  red: "bg-red-100 text-red-700",
  amber: "bg-amber-100 text-amber-700",
  green: "bg-green-100 text-green-700",
};

export default function RiskBanner({ title, tags, body }: RiskBannerProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm border-l-[3px] border-l-[#E24B4A]">
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        <div className="flex flex-wrap gap-1.5">
          {tags.map((tag) => (
            <span
              key={tag.label}
              className={cn(
                "inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium",
                tagStyles[tag.color]
              )}
            >
              {tag.label}
            </span>
          ))}
        </div>
      </div>
      <p className="text-sm text-muted-foreground leading-relaxed">{body}</p>
    </div>
  );
}
