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

    // Read research.md from workspace
    const researchPath = path.join(project.workspacePath, 'research.md')

    try {
      const content = await fs.readFile(researchPath, 'utf-8')
      const stats = await fs.stat(researchPath)

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
    console.error('Error reading research.md:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
