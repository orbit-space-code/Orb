'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import RepositorySelector from '@/components/RepositorySelector'

export default function NewProjectPage() {
  const router = useRouter()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selectedRepos, setSelectedRepos] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim()) {
      setError('Project name is required')
      return
    }

    if (selectedRepos.length === 0) {
      setError('Please select at least one repository')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          description,
          repositoryUrls: selectedRepos,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to create project')
      }

      const data = await response.json()
      router.push(`/projects/${data.project.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-gray-400 hover:text-gray-300 mb-4"
          >
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
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold">Create New Project</h1>
          <p className="text-gray-400 mt-2">
            Start a new AI-powered development project with Orbitspace OrbitSpace
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Project Name */}
          <div>
            <label
              htmlFor="name"
              className="block text-sm font-medium text-gray-300 mb-2"
            >
              Project Name *
            </label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Add OAuth Authentication"
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          {/* Feature Request / Description */}
          <div>
            <label
              htmlFor="description"
              className="block text-sm font-medium text-gray-300 mb-2"
            >
              Feature Request *
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the feature you want to implement in detail..."
              rows={6}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              required
            />
            <p className="mt-2 text-xs text-gray-500">
              Be specific about what you want to build. The research agent will
              analyze your codebase and the planning agent will ask clarifying
              questions.
            </p>
          </div>

          {/* Repository Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Select Repositories *
            </label>
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <RepositorySelector
                selectedUrls={selectedRepos}
                onSelectionChange={setSelectedRepos}
              />
            </div>
            <p className="mt-2 text-xs text-gray-500">
              Select the repositories where the feature will be implemented.
              Branches will be created in all selected repositories.
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300">
              {error}
            </div>
          )}

          {/* Submit Button */}
          <div className="flex items-center justify-between pt-6 border-t border-gray-700">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-6 py-2 text-gray-400 hover:text-gray-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-8 py-3 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <svg
                    className="animate-spin h-5 w-5"
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
                  Creating Project...
                </span>
              ) : (
                'Create Project & Start Research'
              )}
            </button>
          </div>
        </form>

        {/* Info Cards */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-full bg-purple-900/50 flex items-center justify-center">
                <span className="text-purple-400 font-bold">1</span>
              </div>
              <h3 className="font-semibold text-purple-300">Research</h3>
            </div>
            <p className="text-sm text-gray-400">
              AI agent analyzes your codebase and creates a detailed research
              document
            </p>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-full bg-yellow-900/50 flex items-center justify-center">
                <span className="text-yellow-400 font-bold">2</span>
              </div>
              <h3 className="font-semibold text-yellow-300">Planning</h3>
            </div>
            <p className="text-sm text-gray-400">
              Planning agent asks questions and creates an implementation plan
            </p>
          </div>

          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-8 h-8 rounded-full bg-blue-900/50 flex items-center justify-center">
                <span className="text-blue-400 font-bold">3</span>
              </div>
              <h3 className="font-semibold text-blue-300">Implementation</h3>
            </div>
            <p className="text-sm text-gray-400">
              Implementation agent executes the plan and creates commits
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
