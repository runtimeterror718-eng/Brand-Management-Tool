"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import CounterStrategyCard from "@/components/dashboard/counter-strategy-card";
import SectionDivider from "@/components/dashboard/section-divider";
import { counterStrategies } from "@/lib/mock-data";

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const narrativeOptions = [
  "PW is losing its best teachers",
  "PW is becoming the next BYJU'S",
  "Casteist slur incident",
  "Overpriced offline centres",
];

export default function WarRoomPage() {
  const [selectedNarrative, setSelectedNarrative] = useState(narrativeOptions[0]);

  return (
    <motion.div
      className="max-w-5xl mx-auto px-4 py-10 space-y-10"
      variants={stagger}
      initial="hidden"
      animate="show"
    >
      {/* Header */}
      <motion.div variants={fadeUp}>
        <h1 className="text-3xl font-bold tracking-tight">War Room</h1>
        <p className="text-gray-500 mt-1">Counter-narrative strategies and simulations</p>
      </motion.div>

      {/* Narrative Selector */}
      <motion.div variants={fadeUp}>
        <SectionDivider title="Select Narrative to Counter" />
        <div className="mt-4">
          <select
            value={selectedNarrative}
            onChange={(e) => setSelectedNarrative(e.target.value)}
            className="w-full md:w-96 px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent appearance-none cursor-pointer"
          >
            {narrativeOptions.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
          <p className="mt-2 text-sm text-gray-500">
            Showing counter-strategies for: <span className="font-medium">{selectedNarrative}</span>
          </p>
        </div>
      </motion.div>

      {/* Counter Strategy Cards */}
      <motion.div variants={stagger} className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {counterStrategies.map((strategy) => (
          <motion.div key={strategy.name} variants={fadeUp}>
            <CounterStrategyCard
              name={strategy.name}
              borderColor={strategy.borderColor}
              successRate={strategy.successRate}
              action={strategy.action}
              reactions={strategy.reactions}
              risk={strategy.risk}
            />
          </motion.div>
        ))}
      </motion.div>

      {/* Recommendation */}
      <motion.div
        variants={fadeUp}
        className="rounded-2xl border-2 border-purple-500 bg-purple-50 dark:bg-purple-950/20 p-6"
      >
        <h3 className="text-sm font-semibold text-purple-700 dark:text-purple-300 uppercase tracking-wide mb-3">
          Recommendation
        </h3>
        <p className="font-serif italic text-gray-700 dark:text-gray-300 leading-relaxed">
          Strategy A (Radical Transparency) has the highest probability of success at 68%, but
          only if retention data supports it. If faculty attrition hasn&apos;t improved from the
          40% FY24 figure, publishing it will accelerate the narrative rather than counter it.
          Fix the problem first — then fix the narrative. Transparency without substance is just
          a press release. If retention has genuinely improved, lead with the numbers and let
          long-tenured teachers speak on camera. Reddit will verify every claim, so the data
          must be airtight.
        </p>
      </motion.div>
    </motion.div>
  );
}
