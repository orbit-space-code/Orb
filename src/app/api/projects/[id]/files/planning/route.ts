import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { promises as fs } from 'fs'
import path from 'path'

export async function GET(
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

    const planningPath = path.join(project.workspacePath, 'planning.md')

    try {
      const content = await fs.readFile(planningPath, 'utf-8')
      const stats = await fs.stat(planningPath)

      return NextResponse.json({
        content,
        updatedAt: stats.mtime.toISOString()
      })
    } catch (error) {
      return NextResponse.json({
        content: null,
        error: 'File not found'
      }, { status: 404 })
    }
  } catch (error) {
    console.error('Error reading planning.md:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function PUT(
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

    const body = await request.json()
    const { content } = body

    if (!content) {
      return NextResponse.json({ error: 'Content is required' }, { status: 400 })
    }

    const planningPath = path.join(project.workspacePath, 'planning.md')
    await fs.writeFile(planningPath, content, 'utf-8')

    return NextResponse.json({
      success: true,
      updatedAt: new Date().toISOString()
    })
  } catch (error) {
    console.error('Error updating planning.md:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
