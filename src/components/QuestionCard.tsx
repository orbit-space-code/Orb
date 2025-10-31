'use client'

import { useState } from 'react'
import Image from 'next/image'

interface QuestionCardProps {
  projectId: string
  questionId: string
  questionText: string
  choices: string[]
  imageUrl?: string
  answer?: string
  answeredAt?: string
  onAnswer?: (answer: string) => void
}

export default function QuestionCard({
  projectId,
  questionId,
  questionText,
  choices,
  imageUrl,
  answer,
  answeredAt,
  onAnswer,
}: QuestionCardProps) {
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(
    answer || null
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSelectChoice = async (choice: string) => {
    if (selectedAnswer) return // Already answered

    setIsSubmitting(true)
    setError(null)

    try {
      const response = await fetch(
        `/api/projects/${projectId}/questions/${questionId}/answer`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ answer: choice }),
        }
      )

      if (!response.ok) {
        throw new Error('Failed to submit answer')
      }

      setSelectedAnswer(choice)
      if (onAnswer) {
        onAnswer(choice)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit answer')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 shadow-lg">
      {/* Question Header */}
      <div className="mb-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-lg font-semibold text-white flex-1">
            {questionText}
          </h3>
          {selectedAnswer && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-900/50 text-green-300">
              Answered
            </span>
          )}
        </div>
        {answeredAt && (
          <p className="text-xs text-gray-500">
            Answered at {new Date(answeredAt).toLocaleString()}
          </p>
        )}
      </div>

      {/* Optional Image */}
      {imageUrl && (
        <div className="mb-4 relative w-full h-64 bg-gray-900 rounded-lg overflow-hidden">
          <Image
            src={imageUrl}
            alt="Question context"
            fill
            className="object-contain"
          />
        </div>
      )}

      {/* Choices */}
      <div className="space-y-2">
        {choices.map((choice, index) => {
          const isSelected = selectedAnswer === choice
          const isDisabled = selectedAnswer !== null || isSubmitting

          return (
            <button
              key={index}
              onClick={() => handleSelectChoice(choice)}
              disabled={isDisabled}
              className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                isSelected
                  ? 'bg-blue-600 border-blue-500 text-white'
                  : isDisabled
                  ? 'bg-gray-700 border-gray-600 text-gray-400 cursor-not-allowed'
                  : 'bg-gray-700 border-gray-600 text-white hover:bg-gray-600 hover:border-gray-500'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{choice}</span>
                {isSelected && (
                  <svg
                    className="w-5 h-5"
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
              </div>
            </button>
          )
        })}
      </div>

      {/* Skip Option */}
      {!selectedAnswer && !isSubmitting && (
        <button
          onClick={() => handleSelectChoice('Skip')}
          className="mt-3 w-full text-center px-4 py-2 text-sm text-gray-400 hover:text-gray-300 underline"
        >
          Skip this question
        </button>
      )}

      {/* Loading State */}
      {isSubmitting && (
        <div className="mt-4 flex items-center justify-center gap-2 text-sm text-gray-400">
          <svg
            className="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Sending answer to agent...</span>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="mt-4 p-3 bg-red-900/30 border border-red-700 rounded text-sm text-red-300">
          {error}
        </div>
      )}
    </div>
  )
}
