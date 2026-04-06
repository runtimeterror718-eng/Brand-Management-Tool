"use client";

import { cn } from "@/lib/utils";
import { Heart } from "lucide-react";
import { formatNumber } from "@/lib/utils";

interface InstaHashtagCardProps {
  tag: string;
  posts: number;
  sentiment: "positive" | "mixed" | "negative";
  quote: string;
  likes: number;
}

const sentimentStyles: Record<string, string> = {
  positive: "bg-green-100 text-green-700",
  negative: "bg-red-100 text-red-700",
  mixed: "bg-amber-100 text-amber-700",
};

export default function InstaHashtagCard({
  tag,
  posts,
  sentiment,
  quote,
  likes,
}: InstaHashtagCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm bg-gradient-to-br from-pink-50/60 to-white">
      <div className="flex items-center gap-2 mb-3">
        <span
          className="text-sm font-bold"
          style={{ color: "#D4537E" }}
        >
          #{tag}
        </span>
        <span className="text-[10px] text-muted-foreground">
          {formatNumber(posts)} posts
        </span>
        <span
          className={cn(
            "inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium capitalize ml-auto",
            sentimentStyles[sentiment]
          )}
        >
          {sentiment}
        </span>
      </div>

      <p className="text-sm italic text-muted-foreground leading-relaxed mb-3">
        &ldquo;{quote}&rdquo;
      </p>

      <div className="flex items-center gap-1 text-muted-foreground">
        <Heart className="h-3.5 w-3.5" style={{ color: "#D4537E" }} />
        <span className="text-xs font-medium">{formatNumber(likes)}</span>
      </div>
    </div>
  );
}
