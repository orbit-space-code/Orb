"""
GitHub Integration Service
Handles interactions with GitHub API for repository operations
"""
import os
from typing import Dict, List, Optional, Any, Union, Tuple, TypeVar, Type, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
import base64
import json
import logging
import asyncio
import time
from functools import wraps
from pathlib import Path
from typing_extensions import TypedDict, Literal

from github import Github, GithubIntegration, Auth
from github.Repository import Repository
from github.Branch import Branch
from github.PullRequest import PullRequest
from github.GithubException import (
    GithubException, 
    UnknownObjectException, 
    BadCredentialsException, 
    RateLimitExceededException,
    GithubIntegrationException
)
from github.File import File as GithubFile

# Type variables for generic function returns
T = TypeVar('T')
P = TypeVar('P')

# Custom type definitions
class RateLimitInfo(TypedDict):
    limit: int
    remaining: int
    reset_timestamp: int

class FileContent(TypedDict):
    content: str
    encoding: Literal['base64', 'utf-8']
    size: int
    sha: str

logger = logging.getLogger(__name__)

# Custom Exceptions
class GitHubServiceError(Exception):
    """Base exception for GitHub service errors"""
    def __init__(self, message: str = "GitHub service error", details: Optional[Dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(message)
    
    def __str__(self) -> str:
        details = ", ".join(f"{k}={v}" for k, v in self.details.items())
        return f"{super().__str__()}. Details: {details}" if details else super().__str__()

class RepositoryNotFoundError(GitHubServiceError):
    """Raised when a repository is not found"""
    def __init__(self, owner: str, repo_name: str):
        super().__init__(
            f"Repository '{owner}/{repo_name}' not found",
            {"owner": owner, "repo": repo_name}
        )

class UnauthorizedError(GitHubServiceError):
    """Raised when authentication fails"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, {"error_type": "authentication"})

def handle_github_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to handle common GitHub API errors"""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except RateLimitExceededException as e:
            reset_time = datetime.fromtimestamp(int(e.headers.get('X-RateLimit-Reset', 0)))
            raise RateLimitError(reset_time) from e
        except BadCredentialsException as e:
            raise UnauthorizedError("Invalid GitHub credentials") from e
        except UnknownObjectException as e:
            if "Not Found" in str(e):
                raise RepositoryNotFoundError("", "") from e
            raise GitHubServiceError(f"GitHub resource not found: {str(e)}") from e
        except GithubException as e:
            raise GitHubServiceError(f"GitHub API error: {str(e)}") from e
        except Exception as e:
            raise GitHubServiceError(f"Unexpected error: {str(e)}") from e
    return wrapper

class RateLimitError(GitHubServiceError):
    """Raised when GitHub API rate limit is exceeded"""
    def __init__(self, reset_time: Optional[datetime] = None):
        self.reset_time = reset_time
        details = {"reset_time": reset_time.isoformat() if reset_time else None}
        super().__init__("GitHub API rate limit exceeded", details)
    
    def time_until_reset(self) -> float:
        """Return seconds until rate limit resets"""
        if not self.reset_time:
            return 0
        return (self.reset_time - datetime.now()).total_seconds()

@dataclass
class GitUser:
    """Git user information"""
    login: str
    name: str
    email: str
    avatar_url: str

@dataclass
class GitRepository:
    """Repository information"""
    id: str
    name: str
    full_name: str
    private: bool
    html_url: str
    description: str
    owner: GitUser
    created_at: datetime
    updated_at: datetime
    default_branch: str
    permissions: Dict[str, bool] = field(default_factory=dict)

@dataclass
class GitBranch:
    """Branch information"""
    name: str
    protected: bool
    commit_sha: str
    commit_message: str
    commit_author: Optional[GitUser] = None

@dataclass
class GitFile:
    """File information"""
    path: str
    content: str
    sha: str
    size: int
    is_binary: bool = False

@dataclass
class GitCommit:
    """Commit information"""
    sha: str
    message: str
    author: GitUser
    date: datetime
    url: str
    changed_files: List[Dict[str, Any]] = field(default_factory=list)

class GitHubService:
    """Service for interacting with GitHub API with comprehensive error handling"""
    
    def __init__(self, access_token: Optional[str] = None) -> None:
        """Initialize GitHub client with authentication.
        
        Args:
            access_token: Personal Access Token for GitHub API authentication.
                         If not provided, will try to get from GITHUB_ACCESS_TOKEN env var.
        
        Raises:
            UnauthorizedError: If no valid authentication method is found.
            GitHubServiceError: If there's an error initializing the client.
        """
        try:
            self.access_token = access_token or os.getenv("GITHUB_ACCESS_TOKEN")
            self.app_id = os.getenv("GITHUB_APP_ID")
            self.private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
            
            if not any([self.access_token, (self.app_id and self.private_key)]):
                raise UnauthorizedError(
                    "No authentication provided. Set GITHUB_ACCESS_TOKEN or GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY"
                )
                
            self.client = self._get_github_client()
            # Verify authentication works
            self.client.get_user().login
            
        except Exception as e:
            if not isinstance(e, (UnauthorizedError, GitHubServiceError)):
                raise GitHubServiceError(f"Failed to initialize GitHub client: {str(e)}") from e
            raise
    
    @handle_github_errors
    def _get_github_client(self) -> Github:
        """Get GitHub client instance with proper authentication.
        
        Returns:
            Github: Authenticated GitHub client instance.
            
        Raises:
            UnauthorizedError: If authentication fails.
            GitHubServiceError: For other client initialization errors.
        """
        try:
            if self.access_token:
                return Github(
                    login_or_token=self.access_token,
                    timeout=30,  # 30 seconds timeout
                    per_page=100,  # Max items per page
                    retry=3  # Number of retries for failed requests
                )
            elif self.app_id and self.private_key:
                auth = Auth.AppAuth(self.app_id, self.private_key)
                return Github(
                    auth=auth,
                    timeout=30,
                    per_page=100,
                    retry=3
                )
            else:
                # Unauthenticated client (limited rate limits)
                return Github()
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {str(e)}")
            raise GitHubServiceError("Failed to initialize GitHub client") from e
    
    async def get_authenticated_user(self) -> GitUser:
        """Get authenticated user information"""
        try:
            if not self.access_token:
                raise UnauthorizedError("GitHub access token is required")
                
            user = self.client.get_user()
            return GitUser(
                login=user.login,
                name=user.name or user.login,
                email=user.email or f"{user.login}@users.noreply.github.com",
                avatar_url=user.avatar_url
            )
        except BadCredentialsException as e:
            raise UnauthorizedError("Invalid GitHub credentials") from e
        except RateLimitExceededException as e:
            raise RateLimitError() from e
        except Exception as e:
            logger.error(f"Failed to get authenticated user: {str(e)}")
            raise GitHubServiceError("Failed to get user information") from e
    
    async def list_repositories(self) -> List[GitRepository]:
        """List all repositories for the authenticated user"""
        try:
            if not self.access_token:
                raise UnauthorizedError("GitHub access token is required")
                
            repos = []
            for repo in self.client.get_user().get_repos():
                try:
                    owner = GitUser(
                        login=repo.owner.login,
                        name=repo.owner.name or repo.owner.login,
                        email=repo.owner.email or f"{repo.owner.login}@users.noreply.github.com",
                        avatar_url=repo.owner.avatar_url
                    )
                    
                    repos.append(GitRepository(
                        id=str(repo.id),
                        name=repo.name,
                        full_name=repo.full_name,
                        private=repo.private,
                        html_url=repo.html_url,
                        description=repo.description or "",
                        owner=owner,
                        created_at=repo.created_at,
                        updated_at=repo.updated_at,
                        default_branch=repo.default_branch,
                        permissions={
                            "admin": repo.permissions.admin,
                            "push": repo.permissions.push,
                            "pull": repo.permissions.pull
                        }
                    ))
                except Exception as e:
                    logger.warning(f"Skipping repository {repo.full_name}: {str(e)}")
                    continue
            
            return repos
            
        except BadCredentialsException as e:
            raise UnauthorizedError("Invalid GitHub credentials") from e
        except RateLimitExceededException as e:
            raise RateLimitError() from e
        except Exception as e:
            logger.error(f"Failed to list repositories: {str(e)}")
            raise GitHubServiceError("Failed to list repositories") from e
    
    async def get_repository(self, owner: str, repo_name: str) -> GitRepository:
        """Get a specific repository"""
        try:
            repo = self.client.get_repo(f"{owner}/{repo_name}")
            
            owner_user = GitUser(
                login=repo.owner.login,
                name=repo.owner.name or repo.owner.login,
                email=repo.owner.email or f"{repo.owner.login}@users.noreply.github.com",
                avatar_url=repo.owner.avatar_url
            )
            
            return GitRepository(
                id=str(repo.id),
                name=repo.name,
                full_name=repo.full_name,
                private=repo.private,
                html_url=repo.html_url,
                description=repo.description or "",
                owner=owner_user,
                created_at=repo.created_at,
                updated_at=repo.updated_at,
                default_branch=repo.default_branch,
                permissions={
                    "admin": repo.permissions.admin if hasattr(repo, 'permissions') else False,
                    "push": repo.permissions.push if hasattr(repo, 'permissions') else False,
                    "pull": repo.permissions.pull if hasattr(repo, 'permissions') else True
                }
            )
            
        except UnknownObjectException as e:
            raise RepositoryNotFoundError(f"Repository {owner}/{repo_name} not found") from e
        except BadCredentialsException as e:
            raise UnauthorizedError("Invalid GitHub credentials") from e
        except RateLimitExceededException as e:
            raise RateLimitError() from e
        except Exception as e:
            logger.error(f"Failed to get repository {owner}/{repo_name}: {str(e)}")
            raise GitHubServiceError(f"Failed to get repository {owner}/{repo_name}") from e
    
    async def get_file_content(self, owner: str, repo_name: str, path: str, ref: str = "main") -> Optional[GitFile]:
        """Get file content from a repository"""
        try:
            repo = self.client.get_repo(f"{owner}/{repo_name}")
            file = repo.get_contents(path, ref=ref)
            
            if not file:
                return None
                
            # Handle binary files
            if file.encoding == "base64":
                try:
                    content = base64.b64decode(file.content).decode('utf-8')
                    is_binary = False
                except (UnicodeDecodeError, ValueError):
                    content = file.content
                    is_binary = True
            else:
                content = file.content
                is_binary = False
            
            return GitFile(
                path=file.path,
                content=content,
                sha=file.sha,
                size=file.size,
                is_binary=is_binary
            )
            
        except UnknownObjectException:
            return None
        except Exception as e:
            logger.error(f"Failed to get file {path} from {owner}/{repo_name}: {str(e)}")
            raise GitHubServiceError(f"Failed to get file {path}") from e
    
    async def create_branch(
        self, 
        owner: str, 
        repo_name: str, 
        branch_name: str, 
        base_branch: str = "main"
    ) -> GitBranch:
        """Create a new branch from base branch"""
        try:
            repo = self.client.get_repo(f"{owner}/{repo_name}")
            
            # Get the base branch reference
            base_ref = repo.get_git_ref(f"heads/{base_branch}")
            base_commit_sha = base_ref.object.sha
            
            # Create new branch
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=base_commit_sha
            )
            
            # Get the new branch details
            branch = repo.get_branch(branch_name)
            
            return GitBranch(
                name=branch.name,
                protected=branch.protected,
                commit_sha=branch.commit.sha,
                commit_message=branch.commit.commit.message,
                commit_author=GitUser(
                    login=branch.commit.author.login,
                    name=branch.commit.author.name or branch.commit.author.login,
                    email=branch.commit.author.email or f"{branch.commit.author.login}@users.noreply.github.com",
                    avatar_url=branch.commit.author.avatar_url
                ) if branch.commit.author else None
            )
            
        except Exception as e:
            logger.error(f"Failed to create branch {branch_name}: {str(e)}")
            raise GitHubServiceError(f"Failed to create branch {branch_name}") from e
    
    async def create_pull_request(
        self,
        owner: str,
        repo_name: str,
        title: str,
        head_branch: str,
        base_branch: str = "main",
        body: str = "",
        draft: bool = False
    ) -> Dict[str, Any]:
        """Create a pull request"""
        try:
            repo = self.client.get_repo(f"{owner}/{repo_name}")
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch,
                draft=draft
            )
            
            return {
                "id": pr.id,
                "number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "state": pr.state,
                "created_at": pr.created_at,
                "updated_at": pr.updated_at,
                "html_url": pr.html_url,
                "diff_url": pr.diff_url,
                "mergeable": pr.mergeable,
                "mergeable_state": pr.mergeable_state,
                "user": {
                    "login": pr.user.login,
                    "avatar_url": pr.user.avatar_url
                },
                "head": {
                    "ref": pr.head.ref,
                    "sha": pr.head.sha,
                    "repo": {
                        "full_name": pr.head.repo.full_name if pr.head.repo else None
                    }
                },
                "base": {
                    "ref": pr.base.ref,
                    "sha": pr.base.sha,
                    "repo": {
                        "full_name": pr.base.repo.full_name if pr.base.repo else None
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create pull request: {str(e)}")
            raise GitHubServiceError("Failed to create pull request") from e
    
    async def get_rate_limit(self) -> Dict[str, Any]:
        """Get GitHub API rate limit information"""
        try:
            rate_limit = self.client.get_rate_limit()
            return {
                "limit": rate_limit.core.limit,
                "remaining": rate_limit.core.remaining,
                "reset_at": rate_limit.core.reset.timestamp() if rate_limit.core.reset else None,
                "used": rate_limit.core.limit - rate_limit.core.remaining
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit: {str(e)}")
            return {
                "limit": 0,
                "remaining": 0,
                "reset_at": None,
                "used": 0
            }
