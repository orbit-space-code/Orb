"""
FastAPI Routes
All endpoints for agent orchestration and workspace management
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class InitializeProjectRequest(BaseModel):
    project_id: str
    user_id: str
    feature_request: str
    repository_urls: List[str]


class InitializeProjectResponse(BaseModel):
    workspace_path: str
    repositories: List[Dict[str, str]]


class StartPhaseRequest(BaseModel):
    project_id: str
    user_id: str
    feature_request: Optional[str] = None


class StartPhaseResponse(BaseModel):
    task_id: str
    status: str
    phase: str


class HealthResponse(BaseModel):
    status: str
    redis: str
    filesystem: str


# Global instances (injected by main.py)
workspace_manager = None
meta_agent = None
redis_client = None


def set_dependencies(ws_manager, m_agent, r_client):
    """Set global dependencies from main.py"""
    global workspace_manager, meta_agent, redis_client
    workspace_manager = ws_manager
    meta_agent = m_agent
    redis_client = r_client


# Routes
@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis
        redis_status = "connected" if await redis_client.ping() else "disconnected"

        # Check filesystem
        import os

        fs_status = "ok" if os.path.exists("/workspaces") else "error"

        return {
            "status": "healthy" if redis_status == "connected" else "degraded",
            "redis": redis_status,
            "filesystem": fs_status,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "redis": "error",
            "filesystem": "error",
        }


@router.post("/projects/initialize", response_model=InitializeProjectResponse)
async def initialize_project(request: InitializeProjectRequest):
    """
    Initialize workspace for a new project
    - Creates workspace directory
    - Clones repositories
    - Creates feature branches
    """
    try:
        logger.info(f"Initializing project {request.project_id}")

        result = await workspace_manager.initialize_workspace(
            project_id=request.project_id,
            user_id=request.user_id,
            feature_request=request.feature_request,
            repository_urls=request.repository_urls,
        )

        return InitializeProjectResponse(**result)

    except Exception as e:
        logger.error(f"Failed to initialize project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}/workspace")
async def cleanup_workspace(project_id: str):
    """
    Cleanup workspace for a project
    - Deletes workspace directory
    - Removes from Redis
    """
    try:
        await workspace_manager.cleanup_workspace(project_id)
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to cleanup workspace: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/research/start", response_model=StartPhaseResponse)
async def start_research(request: StartPhaseRequest, background_tasks: BackgroundTasks):
    """
    Start research phase
    - Loads research-agent plugin
    - Analyzes codebase
    - Creates research.md
    """
    try:
        logger.info(f"Starting research phase for project {request.project_id}")

        if not request.feature_request:
            raise HTTPException(
                status_code=400, detail="feature_request is required for research phase"
            )

        result = await meta_agent.start_research_phase(
            project_id=request.project_id,
            user_id=request.user_id,
            feature_request=request.feature_request,
        )

        return StartPhaseResponse(**result)

    except Exception as e:
        logger.error(f"Failed to start research: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/planning/start", response_model=StartPhaseResponse)
async def start_planning(request: StartPhaseRequest):
    """
    Start planning phase
    - Loads planning-agent plugin
    - Asks clarifying questions
    - Creates planning.md
    """
    try:
        logger.info(f"Starting planning phase for project {request.project_id}")

        result = await meta_agent.start_planning_phase(
            project_id=request.project_id,
            user_id=request.user_id,
        )

        return StartPhaseResponse(**result)

    except Exception as e:
        logger.error(f"Failed to start planning: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/implementation/start", response_model=StartPhaseResponse)
async def start_implementation(request: StartPhaseRequest):
    """
    Start implementation phase
    - Loads implementation-agent plugin
    - Spawns overwatcher agents
    - Executes code changes
    - Creates commits
    """
    try:
        logger.info(f"Starting implementation phase for project {request.project_id}")

        result = await meta_agent.start_implementation_phase(
            project_id=request.project_id,
            user_id=request.user_id,
        )

        return StartPhaseResponse(**result)

    except Exception as e:
        logger.error(f"Failed to start implementation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{task_id}/pause")
async def pause_agent(task_id: str):
    """Pause running agent"""
    try:
        # Get task from Redis
        task_data = await redis_client.get(f"task:{task_id}")
        if not task_data:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update status
        task_data["status"] = "paused"
        await redis_client.set(f"task:{task_id}", task_data)

        # Publish pause event
        project_id = task_data.get("project_id")
        await redis_client.publish(
            f"project:{project_id}:events",
            {
                "type": "agent_paused",
                "task_id": task_id,
                "agent": task_data.get("agent_name"),
            },
        )

        return {"success": True, "status": "paused"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{task_id}/resume")
async def resume_agent(task_id: str):
    """Resume paused agent"""
    try:
        # Get task from Redis
        task_data = await redis_client.get(f"task:{task_id}")
        if not task_data:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update status
        task_data["status"] = "active"
        await redis_client.set(f"task:{task_id}", task_data)

        # Publish resume event
        project_id = task_data.get("project_id")
        await redis_client.publish(
            f"project:{project_id}:events",
            {
                "type": "agent_resumed",
                "task_id": task_id,
                "agent": task_data.get("agent_name"),
            },
        )

        return {"success": True, "status": "resumed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{task_id}/cancel")
async def cancel_agent(task_id: str):
    """Cancel running agent"""
    try:
        # Get task from Redis
        task_data = await redis_client.get(f"task:{task_id}")
        if not task_data:
            raise HTTPException(status_code=404, detail="Task not found")

        # Update status
        task_data["status"] = "cancelled"
        await redis_client.set(f"task:{task_id}", task_data)

        # Publish cancel event
        project_id = task_data.get("project_id")
        await redis_client.publish(
            f"project:{project_id}:events",
            {
                "type": "agent_cancelled",
                "task_id": task_id,
                "agent": task_data.get("agent_name"),
            },
        )

        return {"success": True, "status": "cancelled"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))
