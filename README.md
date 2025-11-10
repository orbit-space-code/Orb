# Orb - AI-Powered Code Generation Platform

Orb is an advanced AI-powered development platform that helps developers write better code faster through intelligent code generation, quality analysis, and GitHub integration.

## ✨ Features

### Core Capabilities
- **AI-Powered Code Generation**
  - Multi-model support (Claude, GPT, local models)
  - Context-aware code completion
  - Template-based code generation
  - Multi-language support (Python, JavaScript, TypeScript, and more)

### Code Quality & Analysis
- **Static Code Analysis**
  - Automated code reviews
  - Security vulnerability detection
  - Performance optimization suggestions
  - Code style enforcement

### GitHub Integration
- **Repository Management**
  - Browse and search repositories
  - File and directory operations
  - Branch management
  - Pull request automation

### Development Tools
- **Interactive Development Environment**
  - Real-time code execution
  - Debugging assistance
  - Dependency visualization
  - Code search and navigation
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

Orb is built with a modern, scalable architecture:

- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **Backend**: FastAPI with Python for agent orchestration
- **Database**: PostgreSQL with Prisma ORM
- **Cache**: Redis for task queuing and real-time updates
- **Authentication**: JWT with GitHub OAuth
- **AI Integration**: Claude, GPT, and local models
- **Deployment**: Docker containers with Kubernetes support

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+ (for frontend)
- PostgreSQL (for production)
- Redis (for caching and task queue)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/orb.git
   cd orb
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize the database**
   ```bash
   python -m alembic upgrade head
   ```

5. **Start the development server**
   ```bash
   uvicorn main:app --reload
   ```

6. **Access the application**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables

Create a `.env` file with these variables:

```env
# Core Settings
DEBUG=True
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=sqlite:///./orb.db  # Use PostgreSQL in production

# Redis
REDIS_URL=redis://localhost:6379/0

# GitHub OAuth (optional)
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# AI Providers
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key
```

### GitHub Integration

1. Create a GitHub OAuth App at [GitHub Developer Settings](https://github.com/settings/developers)
2. Set the callback URL to: `http://localhost:8000/api/github/auth/callback`
3. Add the client ID and secret to your `.env` file

## 💻 Usage

### Basic Workflow

1. **Start a New Project**
   ```python
   from orb.services.code_generation import CodeGenerator
   
   generator = CodeGenerator()
   response = await generator.generate_code(
       prompt="Create a FastAPI endpoint that returns 'Hello, World!'",
       language="python"
   )
   print(response.generated_code)
   ```

2. **GitHub Integration**
   ```python
   from orb.services.github_service import GitHubService
   
   github = GitHubService(access_token="your-github-token")
   repos = await github.list_repositories()
   for repo in repos:
       print(repo.full_name)
   ```

3. **Code Quality Analysis**
   ```python
   from orb.services.code_quality import analyze_code
   
   report = analyze_code("path/to/your/file.py")
   print(f"Code Quality Score: {report.score}")
   print("Issues found:", report.issues)
   ```

## 📚 Documentation

For detailed documentation, please refer to:
- [API Reference](/docs/api.md)
- [Getting Started Guide](/docs/getting-started.md)
- [Deployment Guide](/docs/deployment.md)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p>Built with ❤️ by the Orb Team</p>
</div>
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