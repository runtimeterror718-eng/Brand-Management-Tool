import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getBrands, getSeverityScores, getLatestAnalysis } from '../lib/supabase'
import SeverityBadge from '../components/SeverityBadge'

export default function Dashboard() {
  const [brands, setBrands] = useState([])
  const [loading, setLoading] = useState(true)
  const [brandStats, setBrandStats] = useState({})

  useEffect(() => {
    async function load() {
      try {
        const brandList = await getBrands()
        setBrands(brandList)

        // Load stats for each brand
        const stats = {}
        for (const brand of brandList) {
          const [severity, analysis] = await Promise.all([
            getSeverityScores(brand.id, { limit: 100 }),
            getLatestAnalysis(brand.id),
          ])

          const levels = { critical: 0, high: 0, medium: 0, low: 0 }
          severity.forEach((s) => {
            levels[s.severity_level] = (levels[s.severity_level] || 0) + 1
          })

          stats[brand.id] = {
            severity: levels,
            totalMentions: analysis?.total_mentions || 0,
            overallSentiment: analysis?.overall_sentiment || 0,
            themes: analysis?.themes || [],
          }
        }
        setBrandStats(stats)
      } catch (err) {
        console.error('Failed to load dashboard:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return <div className="text-center py-20 text-gray-500">Loading dashboard...</div>
  }

  if (brands.length === 0) {
    return (
      <div className="text-center py-20">
        <h2 className="text-xl font-semibold mb-2">No brands configured</h2>
        <p className="text-gray-500">Add brands via the API or set MONITORED_BRANDS in .env</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Brand Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {brands.map((brand) => {
          const stats = brandStats[brand.id] || {}
          const sev = stats.severity || {}

          return (
            <Link
              key={brand.id}
              to={`/brand/${brand.id}`}
              className="bg-white rounded-xl border p-5 hover:shadow-lg transition-shadow"
            >
              <h2 className="text-lg font-semibold mb-2">{brand.name}</h2>

              <div className="flex gap-2 mb-3 flex-wrap">
                {(brand.platforms || []).map((p) => (
                  <span key={p} className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                    {p}
                  </span>
                ))}
              </div>

              <div className="flex gap-2 mb-3">
                {sev.critical > 0 && <SeverityBadge level="critical" />}
                {sev.high > 0 && <SeverityBadge level="high" />}
                {sev.medium > 0 && <SeverityBadge level="medium" />}
                {sev.low > 0 && <SeverityBadge level="low" />}
              </div>

              <div className="text-sm text-gray-500">
                <p>Mentions: {stats.totalMentions || 0}</p>
                <p>
                  Sentiment:{' '}
                  <span
                    className={
                      (stats.overallSentiment || 0) > 0
                        ? 'text-green-600'
                        : (stats.overallSentiment || 0) < 0
                        ? 'text-red-600'
                        : ''
                    }
                  >
                    {(stats.overallSentiment || 0).toFixed(2)}
                  </span>
                </p>
              </div>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
