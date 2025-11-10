import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { codebaseId, mode, toolsSelected } = body;

    // Validate input
    if (!codebaseId || !mode) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Create analysis session
    const analysisSession = await prisma.analysisSession.create({
      data: {
        codebaseId,
        userId: session.user.id,
        mode,
        toolsSelected: toolsSelected || [],
        status: 'PENDING',
        estimatedDuration: mode === 'NORMAL' ? 300 : mode === 'STANDARD' ? 1200 : 3600,
      },
    });

    // Trigger analysis in FastAPI backend
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
    const response = await fetch(`${fastApiUrl}/analysis/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: analysisSession.id,
        codebase_id: codebaseId,
        mode,
        tools: toolsSelected,
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to start analysis');
    }

    return NextResponse.json(analysisSession);
  } catch (error) {
    console.error('Error creating analysis session:', error);
    return NextResponse.json(
      { error: 'Failed to create analysis session' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const codebaseId = searchParams.get('codebaseId');

    const where: any = { userId: session.user.id };
    if (codebaseId) {
      where.codebaseId = codebaseId;
    }

    const sessions = await prisma.analysisSession.findMany({
      where,
      include: {
        codebase: {
          select: {
            id: true,
            name: true,
          },
        },
      },
      orderBy: {
        startedAt: 'desc',
      },
      take: 50,
    });

    return NextResponse.json(sessions);
  } catch (error) {
    console.error('Error fetching analysis sessions:', error);
    return NextResponse.json(
      { error: 'Failed to fetch analysis sessions' },
      { status: 500 }
    );
  }
}
