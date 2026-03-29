import React from 'react'
import SeverityBadge from './SeverityBadge'

export default function MentionCard({ mention }) {
  const {
    platform,
    content_text,
    author_handle,
    sentiment_label,
    engagement_score,
    likes,
    comments_count,
    source_url,
    published_at,
  } = mention

  const sentimentColor = {
    positive: 'text-green-600',
    negative: 'text-red-600',
    neutral: 'text-gray-500',
  }

  return (
    <div className="bg-white rounded-xl border p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium px-2 py-0.5 bg-gray-100 rounded">
            {platform}
          </span>
          {author_handle && (
            <span className="text-sm text-gray-500">@{author_handle}</span>
          )}
        </div>
        {mention.severity && (
          <SeverityBadge
            level={mention.severity.severity_level}
            score={mention.severity.severity_score}
          />
        )}
      </div>

      <p className="text-sm text-gray-800 line-clamp-3 mb-3">
        {content_text || '(no text)'}
      </p>

      <div className="flex items-center gap-4 text-xs text-gray-500">
        {sentiment_label && (
          <span className={sentimentColor[sentiment_label] || ''}>
            {sentiment_label}
          </span>
        )}
        {engagement_score > 0 && <span>Engagement: {engagement_score}</span>}
        {likes > 0 && <span>Likes: {likes}</span>}
        {comments_count > 0 && <span>Comments: {comments_count}</span>}
        {published_at && (
          <span>{new Date(published_at).toLocaleDateString()}</span>
        )}
        {source_url && (
          <a
            href={source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-indigo-600 hover:underline ml-auto"
          >
            View source
          </a>
        )}
      </div>
    </div>
  )
}
