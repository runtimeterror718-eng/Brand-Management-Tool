"use client";

import { Brain } from "lucide-react";

function parseAnalysis(text: string): { heading: string; body: string }[] {
  if (!text) return [];

  // Strip markdown formatting
  let cleaned = text
    .replace(/#{1,6}\s*/g, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/__(.+?)__/g, "$1")
    .replace(/_(.+?)_/g, "$1")
    .replace(/`(.+?)`/g, "$1")
    .replace(/```[\s\S]*?```/g, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/!\[.*?\]\(.*?\)/g, "")
    .replace(/^\s*>\s*/gm, "")
    .replace(/---+/g, "")
    .trim();

  // Split into sections by numbered items or dash bullets
  const lines = cleaned.split(/\n/).map(l => l.trim()).filter(Boolean);
  const cards: { heading: string; body: string }[] = [];
  let currentHeading = "";
  let currentBody: string[] = [];

  for (const line of lines) {
    // Detect heading patterns: "1. Something:", "- Something:", "Threat Name: X"
    const numberedMatch = line.match(/^\d+[.)]\s*(.+)/);
    const dashMatch = line.match(/^[-–•]\s*(.+)/);

    if (numberedMatch || dashMatch) {
      // Save previous card
      if (currentHeading || currentBody.length) {
        cards.push({ heading: currentHeading, body: currentBody.join(" ") });
      }
      const content = (numberedMatch?.[1] || dashMatch?.[1] || line).trim();
      // Split heading from body at colon or period
      const colonIdx = content.indexOf(":");
      const periodIdx = content.indexOf(". ");
      if (colonIdx > 0 && colonIdx < 60) {
        currentHeading = content.slice(0, colonIdx).trim();
        currentBody = [content.slice(colonIdx + 1).trim()];
      } else if (periodIdx > 0 && periodIdx < 80) {
        currentHeading = content.slice(0, periodIdx).trim();
        currentBody = [content.slice(periodIdx + 2).trim()];
      } else {
        currentHeading = content.length > 80 ? "" : content;
        currentBody = content.length > 80 ? [content] : [];
      }
    } else {
      currentBody.push(line);
    }
  }
  if (currentHeading || currentBody.length) {
    cards.push({ heading: currentHeading, body: currentBody.join(" ") });
  }

  // If no structured cards found, split into sentences
  if (cards.length === 0 && cleaned.length > 0) {
    const sentences = cleaned.split(/(?<=[.!?])\s+/).filter(s => s.length > 10);
    for (const s of sentences.slice(0, 5)) {
      cards.push({ heading: "", body: s });
    }
  }

  return cards.filter(c => c.heading || c.body).slice(0, 6);
}

interface RAGInsightProps {
  analysis: string;
  confidence: number;
  mentionsUsed: number;
  avgSimilarity: number;
  title?: string;
  sentimentBreakdown?: Record<string, number>;
}

export default function RAGInsight({
  analysis,
  confidence,
  mentionsUsed,
  avgSimilarity,
  title = "AI Analysis",
  sentimentBreakdown,
}: RAGInsightProps) {
  const confidencePct = Math.round(confidence * 100);
  const cards = parseAnalysis(analysis);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="w-3.5 h-3.5 text-purple-500" />
          <h3 className="text-xs font-semibold text-purple-600 dark:text-purple-400 uppercase tracking-widest">{title}</h3>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
          <span className="font-medium">{confidencePct}% confidence</span>
          <span>from {mentionsUsed} sources</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
        {cards.map((card, i) => (
          <div key={i} className="rounded-xl border border-border bg-card p-3.5 hover:shadow-sm transition-shadow">
            {card.heading && (
              <p className="text-sm font-semibold text-foreground mb-1">{card.heading}</p>
            )}
            {card.body && (
              <p className="text-xs text-muted-foreground leading-relaxed">{card.body}</p>
            )}
          </div>
        ))}
      </div>

      {sentimentBreakdown && Object.keys(sentimentBreakdown).length > 0 && (
        <div className="flex gap-2">
          {Object.entries(sentimentBreakdown).map(([label, count]) => (
            <span key={label}
              className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                label === "negative" ? "bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400"
                : label === "positive" ? "bg-green-100 text-green-600 dark:bg-green-900/20 dark:text-green-400"
                : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
              }`}>
              {label}: {count}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
