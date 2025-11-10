import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'

// GET /api/projects - List user's projects
export async function GET(request: Request) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.email) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const status = searchParams.get('status')
    const limit = parseInt(searchParams.get('limit') || '50')
    const offset = parseInt(searchParams.get('offset') || '0')

    const where: any = {
      user: { email: session.user.email }
    }

    if (status) {
      where.status = status
    }

    const [projects, total] = await Promise.all([
      prisma.project.findMany({
        where,
        include: {
          repositories: true,
          _count: { select: { logs: true, questions: true } }
        },
        orderBy: { createdAt: 'desc' },
        take: limit,
        skip: offset
      }),
      prisma.project.count({ where })
    ])

    return NextResponse.json({ projects, total })
  } catch (error) {
    console.error('Error fetching projects:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

// POST /api/projects - Create new project
export async function POST(request: Request) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.email) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { name, description, repositoryUrls } = body

    if (!name || !description || !repositoryUrls?.length) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 })
    }

    // Get user
    const user = await prisma.user.findUnique({
      where: { id: session.user.id }
    })

    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 })
    }

    // Create project
    const project = await prisma.project.create({
      data: {
        name,
        description,
        userId: user.id,
        workspacePath: `/workspaces/${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
      }
    })

    // Call FastAPI to initialize workspace
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000'
    const initResponse = await fetch(`${fastApiUrl}/projects/initialize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: project.id,
        user_id: user.id,
        feature_request: description,
        repository_urls: repositoryUrls
      })
    })

    if (!initResponse.ok) {
      // Rollback project creation
      await prisma.project.delete({ where: { id: project.id } })
      return NextResponse.json({ error: 'Failed to initialize workspace' }, { status: 500 })
    }

    const initData = await initResponse.json()

    // Create repository records
    for (const repo of initData.repositories) {
      await prisma.repository.create({
        data: {
          projectId: project.id,
          name: repo.name,
          url: repo.url,
          branch: repo.branch,
          defaultBranch: 'main'
        }
      })
    }

    // Fetch complete project with relations
    const completeProject = await prisma.project.findUnique({
      where: { id: project.id },
      include: { repositories: true }
    })

    return NextResponse.json({ project: completeProject, workspace: initData })
  } catch (error) {
    console.error('Error creating project:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
