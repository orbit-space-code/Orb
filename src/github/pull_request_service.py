"""
GitHub Pull Request Service
Handles PR creation, labeling, and GitHub API integration
"""
import os
import json
import hmac
import hashlib
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
import logging
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FileChange:
    """Represents a file change in a pull request"""
    path: str
    status: str  # 'added', 'modified', 'deleted'
    additions: int
    deletions: int
    patch: Optional[str] = None


@dataclass
class PullRequestData:
    """Pull request creation data"""
    title: str
    body: str
    head: str  # feature branch
    base: str  # target branch
    draft: bool = False


class GitHubAPIError(Exception):
    """Custom exception for GitHub API errors"""
    pass


class PullRequestService:
    """
    GitHub Pull Request Service with App authentication
    Handles PR creation, labeling, and repository operations
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.app_id = os.getenv("GITHUB_APP_ID")
        self.private_key_path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
        self.private_key = self._load_private_key()
        self.base_url = "https://api.github.com"
        
        # Rate limiting configuration
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = datetime.now(timezone.utc)
        
        # Repository metadata cache (expires after 1 hour)
        self._repo_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_expiry: Dict[str, datetime] = {}

    def _load_private_key(self) -> Optional[str]:
        """Load GitHub App private key from file or environment"""
        try:
            if self.private_key_path and os.path.exists(self.private_key_path):
                with open(self.private_key_path, 'r') as f:
                    return f.read()
            
            # Fallback to environment variable
            private_key_env = os.getenv("GITHUB_APP_PRIVATE_KEY", "")
            if private_key_env:
                # Handle escaped newlines in environment variable
                return private_key_env.replace('\\n', '\n')
            
            logger.warning("GitHub App private key not found")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load GitHub App private key: {e}")
            return None

    def _generate_jwt_token(self) -> str:
        """Generate JWT token for GitHub App authentication"""
        if not self.private_key:
            raise GitHubAPIError("GitHub App private key not configured")
        
        try:
            import jwt
            
            # JWT payload
            now = datetime.now(timezone.utc)
            payload = {
                'iat': int(now.timestamp()),
                'exp': int((now + timedelta(minutes=10)).timestamp()),
                'iss': self.app_id
            }
            
            # Generate JWT
            token = jwt.encode(payload, self.private_key, algorithm='RS256')
            return token
            
        except ImportError:
            raise GitHubAPIError("PyJWT library required for GitHub App authentication")
        except Exception as e:
            raise GitHubAPIError(f"Failed to generate JWT token: {e}")

    def _parse_repository_url(self, repository_url: str) -> Tuple[str, str]:
        """Parse GitHub repository URL to extract owner and repo name"""
        try:
            # Handle different URL formats
            url = repository_url.rstrip('/')
            
            if url.startswith('https://github.com/'):
                path = url.replace('https://github.com/', '')
            elif url.startswith('git@github.com:'):
                path = url.replace('git@github.com:', '')
            else:
                raise ValueError(f"Unsupported repository URL format: {repository_url}")
            
            # Remove .git suffix if present
            if path.endswith('.git'):
                path = path[:-4]
            
            parts = path.split('/')
            if len(parts) != 2:
                raise ValueError(f"Invalid repository path: {path}")
            
            return parts[0], parts[1]
            
        except Exception as e:
            raise GitHubAPIError(f"Failed to parse repository URL: {e}")

    def validate_webhook_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """
        Validate GitHub webhook signature
        
        Args:
            payload: Raw webhook payload
            signature: GitHub signature header (X-Hub-Signature-256)
            secret: Webhook secret
            
        Returns:
            True if signature is valid
        """
        try:
            if not signature.startswith('sha256='):
                return False
            
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            received_signature = signature[7:]  # Remove 'sha256=' prefix
            
            return hmac.compare_digest(expected_signature, received_signature)
            
        except Exception as e:
            logger.error(f"Webhook signature validation error: {e}")
            return False

    def _analyze_change_types(self, file_changes: List[FileChange]) -> List[str]:
        """Analyze file changes to determine appropriate labels"""
        labels = []
        
        # File extension analysis
        extensions = set()
        for change in file_changes:
            if '.' in change.path:
                ext = change.path.split('.')[-1].lower()
                extensions.add(ext)
        
        # Language-based labels
        if any(ext in ['py', 'pyx', 'pyi'] for ext in extensions):
            labels.append('python')
        if any(ext in ['js', 'jsx', 'ts', 'tsx'] for ext in extensions):
            labels.append('javascript')
        if any(ext in ['html', 'css', 'scss', 'sass'] for ext in extensions):
            labels.append('frontend')
        if any(ext in ['sql', 'db'] for ext in extensions):
            labels.append('database')
        
        # Change type analysis
        has_new_files = any(change.status == 'added' for change in file_changes)
        has_deletions = any(change.status == 'deleted' for change in file_changes)
        
        if has_new_files:
            labels.append('enhancement')
        if has_deletions:
            labels.append('cleanup')
        
        # File path analysis
        paths = [change.path.lower() for change in file_changes]
        
        if any('test' in path or 'spec' in path for path in paths):
            labels.append('tests')
        if any('doc' in path or 'readme' in path for path in paths):
            labels.append('documentation')
        if any('config' in path or '.env' in path for path in paths):
            labels.append('configuration')
        
        # Default label
        if not labels:
            labels.append('feature')
        
        # Add automated label
        labels.append('automated')
        
        return labels

    async def create_pull_request(
        self,
        project_id: str,
        repository_url: str,
        feature_branch: str,
        implementation_summary: str,
        file_changes: List[FileChange]
    ) -> Dict[str, Any]:
        """
        Create pull request with comprehensive description
        
        Args:
            project_id: Project identifier
            repository_url: GitHub repository URL
            feature_branch: Source branch name
            implementation_summary: Summary of implementation
            file_changes: List of file changes
            
        Returns:
            Pull request data including URL and number
        """
        try:
            logger.info(f"Creating pull request for project {project_id}")
            
            # Get repository metadata
            repo_metadata = await self.get_repository_metadata(repository_url)
            owner = repo_metadata['owner']
            repo = repo_metadata['repo']
            default_branch = repo_metadata['default_branch']
            
            # Generate PR title and description
            pr_data = await self._generate_pr_content(
                project_id, implementation_summary, file_changes
            )
            
            # Check if draft PR is needed due to branch protection
            draft = repo_metadata['has_branch_protection']
            if draft:
                logger.info("Creating draft PR due to branch protection rules")
            
            # Create pull request
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
            pr_payload = {
                'title': pr_data.title,
                'body': pr_data.body,
                'head': feature_branch,
                'base': default_branch,
                'draft': draft
            }
            
            pr_response = await self._make_github_request("POST", url, owner, repo, pr_payload)
            
            # Add labels based on change types
            change_types = self._analyze_change_types(file_changes)
            if change_types:
                await self._add_pr_labels(owner, repo, pr_response['number'], change_types)
            
            result = {
                'pr_number': pr_response['number'],
                'pr_url': pr_response['html_url'],
                'title': pr_response['title'],
                'draft': pr_response['draft'],
                'created_at': pr_response['created_at'],
                'labels': change_types
            }
            
            logger.info(f"Created PR #{pr_response['number']} for project {project_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create pull request: {e}")
            raise GitHubAPIError(f"PR creation failed: {e}")

    async def _generate_pr_content(
        self,
        project_id: str,
        implementation_summary: str,
        file_changes: List[FileChange]
    ) -> PullRequestData:
        """Generate PR title and description"""
        try:
            # Generate title
            title = f"[Orb] Implement feature for project {project_id[:8]}"
            
            # Count changes
            total_files = len(file_changes)
            total_additions = sum(change.additions for change in file_changes)
            total_deletions = sum(change.deletions for change in file_changes)
            
            # Generate description
            description = f"""## 🤖 Automated Implementation by Orb

### Summary
{implementation_summary}

### Changes Overview
- **Files changed:** {total_files}
- **Lines added:** {total_additions}
- **Lines deleted:** {total_deletions}

### File Changes
"""
            
            # Add file change details
            for change in file_changes[:10]:  # Limit to first 10 files
                status_emoji = {
                    'added': '✅',
                    'modified': '📝',
                    'deleted': '❌'
                }.get(change.status, '📄')
                
                description += f"- {status_emoji} `{change.path}` (+{change.additions}/-{change.deletions})\n"
            
            if len(file_changes) > 10:
                description += f"- ... and {len(file_changes) - 10} more files\n"
            
            description += f"""
### Implementation Details
This pull request was automatically generated by Orb AI coding agent.

**Project ID:** `{project_id}`
**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC

### Review Checklist
- [ ] Code follows project conventions
- [ ] Tests pass (if applicable)
- [ ] Documentation updated (if needed)
- [ ] No sensitive information exposed

---
*Generated by [OrbitSpace](https://orbitspace.org) - AI-powered coding assistant*
"""
            
            return PullRequestData(
                title=title,
                body=description,
                head="",  # Will be set by caller
                base=""   # Will be set by caller
            )
            
        except Exception as e:
            logger.error(f"Failed to generate PR content: {e}")
            raise GitHubAPIError(f"PR content generation failed: {e}")

    async def _add_pr_labels(self, owner: str, repo: str, pr_number: int, labels: List[str]):
        """Add labels to pull request"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/labels"
            await self._make_github_request("POST", url, owner, repo, {'labels': labels})
            logger.info(f"Added labels {labels} to PR #{pr_number}")
            
        except Exception as e:
            logger.warning(f"Failed to add labels to PR: {e}")
            # Don't fail the whole operation if labeling fails

    async def _get_installation_token(self, owner: str, repo: str) -> str:
        """Get installation access token for repository"""
        try:
            jwt_token = self._generate_jwt_token()
            
            # Get installation ID for repository
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {jwt_token}',
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Orb-GitHub-Integration/1.0'
                }
                
                # Get installation for repository
                url = f"{self.base_url}/repos/{owner}/{repo}/installation"
                async with session.get(url, headers=headers) as response:
                    if response.status == 404:
                        raise GitHubAPIError(f"GitHub App not installed on {owner}/{repo}")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise GitHubAPIError(f"Failed to get installation: {error_text}")
                    
                    installation_data = await response.json()
                    installation_id = installation_data['id']
                
                # Get access token for installation
                url = f"{self.base_url}/app/installations/{installation_id}/access_tokens"
                async with session.post(url, headers=headers) as response:
                    if response.status != 201:
                        error_text = await response.text()
                        raise GitHubAPIError(f"Failed to get access token: {error_text}")
                    
                    token_data = await response.json()
                    return token_data['token']
                    
        except Exception as e:
            logger.error(f"Failed to get installation token: {e}")
            raise GitHubAPIError(f"Installation token error: {e}")

    async def _make_github_request(
        self, 
        method: str, 
        url: str, 
        owner: str, 
        repo: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated GitHub API request with rate limiting and retry logic"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Check rate limiting
                if self.rate_limit_remaining < 100 and datetime.now(timezone.utc) < self.rate_limit_reset:
                    wait_time = (self.rate_limit_reset - datetime.now(timezone.utc)).total_seconds()
                    logger.warning(f"Rate limit low, waiting {wait_time} seconds")
                    await asyncio.sleep(wait_time)
                
                # Get installation token
                token = await self._get_installation_token(owner, repo)
                
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Orb-GitHub-Integration/1.0'
                }
                
                async with aiohttp.ClientSession() as session:
                    request_kwargs = {
                        'headers': headers,
                        'params': params
                    }
                    
                    if data:
                        request_kwargs['json'] = data
                    
                    async with session.request(method, url, **request_kwargs) as response:
                        # Update rate limiting info
                        self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 5000))
                        reset_timestamp = int(response.headers.get('X-RateLimit-Reset', 0))
                        if reset_timestamp:
                            self.rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
                        
                        if response.status == 200 or response.status == 201:
                            return await response.json()
                        elif response.status == 403 and 'rate limit' in (await response.text()).lower():
                            # Rate limited, wait and retry
                            wait_time = 60 * (attempt + 1)
                            logger.warning(f"Rate limited, waiting {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                        elif response.status >= 500:
                            # Server error, retry with exponential backoff
                            wait_time = retry_delay * (2 ** attempt)
                            logger.warning(f"Server error {response.status}, retrying in {wait_time} seconds")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_text = await response.text()
                            raise GitHubAPIError(f"GitHub API error {response.status}: {error_text}")
                            
            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    raise GitHubAPIError(f"Network error: {e}")
                await asyncio.sleep(retry_delay * (2 ** attempt))
            except GitHubAPIError:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(retry_delay * (2 ** attempt))
        
        raise GitHubAPIError("Max retries exceeded")

    async def get_repository_metadata(self, repository_url: str) -> Dict[str, Any]:
        """
        Get repository metadata with caching
        
        Args:
            repository_url: GitHub repository URL
            
        Returns:
            Repository metadata including default branch, protection rules, etc.
        """
        try:
            # Parse repository URL
            owner, repo = self._parse_repository_url(repository_url)
            cache_key = f"{owner}/{repo}"
            
            # Check cache
            if (cache_key in self._repo_cache and 
                cache_key in self._cache_expiry and 
                datetime.now(timezone.utc) < self._cache_expiry[cache_key]):
                return self._repo_cache[cache_key]
            
            # Fetch repository data
            url = f"{self.base_url}/repos/{owner}/{repo}"
            repo_data = await self._make_github_request("GET", url, owner, repo)
            
            # Fetch branch protection rules for default branch
            default_branch = repo_data['default_branch']
            protection_data = await self._get_branch_protection(owner, repo, default_branch)
            
            # Build metadata
            metadata = {
                'owner': owner,
                'repo': repo,
                'full_name': repo_data['full_name'],
                'default_branch': default_branch,
                'private': repo_data['private'],
                'has_branch_protection': protection_data is not None,
                'protection_rules': protection_data,
                'clone_url': repo_data['clone_url'],
                'ssh_url': repo_data['ssh_url'],
                'updated_at': repo_data['updated_at']
            }
            
            # Cache metadata for 1 hour
            self._repo_cache[cache_key] = metadata
            self._cache_expiry[cache_key] = datetime.now(timezone.utc) + timedelta(hours=1)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get repository metadata: {e}")
            raise GitHubAPIError(f"Repository metadata error: {e}")

    async def _get_branch_protection(self, owner: str, repo: str, branch: str) -> Optional[Dict[str, Any]]:
        """Get branch protection rules"""
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/branches/{branch}/protection"
            return await self._make_github_request("GET", url, owner, repo)
        except GitHubAPIError as e:
            if "404" in str(e):
                return None  # No protection rules
            raise

    async def get_file_changes_from_git(self, repo_path: str, base_branch: str = None) -> List[FileChange]:
        """
        Extract file changes from git repository
        
        Args:
            repo_path: Path to git repository
            base_branch: Base branch to compare against (defaults to origin/main)
            
        Returns:
            List of FileChange objects
        """
        try:
            from git import Repo
            
            repo = Repo(repo_path)
            
            # Determine base branch
            if not base_branch:
                try:
                    base_branch = f"origin/{repo.remotes.origin.refs[0].remote_head}"
                except:
                    base_branch = "origin/main"
            
            # Get diff between current branch and base
            try:
                diff = repo.git.diff(base_branch, '--name-status', '--numstat')
            except:
                # Fallback to comparing with HEAD if base branch doesn't exist
                diff = repo.git.diff('HEAD~1', '--name-status', '--numstat')
            
            file_changes = []
            
            if not diff.strip():
                return file_changes
            
            # Parse git diff output
            lines = diff.strip().split('\n')
            for line in lines:
                if not line.strip():
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 2:
                    # Handle different git diff formats
                    if parts[0].isdigit():
                        # --numstat format: additions deletions filename
                        if len(parts) >= 3:
                            additions = int(parts[0]) if parts[0] != '-' else 0
                            deletions = int(parts[1]) if parts[1] != '-' else 0
                            filepath = parts[2]
                            status = 'modified'
                        else:
                            continue
                    else:
                        # --name-status format: status filename
                        status_code = parts[0][0]  # First character
                        filepath = parts[1]
                        
                        status_map = {
                            'A': 'added',
                            'M': 'modified',
                            'D': 'deleted',
                            'R': 'modified',  # Renamed
                            'C': 'modified'   # Copied
                        }
                        status = status_map.get(status_code, 'modified')
                        
                        # Get line counts for this file
                        try:
                            numstat = repo.git.diff(base_branch, '--numstat', '--', filepath)
                            if numstat.strip():
                                numstat_parts = numstat.strip().split('\t')
                                additions = int(numstat_parts[0]) if numstat_parts[0] != '-' else 0
                                deletions = int(numstat_parts[1]) if numstat_parts[1] != '-' else 0
                            else:
                                additions = deletions = 0
                        except:
                            additions = deletions = 0
                    
                    file_changes.append(FileChange(
                        path=filepath,
                        status=status,
                        additions=additions,
                        deletions=deletions
                    ))
            
            return file_changes
            
        except Exception as e:
            logger.error(f"Failed to get file changes from git: {e}")
            return []

    async def handle_merge_conflicts(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """
        Handle merge conflicts in pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            Conflict resolution status
        """
        try:
            # Get PR details
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            pr_data = await self._make_github_request("GET", url, owner, repo)
            
            if not pr_data.get('mergeable_state') == 'dirty':
                return {'has_conflicts': False, 'status': 'clean'}
            
            # Add comment about merge conflicts
            comment_url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
            comment_body = """## ⚠️ Merge Conflicts Detected

This pull request has merge conflicts that need to be resolved before it can be merged.

### Next Steps:
1. Pull the latest changes from the base branch
2. Resolve conflicts in the affected files
3. Commit the resolution
4. Push the updated branch

The conflicts will be automatically resolved in the next iteration if possible."""

            await self._make_github_request("POST", comment_url, owner, repo, {
                'body': comment_body
            })
            
            return {
                'has_conflicts': True,
                'status': 'conflicts_detected',
                'comment_added': True
            }
            
        except Exception as e:
            logger.error(f"Failed to handle merge conflicts: {e}")
            return {'has_conflicts': False, 'status': 'error', 'error': str(e)}

    async def check_branch_protection_rules(self, owner: str, repo: str, branch: str) -> Dict[str, Any]:
        """
        Check branch protection rules and requirements
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name to check
            
        Returns:
            Branch protection information
        """
        try:
            protection_data = await self._get_branch_protection(owner, repo, branch)
            
            if not protection_data:
                return {
                    'protected': False,
                    'requires_reviews': False,
                    'requires_status_checks': False,
                    'requires_draft': False
                }
            
            # Parse protection rules
            requires_reviews = protection_data.get('required_pull_request_reviews', {}).get('required_approving_review_count', 0) > 0
            requires_status_checks = bool(protection_data.get('required_status_checks', {}).get('contexts', []))
            
            return {
                'protected': True,
                'requires_reviews': requires_reviews,
                'requires_status_checks': requires_status_checks,
                'requires_draft': requires_reviews or requires_status_checks,
                'protection_rules': protection_data
            }
            
        except Exception as e:
            logger.error(f"Failed to check branch protection: {e}")
            return {'protected': False, 'error': str(e)}

    async def update_pr_description(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        additional_info: str
    ) -> bool:
        """
        Update pull request description with additional information
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            additional_info: Additional information to append
            
        Returns:
            True if successful
        """
        try:
            # Get current PR data
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            pr_data = await self._make_github_request("GET", url, owner, repo)
            
            # Update description
            current_body = pr_data.get('body', '')
            updated_body = f"{current_body}\n\n---\n\n### Additional Information\n{additional_info}"
            
            # Update PR
            await self._make_github_request("PATCH", url, owner, repo, {
                'body': updated_body
            })
            
            logger.info(f"Updated PR #{pr_number} description")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update PR description: {e}")
            return False

    async def add_agent_recommendations(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        recommendations: List[str]
    ) -> bool:
        """
        Add agent recommendations as PR comment
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            recommendations: List of recommendations
            
        Returns:
            True if successful
        """
        try:
            if not recommendations:
                return True
            
            comment_body = "## 🤖 Agent Recommendations\n\n"
            for i, rec in enumerate(recommendations, 1):
                comment_body += f"{i}. {rec}\n"
            
            comment_body += "\n*These recommendations were generated by the Orb AI agent during implementation.*"
            
            url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
            await self._make_github_request("POST", url, owner, repo, {
                'body': comment_body
            })
            
            logger.info(f"Added agent recommendations to PR #{pr_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add agent recommendations: {e}")
            return False

    async def get_pr_status(self, owner: str, repo: str, pr_number: int) -> Dict[str, Any]:
        """
        Get pull request status and metadata
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            PR status information
        """
        try:
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            pr_data = await self._make_github_request("GET", url, owner, repo)
            
            return {
                'number': pr_data['number'],
                'title': pr_data['title'],
                'state': pr_data['state'],
                'draft': pr_data['draft'],
                'mergeable': pr_data.get('mergeable'),
                'mergeable_state': pr_data.get('mergeable_state'),
                'merged': pr_data['merged'],
                'created_at': pr_data['created_at'],
                'updated_at': pr_data['updated_at'],
                'merged_at': pr_data.get('merged_at'),
                'html_url': pr_data['html_url'],
                'head_sha': pr_data['head']['sha'],
                'base_ref': pr_data['base']['ref'],
                'head_ref': pr_data['head']['ref']
            }
            
        except Exception as e:
            logger.error(f"Failed to get PR status: {e}")
            raise GitHubAPIError(f"PR status error: {e}")

    async def create_pull_request_with_template(
        self,
        project_id: str,
        repository_url: str,
        feature_branch: str,
        implementation_summary: str,
        file_changes: List[FileChange],
        db_client=None
    ) -> Dict[str, Any]:
        """
        Create pull request using appropriate template and track in database
        
        Args:
            project_id: Project identifier
            repository_url: GitHub repository URL
            feature_branch: Source branch name
            implementation_summary: Summary of implementation
            file_changes: List of file changes
            db_client: Database client for tracking
            
        Returns:
            Pull request data including URL and number
        """
        try:
            from .pr_templates import PRTemplateManager, ChangeType
            from datetime import datetime
            
            logger.info(f"Creating templated pull request for project {project_id}")
            
            # Get repository metadata
            repo_metadata = await self.get_repository_metadata(repository_url)
            owner = repo_metadata['owner']
            repo = repo_metadata['repo']
            default_branch = repo_metadata['default_branch']
            
            # Initialize template manager
            template_manager = PRTemplateManager()
            
            # Detect change type
            change_type = template_manager.detect_change_type(file_changes, implementation_summary)
            logger.info(f"Detected change type: {change_type.value}")
            
            # Generate changes summary
            changes_summary = self._generate_changes_summary(file_changes)
            
            # Generate PR content using template
            pr_content = template_manager.generate_pr_content(
                change_type=change_type,
                project_id=project_id,
                description=implementation_summary,
                changes_summary=changes_summary,
                timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            )
            
            # Check if draft PR is needed due to branch protection
            protection_info = await self.check_branch_protection_rules(owner, repo, default_branch)
            draft = protection_info.get('requires_draft', False)
            
            if draft:
                logger.info("Creating draft PR due to branch protection rules")
            
            # Create pull request
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
            pr_payload = {
                'title': pr_content['title'],
                'body': pr_content['body'],
                'head': feature_branch,
                'base': default_branch,
                'draft': draft
            }
            
            pr_response = await self._make_github_request("POST", url, owner, repo, pr_payload)
            
            # Add labels
            labels = pr_content['labels']
            if labels:
                await self._add_pr_labels(owner, repo, pr_response['number'], labels)
            
            # Track in database if client provided
            if db_client:
                await self._track_pr_in_database(
                    db_client, project_id, repository_url, pr_response, labels, draft
                )
            
            result = {
                'pr_number': pr_response['number'],
                'pr_url': pr_response['html_url'],
                'title': pr_response['title'],
                'draft': pr_response['draft'],
                'created_at': pr_response['created_at'],
                'labels': labels,
                'change_type': change_type.value
            }
            
            logger.info(f"Created templated PR #{pr_response['number']} for project {project_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create templated pull request: {e}")
            raise GitHubAPIError(f"Templated PR creation failed: {e}")

    def _generate_changes_summary(self, file_changes: List[FileChange]) -> str:
        """Generate a summary of file changes"""
        if not file_changes:
            return "No file changes detected"
        
        total_files = len(file_changes)
        total_additions = sum(change.additions for change in file_changes)
        total_deletions = sum(change.deletions for change in file_changes)
        
        # Group by status
        added_files = [c for c in file_changes if c.status == 'added']
        modified_files = [c for c in file_changes if c.status == 'modified']
        deleted_files = [c for c in file_changes if c.status == 'deleted']
        
        summary = f"**{total_files} files changed** (+{total_additions}/-{total_deletions})\n\n"
        
        if added_files:
            summary += f"**Added ({len(added_files)} files):**\n"
            for change in added_files[:5]:  # Limit to first 5
                summary += f"- ✅ `{change.path}` (+{change.additions} lines)\n"
            if len(added_files) > 5:
                summary += f"- ... and {len(added_files) - 5} more files\n"
            summary += "\n"
        
        if modified_files:
            summary += f"**Modified ({len(modified_files)} files):**\n"
            for change in modified_files[:5]:  # Limit to first 5
                summary += f"- 📝 `{change.path}` (+{change.additions}/-{change.deletions})\n"
            if len(modified_files) > 5:
                summary += f"- ... and {len(modified_files) - 5} more files\n"
            summary += "\n"
        
        if deleted_files:
            summary += f"**Deleted ({len(deleted_files)} files):**\n"
            for change in deleted_files[:5]:  # Limit to first 5
                summary += f"- ❌ `{change.path}` (-{change.deletions} lines)\n"
            if len(deleted_files) > 5:
                summary += f"- ... and {len(deleted_files) - 5} more files\n"
        
        return summary

    async def _track_pr_in_database(
        self,
        db_client,
        project_id: str,
        repository_url: str,
        pr_response: Dict[str, Any],
        labels: List[str],
        is_draft: bool
    ):
        """Track pull request in database"""
        try:
            pr_data = {
                'projectId': project_id,
                'repositoryUrl': repository_url,
                'prNumber': pr_response['number'],
                'prUrl': pr_response['html_url'],
                'branch': pr_response['head']['ref'],
                'title': pr_response['title'],
                'labels': labels,
                'isDraft': is_draft,
                'status': 'DRAFT' if is_draft else 'OPEN'
            }
            
            await db_client.pullRequest.create({'data': pr_data})
            logger.info(f"Tracked PR #{pr_response['number']} in database")
            
        except Exception as e:
            logger.error(f"Failed to track PR in database: {e}")
            # Don't fail the whole operation if database tracking fails

    async def get_project_pull_requests(self, db_client, project_id: str) -> List[Dict[str, Any]]:
        """Get all pull requests for a project"""
        try:
            prs = await db_client.pullRequest.findMany({
                'where': {'projectId': project_id},
                'orderBy': {'createdAt': 'desc'}
            })
            
            return [
                {
                    'id': pr['id'],
                    'pr_number': pr['prNumber'],
                    'pr_url': pr['prUrl'],
                    'title': pr['title'],
                    'status': pr['status'],
                    'labels': pr['labels'],
                    'is_draft': pr['isDraft'],
                    'created_at': pr['createdAt'].isoformat(),
                    'updated_at': pr['updatedAt'].isoformat(),
                    'merged_at': pr['mergedAt'].isoformat() if pr['mergedAt'] else None,
                    'closed_at': pr['closedAt'].isoformat() if pr['closedAt'] else None
                }
                for pr in prs
            ]
            
        except Exception as e:
            logger.error(f"Failed to get project pull requests: {e}")
            return []