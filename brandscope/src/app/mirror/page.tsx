"use client";

import { motion } from "framer-motion";
import GapBar from "@/components/dashboard/gap-bar";
import { perceptionGaps } from "@/lib/mock-data";

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

export default function MirrorPage() {
  return (
    <motion.div
      className="max-w-5xl mx-auto px-4 py-10 space-y-10"
      variants={stagger}
      initial="hidden"
      animate="show"
    >
      {/* Header */}
      <motion.div variants={fadeUp}>
        <h1 className="text-3xl font-bold tracking-tight">The Mirror</h1>
        <p className="text-gray-500 mt-1">Perception vs Reality</p>
      </motion.div>

      {/* Legend */}
      <motion.div variants={fadeUp} className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-purple-500 inline-block" />
          <span className="text-sm text-gray-600 dark:text-gray-400">What PW claims</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-teal-500 inline-block" />
          <span className="text-sm text-gray-600 dark:text-gray-400">What students think</span>
        </div>
      </motion.div>

      {/* Gap Bars */}
      <motion.div variants={stagger} className="space-y-6">
        {perceptionGaps.map((gap) => (
          <motion.div key={gap.claim} variants={fadeUp}>
            <GapBar
              claim={gap.claim}
              brandPush={gap.brandPush}
              marketAgreement={gap.marketAgreement}
              status={gap.status}
              statusColor={gap.statusColor}
              insight={gap.insight}
              sources={gap.sources}
            />
          </motion.div>
        ))}
      </motion.div>

      {/* Bottom Summary */}
      <motion.div
        variants={fadeUp}
        className="rounded-2xl border border-gray-200 dark:border-gray-800 p-6"
      >
        <p className="font-serif italic text-gray-600 dark:text-gray-400 leading-relaxed">
          The biggest credibility risk is the &ldquo;Best teachers in the industry&rdquo; claim.
          PW pushes it at 94% intensity, but only 38% of the market agrees — that&apos;s a 56-point
          gap, the largest across all four claims. With 40% faculty attrition, the Sankalp
          controversy still circulating, and the recent casteist slur adding another data point,
          this claim is actively damaging trust. Every time it appears in marketing, it invites
          comparison against reality. The &ldquo;Student-first approach&rdquo; claim is equally
          fragile at 30% agreement — consumer court rulings and no-refund complaints are writing
          their own version of the story. Only &ldquo;Tech-enabled learning&rdquo; holds up under
          scrutiny, and even that has recurring app-crash complaints eroding it at the edges.
        </p>
      </motion.div>
    </motion.div>
  );
}
