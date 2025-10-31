'use client'

type Phase = 'IDLE' | 'RESEARCH' | 'PLANNING' | 'IMPLEMENTATION' | 'COMPLETED'

interface PhaseIndicatorProps {
  currentPhase: Phase
}

export default function PhaseIndicator({ currentPhase }: PhaseIndicatorProps) {
  const phases = [
    { key: 'RESEARCH', label: 'Research', color: 'purple' },
    { key: 'PLANNING', label: 'Planning', color: 'yellow' },
    { key: 'IMPLEMENTATION', label: 'Implementation', color: 'blue' },
    { key: 'COMPLETED', label: 'Completed', color: 'green' },
  ]

  const getPhaseIndex = (phase: Phase) => {
    if (phase === 'IDLE') return -1
    return phases.findIndex((p) => p.key === phase)
  }

  const currentIndex = getPhaseIndex(currentPhase)

  const getPhaseColor = (phase: typeof phases[0], index: number) => {
    const isPast = index < currentIndex
    const isCurrent = index === currentIndex
    const isFuture = index > currentIndex

    if (isPast || isCurrent) {
      return {
        bg: `bg-${phase.color}-500`,
        text: `text-${phase.color}-300`,
        border: `border-${phase.color}-500`,
      }
    }

    return {
      bg: 'bg-gray-700',
      text: 'text-gray-500',
      border: 'border-gray-600',
    }
  }

  const getConnectorColor = (index: number) => {
    return index < currentIndex ? 'bg-gray-500' : 'bg-gray-700'
  }

  return (
    <div className="w-full py-6">
      {currentPhase === 'IDLE' ? (
        <div className="text-center text-gray-500 py-4">
          Ready to start
        </div>
      ) : (
        <div className="flex items-center justify-between relative">
          {phases.map((phase, index) => {
            const isPast = index < currentIndex
            const isCurrent = index === currentIndex
            const isFuture = index > currentIndex

            return (
              <div key={phase.key} className="flex items-center flex-1">
                {/* Phase Node */}
                <div className="flex flex-col items-center relative z-10">
                  {/* Circle */}
                  <div
                    className={`w-10 h-10 rounded-full border-2 flex items-center justify-center ${
                      isCurrent
                        ? `bg-${phase.color}-500 border-${phase.color}-400`
                        : isPast
                        ? `bg-${phase.color}-600 border-${phase.color}-500`
                        : 'bg-gray-800 border-gray-600'
                    }`}
                  >
                    {isPast && (
                      <svg
                        className="w-6 h-6 text-white"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    )}
                    {isCurrent && (
                      <div className="w-3 h-3 bg-white rounded-full animate-pulse" />
                    )}
                    {isFuture && (
                      <div className="w-3 h-3 bg-gray-600 rounded-full" />
                    )}
                  </div>

                  {/* Label */}
                  <span
                    className={`mt-2 text-sm font-medium ${
                      isCurrent
                        ? `text-${phase.color}-300`
                        : isPast
                        ? 'text-gray-300'
                        : 'text-gray-500'
                    }`}
                  >
                    {phase.label}
                  </span>
                </div>

                {/* Connector Line */}
                {index < phases.length - 1 && (
                  <div className="flex-1 h-0.5 mx-4 -mt-8">
                    <div
                      className={`h-full ${
                        index < currentIndex ? 'bg-gray-500' : 'bg-gray-700'
                      }`}
                    />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
