import { prisma } from '@/lib/prisma'
import { encryptForStorage, decryptFromStorage } from '@/lib/encryption'
import { ApiKeyProvider } from '@/types/analysis'

export class ApiKeyService {
  /**
   * Store an encrypted API key for a user
   */
  async storeKey(userId: string, provider: ApiKeyProvider, key: string): Promise<void> {
    // Validate the key first
    const isValid = await this.validateKey(provider, key)
    if (!isValid) {
      throw new Error(`Invalid API key for provider: ${provider}`)
    }

    const encryptedKey = encryptForStorage(key)

    await prisma.userApiKey.upsert({
      where: {
        userId_provider: {
          userId,
          provider
        }
      },
      update: {
        encryptedKey,
        isActive: true,
        updatedAt: new Date()
      },
      create: {
        userId,
        provider,
        encryptedKey,
        isActive: true
      }
    })
  }

  /**
   * Retrieve and decrypt an API key for a user
   */
  async getKey(userId: string, provider: ApiKeyProvider): Promise<string | null> {
    const apiKey = await prisma.userApiKey.findUnique({
      where: {
        userId_provider: {
          userId,
          provider
        }
      }
    })

    if (!apiKey || !apiKey.isActive) {
      return null
    }

    try {
      return decryptFromStorage(apiKey.encryptedKey)
    } catch (error) {
      console.error('Failed to decrypt API key:', error)
      return null
    }
  }

  /**
   * Validate an API key for a specific provider
   */
  async validateKey(provider: ApiKeyProvider, key: string): Promise<boolean> {
    try {
      switch (provider) {
        case 'anthropic':
          return await this.validateAnthropicKey(key)
        case 'openai':
          return await this.validateOpenAIKey(key)
        case 'custom':
          return this.validateCustomKey(key)
        default:
          return false
      }
    } catch (error) {
      console.error(`API key validation failed for ${provider}:`, error)
      return false
    }
  }

  /**
   * Delete an API key for a user
   */
  async deleteKey(userId: string, provider: ApiKeyProvider): Promise<void> {
    await prisma.userApiKey.update({
      where: {
        userId_provider: {
          userId,
          provider
        }
      },
      data: {
        isActive: false,
        updatedAt: new Date()
      }
    })
  }

  /**
   * List all active providers for a user
   */
  async listProviders(userId: string): Promise<ApiKeyProvider[]> {
    const apiKeys = await prisma.userApiKey.findMany({
      where: {
        userId,
        isActive: true
      },
      select: {
        provider: true
      }
    })

    return apiKeys.map(key => key.provider as ApiKeyProvider)
  }

  /**
   * Get masked API key for display purposes
   */
  async getMaskedKey(userId: string, provider: ApiKeyProvider): Promise<string | null> {
    const key = await this.getKey(userId, provider)
    if (!key) return null

    // Show first 4 and last 4 characters
    if (key.length <= 8) {
      return '*'.repeat(key.length)
    }

    return key.substring(0, 4) + '*'.repeat(key.length - 8) + key.substring(key.length - 4)
  }

  /**
   * Test API key by making a simple request
   */
  async testKey(userId: string, provider: ApiKeyProvider): Promise<boolean> {
    const key = await this.getKey(userId, provider)
    if (!key) return false

    return await this.validateKey(provider, key)
  }

  // Private validation methods
  private async validateAnthropicKey(key: string): Promise<boolean> {
    if (!key.startsWith('sk-ant-')) {
      return false
    }

    try {
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': key,
          'anthropic-version': '2023-06-01'
        },
        body: JSON.stringify({
          model: 'claude-3-haiku-20240307',
          max_tokens: 1,
          messages: [{ role: 'user', content: 'test' }]
        })
      })

      // Key is valid if we don't get a 401 Unauthorized
      return response.status !== 401
    } catch {
      return false
    }
  }

  private async validateOpenAIKey(key: string): Promise<boolean> {
    if (!key.startsWith('sk-')) {
      return false
    }

    try {
      const response = await fetch('https://api.openai.com/v1/models', {
        headers: {
          'Authorization': `Bearer ${key}`
        }
      })

      return response.status === 200
    } catch {
      return false
    }
  }

  private validateCustomKey(key: string): boolean {
    // Basic validation for custom keys
    return key.length >= 10 && key.length <= 200
  }
}

// Singleton instance
export const apiKeyService = new ApiKeyService()