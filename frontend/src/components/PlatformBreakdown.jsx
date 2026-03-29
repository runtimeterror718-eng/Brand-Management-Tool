import React from 'react'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

const PLATFORM_COLORS = {
  youtube: '#FF0000',
  telegram: '#0088cc',
  instagram: '#E4405F',
  reddit: '#FF4500',
  twitter: '#1DA1F2',
  seo_news: '#34A853',
  facebook: '#1877F2',
  linkedin: '#0A66C2',
}

export default function PlatformBreakdown({ data }) {
  // data: { youtube: 45, reddit: 30, ... }
  const chartData = Object.entries(data || {}).map(([name, value]) => ({
    name,
    value,
  }))

  return (
    <div className="bg-white rounded-xl border p-4">
      <h3 className="text-sm font-semibold mb-3">Platform Breakdown</h3>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            outerRadius={80}
            dataKey="value"
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.name}
                fill={PLATFORM_COLORS[entry.name] || '#6366f1'}
              />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
