"use client";

import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface BriefCardProps {
  label?: string;
  children: ReactNode;
  variant?: "default" | "editorial";
}

export default function BriefCard({
  label,
  children,
  variant = "default",
}: BriefCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      {label && (
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
          {label}
        </p>
      )}
      <div
        className={cn(
          variant === "editorial" &&
            "font-serif text-muted-foreground leading-[1.7]"
        )}
      >
        {children}
      </div>
    </div>
  );
}
