'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import PhaseIndicator from '@/components/PhaseIndicator'
import LogStream from '@/components/LogStream'
import QuestionCard from '@/components/QuestionCard'
import FileChangeCard from '@/components/FileChangeCard'
import MarkdownEditor from '@/components/MarkdownEditor'

type Phase = 'IDLE' | 'RESEARCH' | 'PLANNING' | 'IMPLEMENTATION' | 'COMPLETED'
type Status = 'ACTIVE' | 'PAUSED' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

interface Project {
  id: string
  name: string
  description: string
  currentPhase: Phase
  status: Status
  workspacePath: string
  createdAt: string
  updatedAt: string
}

interface Repository {
  id: string
  name: string
  url: string
  branch: string
  defaultBranch: string
}

interface Question {
  id: string
  questionText: string
  choices: string[]
  imageUrl?: string
  answer?: string
  answeredAt?: string
}

export default function ProjectDetailPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string

  const [project, setProject] = useState<Project | null>(null)
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [questions, setQuestions] = useState<Question[]>([])
  const [activeTab, setActiveTab] = useState<'logs' | 'research' | 'planning' | 'implementation'>('logs')
  const [researchContent, setResearchContent] = useState<string>('')
  const [planningContent, setPlanningContent] = useState<string>('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isStartingPhase, setIsStartingPhase] = useState(false)

  useEffect(() => {
    fetchProject()
    fetchQuestions()
  }, [projectId])

  useEffect(() => {
    if (project?.currentPhase === 'RESEARCH' || project?.currentPhase === 'PLANNING' || project?.currentPhase === 'IMPLEMENTATION' || project?.currentPhase === 'COMPLETED') {
      fetchResearchFile()
    }
    if (project?.currentPhase === 'PLANNING' || project?.currentPhase === 'IMPLEMENTATION' || project?.currentPhase === 'COMPLETED') {
      fetchPlanningFile()
    }
  }, [project?.currentPhase])

  const fetchProject = async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}`)
      if (!response.ok) throw new Error('Failed to fetch project')
      const data = await response.json()
      setProject(data.project)
      setRepositories(data.repositories || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load project')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchQuestions = async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/questions`)
      if (!response.ok) throw new Error('Failed to fetch questions')
      const data = await response.json()
      setQuestions(data.questions || [])
    } catch (err) {
      console.error('Failed to fetch questions:', err)
    }
  }

  const fetchResearchFile = async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/files/research`)
      if (response.ok) {
        const data = await response.json()
        setResearchContent(data.content)
      }
    } catch (err) {
      console.error('Failed to fetch research file:', err)
    }
  }

  const fetchPlanningFile = async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/files/planning`)
      if (response.ok) {
        const data = await response.json()
        setPlanningContent(data.content)
      }
    } catch (err) {
      console.error('Failed to fetch planning file:', err)
    }
  }

  const handleStartPhase = async (phase: 'research' | 'planning' | 'implementation') => {
    setIsStartingPhase(true)
    try {
      const response = await fetch(`/api/projects/${projectId}/start-${phase}`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error(`Failed to start ${phase}`)
      await fetchProject()
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to start ${phase}`)
    } finally {
      setIsStartingPhase(false)
    }
  }

  const handleSavePlanning = async (content: string) => {
    const response = await fetch(`/api/projects/${projectId}/files/planning`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content }),
    })
    if (!response.ok) throw new Error('Failed to save planning')
    setPlanningContent(content)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <svg
            className="animate-spin h-12 w-12 text-blue-500 mx-auto mb-4"
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
          <p className="text-gray-400">Loading project...</p>
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error || 'Project not found'}</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="text-blue-400 hover:text-blue-300"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  const getStatusBadge = (status: Status) => {
    const badges = {
      ACTIVE: { bg: 'bg-green-900/50', text: 'text-green-300', label: 'Active' },
      PAUSED: { bg: 'bg-yellow-900/50', text: 'text-yellow-300', label: 'Paused' },
      COMPLETED: { bg: 'bg-gray-700', text: 'text-gray-300', label: 'Completed' },
      FAILED: { bg: 'bg-red-900/50', text: 'text-red-300', label: 'Failed' },
      CANCELLED: { bg: 'bg-gray-700', text: 'text-gray-400', label: 'Cancelled' },
    }

    const badge = badges[status]
    return (
      <span
        className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${badge.bg} ${badge.text}`}
      >
        {badge.label}
      </span>
    )
  }

  const unansweredQuestions = questions.filter((q) => !q.answer)

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-850">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <button
            onClick={() => router.push('/dashboard')}
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

          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h1 className="text-3xl font-bold mb-2">{project.name}</h1>
              {project.description && (
                <p className="text-gray-400 mb-4">{project.description}</p>
              )}
              <div className="flex items-center gap-3">
                {getStatusBadge(project.status)}
                <span className="text-sm text-gray-500">
                  Created {new Date(project.createdAt).toLocaleDateString()}
                </span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              {project.currentPhase === 'IDLE' && (
                <button
                  onClick={() => handleStartPhase('research')}
                  disabled={isStartingPhase}
                  className="px-6 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg disabled:opacity-50"
                >
                  Start Research
                </button>
              )}
              {project.currentPhase === 'RESEARCH' && project.status !== 'ACTIVE' && researchContent && (
                <button
                  onClick={() => handleStartPhase('planning')}
                  disabled={isStartingPhase}
                  className="px-6 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg disabled:opacity-50"
                >
                  Start Planning
                </button>
              )}
              {project.currentPhase === 'PLANNING' && project.status !== 'ACTIVE' && planningContent && (
                <button
                  onClick={() => handleStartPhase('implementation')}
                  disabled={isStartingPhase}
                  className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-50"
                >
                  Start Implementation
                </button>
              )}
            </div>
          </div>

          {/* Phase Indicator */}
          <PhaseIndicator currentPhase={project.currentPhase} />

          {/* Repositories */}
          {repositories.length > 0 && (
            <div className="mt-4 flex items-center gap-2 text-sm">
              <span className="text-gray-500">Repositories:</span>
              {repositories.map((repo) => (
                <span
                  key={repo.id}
                  className="inline-flex items-center px-2 py-1 rounded bg-gray-800 text-gray-300"
                >
                  {repo.name}
                  <span className="ml-1 text-gray-500">({repo.branch})</span>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* Sidebar */}
          <div className="w-64 flex-shrink-0">
            <nav className="space-y-1">
              <button
                onClick={() => setActiveTab('logs')}
                className={`w-full text-left px-4 py-2 rounded-lg ${
                  activeTab === 'logs'
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-300'
                }`}
              >
                Live Logs
              </button>
              {(project.currentPhase !== 'IDLE' && project.currentPhase !== 'RESEARCH') && (
                <button
                  onClick={() => setActiveTab('research')}
                  className={`w-full text-left px-4 py-2 rounded-lg ${
                    activeTab === 'research'
                      ? 'bg-gray-800 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-300'
                  }`}
                >
                  Research
                </button>
              )}
              {(project.currentPhase === 'PLANNING' || project.currentPhase === 'IMPLEMENTATION' || project.currentPhase === 'COMPLETED') && (
                <button
                  onClick={() => setActiveTab('planning')}
                  className={`w-full text-left px-4 py-2 rounded-lg ${
                    activeTab === 'planning'
                      ? 'bg-gray-800 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-300'
                  }`}
                >
                  Planning
                </button>
              )}
              {(project.currentPhase === 'IMPLEMENTATION' || project.currentPhase === 'COMPLETED') && (
                <button
                  onClick={() => setActiveTab('implementation')}
                  className={`w-full text-left px-4 py-2 rounded-lg ${
                    activeTab === 'implementation'
                      ? 'bg-gray-800 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-300'
                  }`}
                >
                  Implementation
                </button>
              )}
            </nav>
          </div>

          {/* Main Content Area */}
          <div className="flex-1 space-y-6">
            {/* Unanswered Questions */}
            {unansweredQuestions.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-xl font-semibold">Questions from Agent</h2>
                {unansweredQuestions.map((question) => (
                  <QuestionCard
                    key={question.id}
                    projectId={projectId}
                    questionId={question.id}
                    questionText={question.questionText}
                    choices={question.choices}
                    imageUrl={question.imageUrl}
                    answer={question.answer}
                    answeredAt={question.answeredAt}
                    onAnswer={() => fetchQuestions()}
                  />
                ))}
              </div>
            )}

            {/* Tab Content */}
            {activeTab === 'logs' && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Live Activity Log</h2>
                <LogStream projectId={projectId} />
              </div>
            )}

            {activeTab === 'research' && researchContent && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Research Document</h2>
                <div className="bg-gray-800 rounded-lg p-6 prose prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap font-mono text-sm text-gray-300">
                    {researchContent}
                  </pre>
                </div>
              </div>
            )}

            {activeTab === 'planning' && planningContent && (
              <div className="h-[600px]">
                <h2 className="text-xl font-semibold mb-4">Implementation Plan</h2>
                <MarkdownEditor
                  content={planningContent}
                  onSave={handleSavePlanning}
                  readOnly={project.currentPhase === 'IMPLEMENTATION' || project.currentPhase === 'COMPLETED'}
                />
              </div>
            )}

            {activeTab === 'implementation' && (
              <div>
                <h2 className="text-xl font-semibold mb-4">Implementation Progress</h2>
                <p className="text-gray-400 mb-4">
                  File changes and commits will appear here as the implementation agent works.
                </p>
                {/* This would be populated with actual file changes from the backend */}
                <div className="text-gray-500 text-center py-8">
                  No file changes yet
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
