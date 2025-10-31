import { getServerSession } from "next-auth"
import { authOptions } from "@/lib/auth"
import { redirect } from "next/navigation"
import { prisma } from "@/lib/prisma"
import ProjectCard from "@/components/ProjectCard"

export default async function DashboardPage() {
  const session = await getServerSession(authOptions)

  if (!session?.user) {
    redirect("/")
  }

  // Fetch user's projects
  const projects = await prisma.project.findMany({
    where: {
      user: {
        email: session.user.email!,
      },
    },
    orderBy: {
      createdAt: "desc",
    },
    take: 50,
  })

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-white">Orbitspace Compyle</h1>
            <div className="flex items-center gap-4">
              <span className="text-gray-400">
                {session.user.name || session.user.email}
              </span>
              <a
                href="/api/auth/signout"
                className="text-gray-400 hover:text-white transition-colors"
              >
                Sign out
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-8">
          <h2 className="text-3xl font-bold text-white">Your Projects</h2>
          <a
            href="/projects/new"
            className="px-6 py-3 bg-accent hover:bg-blue-600 text-white rounded-lg font-semibold transition-colors"
          >
            + New Project
          </a>
        </div>

        {/* Projects list */}
        {projects.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-400 text-lg mb-4">
              No projects yet. Create your first project to get started!
            </p>
            <a
              href="/projects/new"
              className="inline-block px-6 py-3 bg-accent hover:bg-blue-600 text-white rounded-lg font-semibold transition-colors"
            >
              Create Project
            </a>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <a
                key={project.id}
                href={`/projects/${project.id}`}
                className="block p-6 bg-gray-900 border border-gray-800 rounded-lg hover:border-accent transition-colors"
              >
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-xl font-semibold text-white">{project.name}</h3>
                  <span
                    className={`px-3 py-1 text-xs font-semibold rounded-full ${getStatusColor(
                      project.status
                    )}`}
                  >
                    {project.status}
                  </span>
                </div>

                {project.description && (
                  <p className="text-gray-400 text-sm mb-4 line-clamp-2">
                    {project.description}
                  </p>
                )}

                <div className="flex items-center justify-between">
                  <span
                    className={`px-3 py-1 text-xs font-semibold rounded-full ${getPhaseColor(
                      project.currentPhase
                    )}`}
                  >
                    {project.currentPhase}
                  </span>
                  <span className="text-gray-500 text-xs">
                    {new Date(project.createdAt).toLocaleDateString()}
                  </span>
                </div>
              </a>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

function getPhaseColor(phase: string): string {
  switch (phase) {
    case "RESEARCH":
      return "bg-phase-research/20 text-phase-research"
    case "PLANNING":
      return "bg-phase-planning/20 text-phase-planning"
    case "IMPLEMENTATION":
      return "bg-phase-implementation/20 text-phase-implementation"
    case "COMPLETED":
      return "bg-phase-complete/20 text-phase-complete"
    default:
      return "bg-gray-700 text-gray-300"
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case "ACTIVE":
      return "bg-status-active/20 text-status-active"
    case "PAUSED":
      return "bg-status-paused/20 text-status-paused"
    case "FAILED":
      return "bg-status-failed/20 text-status-failed"
    case "CANCELLED":
      return "bg-status-cancelled/20 text-status-cancelled"
    case "COMPLETED":
      return "bg-phase-complete/20 text-phase-complete"
    default:
      return "bg-gray-700 text-gray-300"
  }
}
