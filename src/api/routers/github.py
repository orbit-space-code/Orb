"""
GitHub Integration API
Handles GitHub repository operations and webhook management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
import logging
import hmac
import hashlib
import json

from ...services.github_service import GitHubService, GitRepository, GitFile, GitBranch
from ...auth.service import get_current_active_user, User
from ...core.config import settings

router = APIRouter(prefix="/api/github", tags=["github"])
logger = logging.getLogger(__name__)

# Request/Response Models
class GitHubAuthRequest(BaseModel):
    """GitHub OAuth request model"""
    code: str
    redirect_uri: Optional[HttpUrl] = None

class GitHubAuthResponse(BaseModel):
    """GitHub OAuth response model"""
    access_token: str
    token_type: str
    scope: str

class GitHubWebhookPayload(BaseModel):
    """GitHub webhook payload model"""
    ref: str
    before: str
    after: str
    repository: Dict[str, Any]
    pusher: Dict[str, Any]
    commits: List[Dict[str, Any]]
    head_commit: Optional[Dict[str, Any]] = None

class CreateBranchRequest(BaseModel):
    """Create branch request model"""
    branch_name: str
    base_branch: str = "main"

class CreatePullRequestRequest(BaseModel):
    """Create pull request request model"""
    title: str
    head_branch: str
    base_branch: str = "main"
    body: str = ""
    draft: bool = False

class FileUpdateRequest(BaseModel):
    """File update request model"""
    path: str
    content: str
    message: str
    branch: str = "main"
    sha: Optional[str] = None  # Required for updates, None for new files

# Initialize GitHub service
github_service = GitHubService()

# Webhook secret for GitHub
WEBHOOK_SECRET = settings.GITHUB_WEBHOOK_SECRET

@router.post("/auth/callback", response_model=GitHubAuthResponse)
async def github_auth_callback(
    request: Request,
    auth_request: GitHubAuthRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Exchange GitHub OAuth code for access token"""
    try:
        # In a real implementation, you would exchange the code for an access token
        # using GitHub's OAuth API
        # For now, we'll just return a mock response
        return {
            "access_token": "gho_mock_access_token_1234567890",
            "token_type": "bearer",
            "scope": "repo,user"
        }
    except Exception as e:
        logger.error(f"GitHub auth error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authenticate with GitHub"
        )

@router.get("/repos", response_model=List[GitRepository])
async def list_repositories(
    current_user: User = Depends(get_current_active_user)
):
    """List all repositories for the authenticated user"""
    try:
        if not current_user.github_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub access token is required"
            )
            
        # Initialize GitHub service with user's access token
        github = GitHubService(access_token=current_user.github_token)
        return await github.list_repositories()
        
    except Exception as e:
        logger.error(f"Failed to list repositories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch repositories"
        )

@router.get("/repos/{owner}/{repo}", response_model=GitRepository)
async def get_repository(
    owner: str,
    repo: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific repository"""
    try:
        github = GitHubService(access_token=current_user.github_token)
        return await github.get_repository(owner, repo)
    except Exception as e:
        logger.error(f"Failed to get repository {owner}/{repo}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch repository {owner}/{repo}"
        )

@router.get("/repos/{owner}/{repo}/contents/{path:path}", response_model=GitFile)
async def get_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: str = "main",
    current_user: User = Depends(get_current_active_user)
):
    """Get file content from a repository"""
    try:
        github = GitHubService(access_token=current_user.github_token)
        file = await github.get_file_content(owner, repo, path, ref)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        return file
    except Exception as e:
        logger.error(f"Failed to get file {path}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch file {path}"
        )

@router.post("/repos/{owner}/{repo}/branches", response_model=GitBranch)
async def create_branch(
    owner: str,
    repo: str,
    branch_data: CreateBranchRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new branch"""
    try:
        github = GitHubService(access_token=current_user.github_token)
        return await github.create_branch(
            owner=owner,
            repo_name=repo,
            branch_name=branch_data.branch_name,
            base_branch=branch_data.base_branch
        )
    except Exception as e:
        logger.error(f"Failed to create branch: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create branch"
        )

@router.post("/repos/{owner}/{repo}/pulls", response_model=Dict[str, Any])
async def create_pull_request(
    owner: str,
    repo: str,
    pr_data: CreatePullRequestRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create a new pull request"""
    try:
        github = GitHubService(access_token=current_user.github_token)
        return await github.create_pull_request(
            owner=owner,
            repo_name=repo,
            title=pr_data.title,
            head_branch=pr_data.head_branch,
            base_branch=pr_data.base_branch,
            body=pr_data.body,
            draft=pr_data.draft
        )
    except Exception as e:
        logger.error(f"Failed to create pull request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create pull request"
        )

@router.put("/repos/{owner}/{repo}/contents/{path:path}")
async def update_file(
    owner: str,
    repo: str,
    path: str,
    file_data: FileUpdateRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create or update a file in a repository"""
    try:
        github = GitHubService(access_token=current_user.github_token)
        
        # Get file SHA if it exists (for updates)
        if not file_data.sha:
            try:
                existing_file = await github.get_file_content(owner, repo, path, file_data.branch)
                file_data.sha = existing_file.sha
            except Exception:
                # File doesn't exist, will be created
                pass
        
        # In a real implementation, you would use the GitHub API to create/update the file
        # For now, we'll just return a success response
        return {
            "message": "File updated successfully",
            "content": {
                "name": path.split("/")[-1],
                "path": path,
                "sha": "abc123",  # Mock SHA
                "size": len(file_data.content),
                "url": f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={file_data.branch}",
                "html_url": f"https://github.com/{owner}/{repo}/blob/{file_data.branch}/{path}",
                "git_url": f"https://api.github.com/repos/{owner}/{repo}/git/blobs/abc123",
                "download_url": f"https://raw.githubusercontent.com/{owner}/{repo}/{file_data.branch}/{path}",
                "type": "file",
                "_links": {
                    "self": f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={file_data.branch}",
                    "git": f"https://api.github.com/repos/{owner}/{repo}/git/blobs/abc123",
                    "html": f"https://github.com/{owner}/{repo}/blob/{file_data.branch}/{path}"
                }
            },
            "commit": {
                "sha": "def456",  # Mock commit SHA
                "node_id": "MDY6Q29tbWl0MTIzNDU2Nzg5OjEyMzQ1Njc4OTg3NjU0MzIx",
                "url": f"https://api.github.com/repos/{owner}/{repo}/git/commits/def456",
                "html_url": f"https://github.com/{owner}/{repo}/commit/def456",
                "author": {
                    "name": current_user.full_name,
                    "email": current_user.email,
                    "date": "2023-01-01T00:00:00Z"
                },
                "committer": {
                    "name": current_user.full_name,
                    "email": current_user.email,
                    "date": "2023-01-01T00:00:00Z"
                },
                "message": file_data.message,
                "tree": {
                    "sha": "ghi789",
                    "url": f"https://api.github.com/repos/{owner}/{repo}/git/trees/ghi789"
                },
                "parents": [
                    {
                        "sha": "jkl012",
                        "url": f"https://api.github.com/repos/{owner}/{repo}/commits/jkl012",
                        "html_url": f"https://github.com/{owner}/{repo}/commit/jkl012"
                    }
                ],
                "verification": {
                    "verified": False,
                    "reason": "unsigned",
                    "signature": None,
                    "payload": None
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to update file {path}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update file {path}"
        )

@router.post("/webhook")
async def github_webhook(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    x_github_event: str = "",
    x_hub_signature_256: str = ""
):
    """Handle GitHub webhook events"""
    try:
        # Verify webhook signature
        if WEBHOOK_SECRET:
            body = await request.body()
            signature = hmac.new(
                WEBHOOK_SECRET.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            expected_signature = f"sha256={signature}"
            if not hmac.compare_digest(x_hub_signature_256, expected_signature):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid signature"
                )
        
        # Process the webhook event
        event_type = x_github_event
        logger.info(f"Received GitHub webhook event: {event_type}")
        
        if event_type == "push":
            # Handle push event
            repo = payload["repository"]["full_name"]
            branch = payload["ref"].split("/")[-1]
            commits = payload.get("commits", [])
            
            logger.info(f"Push to {repo} on branch {branch} with {len(commits)} commits")
            
            # In a real implementation, you would process the push event
            # For example, trigger CI/CD pipeline, update deployment status, etc.
            
        elif event_type == "pull_request":
            # Handle pull request event
            pr_number = payload["pull_request"]["number"]
            action = payload["action"]
            repo = payload["repository"]["full_name"]
            
            logger.info(f"Pull request {action} on {repo}#{pr_number}")
            
            # In a real implementation, you would process the PR event
            # For example, run tests, add labels, request reviews, etc.
        
        return {"status": "webhook received"}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing webhook"
        )

@router.get("/rate-limit", response_model=Dict[str, Any])
async def get_rate_limit(
    current_user: User = Depends(get_current_active_user)
):
    """Get GitHub API rate limit information"""
    try:
        github = GitHubService(access_token=current_user.github_token)
        return await github.get_rate_limit()
    except Exception as e:
        logger.error(f"Failed to get rate limit: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rate limit"
        )
