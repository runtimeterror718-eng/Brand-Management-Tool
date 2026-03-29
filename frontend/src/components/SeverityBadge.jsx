import React from 'react'

const COLORS = {
  critical: 'bg-red-100 text-red-800 border-red-200',
  high: 'bg-orange-100 text-orange-800 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-green-100 text-green-800 border-green-200',
}

export default function SeverityBadge({ level, score }) {
  const color = COLORS[level] || COLORS.low

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${color}`}>
      {level}
      {score != null && <span className="opacity-70">({(score * 100).toFixed(0)}%)</span>}
    </span>
  )
}
