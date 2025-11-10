import { NextRequest } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { getRedisClient } from '@/lib/redis';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return new Response('Unauthorized', { status: 401 });
  }

  const encoder = new TextEncoder();
  const redis = getRedisClient();

  const stream = new ReadableStream({
    async start(controller) {
      try {
        // Subscribe to Redis channel for this analysis session
        const channel = `analysis:${params.id}`;
        
        await redis.subscribe(channel, (message) => {
          const data = `data: ${JSON.stringify(message)}\n\n`;
          controller.enqueue(encoder.encode(data));
        });

        // Send initial connection message
        const initialData = `data: ${JSON.stringify({ type: 'connected', sessionId: params.id })}\n\n`;
        controller.enqueue(encoder.encode(initialData));

      } catch (error) {
        console.error('SSE stream error:', error);
        controller.error(error);
      }
    },
    cancel() {
      // Cleanup: unsubscribe from Redis
      redis.unsubscribe(`analysis:${params.id}`);
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
