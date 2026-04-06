"use client"

import { useEffect, useRef, useState } from "react"
import { Info } from "lucide-react"

interface BrandScoreProps {
  title: string
  description: string
  score: number | null
  max?: number
  linkHref?: string
  linkLabel?: string
}

function getStrengthColor(score: number | null, max: number): { label: string; colors: string[]; badge: string } {
  if (!score) return { label: "No data", colors: ["#9CA3AF", "#6B7280"], badge: "bg-gray-100 text-gray-500" }
  const pct = score / max
  if (pct >= 0.7) return { label: "Strong", colors: ["hsl(142,71%,65%)", "hsl(142,71%,45%)"], badge: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300" }
  if (pct >= 0.4) return { label: "Moderate", colors: ["hsl(38,92%,65%)", "hsl(38,92%,45%)"], badge: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300" }
  return { label: "Weak", colors: ["hsl(0,84%,70%)", "hsl(0,84%,50%)"], badge: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300" }
}

function HalfCircle({ score, max }: { score: number | null; max: number }) {
  const ref = useRef<SVGCircleElement>(null)
  const [gradId] = useState(() => `sg-${Math.random().toString(36).slice(2, 6)}`)
  const r = 42
  const circ = 2 * Math.PI * r
  const half = circ / 2
  const offset = score !== null ? Math.min(score / max, 1) * -half : -(half / 2)
  const { colors } = getStrengthColor(score, max)

  useEffect(() => {
    ref.current?.animate(
      [{ strokeDashoffset: "0", offset: 0 }, { strokeDashoffset: "0", offset: 0.3 }, { strokeDashoffset: offset.toString() }],
      { duration: 1400, easing: "cubic-bezier(0.65, 0, 0.35, 1)", fill: "forwards" },
    )
  }, [score, max, offset])

  return (
    <svg className="block mx-auto h-24 w-auto" viewBox="0 0 100 52" aria-hidden="true">
      <defs><linearGradient id={gradId} x1="0" y1="0" x2="1" y2="0">
        {colors.map((c, i) => <stop key={i} offset={`${i * 100}%`} stopColor={c} />)}
      </linearGradient></defs>
      <g fill="none" strokeWidth="9" transform="translate(50, 50)">
        <circle className="stroke-muted/15" r={r} />
        <circle ref={ref} stroke={`url(#${gradId})`} strokeDasharray={`${half} ${half}`} r={r} strokeLinecap="round" />
      </g>
    </svg>
  )
}

function ScoreNumber({ score }: { score: number | null }) {
  const digits = score !== null ? String(Math.floor(score)).split("") : []
  return (
    <div className="absolute bottom-0 w-full text-center">
      <div className="text-2xl font-bold h-9 overflow-hidden relative">
        <div className="absolute inset-0">
          {digits.map((d, i) => (
            <span key={i} className="inline-block animate-in slide-in-from-bottom-full fill-mode-both"
              style={{ animationDelay: `${500 + i * 120}ms`, animationDuration: `${800 + i * 200}ms` }}>{d}</span>
          ))}
        </div>
      </div>
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">out of 100</p>
    </div>
  )
}

function ScoreCard({ title, description, score, max = 100, linkHref, linkLabel }: BrandScoreProps) {
  const [showTooltip, setShowTooltip] = useState(false)
  const [visible, setVisible] = useState(false)
  const { label, badge } = getStrengthColor(score, max)

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 100)
    return () => clearTimeout(t)
  }, [])

  if (!visible) return <div className="flex-1 min-w-[200px] h-[260px]" />

  return (
    <div className="flex-1 min-w-[200px] rounded-2xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow animate-in fade-in slide-in-from-bottom-6 duration-700 fill-mode-both">
      <div className="p-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">{title}</h3>
            <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded-full ${badge}`}>{label}</span>
          </div>
          <div className="relative">
            <button
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <Info className="w-3.5 h-3.5" />
            </button>
            {showTooltip && (
              <div className="absolute right-0 top-6 z-50 w-64 p-3 rounded-xl border border-border shadow-xl text-xs leading-relaxed bg-white dark:bg-gray-900 text-gray-600 dark:text-gray-300">
                <p className="font-semibold text-foreground mb-1">What is {title}?</p>
                <p>{description}</p>
              </div>
            )}
          </div>
        </div>

        {/* Gauge */}
        <div className="relative mb-4">
          <HalfCircle score={score} max={max} />
          <ScoreNumber score={score} />
        </div>

        {/* Link */}
        {linkHref && (
          <a href={linkHref}
            className="block w-full text-center text-xs font-medium py-2 rounded-lg border border-border bg-muted/50 hover:bg-muted transition-colors cursor-pointer">
            {linkLabel || "View Details"}
          </a>
        )}
      </div>
    </div>
  )
}

export function BrandScoreCards({ scores }: { scores: BrandScoreProps[] }) {
  return (
    <div className="flex gap-3">
      {scores.map((card, i) => (
        <ScoreCard key={i} {...card} />
      ))}
    </div>
  )
}

export type { BrandScoreProps }
