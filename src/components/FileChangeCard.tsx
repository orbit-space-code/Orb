'use client'

import { useState } from 'react'

type ChangeType = 'added' | 'modified' | 'deleted'

interface FileChangeCardProps {
  filePath: string
  changeType: ChangeType
  linesAdded?: number
  linesRemoved?: number
  diff?: string
}

export default function FileChangeCard({
  filePath,
  changeType,
  linesAdded = 0,
  linesRemoved = 0,
  diff,
}: FileChangeCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const getChangeIcon = (type: ChangeType) => {
    switch (type) {
      case 'added':
        return (
          <svg
            className="w-5 h-5 text-green-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        )
      case 'modified':
        return (
          <svg
            className="w-5 h-5 text-blue-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
            />
          </svg>
        )
      case 'deleted':
        return (
          <svg
            className="w-5 h-5 text-red-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20 12H4"
            />
          </svg>
        )
    }
  }

  const getChangeBadge = (type: ChangeType) => {
    switch (type) {
      case 'added':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-900/50 text-green-300">
            Added
          </span>
        )
      case 'modified':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-900/50 text-blue-300">
            Modified
          </span>
        )
      case 'deleted':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-900/50 text-red-300">
            Deleted
          </span>
        )
    }
  }

  const getFileExtension = (path: string) => {
    const parts = path.split('.')
    return parts.length > 1 ? parts[parts.length - 1] : ''
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => diff && setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-750 transition-colors"
      >
        <div className="flex items-center gap-3">
          {getChangeIcon(changeType)}
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-white">{filePath}</span>
              {getChangeBadge(changeType)}
            </div>
            {(linesAdded > 0 || linesRemoved > 0) && (
              <div className="flex items-center gap-3 mt-1 text-xs">
                {linesAdded > 0 && (
                  <span className="text-green-400">+{linesAdded}</span>
                )}
                {linesRemoved > 0 && (
                  <span className="text-red-400">-{linesRemoved}</span>
                )}
              </div>
            )}
          </div>
        </div>

        {diff && (
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${
              isExpanded ? 'rotate-180' : ''
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        )}
      </button>

      {/* Expanded Diff */}
      {isExpanded && diff && (
        <div className="border-t border-gray-700 bg-gray-900 p-4 overflow-x-auto">
          <pre className="font-mono text-xs">
            {diff.split('\n').map((line, index) => {
              let lineClass = 'text-gray-400'
              if (line.startsWith('+')) lineClass = 'text-green-400 bg-green-900/20'
              if (line.startsWith('-')) lineClass = 'text-red-400 bg-red-900/20'
              if (line.startsWith('@@')) lineClass = 'text-blue-400'

              return (
                <div key={index} className={`${lineClass} px-2`}>
                  {line}
                </div>
              )
            })}
          </pre>
        </div>
      )}
    </div>
  )
}
