# Development Guide

This document outlines the implementation roadmap for completing the Orbitspace OrbitSpace platform.

## Current Status

**Phase 1: Foundation** ✅ **COMPLETE**

The following has been implemented:

### Frontend (Next.js)
- ✅ Project structure with TypeScript and Tailwind CSS
- ✅ Next.js 14 App Router configuration
- ✅ Prisma schema with all database models
- ✅ NextAuth.js GitHub OAuth authentication
- ✅ Landing page with sign-in flow
- ✅ Dashboard page with project list
- ✅ Prisma client singleton
- ✅ Health check API endpoint

### Backend (FastAPI)
- ✅ FastAPI application structure
- ✅ Meta-agent orchestration module (stub)
- ✅ Tool registry base class
- ✅ Git repository manager (stub)
- ✅ File manager with workspace operations
- ✅ Plugin loader with YAML frontmatter parser
- ✅ Health and metrics endpoints

### Infrastructure
- ✅ Docker Compose with PostgreSQL, Redis, Next.js, and FastAPI
- ✅ Dockerfiles for both services
- ✅ Environment configuration examples
- ✅ Python requirements.txt
- ✅ Node.js package.json with all dependencies

## Next Steps

### Phase 2: Core Infrastructure (4-6 weeks)

#### 2.1 Workspace Management
**Location:** `src/orchestrator/workspace.py`

Implement workspace initialization that:
- Creates `/workspaces/{project-id}/` directory
- Clones specified repositories
- Creates `.OrbitSpace/` directory with metadata
- Stores workspace path in database

**Key functions:**
```python
async def initialize_workspace(project_id: str, repositories: List[str]) -> str
async def cleanup_workspace(project_id: str) -> bool
```

#### 2.2 Git Operations
**Location:** `src/git/repository.py`

Complete the RepositoryManager class:
- `clone_repository()` - Clone with GitHub token authentication
- `create_feature_branch()` - Branch naming: `OrbitSpace/{project-id}-{slug}-{timestamp}`
- `commit_changes()` - Commit with OrbitSpace Bot identity
- `push_branch()` - Push to remote
- `get_status()` - List modified/untracked files
- `get_diff()` - Unified diff

**Testing:** Create test script that clones a repo, creates branch, makes change, commits.

#### 2.3 Implement All 8 Tools
**Location:** `src/tools/`

Each tool must:
- Extend the `Tool` base class from `registry.py`
- Implement `execute(**kwargs)` method
- Validate workspace paths (security)
- Log all executions
- Handle errors gracefully

**Tools to implement:**

1. **grep_tool.py** - Uses `ripgrep` (rg command)
```python
async def execute(workspace_path: str, pattern: str, path: str = ".", case_sensitive: bool = True)
```

2. **glob_tool.py** - Uses Python's `glob` module
```python
async def execute(workspace_path: str, pattern: str)
```

3. **read_tool.py** - Reads file contents
```python
async def execute(workspace_path: str, file_path: str, start_line: int = None, end_line: int = None)
```

4. **edit_tool.py** - Search and replace in files
```python
async def execute(workspace_path: str, file_path: str, old_string: str, new_string: str, replace_all: bool = False)
```

5. **bash_tool.py** - Execute shell commands
```python
async def execute(workspace_path: str, command: str, timeout: int = 60)
# Must whitelist commands, no rm -rf /, network restrictions
```

6. **git_tool.py** - Git operations wrapper
```python
async def execute(workspace_path: str, repo_name: str, operation: str, **params)
```

7. **todo_tool.py** - Task list management
```python
async def execute(project_id: str, todos: List[Dict])
# Store in Redis
```

8. **ask_user_tool.py** - Question-answer flow
```python
async def execute(project_id: str, question: str, choices: List[str], image_url: str = None)
# Publish to Redis, wait for answer from Next.js API
```

**Testing:** Create unit tests for each tool.

#### 2.4 Plugin System
**Location:** `src/plugins/loader.py`

Already has YAML frontmatter parser. Need to add:
- Load commands and skills (not just agents)
- Workspace plugin loading (in addition to system plugins)
- Plugin validation
- Plugin marketplace.json parser

#### 2.5 System Plugin Definitions
**Location:** `system-plugins/plugins/core-agents/agents/`

Create markdown files with agent definitions:

**research-agent.md:**
```markdown
---
name: research-agent
description: Analyzes codebase and creates research.md
model: claude-sonnet-4
tools: [Grep, Glob, Read, Bash, TodoWrite]
triggers: [phase:research]
---

# Research Agent

You are a research agent analyzing codebases for the Orbitspace OrbitSpace platform.

## Your Role
Gather comprehensive context about the codebase to inform planning.

## Process
1. Analyze repository structure using Glob
2. Search for patterns using Grep
3. Read key files using Read
4. Execute commands to understand setup (package.json, requirements.txt)
5. Document findings in research.md

## Output Format
See example in /workspace/cmhelszn505n6ooimm5sgsssx/research.md

...
```

Create similar files for:
- `planning-agent.md`
- `implementation-agent.md`
- `review-agent.md`
- `security-agent.md`
- `test-agent.md`

### Phase 3: Agent Orchestration (4-6 weeks)

#### 3.1 Redis Integration
**Location:** `src/orchestrator/redis_client.py`

Set up Redis client:
```python
class RedisClient:
    def __init__(self, url: str)
    async def publish(channel: str, message: dict)
    async def subscribe(channel: str) -> AsyncIterator[dict]
    async def enqueue_task(queue: str, task: dict)
    async def dequeue_task(queue: str) -> Optional[dict]
    async def get_task_status(task_id: str) -> dict
```

Task queues:
- `tasks:pending` - Tasks waiting to be processed
- `tasks:active` - Currently running tasks
- `tasks:completed` - Finished tasks
- `tasks:failed` - Failed tasks for retry

#### 3.2 Agent Execution Framework
**Location:** `src/orchestrator/agent_executor.py`

Implement agent execution loop:
```python
class AgentExecutor:
    async def execute_agent(
        agent_name: str,
        project_id: str,
        phase: str,
        inputs: Dict[str, Any]
    ) -> str:
        # 1. Load agent definition from plugins
        # 2. Initialize Claude client with appropriate model
        # 3. Provide tools to agent
        # 4. Stream outputs to Redis pub/sub
        # 5. Handle tool calls
        # 6. Store results
        # 7. Update project phase in database
```

Key challenges:
- Tool calling loop (agent requests tool → execute → return result → repeat)
- Streaming outputs to Redis for real-time UI updates
- Error handling and retries
- Timeout management

#### 3.3 Meta-Agent Implementation
**Location:** `src/orchestrator/meta_agent.py`

Complete the MetaAgent class to:
- Distribute tasks to appropriate agents
- Monitor execution across multiple agents
- Aggregate results from parallel agents (overwatchers)
- Handle agent failures and retries

#### 3.4 Claude API Integration
**Location:** `src/orchestrator/claude_client.py`

Wrapper around Anthropic SDK:
```python
class ClaudeClient:
    async def create_message(
        model: str,
        system_prompt: str,
        messages: List[Dict],
        tools: List[Tool],
        stream: bool = True
    ) -> AsyncIterator[dict]:
        # Handle streaming responses
        # Parse tool calls
        # Handle stop reasons
```

### Phase 4: Implementation Agents (3-4 weeks)

#### 4.1 Implement Research Agent
Connect agent definition to execution:
- Use Grep, Glob, Read tools to analyze code
- Generate research.md with findings
- Transition project to PLANNING phase

#### 4.2 Implement Planning Agent
- Read research.md
- Ask questions using AskUser tool
- Wait for answers via Redis pub/sub
- Generate planning.md
- Allow user to edit planning.md

#### 4.3 Implement Implementation Agent
- Read planning.md and research.md
- Execute changes using Edit tool
- Create commits using Git tool
- Stream progress updates

#### 4.4 Implement Overwatcher Agents
Run in parallel with Implementation Agent:
- **Review Agent**: Check code quality, suggest improvements
- **Security Agent**: Scan for vulnerabilities
- **Test Agent**: Run tests after changes

### Phase 5: Real-Time UI (3-4 weeks)

#### 5.1 SSE Streaming Endpoint
**Location:** `src/app/api/projects/[id]/stream/route.ts`

Server-Sent Events endpoint:
```typescript
export async function GET(request: Request, { params }) {
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    async start(controller) {
      // Subscribe to Redis pub/sub for project
      // Stream events to client
      // Format: event: log\ndata: {JSON}\n\n
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
```

#### 5.2 Redis to SSE Bridge
**Location:** `src/orchestrator/sse_bridge.py`

FastAPI publishes to Redis → Next.js SSE endpoint subscribes → Browser receives

#### 5.3 React Components

**LogStream.tsx** - Real-time log viewer
```typescript
const LogStream = ({ projectId }: { projectId: string }) => {
  // Connect to SSE endpoint
  // Display logs with syntax highlighting
  // Auto-scroll to bottom
  // Color-code by log type
}
```

**QuestionCard.tsx** - Interactive question UI
```typescript
const QuestionCard = ({ question }: { question: Question }) => {
  // Display question text
  // Show optional image
  // Render choice buttons
  // POST answer to API
  // Show loading state
}
```

**PhaseIndicator.tsx** - Visual progress stepper
```typescript
const PhaseIndicator = ({ currentPhase }: { currentPhase: Phase }) => {
  // Show: Research → Planning → Implementation → Complete
  // Highlight current phase
  // Gray out future phases
}
```

**MarkdownEditor.tsx** - Edit planning.md
```typescript
const MarkdownEditor = ({ content, onSave }: Props) => {
  // Monaco editor integration
  // Live preview pane
  // Save button
}
```

#### 5.4 Project Creation Flow
**Location:** `src/app/projects/new/page.tsx`

Form to create project:
- Feature request text area
- Repository selector (fetch from GitHub API)
- Start Research button

When submitted:
1. POST to `/api/projects` (Next.js)
2. Next.js calls FastAPI `/projects/initialize`
3. FastAPI initializes workspace, clones repos
4. Redirect to `/projects/[id]`
5. Automatically start research phase

### Phase 6: Polish & Production (2-3 weeks)

#### 6.1 Error Handling
- Agent execution failures
- Tool execution errors
- Network timeouts
- Database connection issues
- Redis connection issues
- Graceful degradation

#### 6.2 Testing
- Unit tests for all tools
- Integration tests for agent workflows
- End-to-end tests for full project flow
- Load testing for concurrent projects

#### 6.3 Documentation
- API documentation (OpenAPI/Swagger)
- Agent development guide
- Plugin development guide
- Deployment guide

#### 6.4 Production Deployment
- Environment-specific configurations
- Secrets management
- Database migrations
- Monitoring and logging
- Performance optimization
- Security audit

## Development Tips

### Local Development Setup

1. **Start only database and Redis:**
```bash
docker-compose up postgres redis -d
```

2. **Run Next.js in development mode:**
```bash
npm install
npx prisma generate
npx prisma migrate dev
npm run dev
```

3. **Run FastAPI with hot reload:**
```bash
pip install -r requirements.txt
uvicorn src.main:app --reload
```

### Testing Individual Components

**Test a tool:**
```python
# test_grep_tool.py
from src.tools.grep_tool import GrepTool

async def test_grep():
    tool = GrepTool()
    results = await tool.execute(
        workspace_path="/workspaces/test",
        pattern="function",
        path="."
    )
    assert len(results) > 0
```

**Test agent execution:**
```python
# test_research_agent.py
from src.orchestrator.agent_executor import AgentExecutor

async def test_research_agent():
    executor = AgentExecutor()
    task_id = await executor.execute_agent(
        agent_name="research-agent",
        project_id="test-123",
        phase="RESEARCH",
        inputs={"feature_request": "Add auth"}
    )
    # Wait for completion and verify research.md created
```

### Debugging

**FastAPI logs:**
```bash
docker-compose logs -f fastapi
```

**Next.js logs:**
```bash
docker-compose logs -f nextjs
```

**Redis monitoring:**
```bash
docker exec -it <redis-container> redis-cli MONITOR
```

**Database queries:**
```bash
npx prisma studio
```

## Architecture Decisions

### Why Next.js API Routes for Database?
- Prisma works best in Node.js environment
- Clean separation: Next.js owns data, FastAPI owns AI logic
- FastAPI calls Next.js API for database operations

### Why Redis for Task Queue?
- Fast in-memory operations
- Built-in pub/sub for real-time updates
- Simple task queue patterns
- Scales horizontally

### Why Two Models (Sonnet + Haiku)?
- Sonnet 4: Planning, review, critical decisions (slower, smarter)
- Haiku 4: Code generation, fast execution (faster, cheaper)
- Cost optimization while maintaining quality

### Why SSE Instead of WebSockets?
- Simpler for server-to-client streaming
- Automatic reconnection in browsers
- Works well with HTTP/2
- No need for bidirectional communication

## Common Issues & Solutions

### Issue: Prisma Client Not Found
**Solution:**
```bash
npx prisma generate
```

### Issue: Redis Connection Failed
**Solution:**
Check Redis is running:
```bash
docker-compose ps redis
```

### Issue: GitHub OAuth Not Working
**Solution:**
1. Check callback URL matches: `http://localhost:3000/api/auth/callback/github`
2. Verify environment variables are set
3. Check GitHub App permissions

### Issue: Agent Not Starting
**Solution:**
1. Check ANTHROPIC_API_KEY is set
2. Verify plugin definition loaded
3. Check Redis connection
4. Review FastAPI logs

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Anthropic API Reference](https://docs.anthropic.com/)
- [Prisma Documentation](https://www.prisma.io/docs)
- [Redis Documentation](https://redis.io/docs/)

## Questions?

Refer to `planning.md` for detailed specifications of all components.
