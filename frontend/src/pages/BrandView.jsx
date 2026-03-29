import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { supabase, getMentions, getSeverityScores, getLatestAnalysis } from '../lib/supabase'
import SentimentChart from '../components/SentimentChart'
import PlatformBreakdown from '../components/PlatformBreakdown'
import MentionCard from '../components/MentionCard'
import SeverityBadge from '../components/SeverityBadge'

export default function BrandView() {
  const { brandId } = useParams()
  const [brand, setBrand] = useState(null)
  const [mentions, setMentions] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const { data: brandData } = await supabase
          .from('brands')
          .select('*')
          .eq('id', brandId)
          .single()
        setBrand(brandData)

        const [mentionData, analysisData] = await Promise.all([
          getMentions(brandId, { limit: 50 }),
          getLatestAnalysis(brandId),
        ])
        setMentions(mentionData)
        setAnalysis(analysisData)
      } catch (err) {
        console.error('Failed to load brand:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [brandId])

  if (loading) return <div className="text-center py-20 text-gray-500">Loading...</div>
  if (!brand) return <div className="text-center py-20">Brand not found</div>

  // Compute sentiment distribution from mentions
  const sentimentDist = { positive: 0, neutral: 0, negative: 0 }
  mentions.forEach((m) => {
    const label = m.sentiment_label || 'neutral'
    sentimentDist[label] = (sentimentDist[label] || 0) + 1
  })
  const sentimentData = Object.entries(sentimentDist).map(([name, value]) => ({ name, value }))

  // Platform breakdown
  const platformCounts = {}
  mentions.forEach((m) => {
    platformCounts[m.platform] = (platformCounts[m.platform] || 0) + 1
  })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">{brand.name}</h1>
      <p className="text-gray-500 mb-6">
        Keywords: {(brand.keywords || []).join(', ')} | Platforms: {(brand.platforms || []).join(', ')}
      </p>

      {/* Severity overview */}
      {analysis?.severity_summary && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          {['critical', 'high', 'medium', 'low'].map((level) => (
            <div key={level} className="bg-white rounded-xl border p-4 text-center">
              <SeverityBadge level={level} />
              <p className="text-2xl font-bold mt-2">
                {analysis.severity_summary[level] || 0}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <SentimentChart data={sentimentData} />
        <PlatformBreakdown data={platformCounts} />
      </div>

      {/* Themes from analysis */}
      {analysis?.themes && analysis.themes.length > 0 && (
        <div className="bg-white rounded-xl border p-4 mb-6">
          <h3 className="text-sm font-semibold mb-3">Key Themes</h3>
          <div className="space-y-2">
            {analysis.themes.map((theme, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <span className="font-medium">{theme.name}</span>
                <span className="text-gray-500">
                  {theme.mention_count} mentions | sentiment: {theme.avg_sentiment?.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Mentions */}
      <h2 className="text-lg font-semibold mb-3">Recent Mentions</h2>
      <div className="space-y-3">
        {mentions.map((m) => (
          <MentionCard key={m.id} mention={m} />
        ))}
        {mentions.length === 0 && (
          <p className="text-gray-500 text-center py-8">No mentions yet</p>
        )}
      </div>
    </div>
  )
}
