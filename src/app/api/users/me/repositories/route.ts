import { NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { Octokit } from '@octokit/rest'

export async function GET() {
  try {
    const session = await getServerSession(authOptions)

    if (!session?.user?.email) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get GitHub access token from session
    // @ts-ignore - NextAuth types don't include accessToken by default
    const accessToken = session.accessToken

    if (!accessToken) {
      return NextResponse.json(
        { error: 'GitHub access token not found' },
        { status: 401 }
      )
    }

    // Initialize Octokit with user's access token
    const octokit = new Octokit({
      auth: accessToken,
    })

    // Fetch user's repositories
    const { data } = await octokit.repos.listForAuthenticatedUser({
      sort: 'updated',
      per_page: 100,
      affiliation: 'owner,collaborator',
    })

    // Format repositories for frontend
    const repositories = data.map((repo) => ({
      name: repo.name,
      url: repo.html_url,
      private: repo.private,
      stars: repo.stargazers_count,
      updatedAt: repo.updated_at,
      description: repo.description,
      language: repo.language,
    }))

    return NextResponse.json(repositories)
  } catch (error) {
    console.error('Error fetching repositories:', error)
    return NextResponse.json(
      { error: 'Failed to fetch repositories from GitHub' },
      { status: 500 }
    )
  }
}
