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
    const { name, description, sourceType, sourceUrl } = body;

    // Validate input
    if (!name || !sourceType) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Create codebase
    const codebase = await prisma.codebase.create({
      data: {
        userId: session.user.id,
        name,
        description,
        sourceType,
        sourceUrl,
        languages: [],
        frameworkInfo: {},
      },
    });

    // Trigger codebase indexing in FastAPI backend
    const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
    await fetch(`${fastApiUrl}/codebases/${codebase.id}/index`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        codebase_id: codebase.id,
        source_type: sourceType,
        source_url: sourceUrl,
      }),
    });

    return NextResponse.json(codebase);
  } catch (error) {
    console.error('Error creating codebase:', error);
    return NextResponse.json(
      { error: 'Failed to create codebase' },
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

    const codebases = await prisma.codebase.findMany({
      where: {
        userId: session.user.id,
      },
      include: {
        analysisSessions: {
          select: {
            id: true,
            status: true,
            startedAt: true,
          },
          orderBy: {
            startedAt: 'desc',
          },
          take: 1,
        },
      },
      orderBy: {
        createdAt: 'desc',
      },
    });

    return NextResponse.json(codebases);
  } catch (error) {
    console.error('Error fetching codebases:', error);
    return NextResponse.json(
      { error: 'Failed to fetch codebases' },
      { status: 500 }
    );
  }
}
