import React, { useState } from 'react'
import MentionCard from '../components/MentionCard'

export default function Search() {
  const [keywords, setKeywords] = useState('')
  const [platforms, setPlatforms] = useState([])
  const [minLikes, setMinLikes] = useState(0)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)

  const allPlatforms = [
    'youtube', 'telegram', 'instagram', 'reddit', 'twitter', 'seo_news',
  ]

  const togglePlatform = (p) => {
    setPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    )
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const resp = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keywords: keywords.split(',').map((k) => k.trim()).filter(Boolean),
          platforms: platforms.length ? platforms : allPlatforms,
          min_likes: minLikes,
        }),
      })
      const data = await resp.json()
      setResults(data.results || [])
    } catch (err) {
      console.error('Search failed:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Search</h1>

      <form onSubmit={handleSearch} className="bg-white rounded-xl border p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Keywords (comma-separated)</label>
            <input
              type="text"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="brand name, product, topic..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Min Likes</label>
            <input
              type="number"
              value={minLikes}
              onChange={(e) => setMinLikes(Number(e.target.value))}
              className="w-full border rounded-lg px-3 py-2 text-sm"
              min={0}
            />
          </div>
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">Platforms</label>
          <div className="flex flex-wrap gap-2">
            {allPlatforms.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => togglePlatform(p)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  platforms.includes(p)
                    ? 'bg-indigo-600 text-white border-indigo-600'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-indigo-400'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !keywords.trim()}
          className="bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {results.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-3">
            Results ({results.length})
          </h2>
          <div className="space-y-3">
            {results.map((r, i) => (
              <MentionCard key={r.id || i} mention={r} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
