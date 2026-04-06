"use client";

import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

interface ContagionNode {
  label: string;
  color: string;
  timestamp: string;
}

interface ContagionChainProps {
  nodes: ContagionNode[];
}

export default function ContagionChain({ nodes }: ContagionChainProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
      <div className="flex flex-col md:flex-row items-start md:items-center gap-2 md:gap-0">
        {nodes.map((node, i) => (
          <motion.div
            key={i}
            className="flex items-center"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.15, duration: 0.3 }}
          >
            <div className="flex flex-col items-center">
              <div
                className="rounded-lg px-4 py-2 text-xs font-semibold text-white whitespace-nowrap"
                style={{ backgroundColor: node.color }}
              >
                {node.label}
              </div>
              <span className="text-[10px] text-muted-foreground mt-1">
                {node.timestamp}
              </span>
            </div>

            {i < nodes.length - 1 && (
              <ChevronRight className="h-4 w-4 text-muted-foreground mx-1 shrink-0 hidden md:block" />
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
