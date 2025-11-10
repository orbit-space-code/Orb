import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import Redis from 'ioredis'

export async function POST(
  request: Request,
  { params }: { params: { id: string; questionId: string } }
) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.email) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { answer } = body

    if (!answer) {
      return NextResponse.json({ error: 'Answer is required' }, { status: 400 })
    }

    // Update question in database
    const question = await prisma.question.update({
      where: { id: params.questionId },
      data: {
        answer,
        answeredAt: new Date()
      }
    })

    // Publish answer to Redis for agent
    const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379')
    const answerKey = `project:${params.id}:answer:${params.questionId}`
    const answerData = {
      answer,
      answered_at: new Date().toISOString()
    }

    await redis.set(answerKey, JSON.stringify(answerData), 'EX', 300)
    await redis.quit()

    return NextResponse.json({ success: true, question })
  } catch (error) {
    console.error('Error submitting answer:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
