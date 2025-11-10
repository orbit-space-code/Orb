# Orbitspace Compyle - Setup Guide

Complete setup guide for running the Compyle.ai replica system.

## **System Architecture**

```
Browser (React/Next.js)
    ↓
Next.js API Routes (Prisma/PostgreSQL)
    ↓
FastAPI Backend (Agent Orchestration)
    ↓
Claude API (Sonnet 4 & Haiku 4)
    ↓
Redis (Task Queue & Pub/Sub)
    ↓
Workspaces (Git Repositories)
```

## **Prerequisites**

- **Node.js** 20+ and npm/yarn/pnpm
- **Python** 3.11+
- **PostgreSQL** 15+
- **Redis** 7+
- **Git**
- **Anthropic API Key** (Claude access)
- **GitHub App** (for OAuth & repository access)

## **Step 1: Clone and Install**

```bash
# Navigate to Orb directory
cd Orb

# Install Next.js dependencies
npm install

# Install Python dependencies (in virtual environment)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## **Step 2: Database Setup**

```bash
# Start PostgreSQL (if using Docker)
docker run --name compyle-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=orbitspace_compyle \
  -p 5432:5432 \
  -d postgres:15

# Run Prisma migrations
npx prisma migrate deploy

# Generate Prisma client
npx prisma generate
```

## **Step 3: Redis Setup**

```bash
# Start Redis (if using Docker)
docker run --name compyle-redis \
  -p 6379:6379 \
  -d redis:7-alpine
```

## **Step 4: GitHub App Setup**

1. Go to https://github.com/settings/apps/new
2. Create a new GitHub App with these settings:
   - **App name**: Orbitspace Compyle
   - **Homepage URL**: http://localhost:3000
   - **Callback URL**: http://localhost:3000/api/auth/callback/github
   - **Webhooks**: Disabled (not needed)
   - **Permissions**:
     - Repository contents: Read & Write
     - Pull requests: Read & Write
     - Metadata: Read-only
3. Generate a private key and download it
4. Install the app to your GitHub account
5. Copy Client ID, Client Secret, App ID, and Private Key

## **Step 5: Environment Configuration**

### **Next.js (.env.local)**

```bash
# Copy example file
cp .env.local.example .env.local

# Edit with your values
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/orbitspace_compyle"
GITHUB_CLIENT_ID="your_github_client_id"
GITHUB_CLIENT_SECRET="your_github_client_secret"
GITHUB_APP_ID="your_github_app_id"
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
NEXTAUTH_SECRET="$(openssl rand -base64 32)"
NEXTAUTH_URL="http://localhost:3000"
FASTAPI_URL="http://localhost:8000"
REDIS_URL="redis://localhost:6379"
```

### **FastAPI (.env)**

```bash
# Copy example file
cp .env.example .env

# Edit with your values
ANTHROPIC_API_KEY="your_anthropic_api_key"
REDIS_URL="redis://localhost:6379"
NEXTJS_API_URL="http://localhost:3000"
WORKSPACE_ROOT="/workspaces"
GIT_BOT_NAME="Compyle Bot"
GIT_BOT_EMAIL="bot@compyle.dev"
GITHUB_APP_ID="your_github_app_id"
GITHUB_APP_PRIVATE_KEY_PATH="/path/to/private-key.pem"
```

## **Step 6: Create Workspaces Directory**

```bash
# Create directory for workspace operations
sudo mkdir -p /workspaces
sudo chown $USER:$USER /workspaces

# Or use a local directory
mkdir -p ~/compyle-workspaces
# Then set WORKSPACE_ROOT=~/compyle-workspaces in .env
```

## **Step 7: Start the System**

### **Terminal 1: Next.js Frontend**

```bash
npm run dev
# Runs on http://localhost:3000
```

### **Terminal 2: FastAPI Backend**

```bash
source venv/bin/activate
cd src
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Runs on http://localhost:8000
```

### **Terminal 3: Check Services**

```bash
# Check FastAPI health
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","redis":"connected","filesystem":"ok","agents_loaded":7}

# Check Next.js
curl http://localhost:3000/api/health
```

## **Step 8: First Run**

1. Open http://localhost:3000
2. Click "Sign in with GitHub"
3. Authorize the GitHub App
4. Create a new project:
   - Enter project name
   - Describe the feature you want to build
   - Select repositories
5. Click "Create Project & Start Research"
6. Watch the agents work in real-time!

## **System Components**

### **Frontend (Next.js)**
- **Port**: 3000
- **Database**: PostgreSQL via Prisma
- **Features**:
  - User authentication (GitHub OAuth)
  - Project management UI
  - Real-time event streaming (SSE)
  - Interactive question cards

### **Backend (FastAPI)**
- **Port**: 8000
- **Features**:
  - Agent orchestration (Meta-agent)
  - Tool execution (8 tools)
  - Plugin system (7 agents)
  - Workspace management
  - Git operations

### **Agents Available**

1. **research-agent** (Sonnet 4) - Analyzes codebase
2. **planning-agent** (Sonnet 4) - Creates implementation plan
3. **implementation-agent** (Haiku 4) - Writes code
4. **review-agent** (Sonnet 4) - Code quality checks
5. **security-agent** (Sonnet 4) - Security scanning
6. **test-agent** (Haiku 4) - Test execution
7. **documentation-agent** (Haiku 4) - Documentation generation

## **Troubleshooting**

### **"Redis connection failed"**
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# Restart Redis
docker restart compyle-redis
```

### **"PostgreSQL connection failed"**
```bash
# Check PostgreSQL is running
psql -h localhost -U postgres -d orbitspace_compyle

# Restart PostgreSQL
docker restart compyle-postgres
```

### **"Anthropic API error"**
```bash
# Verify API key is valid
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### **"Workspace permissions error"**
```bash
# Fix workspace directory permissions
sudo chown -R $USER:$USER /workspaces
chmod -R 755 /workspaces
```

### **"Agent plugin not found"**
```bash
# Check plugins are loaded
curl http://localhost:8000/plugins

# Verify plugin files exist
ls -la system-plugins/plugins/core-agents/agents/
```

## **Development Mode**

### **Hot Reload**
- Next.js: Automatic with `npm run dev`
- FastAPI: Automatic with `--reload` flag

### **View Logs**
```bash
# FastAPI logs
tail -f logs/fastapi.log

# Check agent execution
curl http://localhost:8000/metrics
```

### **Database GUI**
```bash
# Use Prisma Studio
npx prisma studio
# Opens on http://localhost:5555
```

### **Redis CLI**
```bash
# Monitor Redis commands
redis-cli monitor

# Check task queue
redis-cli LLEN tasks:pending
redis-cli LLEN tasks:active
```

## **Production Deployment**

### **Using Docker Compose**

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### **Environment Variables for Production**
- Set `NODE_ENV=production`
- Set `ENV=production`
- Use strong `NEXTAUTH_SECRET`
- Use managed PostgreSQL & Redis
- Enable HTTPS
- Set proper CORS origins

## **Testing the System**

### **1. Test Research Phase**
```bash
# Create a test project via API
curl -X POST http://localhost:3000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Project",
    "description": "Add a login page with email and password",
    "repositoryUrls": ["https://github.com/yourusername/test-repo"]
  }'

# Start research phase
curl -X POST http://localhost:3000/api/projects/{project_id}/start-research
```

### **2. Monitor Real-time Events**
```bash
# Subscribe to SSE stream
curl -N http://localhost:3000/api/projects/{project_id}/stream
```

### **3. Check Workspace**
```bash
# View workspace contents
ls -la /workspaces/{project_id}/

# Check research.md
cat /workspaces/{project_id}/research.md
```

## **Next Steps**

1. **Configure GitHub App** with proper permissions
2. **Test with a real repository** to see full workflow
3. **Monitor agent execution** via SSE streams
4. **Review generated code** in feature branches
5. **Customize agent definitions** in `system-plugins/plugins/`

## **Support & Documentation**

- **API Documentation**: http://localhost:8000/docs
- **GitHub Issues**: Report bugs and feature requests
- **Planning Document**: See `planning.md` for full specification

## **Security Notes**

⚠️ **Important Security Considerations:**

1. **Never commit `.env` or `.env.local`** files
2. **Rotate GitHub tokens** if accidentally exposed
3. **Use strong NEXTAUTH_SECRET** in production
4. **Enable rate limiting** on API endpoints
5. **Validate all user inputs** before processing
6. **Use HTTPS only** in production
7. **Encrypt database backups**
8. **Implement proper CORS** settings

---

**System is ready! Start building with AI agents.** 🚀
