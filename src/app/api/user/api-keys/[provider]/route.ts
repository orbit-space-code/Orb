import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { apiKeyService } from '@/services/api-key.service'
import { UpdateApiKeySchema, ApiKeyProviderSchema } from '@/types/analysis'
import { z } from 'zod'

interface RouteParams {
  params: {
    provider: string
  }
}

export async function PUT(request: NextRequest, { params }: RouteParams) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const provider = ApiKeyProviderSchema.parse(params.provider)
    const body = await request.json()
    const { key } = UpdateApiKeySchema.parse(body)

    await apiKeyService.storeKey(session.user.id, provider, key)

    return NextResponse.json({
      success: true,
      message: 'API key updated successfully'
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }

    console.error('Failed to update API key:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Failed to update API key' },
      { status: 500 }
    )
  }
}

export async function DELETE(request: NextRequest, { params }: RouteParams) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const provider = ApiKeyProviderSchema.parse(params.provider)
    await apiKeyService.deleteKey(session.user.id, provider)

    return NextResponse.json({
      success: true,
      message: 'API key deleted successfully'
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid provider' },
        { status: 400 }
      )
    }

    console.error('Failed to delete API key:', error)
    return NextResponse.json(
      { error: 'Failed to delete API key' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest, { params }: RouteParams) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const provider = ApiKeyProviderSchema.parse(params.provider)
    const isValid = await apiKeyService.testKey(session.user.id, provider)

    return NextResponse.json({
      success: true,
      data: { isValid }
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid provider' },
        { status: 400 }
      )
    }

    console.error('Failed to test API key:', error)
    return NextResponse.json(
      { error: 'Failed to test API key' },
      { status: 500 }
    )
  }
}