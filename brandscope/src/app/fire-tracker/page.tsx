"use client";

import { motion } from "framer-motion";
import ContagionChain from "@/components/dashboard/contagion-chain";
import SectionDivider from "@/components/dashboard/section-divider";
import { contagionChain, activeNarratives, fadingNarratives } from "@/lib/mock-data";

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.12 } },
};

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5 } },
};

const severityColors: Record<string, string> = {
  red: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  amber: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  green: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
};

const velocityBarColor: Record<string, string> = {
  red: "bg-red-500",
  amber: "bg-amber-500",
  green: "bg-green-500",
};

const amplifiers = [
  { handle: "@Education_Watchdog", followers: "142K", role: "Edtech critic, ex-journalist" },
  { handle: "@JEETard_Memes", followers: "89K", role: "Student meme page, amplifies controversies" },
  { handle: "@DalitVoiceIndia", followers: "234K", role: "Caste discrimination accountability" },
  { handle: "@EdtechInsider_", followers: "67K", role: "Industry analyst, balanced but critical" },
  { handle: "@ParentForumIND", followers: "53K", role: "Parent community, fee/quality concerns" },
];

export default function FireTrackerPage() {
  return (
    <motion.div
      className="max-w-5xl mx-auto px-4 py-10 space-y-10"
      variants={stagger}
      initial="hidden"
      animate="show"
    >
      {/* Header */}
      <motion.div variants={fadeUp}>
        <h1 className="text-3xl font-bold tracking-tight">Fire Tracker</h1>
        <p className="text-gray-500 mt-1">Narrative velocity and crisis propagation</p>
      </motion.div>

      {/* Contagion Chain */}
      <motion.div variants={fadeUp}>
        <SectionDivider title="Latest Contagion Chain" />
        <p className="text-sm text-gray-500 mb-4">48 hours from tweet to national news</p>
        <ContagionChain nodes={contagionChain} />
      </motion.div>

      {/* Active Narratives */}
      <motion.div variants={fadeUp}>
        <SectionDivider title="Active Narratives" />
      </motion.div>
      <motion.div variants={stagger} className="space-y-4">
        {activeNarratives.map((narrative) => (
          <motion.div
            key={narrative.title}
            variants={fadeUp}
            className="rounded-2xl border border-gray-200 dark:border-gray-800 p-5"
          >
            <div className="flex items-start justify-between gap-4 mb-3">
              <h3 className="font-semibold text-lg">{narrative.title}</h3>
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${severityColors[narrative.severity]}`}
              >
                {narrative.severity === "red" ? "Critical" : narrative.severity === "amber" ? "Warning" : "Low"}
              </span>
            </div>
            <div className="mb-3">
              <div className="flex items-center justify-between text-sm text-gray-500 mb-1">
                <span>Velocity: {narrative.velocityLabel}</span>
                <span>{narrative.age}</span>
              </div>
              <div className="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${velocityBarColor[narrative.severity]}`}
                  style={{ width: `${Math.abs(narrative.velocity) * 100}%` }}
                />
              </div>
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* Fading Narratives */}
      <motion.div variants={fadeUp}>
        <SectionDivider title="Fading Narratives" />
      </motion.div>
      <motion.div variants={stagger} className="space-y-4">
        {fadingNarratives.map((narrative) => (
          <motion.div
            key={narrative.title}
            variants={fadeUp}
            className="rounded-2xl border border-gray-200 dark:border-gray-800 p-5"
          >
            <div className="flex items-start justify-between gap-4 mb-3">
              <h3 className="font-semibold text-lg">{narrative.title}</h3>
              <span
                className={`text-xs font-medium px-2.5 py-1 rounded-full whitespace-nowrap ${severityColors[narrative.severity]}`}
              >
                {narrative.severity === "green" ? "Fading" : "Cooling"}
              </span>
            </div>
            <div className="mb-3">
              <div className="flex items-center justify-between text-sm text-gray-500 mb-1">
                <span>Velocity: {narrative.velocityLabel}</span>
                <span>{narrative.age}</span>
              </div>
              <div className="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${velocityBarColor[narrative.severity]}`}
                  style={{ width: `${Math.abs(narrative.velocity) * 100}%` }}
                />
              </div>
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* Key Amplifiers */}
      <motion.div variants={fadeUp}>
        <SectionDivider title="Key Amplifier Accounts" />
      </motion.div>
      <motion.div
        variants={fadeUp}
        className="rounded-2xl border border-gray-200 dark:border-gray-800 overflow-hidden"
      >
        <div className="divide-y divide-gray-100 dark:divide-gray-800">
          {amplifiers.map((amp) => (
            <div key={amp.handle} className="px-5 py-4 flex items-center justify-between gap-4">
              <div>
                <p className="font-medium text-sm">{amp.handle}</p>
                <p className="text-xs text-gray-500">{amp.role}</p>
              </div>
              <span className="text-sm text-gray-500 whitespace-nowrap">{amp.followers} followers</span>
            </div>
          ))}
        </div>
        <div className="px-5 py-3 bg-gray-50 dark:bg-gray-900/50">
          <p className="text-xs text-gray-400 italic">
            Handles anonymized. Based on amplification patterns in the last 30 days.
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
}
