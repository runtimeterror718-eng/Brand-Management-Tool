"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, MessageCircle, X, Send, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface Source {
  content_text: string;
  platform: string;
  sentiment_label: string;
  likes: number;
}

export default function AskOval() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    answer: string;
    sources: Source[];
    stats?: { total: number; negative: number; positive: number };
    llm: boolean;
  } | null>(null);

  const handleAsk = async () => {
    if (!query.trim() || loading) return;
    setLoading(true);
    setResult(null);

    try {
      const resp = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: query }),
      });
      const data = await resp.json();
      if (data.presentation_only) {
        setIsOpen(false);
        toast.info("This feature requires Secret Keys and can be demonstrated during presentation", {
          duration: 5000,
        });
        return;
      }
      setResult(data);
    } catch {
      setResult({ answer: "Failed to connect. Check your API configuration.", sources: [], llm: false });
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    "What are students saying about PW teachers?",
    "How does PW compare to Allen?",
    "What are the main complaints on Reddit?",
    "Is Instagram sentiment different from Reddit?",
    "What do students think about PW pricing?",
  ];

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-20 md:bottom-6 right-6 z-50 bg-[#534AB7] text-white p-3.5 rounded-full shadow-lg hover:shadow-xl transition-all duration-200 cursor-pointer hover:scale-105"
        aria-label="Ask OVAL"
      >
        <MessageCircle className="h-5 w-5" />
      </button>

      {/* Modal */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end md:items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
            onClick={(e) => e.target === e.currentTarget && setIsOpen(false)}
          >
            <motion.div
              initial={{ y: 50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 50, opacity: 0 }}
              className="w-full max-w-2xl bg-[var(--card)] rounded-2xl shadow-2xl border border-[var(--border)] overflow-hidden max-h-[80vh] flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-[#534AB7]" />
                  <h2 className="font-semibold text-sm">Ask OVAL</h2>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#534AB7]/10 text-[#534AB7]">
                    RAG-powered
                  </span>
                </div>
                <button onClick={() => setIsOpen(false)} className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] cursor-pointer" aria-label="Close">
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-5 space-y-4">
                {/* Suggested questions */}
                {!result && !loading && (
                  <div className="space-y-2">
                    <p className="text-xs text-[var(--muted-foreground)]">Ask anything about your brand data:</p>
                    <div className="flex flex-wrap gap-2">
                      {suggestedQuestions.map((q) => (
                        <button
                          key={q}
                          onClick={() => { setQuery(q); }}
                          className="text-xs px-3 py-1.5 rounded-full border border-[var(--border)] text-[var(--muted-foreground)] hover:border-[#534AB7] hover:text-[#534AB7] transition-colors duration-200 cursor-pointer"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Loading */}
                {loading && (
                  <div className="flex items-center gap-3 py-8 justify-center">
                    <Loader2 className="h-5 w-5 animate-spin text-[#534AB7]" />
                    <span className="text-sm text-[var(--muted-foreground)]">Searching your data...</span>
                  </div>
                )}

                {/* Result */}
                {result && (
                  <div className="space-y-4">
                    {/* Stats */}
                    {result.stats && (
                      <div className="flex gap-3 text-xs text-[var(--muted-foreground)]">
                        <span>Searched {result.stats.total} mentions</span>
                        <span>{result.sources.length} relevant found</span>
                        {result.llm && <span className="text-[#534AB7]">AI-generated answer</span>}
                      </div>
                    )}

                    {/* Answer */}
                    <div className="rounded-xl bg-[var(--muted)] p-4">
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{result.answer}</p>
                    </div>

                    {/* Sources */}
                    {result.sources.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-[var(--muted-foreground)] mb-2">Sources ({result.sources.length} mentions)</p>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                          {result.sources.slice(0, 8).map((s, i) => (
                            <div key={i} className="text-xs p-2.5 rounded-lg border border-[var(--border)]">
                              <div className="flex items-center gap-2 mb-1">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                  s.platform === "reddit" ? "bg-[#D85A30]/10 text-[#D85A30]" : "bg-[#D4537E]/10 text-[#D4537E]"
                                }`}>
                                  {s.platform}
                                </span>
                                {s.sentiment_label && (
                                  <span className={`text-[10px] ${
                                    s.sentiment_label === "negative" ? "text-red-500" :
                                    s.sentiment_label === "positive" ? "text-green-500" : "text-gray-400"
                                  }`}>
                                    {s.sentiment_label}
                                  </span>
                                )}
                                {s.likes > 0 && <span className="text-[var(--muted-foreground)]">{s.likes} likes</span>}
                              </div>
                              <p className="text-[var(--foreground)] line-clamp-2">{s.content_text?.slice(0, 150)}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Input */}
              <div className="px-5 py-4 border-t border-[var(--border)]">
                <form onSubmit={(e) => { e.preventDefault(); handleAsk(); }} className="flex gap-2">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="What are students saying about..."
                    className="flex-1 px-4 py-2.5 rounded-xl border border-[var(--border)] bg-transparent text-sm focus:border-[#534AB7] focus:outline-none transition-colors duration-200"
                  />
                  <button
                    type="submit"
                    disabled={!query.trim() || loading}
                    className="px-4 py-2.5 rounded-xl bg-[#534AB7] text-white text-sm font-medium disabled:opacity-50 cursor-pointer hover:bg-[#4a42a3] transition-colors duration-200"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </form>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
