import { Metadata } from 'next'
import ApiKeyManager from '@/components/api-keys/ApiKeyManager'

export const metadata: Metadata = {
  title: 'API Keys - OrbitSpace',
  description: 'Manage your AI service API keys for advanced codebase analysis',
}

export default function ApiKeysPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <ApiKeyManager />
      </div>
    </div>
  )
}