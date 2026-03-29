import React, { useEffect, useState } from 'react'
import { getBrands, getSeverityScores } from '../lib/supabase'
import SeverityBadge from '../components/SeverityBadge'

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const brands = await getBrands()
        const allAlerts = []

        for (const brand of brands) {
          const scores = await getSeverityScores(brand.id, { limit: 50 })
          const critical = scores.filter((s) => s.severity_level === 'critical')
          const high = scores.filter((s) => s.severity_level === 'high')

          for (const s of [...critical, ...high]) {
            allAlerts.push({
              ...s,
              brand_name: brand.name,
            })
          }
        }

        // Sort by most recent
        allAlerts.sort((a, b) => new Date(b.computed_at) - new Date(a.computed_at))
        setAlerts(allAlerts)
      } catch (err) {
        console.error('Failed to load alerts:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <div className="text-center py-20 text-gray-500">Loading alerts...</div>

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Alerts</h1>

      {alerts.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border">
          <p className="text-gray-500">No critical or high severity alerts</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className="bg-white rounded-xl border p-4 flex items-center justify-between"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold">{alert.brand_name}</span>
                  <SeverityBadge level={alert.severity_level} score={alert.severity_score} />
                </div>
                <div className="text-xs text-gray-500 flex gap-4">
                  <span>Sentiment: {alert.sentiment_component?.toFixed(3)}</span>
                  <span>Engagement: {alert.engagement_component?.toFixed(3)}</span>
                  <span>Velocity: {alert.velocity_component?.toFixed(3)}</span>
                  <span>Keywords: {alert.keyword_component?.toFixed(3)}</span>
                </div>
              </div>
              <div className="text-xs text-gray-400">
                {alert.computed_at && new Date(alert.computed_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
