import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { apiKeyService } from '@/services/api-key.service'
import { CreateApiKeySchema, ApiKeyProvider } from '@/types/analysis'
import { z } from 'zod'

export async function GET() {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const providers = await apiKeyService.listProviders(session.user.id)
    
    // Get masked keys for display
    const apiKeys = await Promise.all(
      providers.map(async (provider) => ({
        provider,
        maskedKey: await apiKeyService.getMaskedKey(session.user.id, provider),
        isActive: true
      }))
    )

    return NextResponse.json({
      success: true,
      data: apiKeys
    })
  } catch (error) {
    console.error('Failed to fetch API keys:', error)
    return NextResponse.json(
      { error: 'Failed to fetch API keys' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { provider, key } = CreateApiKeySchema.parse(body)

    await apiKeyService.storeKey(session.user.id, provider, key)

    return NextResponse.json({
      success: true,
      message: 'API key stored successfully'
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }

    console.error('Failed to store API key:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to store API key' },
      { status: 500 }
    )
  }
}