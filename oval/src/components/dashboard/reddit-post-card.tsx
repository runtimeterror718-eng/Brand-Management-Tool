"use client";

import { cn } from "@/lib/utils";
import { ArrowBigUp, MessageSquare } from "lucide-react";

interface RedditPostCardProps {
  subreddit: string;
  title: string;
  snippet: string;
  upvotes: number;
  comments: number;
  sentiment: "positive" | "negative" | "mixed";
}

const sentimentStyles: Record<string, string> = {
  positive: "bg-green-100 text-green-700",
  negative: "bg-red-100 text-red-700",
  mixed: "bg-amber-100 text-amber-700",
};

export default function RedditPostCard({
  subreddit,
  title,
  snippet,
  upvotes,
  comments,
  sentiment,
}: RedditPostCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span
              className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold text-white"
              style={{ backgroundColor: "#D85A30" }}
            >
              r/{subreddit}
            </span>
            <span
              className={cn(
                "inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium capitalize",
                sentimentStyles[sentiment]
              )}
            >
              {sentiment}
            </span>
          </div>
          <h4 className="text-sm font-bold mb-1 leading-snug">{title}</h4>
          <p className="text-xs italic text-muted-foreground leading-relaxed">
            {snippet}
          </p>
        </div>

        <div className="flex flex-col items-center gap-2 shrink-0 text-muted-foreground">
          <div className="flex items-center gap-1">
            <ArrowBigUp className="h-4 w-4" />
            <span className="text-xs font-medium">{upvotes}</span>
          </div>
          <div className="flex items-center gap-1">
            <MessageSquare className="h-3.5 w-3.5" />
            <span className="text-xs font-medium">{comments}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
