#!/usr/bin/env python3
"""
OrbitSpace FastAPI Backend
Main application entry point for the agent orchestration system
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Import services
from src.api.routes import router, set_dependencies
from src.api.routers import debug as debug_router
from src.orchestrator.workspace import WorkspaceManager
from src.orchestrator.meta_agent import MetaAgent
from src.orchestrator.redis_client import get_redis_client
from src.orchestrator.agent_executor import AgentExecutor
from src.orchestrator.claude_client import ClaudeClient
from src.plugins.loader import PluginLoader
from src.files.manager import FileManager
from src.github.pull_request_service import PullRequestService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
workspace_manager = None
meta_agent = None
redis_client = None
pr_service = None
agent_executor = None
file_manager = None
plugin_loader = None
claude_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global workspace_manager, meta_agent, redis_client, pr_service, agent_executor, file_manager, plugin_loader, claude_client
    
    logger.info("Starting OrbitSpace FastAPI backend...")
    
    try:
        # Initialize Redis client
        redis_client = get_redis_client()
        await redis_client.connect()
        logger.info("Redis client connected")
        
        # Initialize workspace manager
        workspace_manager = WorkspaceManager()
        logger.info("Workspace manager initialized")
        
        # Initialize file manager
        file_manager = FileManager()
        logger.info("File manager initialized")
        
        # Initialize plugin loader
        plugin_loader = PluginLoader()
        logger.info("Plugin loader initialized")
        
        # Initialize Claude client
        claude_client = ClaudeClient()
        logger.info("Claude client initialized")
        
        # Initialize agent executor
        agent_executor = AgentExecutor(
            plugin_loader=plugin_loader,
            claude_client=claude_client,
            redis_client=redis_client,
            file_manager=file_manager
        )
        logger.info("Agent executor initialized")
        
        # Initialize pull request service
        pr_service = PullRequestService()
        logger.info("Pull request service initialized")
        
        # Initialize meta agent
        meta_agent = MetaAgent(
            agent_executor=agent_executor,
            redis_client=redis_client,
            workspace_manager=workspace_manager,
            file_manager=file_manager,
            pr_service=pr_service
        )
        logger.info("Meta agent initialized")
        
        # Set dependencies for routes
        set_dependencies(
            ws_manager=workspace_manager,
            m_agent=meta_agent,
            r_client=redis_client,
            pr_svc=pr_service,
            db_cli=None  # We'll use Prisma from Next.js for now
        )
        
        logger.info("OrbitSpace backend started successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start backend: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down OrbitSpace backend...")
        if redis_client:
            await redis_client.disconnect()
        logger.info("OrbitSpace backend shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="OrbitSpace API",
    description="AI-powered codebase analysis and development automation platform",
    version="1.0.0",
    lifespan=lifespan
)

# Security
security = HTTPBearer()

# Validate required environment variables
required_env_vars = ["FASTAPI_SECRET_KEY", "DATABASE_URL", "REDIS_URL"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {missing_vars}")
    raise ValueError(f"Missing required environment variables: {missing_vars}")

# Configure CORS
cors_origins = os.getenv("FASTAPI_CORS_ORIGINS", "http://localhost:3000,https://orbitspace.org").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")
app.include_router(debug_router.router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint with API information"""
    return templates.TemplateResponse("index.html", {"request": request})

# Health check endpoint
@app.get("/health")
async def health():
    """Simple health check"""
    return {"status": "healthy", "service": "orbitspace-api"}

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found", "path": str(request.url.path)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("ENVIRONMENT", "development") == "development"
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )