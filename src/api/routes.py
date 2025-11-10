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


class CreatePRRequest(BaseModel):
    project_id: str
    repository_url: str
    feature_branch: str
    implementation_summary: str


class CreatePRResponse(BaseModel):
    pr_number: int
    pr_url: str
    title: str
    draft: bool
    labels: List[str]


class PRStatusResponse(BaseModel):
    pr_number: int
    title: str
    state: str
    draft: bool
    mergeable: Optional[bool]
    html_url: str
    created_at: str


class RetryPRRequest(BaseModel):
    project_id: str


# Global instances (injected by main.py)
workspace_manager = None
meta_agent = None
redis_client = None
pr_service = None
db_client = None


def set_dependencies(ws_manager, m_agent, r_client, pr_svc=None, db_cli=None):
    """Set global dependencies from main.py"""
    global workspace_manager, meta_agent, redis_client, pr_service, db_client
    workspace_manager = ws_manager
    meta_agent = m_agent
    redis_client = r_client
    pr_service = pr_svc
    db_client = db_cli


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


@router.post("/pull-requests/create", response_model=CreatePRResponse)
async def create_pull_request(request: CreatePRRequest):
    """
    Create pull request for project implementation
    - Analyzes git changes
    - Generates appropriate PR template
    - Creates PR with labels and metadata
    """
    try:
        if not pr_service:
            raise HTTPException(status_code=503, detail="Pull request service not available")
        
        logger.info(f"Creating pull request for project {request.project_id}")
        
        # Get workspace path
        workspace_info = await workspace_manager.get_workspace_info(request.project_id)
        workspace_path = workspace_info['workspace_path']
        repo_name = request.repository_url.split('/')[-1].replace('.git', '')
        repo_path = f"{workspace_path}/{repo_name}"
        
        # Get file changes from git
        file_changes = await pr_service.get_file_changes_from_git(repo_path)
        
        if not file_changes:
            raise HTTPException(status_code=400, detail="No changes found to create pull request")
        
        # Create pull request with template
        result = await pr_service.create_pull_request_with_template(
            project_id=request.project_id,
            repository_url=request.repository_url,
            feature_branch=request.feature_branch,
            implementation_summary=request.implementation_summary,
            file_changes=file_changes,
            db_client=db_client
        )
        
        return CreatePRResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create pull request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pull-requests/{owner}/{repo}/{pr_number}/status", response_model=PRStatusResponse)
async def get_pr_status(owner: str, repo: str, pr_number: int):
    """Get pull request status from GitHub"""
    try:
        if not pr_service:
            raise HTTPException(status_code=503, detail="Pull request service not available")
        
        status = await pr_service.get_pr_status(owner, repo, pr_number)
        return PRStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Failed to get PR status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/pull-requests")
async def get_project_pull_requests(project_id: str):
    """Get all pull requests for a project"""
    try:
        if not pr_service or not db_client:
            raise HTTPException(status_code=503, detail="Pull request service not available")
        
        prs = await pr_service.get_project_pull_requests(db_client, project_id)
        return {"pull_requests": prs}
        
    except Exception as e:
        logger.error(f"Failed to get project pull requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pull-requests/retry")
async def retry_pr_creation(request: RetryPRRequest):
    """Retry pull request creation for a project"""
    try:
        if not meta_agent:
            raise HTTPException(status_code=503, detail="Meta agent not available")
        
        result = await meta_agent.retry_pr_creation(request.project_id)
        
        if result["success"]:
            return {"success": True, "message": f"PR creation retry initiated (attempt {result['retry_count']})"}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry PR creation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pull-requests/{owner}/{repo}/{pr_number}/sync")
async def sync_pr_status(owner: str, repo: str, pr_number: int):
    """Sync pull request status between GitHub and database"""
    try:
        if not pr_service or not db_client:
            raise HTTPException(status_code=503, detail="Pull request service not available")
        
        repository_url = f"https://github.com/{owner}/{repo}"
        result = await pr_service.sync_pr_status_with_github(db_client, repository_url, pr_number)
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to sync PR status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Additional Pull Request Management Endpoints

@router.get("/projects/{project_id}/pull-requests")
async def get_project_pull_requests(project_id: str):
    """Get all pull requests for a project with current status"""
    try:
        if not pr_service or not db_client:
            raise HTTPException(status_code=503, detail="Pull request service not available")
        
        from ..github.pr_automation import PRAutomationService
        pr_automation = PRAutomationService(pr_service, db_client)
        
        prs = await pr_automation.get_pr_status_for_project(project_id)
        
        return {
            "project_id": project_id,
            "pull_requests": prs,
            "total_count": len(prs)
        }
        
    except Exception as e:
        logger.error(f"Failed to get project pull requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/pull-requests/create")
async def create_project_pull_requests(project_id: str, background_tasks: BackgroundTasks):
    """Manually trigger PR creation for a project"""
    try:
        if not pr_service or not db_client:
            raise HTTPException(status_code=503, detail="Pull request service not available")
        
        # Get project data
        project_data = await db_client.project.findUnique({
            'where': {'id': project_id}
        })
        
        if not project_data:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get workspace info
        workspace_info = await workspace_manager.get_workspace_info(project_id)
        if not workspace_info.get('exists'):
            raise HTTPException(status_code=400, detail="Project workspace not found")
        
        from ..github.pr_automation import PRAutomationService
        pr_automation = PRAutomationService(pr_service, db_client)
        
        # Create PRs in background
        background_tasks.add_task(
            pr_automation.create_prs_for_project,
            project_id,
            workspace_info['workspace_path'],
            project_data.get('description', 'Manual PR creation'),
            None
        )
        
        return {
            "message": "PR creation initiated",
            "project_id": project_id,
            "status": "in_progress"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create project pull requests: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/github/labels/definitions")
async def get_label_definitions():
    """Get OrbitSpace label definitions for repository setup"""
    try:
        from ..github.pr_labeling import PRLabelingService
        labeling_service = PRLabelingService()
        
        label_definitions = labeling_service.create_label_definitions()
        
        return {
            "labels": label_definitions,
            "total_count": len(label_definitions),
            "categories": [
                "type", "scope", "priority", "size", "status", "automation"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get label definitions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
