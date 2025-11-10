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
            <h1 className="text-2xl font-bold text-white">Orbitspace OrbitSpace</h1>
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
              <ProjectCard
                key={project.id}
                id={project.id}
                name={project.name}
                description={project.description || undefined}
                currentPhase={project.currentPhase}
                status={project.status}
                createdAt={project.createdAt.toISOString()}
                updatedAt={project.updatedAt.toISOString()}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
