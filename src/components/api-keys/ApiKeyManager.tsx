'use client'

import { useState, useEffect } from 'react'
import { ApiKeyProvider } from '@/types/analysis'

interface ApiKey {
  provider: ApiKeyProvider
  maskedKey: string
  isActive: boolean
}

export default function ApiKeyManager() {
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)

  useEffect(() => {
    fetchApiKeys()
  }, [])

  const fetchApiKeys = async () => {
    try {
      const response = await fetch('/api/user/api-keys')
      const data = await response.json()
      
      if (data.success) {
        setApiKeys(data.data)
      } else {
        setError('Failed to fetch API keys')
      }
    } catch (err) {
      setError('Failed to fetch API keys')
    } finally {
      setLoading(false)
    }
  }

  const handleAddApiKey = async (provider: ApiKeyProvider, key: string) => {
    try {
      const response = await fetch('/api/user/api-keys', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ provider, key }),
      })

      const data = await response.json()
      
      if (data.success) {
        await fetchApiKeys()
        setShowAddForm(false)
        setError(null)
      } else {
        setError(data.error || 'Failed to add API key')
      }
    } catch (err) {
      setError('Failed to add API key')
    }
  }

  const handleDeleteApiKey = async (provider: ApiKeyProvider) => {
    if (!confirm(`Are you sure you want to delete the ${provider} API key?`)) {
      return
    }

    try {
      const response = await fetch(`/api/user/api-keys/${provider}`, {
        method: 'DELETE',
      })

      const data = await response.json()
      
      if (data.success) {
        await fetchApiKeys()
        setError(null)
      } else {
        setError(data.error || 'Failed to delete API key')
      }
    } catch (err) {
      setError('Failed to delete API key')
    }
  }

  const handleTestApiKey = async (provider: ApiKeyProvider) => {
    try {
      const response = await fetch(`/api/user/api-keys/${provider}`, {
        method: 'POST',
      })

      const data = await response.json()
      
      if (data.success) {
        alert(data.data.isValid ? 'API key is valid!' : 'API key is invalid')
      } else {
        setError(data.error || 'Failed to test API key')
      }
    } catch (err) {
      setError('Failed to test API key')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">API Key Management</h2>
        <button
          onClick={() => setShowAddForm(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
        >
          Add API Key
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          {error}
        </div>
      )}

      <div className="bg-white shadow rounded-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Your API Keys</h3>
          <p className="text-sm text-gray-500 mt-1">
            Manage your AI service API keys for codebase analysis
          </p>
        </div>

        <div className="divide-y divide-gray-200">
          {apiKeys.length === 0 ? (
            <div className="px-6 py-8 text-center text-gray-500">
              No API keys configured. Add one to get started with AI-powered analysis.
            </div>
          ) : (
            apiKeys.map((apiKey) => (
              <div key={apiKey.provider} className="px-6 py-4 flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                      <span className="text-sm font-medium text-gray-600 uppercase">
                        {apiKey.provider.slice(0, 2)}
                      </span>
                    </div>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-900 capitalize">
                      {apiKey.provider}
                    </h4>
                    <p className="text-sm text-gray-500 font-mono">
                      {apiKey.maskedKey}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleTestApiKey(apiKey.provider)}
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    Test
                  </button>
                  <button
                    onClick={() => handleDeleteApiKey(apiKey.provider)}
                    className="text-red-600 hover:text-red-800 text-sm font-medium"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {showAddForm && (
        <AddApiKeyForm
          onAdd={handleAddApiKey}
          onCancel={() => setShowAddForm(false)}
        />
      )}
    </div>
  )
}

interface AddApiKeyFormProps {
  onAdd: (provider: ApiKeyProvider, key: string) => void
  onCancel: () => void
}

function AddApiKeyForm({ onAdd, onCancel }: AddApiKeyFormProps) {
  const [provider, setProvider] = useState<ApiKeyProvider>('anthropic')
  const [key, setKey] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!key.trim()) return

    setLoading(true)
    try {
      await onAdd(provider, key.trim())
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-medium text-gray-900">Add API Key</h3>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value as ApiKeyProvider)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="openai">OpenAI (GPT)</option>
              <option value="custom">Custom</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              API Key
            </label>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder={`Enter your ${provider} API key`}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Your API key will be encrypted and stored securely
            </p>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !key.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Adding...' : 'Add Key'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}