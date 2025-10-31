'use client'

import Link from 'next/link'

type Phase = 'IDLE' | 'RESEARCH' | 'PLANNING' | 'IMPLEMENTATION' | 'COMPLETED'
type Status = 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

interface ProjectCardProps {
  id: string
  name: string
  description?: string
  currentPhase: Phase
  status: Status
  createdAt: string
  updatedAt: string
}

export default function ProjectCard({
  id,
  name,
  description,
  currentPhase,
  status,
  createdAt,
  updatedAt,
}: ProjectCardProps) {
  const getPhaseBadge = (phase: Phase) => {
    const badges = {
      IDLE: { bg: 'bg-gray-700', text: 'text-gray-300', label: 'Idle' },
      RESEARCH: { bg: 'bg-purple-900/50', text: 'text-purple-300', label: 'Research' },
      PLANNING: { bg: 'bg-yellow-900/50', text: 'text-yellow-300', label: 'Planning' },
      IMPLEMENTATION: { bg: 'bg-blue-900/50', text: 'text-blue-300', label: 'Implementation' },
      COMPLETED: { bg: 'bg-green-900/50', text: 'text-green-300', label: 'Completed' },
    }

    const badge = badges[phase]
    return (
      <span
        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}
      >
        {badge.label}
      </span>
    )
  }

  const getStatusBadge = (status: Status) => {
    const badges = {
      ACTIVE: { bg: 'bg-green-900/50', text: 'text-green-300', label: 'Active', icon: '●' },
      PAUSED: { bg: 'bg-yellow-900/50', text: 'text-yellow-300', label: 'Paused', icon: '⏸' },
      COMPLETED: { bg: 'bg-gray-700', text: 'text-gray-300', label: 'Completed', icon: '✓' },
      FAILED: { bg: 'bg-red-900/50', text: 'text-red-300', label: 'Failed', icon: '✕' },
      CANCELLED: { bg: 'bg-gray-700', text: 'text-gray-400', label: 'Cancelled', icon: '⊘' },
    }

    const badge = badges[status]
    return (
      <span
        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.bg} ${badge.text}`}
      >
        <span>{badge.icon}</span>
        {badge.label}
      </span>
    )
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  return (
    <Link href={`/projects/${id}`}>
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 hover:border-gray-600 transition-all hover:shadow-lg cursor-pointer">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <h3 className="text-xl font-semibold text-white flex-1 mr-4">
            {name}
          </h3>
          {getStatusBadge(status)}
        </div>

        {/* Description */}
        {description && (
          <p className="text-gray-400 text-sm mb-4 line-clamp-2">
            {description}
          </p>
        )}

        {/* Phase & Metadata */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getPhaseBadge(currentPhase)}
          </div>

          <div className="flex flex-col items-end text-xs text-gray-500">
            <span>Created {formatDate(createdAt)}</span>
            {updatedAt !== createdAt && (
              <span className="text-gray-600">Updated {formatDate(updatedAt)}</span>
            )}
          </div>
        </div>

        {/* Progress Indicator (for active projects) */}
        {status === 'ACTIVE' && currentPhase !== 'IDLE' && (
          <div className="mt-4 pt-4 border-t border-gray-700">
            <div className="flex items-center gap-2 text-xs text-blue-400">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              <span>In progress...</span>
            </div>
          </div>
        )}
      </div>
    </Link>
  )
}
