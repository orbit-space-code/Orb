import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const analysisSession = await prisma.analysisSession.findUnique({
      where: {
        id: params.id,
        userId: session.user.id,
      },
      include: {
        codebase: true,
        toolResults: {
          orderBy: {
            startedAt: 'desc',
          },
        },
        reports: {
          orderBy: {
            generatedAt: 'desc',
          },
        },
      },
    });

    if (!analysisSession) {
      return NextResponse.json(
        { error: 'Analysis session not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(analysisSession);
  } catch (error) {
    console.error('Error fetching analysis session:', error);
    return NextResponse.json(
      { error: 'Failed to fetch analysis session' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Cancel analysis in FastAPI backend
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
    await fetch(`${fastApiUrl}/analysis/${params.id}/cancel`, {
      method: 'POST',
    });

    // Update status in database
    await prisma.analysisSession.update({
      where: {
        id: params.id,
        userId: session.user.id,
      },
      data: {
        status: 'CANCELLED',
      },
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error cancelling analysis session:', error);
    return NextResponse.json(
      { error: 'Failed to cancel analysis session' },
      { status: 500 }
    );
  }
}
