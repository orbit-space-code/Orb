import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.email) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const project = await prisma.project.findFirst({
      where: {
        id: params.id,
        user: { email: session.user.email }
      }
    })

    if (!project) {
      return NextResponse.json({ error: 'Project not found' }, { status: 404 })
    }

    // Update project phase
    await prisma.project.update({
      where: { id: params.id },
      data: { currentPhase: 'RESEARCH' }
    })

    // Call FastAPI to start research agent
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000'
    const response = await fetch(`${fastApiUrl}/agents/research/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: params.id,
        feature_request: project.description
      })
    })

    if (!response.ok) {
      throw new Error('Failed to start research agent')
    }

    const data = await response.json()

    return NextResponse.json({
      success: true,
      phase: 'RESEARCH',
      task_id: data.task_id
    })
  } catch (error) {
    console.error('Error starting research:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
