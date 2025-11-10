"""
Orbitspace OrbitSpace - FastAPI Backend
Main application entry point for agent orchestration and tool execution
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import os

from src.orchestrator.workspace import WorkspaceManager
from src.orchestrator.agent_executor import AgentExecutor
from src.orchestrator.claude_client import ClaudeClient
from src.orchestrator.redis_client import RedisClient, get_redis_client
from src.orchestrator.meta_agent import MetaAgent
from src.plugins.loader import PluginLoader
from src.files.manager import FileManager
from src.api import routes
from src.api.routers import codegen_router
from src.services.template_manager import template_manager
from src.config import settings
from src.utils.logger import setup_logger, get_logger

# Setup root logger
setup_logger("OrbitSpace", level=os.getenv("LOG_LEVEL", "INFO"), json_format=os.getenv("LOG_FORMAT") == "json")
logger = get_logger(__name__)

# Global instances
redis_client: Optional[RedisClient] = None
plugin_loader: Optional[PluginLoader] = None
claude_client: Optional[ClaudeClient] = None
agent_executor: Optional[AgentExecutor] = None
workspace_manager: Optional[WorkspaceManager] = None
file_manager: Optional[FileManager] = None
meta_agent: Optional[MetaAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events with comprehensive error handling"""
    global redis_client, plugin_loader, claude_client, agent_executor, workspace_manager, file_manager, meta_agent

    try:
        # Startup
        logger.info("🚀 Initializing Orbitspace OrbitSpace...")

        # Initialize Redis
        try:
            redis_client = get_redis_client()
            await redis_client.connect()
            logger.info("✓ Redis connected")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise

        # Initialize plugin loader
        try:
            plugin_loader = PluginLoader()
            plugin_loader.load_all_plugins()
            agent_count = len(plugin_loader.list_agents())
            logger.info(f"✓ Loaded {agent_count} agents")
        except Exception as e:
            logger.error(f"❌ Failed to load plugins: {e}")
            raise

        # Initialize Claude client
        try:
            claude_client = ClaudeClient()
            logger.info("✓ Claude client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Claude client: {e}")
            raise

        # Initialize file manager
        try:
            file_manager = FileManager()
            logger.info("✓ File manager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize file manager: {e}")
            raise

        # Initialize workspace manager
        try:
            workspace_manager = WorkspaceManager()
            logger.info("✓ Workspace manager initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize workspace manager: {e}")
            raise

        # Initialize agent executor
        try:
            agent_executor = AgentExecutor(
                plugin_loader=plugin_loader,
                claude_client=claude_client,
                redis_client=redis_client,
                file_manager=file_manager
            )
            logger.info("✓ Agent executor initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize agent executor: {e}")
            raise

        # Initialize meta-agent coordinator
        try:
            meta_agent = MetaAgent(
                agent_executor=agent_executor,
                redis_client=redis_client,
                workspace_manager=workspace_manager,
                file_manager=file_manager
            )
            logger.info("✓ Meta-agent coordinator initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize meta-agent: {e}")
            raise

        # Inject dependencies into routes
        try:
            routes.set_dependencies(workspace_manager, meta_agent, redis_client)
            logger.info("✓ Routes configured")
        except Exception as e:
            logger.error(f"❌ Failed to configure routes: {e}")
            raise

        logger.info("🎉 Orbitspace OrbitSpace is ready!")

        yield

    except Exception as e:
        logger.critical(f"💥 Fatal error during startup: {e}")
        raise

    finally:
        # Shutdown
        logger.info("Shutting down...")
        try:
            if redis_client:
                await redis_client.disconnect()
                logger.info("✓ Redis disconnected")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Initialize template manager with built-in templates
template_manager.initialize_templates()

app = FastAPI(
    title="Orbitspace OrbitSpace API",
    description="AI coding agent orchestration platform with Claude integration",
    version="0.1.0",
    lifespan=lifespan
)

# Add production middleware
from src.middleware import (
    rate_limit_middleware,
    metrics_middleware,
    error_tracking_middleware,
    get_metrics as get_app_metrics,
    get_prometheus_metrics,
)

# Error tracking (first)
app.middleware("http")(error_tracking_middleware)

# Metrics collection
app.middleware("http")(metrics_middleware)

# Rate limiting
app.middleware("http")(rate_limit_middleware)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "Content-Length", "Authorization"],
    allow_credentials=True,
)

# Include API routes
app.include_router(routes.router)
app.include_router(codegen_router.router)

# Include analysis routes
from src.api.analysis_routes import router as analysis_router
app.include_router(analysis_router)

# Pydantic models (kept for backward compatibility)
class InitializeProjectRequest(BaseModel):
    project_id: str
    user_id: str
    feature_request: str
    repository_urls: List[str]

class InitializeProjectResponse(BaseModel):
    workspace_path: str
    repositories: List[Dict[str, str]]

class StartAgentRequest(BaseModel):
    project_id: str
    feature_request: Optional[str] = None

class StartAgentResponse(BaseModel):
    task_id: str
    status: str
    overwatcher_task_ids: Optional[List[str]] = None


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_status = "connected" if redis_client and await redis_client.ping() else "disconnected"

    return {
        "status": "healthy",
        "redis": redis_status,
        "filesystem": "ok",
        "agents_loaded": len(plugin_loader.list_agents()) if plugin_loader else 0
    }


# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """System metrics"""
    # Get queue lengths from Redis
    pending_count = 0
    active_count = 0

    if redis_client:
        try:
            pending_count = await redis_client.get_queue_length("tasks:pending")
            active_count = await redis_client.get_queue_length("tasks:active")
        except:
            pass
    
    # Get application metrics
    app_metrics = await get_app_metrics()

    return {
        "active_agents": active_count,
        "queued_tasks": pending_count,
        "workspace_count": 0,
        "application": app_metrics,
    }


# Prometheus metrics endpoint
@app.get("/metrics/prometheus")
async def prometheus_metrics():
    """Prometheus-formatted metrics"""
    return await get_prometheus_metrics()


# Project management endpoints
@app.post("/projects/initialize", response_model=InitializeProjectResponse)
async def initialize_project(request: InitializeProjectRequest):
    """Initialize workspace for project"""
    try:
        result = await workspace_manager.initialize_workspace(
            project_id=request.project_id,
            user_id=request.user_id,
            feature_request=request.feature_request,
            repository_urls=request.repository_urls
        )

        return InitializeProjectResponse(
            workspace_path=result["workspace_path"],
            repositories=result["repositories"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/projects/{project_id}/workspace")
async def cleanup_workspace(project_id: str):
    """Clean up workspace"""
    try:
        success = await workspace_manager.cleanup_workspace(project_id)

        return {
            "success": success,
            "project_id": project_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Agent execution endpoints
@app.post("/agents/research/start", response_model=StartAgentResponse)
async def start_research_agent(request: StartAgentRequest):
    """Start research agent"""
    try:
        task_id = await agent_executor.execute_agent(
            agent_name="research-agent",
            project_id=request.project_id,
            phase="research",
            inputs={
                "feature_request": request.feature_request
            }
        )

        return StartAgentResponse(
            task_id=task_id,
            status="started"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/planning/start", response_model=StartAgentResponse)
async def start_planning_agent(request: StartAgentRequest):
    """Start planning agent"""
    try:
        task_id = await agent_executor.execute_agent(
            agent_name="planning-agent",
            project_id=request.project_id,
            phase="planning",
            inputs={
                "feature_request": request.feature_request
            }
        )

        return StartAgentResponse(
            task_id=task_id,
            status="started"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/implementation/start", response_model=StartAgentResponse)
async def start_implementation_agent(request: StartAgentRequest):
    """Start implementation agent with overwatchers"""
    try:
        # Start main implementation agent
        task_id = await agent_executor.execute_agent(
            agent_name="implementation-agent",
            project_id=request.project_id,
            phase="implementation",
            inputs={
                "feature_request": request.feature_request
            }
        )

        # TODO: Start overwatcher agents in parallel
        # overwatcher_task_ids = []

        return StartAgentResponse(
            task_id=task_id,
            status="started",
            overwatcher_task_ids=[]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/{task_id}/status")
async def get_agent_status(task_id: str):
    """Get agent execution status"""
    try:
        status = await redis_client.get_task_status(task_id)

        if not status:
            raise HTTPException(status_code=404, detail="Task not found")

        return status

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/{task_id}/pause")
async def pause_agent(task_id: str):
    """Pause running agent"""
    # TODO: Implement agent pause
    raise HTTPException(status_code=501, detail="Not implemented yet")


@app.post("/agents/{task_id}/resume")
async def resume_agent(task_id: str):
    """Resume paused agent"""
    # TODO: Implement agent resume
    raise HTTPException(status_code=501, detail="Not implemented yet")


@app.post("/agents/{task_id}/cancel")
async def cancel_agent(task_id: str):
    """Cancel running agent"""
    # TODO: Implement agent cancellation
    raise HTTPException(status_code=501, detail="Not implemented yet")


# Plugin management endpoints
@app.get("/plugins")
async def list_plugins():
    """List available plugins"""
    try:
        agents = plugin_loader.list_agents()

        plugins = []
        for agent_name in agents:
            agent_def = plugin_loader.get_agent(agent_name)
            plugins.append({
                "name": agent_def.name,
                "type": "agent",
                "description": agent_def.description,
                "model": agent_def.model,
                "tools": agent_def.tools
            })

        return {"plugins": plugins}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/plugins/{plugin_name}")
async def get_plugin(plugin_name: str):
    """Get plugin definition"""
    try:
        agent_def = plugin_loader.get_agent(plugin_name)

        if not agent_def:
            raise HTTPException(status_code=404, detail="Plugin not found")

        return {
            "name": agent_def.name,
            "description": agent_def.description,
            "model": agent_def.model,
            "tools": agent_def.tools,
            "triggers": agent_def.triggers,
            "instructions": agent_def.instructions
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
