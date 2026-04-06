"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";

interface Suggestion {
  text: string;
  highlight: string;
  sentiment: "neutral" | "negative" | "warning";
}

interface AutocompletePreviewProps {
  suggestions: Suggestion[];
}

const sentimentTextColor: Record<string, string> = {
  neutral: "text-gray-500",
  negative: "text-red-600",
  warning: "text-amber-600",
};

export default function AutocompletePreview({
  suggestions,
}: AutocompletePreviewProps) {
  const negativeCount = suggestions.filter(
    (s) => s.sentiment === "negative"
  ).length;

  return (
    <div className="w-full max-w-xl">
      <div className="rounded-2xl border border-gray-200 bg-white shadow-lg overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100">
          <Search className="h-4 w-4 text-gray-400 shrink-0" />
          <div className="flex items-center text-sm text-gray-900">
            <span>Physics Wallah</span>
            <span className="ml-0.5 inline-block w-[2px] h-4 bg-gray-900 animate-[blink_1s_step-end_infinite]" />
          </div>
        </div>

        {/* Suggestions */}
        <ul className="py-1">
          {suggestions.map((suggestion, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.25 }}
              className="flex items-center gap-3 px-4 py-2 hover:bg-gray-50 cursor-default"
            >
              <Search className="h-3.5 w-3.5 text-gray-400 shrink-0" />
              <span className="text-sm">
                <span className="text-gray-700">{suggestion.text} </span>
                <span
                  className={cn(
                    "font-bold",
                    sentimentTextColor[suggestion.sentiment]
                  )}
                >
                  {suggestion.highlight}
                </span>
              </span>
            </motion.li>
          ))}
        </ul>
      </div>

      {negativeCount > 0 && (
        <p className="mt-3 text-xs text-red-600 font-medium">
          {negativeCount} of {suggestions.length} autocomplete suggestions carry
          negative sentiment
        </p>
      )}

      <style jsx>{`
        @keyframes blink {
          50% {
            opacity: 0;
          }
        }
      `}</style>
    </div>
  );
}
