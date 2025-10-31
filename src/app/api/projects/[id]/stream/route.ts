import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import Redis from 'ioredis'

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions)
  if (!session?.user?.email) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Create SSE stream
  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      // Connect to Redis
      const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379')
      const subscriber = redis.duplicate()

      const channel = `project:${params.id}:events`

      try {
        await subscriber.subscribe(channel)

        subscriber.on('message', (ch, message) => {
          if (ch === channel) {
            try {
              const data = JSON.parse(message)
              const sseMessage = `event: ${data.type}\ndata: ${JSON.stringify(data)}\n\n`
              controller.enqueue(encoder.encode(sseMessage))
            } catch (error) {
              console.error('Error parsing message:', error)
            }
          }
        })

        // Send heartbeat every 15 seconds
        const heartbeat = setInterval(() => {
          try {
            controller.enqueue(encoder.encode(':heartbeat\n\n'))
          } catch (error) {
            clearInterval(heartbeat)
          }
        }, 15000)

        // Cleanup on close
        request.signal.addEventListener('abort', () => {
          clearInterval(heartbeat)
          subscriber.unsubscribe(channel)
          subscriber.quit()
          redis.quit()
          controller.close()
        })

      } catch (error) {
        console.error('SSE error:', error)
        subscriber.quit()
        redis.quit()
        controller.close()
      }
    }
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}
