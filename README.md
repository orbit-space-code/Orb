# Orbitspace Compyle

A collaborative AI coding agent platform built on Claude that uses a three-phase workflow (Research → Planning → Implementation) to maintain developer control while automating code generation.

## 🏗️ Architecture

```
Browser (React) ←→ Next.js (Prisma + API Routes) ←→ FastAPI (Agent Orchestration) ←→ Claude API
                          ↓                                    ↓
                   PostgreSQL                           Redis (Task Queue)
```

## 📦 Tech Stack

**Frontend:**
- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS
- NextAuth.js for authentication
- Monaco Editor for code editing

**Backend:**
- Python 3.11
- FastAPI
- Anthropic Claude API (Sonnet 4 + Haiku 4)
- Redis for task queuing
- GitPython for repository operations

**Database:**
- PostgreSQL 15
- Prisma ORM

**Infrastructure:**
- Docker + Docker Compose
- GitHub App for repository access

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.11+
- GitHub Account
- Anthropic API Key

### Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd Orb
```

2. **Configure environment variables:**
```bash
cp .env.example .env.local
```

Edit `.env.local` and add:
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `GITHUB_CLIENT_ID` - GitHub OAuth App client ID
- `GITHUB_CLIENT_SECRET` - GitHub OAuth App secret
- `GITHUB_APP_ID` - GitHub App ID
- `GITHUB_APP_PRIVATE_KEY` - GitHub App private key
- `NEXTAUTH_SECRET` - Random secret (32+ characters)

3. **Create GitHub App:**

Go to GitHub Settings → Developer Settings → GitHub Apps → New GitHub App

Required permissions:
- Contents: Read & Write
- Pull requests: Read & Write
- Metadata: Read

4. **Start services with Docker Compose:**
```bash
docker-compose up -d
```

Or run locally:

**Terminal 1 - Database & Redis:**
```bash
docker-compose up postgres redis
```

**Terminal 2 - Next.js:**
```bash
npm install
npx prisma generate
npx prisma migrate dev
npm run dev
```

**Terminal 3 - FastAPI:**
```bash
pip install -r requirements.txt
uvicorn src.main:app --reload
```

5. **Access the application:**
- Frontend: http://localhost:3000
- FastAPI Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## 📂 Project Structure

```
Orb/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── api/               # API routes
│   │   ├── dashboard/         # Dashboard page
│   │   ├── projects/          # Project pages
│   │   ├── layout.tsx         # Root layout
│   │   └── page.tsx           # Landing page
│   ├── components/            # React components
│   │   ├── ProjectCard.tsx
│   │   ├── LogStream.tsx
│   │   ├── QuestionCard.tsx
│   │   └── ...
│   ├── lib/                   # Shared utilities
│   │   ├── auth.ts           # NextAuth configuration
│   │   └── prisma.ts         # Prisma client
│   ├── orchestrator/          # FastAPI - Agent orchestration
│   │   └── meta_agent.py
│   ├── tools/                 # FastAPI - Tool implementations
│   │   ├── grep_tool.py
│   │   ├── glob_tool.py
│   │   ├── read_tool.py
│   │   ├── edit_tool.py
│   │   ├── bash_tool.py
│   │   ├── git_tool.py
│   │   ├── todo_tool.py
│   │   ├── ask_user_tool.py
│   │   └── registry.py
│   ├── git/                   # FastAPI - Git operations
│   │   └── repository.py
│   ├── files/                 # FastAPI - File management
│   │   └── manager.py
│   ├── plugins/               # FastAPI - Plugin system
│   │   └── loader.py
│   └── main.py               # FastAPI app entry point
├── prisma/
│   └── schema.prisma         # Database schema
├── system-plugins/           # Built-in agent definitions
│   └── plugins/
│       └── core-agents/
│           ├── agents/
│           │   ├── research-agent.md
│           │   ├── planning-agent.md
│           │   └── implementation-agent.md
│           └── skills/
│               ├── typescript.md
│               ├── python.md
│               └── ...
├── docker-compose.yml        # Docker services
├── Dockerfile.nextjs         # Next.js container
├── Dockerfile.fastapi        # FastAPI container
├── package.json              # Node.js dependencies
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🔄 Three-Phase Workflow

### Phase 1: Research
1. User creates project and selects repositories
2. Research agent clones repositories and creates feature branches
3. Agent analyzes codebase using Grep, Glob, and Read tools
4. Generates `research.md` with findings and patterns
5. Automatically transitions to Planning phase

### Phase 2: Planning
1. Planning agent reads `research.md`
2. Agent asks clarifying questions via UI (multiple-choice)
3. User answers questions to refine requirements
4. Agent creates detailed `planning.md` with implementation plan
5. User reviews and can edit `planning.md`
6. User approves to start Implementation

### Phase 3: Implementation
1. Implementation agent reads `planning.md` and `research.md`
2. Main agent writes code using Edit and Git tools
3. Parallel overwatcher agents monitor:
   - Review agent: Code quality and patterns
   - Security agent: Vulnerability scanning
   - Test agent: Running tests
4. Creates commits in feature branches
5. Real-time progress streamed to UI via SSE
6. Completes with summary and branch links

## 🛠️ Development Status

### ✅ Phase 1: Foundation (Complete)
- [x] Next.js project structure
- [x] FastAPI project structure
- [x] Docker Compose configuration
- [x] Prisma schema with all models
- [x] GitHub OAuth authentication
- [x] Landing page and dashboard UI

### 🚧 Phase 2: Core Infrastructure (In Progress)
- [ ] Workspace management (FastAPI)
- [ ] Git operations (clone, branch, commit)
- [ ] Plugin system with loader
- [ ] System plugin definitions
- [ ] All 8 tools (Grep, Glob, Read, Edit, Bash, Git, TodoWrite, AskUser)
- [ ] Tool registry with sandboxing

### ⏳ Phase 3: Agent Orchestration (Pending)
- [ ] Redis task queue integration
- [ ] Meta-agent orchestration logic
- [ ] Agent execution framework
- [ ] Research agent implementation
- [ ] Planning agent with Q&A flow

### ⏳ Phase 4: Implementation & Overwatchers (Pending)
- [ ] Implementation agent
- [ ] Review agent (overwatcher)
- [ ] Security agent (overwatcher)
- [ ] Test agent (overwatcher)

### ⏳ Phase 5: Real-Time UI (Pending)
- [ ] SSE streaming endpoint
- [ ] Redis pub/sub to SSE bridge
- [ ] LogStream component
- [ ] QuestionCard component
- [ ] PhaseIndicator component
- [ ] Full project creation flow

### ⏳ Phase 6: Polish & Production (Pending)
- [ ] Error handling and retry logic
- [ ] Unit and integration tests
- [ ] API documentation
- [ ] Deployment configuration

## 🔧 API Endpoints

### Next.js API Routes (Port 3000)

**Authentication:**
- `GET /api/auth/signin` - Initiate GitHub OAuth
- `GET /api/auth/callback` - OAuth callback
- `GET /api/auth/session` - Get current session
- `POST /api/auth/signout` - Sign out

**Projects:**
- `GET /api/projects` - List user's projects
- `POST /api/projects` - Create new project
- `GET /api/projects/[id]` - Get project details
- `PATCH /api/projects/[id]` - Update project
- `DELETE /api/projects/[id]` - Delete project

**Project Actions:**
- `POST /api/projects/[id]/start-research` - Start research phase
- `POST /api/projects/[id]/start-planning` - Start planning phase
- `POST /api/projects/[id]/start-implementation` - Start implementation
- `GET /api/projects/[id]/stream` - SSE stream for real-time updates

**Files:**
- `GET /api/projects/[id]/files/research` - Get research.md
- `GET /api/projects/[id]/files/planning` - Get planning.md
- `PUT /api/projects/[id]/files/planning` - Update planning.md

### FastAPI Backend (Port 8000)

**Health:**
- `GET /health` - Health check
- `GET /metrics` - System metrics

**Projects:**
- `POST /projects/initialize` - Initialize workspace and clone repos
- `DELETE /projects/{project_id}/workspace` - Cleanup workspace

**Agents:**
- `POST /agents/research/start` - Start research agent
- `POST /agents/planning/start` - Start planning agent
- `POST /agents/implementation/start` - Start implementation agent
- `POST /agents/{task_id}/pause` - Pause agent
- `POST /agents/{task_id}/resume` - Resume agent
- `POST /agents/{task_id}/cancel` - Cancel agent

**Plugins:**
- `GET /plugins` - List available plugins
- `GET /plugins/{plugin_name}` - Get plugin definition

## 🔐 Security

- All file operations sandboxed to workspace directories
- Bash tool with command whitelist and timeout
- GitHub tokens encrypted in database
- Path traversal protection
- Input validation on all endpoints
- CORS configured for Next.js origin only

## 📝 Database Schema

Key models:
- **User** - GitHub OAuth users
- **Project** - AI agent projects
- **Repository** - Git repositories linked to projects
- **Question** - Clarifying questions from planning agent
- **Log** - Agent execution logs

See `prisma/schema.prisma` for full schema.

## 🤝 Contributing

This project follows the compyle.ai architecture. See `planning.md` for detailed specifications.

### Development Workflow

1. Read `planning.md` for feature specifications
2. Implement following the phased approach
3. Test locally with Docker Compose
4. Submit PR with tests and documentation

## 📄 License

[Add your license here]

## 🙏 Acknowledgments

Built on Claude Code and inspired by compyle.ai's collaborative AI agent approach.
