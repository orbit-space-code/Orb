'use client'

import { useEffect, useState, useRef } from 'react'

export interface LogEntry {
  type: 'log' | 'question' | 'phase' | 'progress' | 'tool' | 'error'
  timestamp: string
  phase?: string
  agentName?: string
  message?: string
  data?: any
}

interface LogStreamProps {
  projectId: string
}

export default function LogStream({ projectId }: LogStreamProps) {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const logContainerRef = useRef<HTMLDivElement>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const connectSSE = () => {
      const eventSource = new EventSource(`/api/projects/${projectId}/stream`)
      eventSourceRef.current = eventSource

      eventSource.onopen = () => {
        setIsConnected(true)
        setRetryCount(0)
      }

      eventSource.addEventListener('log', (event) => {
        const data = JSON.parse(event.data)
        setLogs((prev) => [...prev, { type: 'log', ...data }])
      })

      eventSource.addEventListener('question', (event) => {
        const data = JSON.parse(event.data)
        setLogs((prev) => [...prev, { type: 'question', ...data }])
      })

      eventSource.addEventListener('phase', (event) => {
        const data = JSON.parse(event.data)
        setLogs((prev) => [...prev, { type: 'phase', ...data }])
      })

      eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data)
        setLogs((prev) => [...prev, { type: 'progress', ...data }])
      })

      eventSource.addEventListener('tool', (event) => {
        const data = JSON.parse(event.data)
        setLogs((prev) => [...prev, { type: 'tool', ...data }])
      })

      eventSource.addEventListener('error', (event) => {
        const data = JSON.parse(event.data)
        setLogs((prev) => [...prev, { type: 'error', ...data }])
      })

      eventSource.onerror = () => {
        setIsConnected(false)
        eventSource.close()

        // Exponential backoff retry
        const delay = Math.min(1000 * Math.pow(2, retryCount), 30000)
        setTimeout(() => {
          setRetryCount((prev) => prev + 1)
          connectSSE()
        }, delay)
      }
    }

    connectSSE()

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [projectId, retryCount])

  // Auto-scroll to bottom
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  const getLogColor = (type: string) => {
    switch (type) {
      case 'log':
        return 'bg-gray-800 text-gray-300'
      case 'progress':
        return 'bg-blue-900/30 text-blue-300 border-l-4 border-blue-500'
      case 'tool':
        return 'bg-green-900/30 text-green-300 border-l-4 border-green-500'
      case 'error':
        return 'bg-red-900/30 text-red-300 border-l-4 border-red-500'
      case 'phase':
        return 'bg-purple-900/30 text-purple-300 border-l-4 border-purple-500'
      case 'question':
        return 'bg-yellow-900/30 text-yellow-300 border-l-4 border-yellow-500'
      default:
        return 'bg-gray-800 text-gray-300'
    }
  }

  const formatMessage = (log: LogEntry) => {
    if (log.message) return log.message
    if (log.data) {
      if (typeof log.data === 'string') return log.data
      return JSON.stringify(log.data, null, 2)
    }
    return 'No message'
  }

  return (
    <div className="space-y-2">
      {/* Connection Status */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-xs text-gray-400">
            {isConnected ? 'Connected' : 'Reconnecting...'}
          </span>
        </div>
        <span className="text-xs text-gray-500">{logs.length} events</span>
      </div>

      {/* Log Container */}
      <div
        ref={logContainerRef}
        className="space-y-2 max-h-[600px] overflow-y-auto bg-gray-900 rounded-lg p-4 font-mono text-sm"
      >
        {logs.length === 0 ? (
          <div className="text-gray-500 text-center py-8">
            Waiting for events...
          </div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className={`p-3 rounded ${getLogColor(log.type)}`}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  {log.agentName && (
                    <span className="text-xs font-semibold text-gray-400 uppercase">
                      [{log.agentName}]
                    </span>
                  )}{' '}
                  <span className="break-words">{formatMessage(log)}</span>
                </div>
                <span className="text-xs text-gray-500 whitespace-nowrap">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
