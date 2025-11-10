# OrbitSpace - Advanced Codebase Analysis Platform

[![Deploy OrbitSpace](https://github.com/orbitspace/orbitspace/actions/workflows/deploy.yml/badge.svg)](https://github.com/orbitspace/orbitspace/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

OrbitSpace is a comprehensive AI-powered codebase analysis platform that helps developers understand, analyze, and improve their code through advanced static analysis, security scanning, and intelligent recommendations.

## 🚀 Features

### Core Capabilities
- **Multi-Source Codebase Import** - GitHub, GitLab, local upload, and URL import
- **AI-Powered Analysis** - Bring your own API keys (Anthropic, OpenAI, custom)
- **60+ Analysis Tools** - Static analysis, security scanning, performance optimization
- **Three Analysis Modes** - Normal (5 min), Standard (20 min), Deep (60 min)
- **Comprehensive Reporting** - PDF, HTML, JSON, and interactive dashboards
- **GitHub Integration** - PR comments, automated analysis, GitHub Actions

### Analysis Tools Suite

#### Static Analysis (15 tools)
- ESLint, TSLint, Pylint, RuboCop, Checkstyle
- SonarQube, CodeClimate, Codacy
- Language-specific analyzers (Go vet, Rust clippy, etc.)

#### Security Scanners (12 tools)
- Bandit (Python), Brakeman (Ruby), ESLint Security
- Snyk, OWASP Dependency Check, Safety
- Secret scanners (GitLeaks, TruffleHog)
- SAST tools (Semgrep, CodeQL)

#### Code Quality Tools (10 tools)
- Prettier, Black, gofmt, rustfmt
- Complexity analyzers (McCabe, Halstead)
- Duplication detectors (PMD CPD, SonarQube)
- Test coverage analyzers

#### Performance Tools (8 tools)
- Profilers (py-spy, perf, pprof)
- Memory analyzers (Valgrind, AddressSanitizer)
- Bundle analyzers (webpack-bundle-analyzer)
- Performance linters

#### Documentation Tools (6 tools)
- JSDoc, Sphinx, Doxygen
- README analyzers
- API documentation generators
- Comment quality analyzers

#### Architecture Tools (9 tools)
- Dependency analyzers (madge, jdeps)
- Architecture validators
- Design pattern detectors
- Coupling/cohesion analyzers
- Dead code detectors

## 🏗️ Architecture

OrbitSpace is built with a modern, scalable architecture:

- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Backend**: FastAPI with Python for agent orchestration
- **Database**: PostgreSQL with Prisma ORM
- **Cache**: Redis for task queuing and real-time updates
- **Authentication**: NextAuth.js with GitHub OAuth
- **AI Integration**: Anthropic Claude and OpenAI GPT APIs
- **Deployment**: Docker containers with Kubernetes support

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/orbitspace/orbitspace.git
   cd orbitspace
   ```

2. **Install dependencies**
   ```bash
   # Install Node.js dependencies
   npm install
   
   # Install Python dependencies
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   
   # Generate secure secrets
   node generate-secrets.js
   
   # Copy the generated secrets to your .env file
   # Edit .env with your other configuration
   ```

4. **Set up the database**
   ```bash
   npx prisma generate
   npx prisma db push
   ```

5. **Start the development servers**
   ```bash
   # Start Next.js frontend
   npm run dev
   
   # Start FastAPI backend (in another terminal)
   python main.py
   ```

6. **Visit the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

#### 🔐 Generate Secure Secrets

First, generate cryptographically secure secrets:

```bash
node generate-secrets.js
```

This will generate:
- **NEXTAUTH_SECRET**: 128-character hex string for NextAuth JWT signing
- **FASTAPI_SECRET_KEY**: 128-character hex string for FastAPI JWT/sessions
- **NEXTJS_API_SECRET**: Base64-encoded secret for internal API communication
- **ENCRYPTION_KEY**: 64-character hex string for API key encryption

#### 📝 Complete Environment Configuration

```env
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/orbitspace"

# GitHub OAuth
GITHUB_CLIENT_ID="your_github_client_id"
GITHUB_CLIENT_SECRET="your_github_client_secret"

# NextAuth
NEXTAUTH_SECRET="your_nextauth_secret"
NEXTAUTH_URL="http://localhost:3000"

# Redis
REDIS_URL="redis://localhost:6379"
# Or for Upstash Redis:
# REDIS_URL="https://your-redis-url.upstash.io"
# REDIS_TOKEN="your_redis_token"

# Encryption
ENCRYPTION_KEY="your_32_byte_encryption_key"

# FastAPI Backend
FASTAPI_URL="http://localhost:8000"
```

### GitHub OAuth Setup

1. Go to GitHub Settings > Developer settings > OAuth Apps
2. Create a new OAuth App with:
   - Application name: OrbitSpace
   - Homepage URL: http://localhost:3000 (or your domain)
   - Authorization callback URL: http://localhost:3000/api/auth/callback/github
3. Copy the Client ID and Client Secret to your `.env` file

### API Key Management

Users can securely store their AI service API keys:

1. Navigate to Settings > API Keys
2. Add your Anthropic or OpenAI API key
3. Keys are encrypted and stored securely
4. Test keys to ensure they're valid

## 📊 Usage

### Basic Workflow

1. **Import Codebase**
   - Connect GitHub repository
   - Upload local files
   - Import from URL

2. **Configure Analysis**
   - Choose analysis mode (Normal/Standard/Deep)
   - Select specific tools
   - Set custom parameters

3. **Run Analysis**
   - Monitor real-time progress
   - View tool execution status
   - Get notifications on completion

4. **Review Results**
   - Interactive dashboard
   - Detailed technical reports
   - Executive summaries
   - Export in multiple formats

### Analysis Modes

- **Normal Mode** (2-5 minutes)
  - Basic static analysis
  - Language-specific linting
  - Simple security scanning
  - Essential metrics

- **Standard Mode** (10-20 minutes)
  - Comprehensive static analysis
  - Security vulnerability scanning
  - Code quality metrics
  - Dependency analysis

- **Deep Mode** (30-60 minutes)
  - All available tools
  - Advanced security auditing
  - Performance profiling
  - AI-powered recommendations
  - Architecture analysis

## 🔌 API Reference

### REST API Endpoints

#### Codebase Management
- `GET /api/codebases` - List user codebases
- `POST /api/codebases` - Import new codebase
- `GET /api/codebases/{id}` - Get codebase details
- `DELETE /api/codebases/{id}` - Delete codebase

#### Analysis Sessions
- `POST /api/analysis/sessions` - Start analysis
- `GET /api/analysis/sessions/{id}` - Get session status
- `GET /api/analysis/sessions/{id}/results` - Get results
- `DELETE /api/analysis/sessions/{id}` - Cancel analysis

#### API Key Management
- `GET /api/user/api-keys` - List user API keys
- `POST /api/user/api-keys` - Add API key
- `PUT /api/user/api-keys/{provider}` - Update API key
- `DELETE /api/user/api-keys/{provider}` - Delete API key

### WebSocket Events

Real-time updates for analysis progress:

```javascript
const ws = new WebSocket('ws://localhost:3000/api/ws')

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  
  if (data.type === 'analysis_progress') {
    console.log(`Progress: ${data.progress}%`)
  }
}
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
npm test

# Run Python tests
python -m pytest tests/ -v

# Run with coverage
npm run test:coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Test Structure

```
tests/
├── frontend/           # Next.js component tests
├── backend/           # FastAPI endpoint tests
├── integration/       # End-to-end tests
└── fixtures/         # Test data and mocks
```

## 🚀 Deployment

### Docker Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Run migrations
docker-compose exec web npx prisma db push
```

### Production Deployment

1. **Environment Setup**
   - Set production environment variables
   - Configure database and Redis
   - Set up SSL certificates

2. **Build Application**
   ```bash
   npm run build
   ```

3. **Deploy**
   - Use the provided GitHub Actions workflow
   - Or deploy manually to your preferred platform

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style

- TypeScript/JavaScript: ESLint + Prettier
- Python: Black + isort + flake8
- Commit messages: Conventional Commits

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [docs.orbitspace.org](https://docs.orbitspace.org)
- **Issues**: [GitHub Issues](https://github.com/orbitspace/orbitspace/issues)
- **Discussions**: [GitHub Discussions](https://github.com/orbitspace/orbitspace/discussions)
- **Email**: support@orbitspace.org

## 🗺️ Roadmap

- [ ] **Q1 2024**: Advanced AI integrations
- [ ] **Q2 2024**: Enterprise features
- [ ] **Q3 2024**: Plugin ecosystem
- [ ] **Q4 2024**: Cloud deployment options

## 🙏 Acknowledgments

- Built with [Next.js](https://nextjs.org/), [FastAPI](https://fastapi.tiangolo.com/), and [Prisma](https://prisma.io/)
- Powered by [Anthropic Claude](https://anthropic.com/) and [OpenAI](https://openai.com/)
- Inspired by the open-source community

---

**OrbitSpace** - Elevating code quality through intelligent analysis 🚀