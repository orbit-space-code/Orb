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
      data: { currentPhase: 'IMPLEMENTATION' }
    })

    // Call FastAPI to start implementation agent
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000'
    const response = await fetch(`${fastApiUrl}/agents/implementation/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: params.id,
        feature_request: project.description
      })
    })

    if (!response.ok) {
      throw new Error('Failed to start implementation agent')
    }

    const data = await response.json()

    return NextResponse.json({
      success: true,
      phase: 'IMPLEMENTATION',
      task_id: data.task_id,
      overwatcher_task_ids: data.overwatcher_task_ids || []
    })
  } catch (error) {
    console.error('Error starting implementation:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
