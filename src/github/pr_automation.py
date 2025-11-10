"""
GitHub Pull Request Automation
Handles automatic PR creation from feature branches with real implementation
"""
import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from .pull_request_service import PullRequestService, FileChange
from .pr_templates import PRTemplateManager, ChangeType
from .pr_labeling import PRLabelingService

logger = logging.getLogger(__name__)


class PRAutomationService:
    """
    Service for automating pull request creation from feature branches
    Real implementation without mock data
    """

    def __init__(self, pr_service: PullRequestService, db_client=None):
        self.pr_service = pr_service
        self.db_client = db_client
        self.template_manager = PRTemplateManager()
        self.labeling_service = PRLabelingService()

    async def create_pr_from_implementation(
        self,
        project_id: str,
        repository_url: str,
        workspace_path: str,
        implementation_summary: str,
        agent_recommendations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create pull request automatically from implementation completion
        
        Args:
            project_id: Project identifier
            repository_url: GitHub repository URL
            workspace_path: Path to workspace containing repository
            implementation_summary: Summary of what was implemented
            agent_recommendations: Optional recommendations from AI agent
            
        Returns:
            PR creation result with URL and metadata
        """
        try:
            logger.info(f"Creating PR for project {project_id} from implementation")
            
            # Get repository metadata
            repo_metadata = await self.pr_service.get_repository_metadata(repository_url)
            repo_name = repo_metadata['repo']
            
            # Get repository path in workspace
            repo_path = os.path.join(workspace_path, repo_name)
            
            if not os.path.exists(repo_path):
                raise ValueError(f"Repository path not found: {repo_path}")
            
            # Get current branch name from git
            current_branch = await self._get_current_branch(repo_path)
            if not current_branch or current_branch == repo_metadata['default_branch']:
                raise ValueError(f"Not on a feature branch. Current branch: {current_branch}")
            
            # Get file changes from git
            file_changes = await self.pr_service.get_file_changes_from_git(
                repo_path, f"origin/{repo_metadata['default_branch']}"
            )
            
            if not file_changes:
                logger.warning(f"No file changes found for project {project_id}")
                return {
                    'success': False,
                    'error': 'No file changes found to create pull request'
                }
            
            logger.info(f"Found {len(file_changes)} file changes for PR creation")
            
            # Create pull request with template
            pr_result = await self.pr_service.create_pull_request_with_template(
                project_id=project_id,
                repository_url=repository_url,
                feature_branch=current_branch,
                implementation_summary=implementation_summary,
                file_changes=file_changes,
                db_client=self.db_client
            )
            
            # Add comprehensive labeling
            if pr_result.get('pr_number'):
                repo_metadata = await self.pr_service.get_repository_metadata(repository_url)
                
                # Generate comprehensive labels
                comprehensive_labels = self.labeling_service.analyze_and_label_pr(
                    file_changes=file_changes,
                    pr_title=pr_result.get('title', ''),
                    pr_description='',  # Would need to get from PR
                    is_draft=pr_result.get('draft', False),
                    project_context={'project_id': project_id, 'phase': 'implementation'}
                )
                
                # Apply additional labels beyond the template ones
                if comprehensive_labels:
                    try:
                        await self.pr_service._add_pr_labels(
                            repo_metadata['owner'],
                            repo_metadata['repo'],
                            pr_result['pr_number'],
                            comprehensive_labels
                        )
                        pr_result['comprehensive_labels'] = comprehensive_labels
                        logger.info(f"Applied {len(comprehensive_labels)} comprehensive labels to PR #{pr_result['pr_number']}")
                    except Exception as e:
                        logger.warning(f"Failed to apply comprehensive labels: {e}")
                
                # Get recommended reviewers
                recommended_reviewers = self.labeling_service.get_recommended_reviewers(
                    file_changes, {'project_id': project_id}
                )
                pr_result['recommended_reviewers'] = recommended_reviewers
            
            # Add agent recommendations if provided
            if agent_recommendations and pr_result.get('pr_number'):
                await self.pr_service.add_agent_recommendations(
                    repo_metadata['owner'],
                    repo_metadata['repo'],
                    pr_result['pr_number'],
                    agent_recommendations
                )
                pr_result['recommendations_added'] = True
            
            # Check for merge conflicts
            if pr_result.get('pr_number'):
                conflict_status = await self.pr_service.handle_merge_conflicts(
                    repo_metadata['owner'],
                    repo_metadata['repo'],
                    pr_result['pr_number']
                )
                pr_result['merge_conflicts'] = conflict_status
            
            logger.info(f"Successfully created PR #{pr_result.get('pr_number')} for project {project_id}")
            return {
                'success': True,
                'pr_data': pr_result,
                'file_changes_count': len(file_changes),
                'repository': repo_name
            }
            
        except Exception as e:
            logger.error(f"Failed to create PR for project {project_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'project_id': project_id
            }

    async def create_prs_for_project(
        self,
        project_id: str,
        workspace_path: str,
        implementation_summary: str,
        agent_recommendations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create pull requests for all repositories in a project
        
        Args:
            project_id: Project identifier
            workspace_path: Path to project workspace
            implementation_summary: Summary of implementation
            agent_recommendations: Optional agent recommendations
            
        Returns:
            Results for all PR creation attempts
        """
        try:
            if not self.db_client:
                raise ValueError("Database client required for project PR creation")
            
            # Get project data with repositories
            project_data = await self.db_client.project.findUnique({
                'where': {'id': project_id},
                'include': {'repositories': True}
            })
            
            if not project_data:
                raise ValueError(f"Project not found: {project_id}")
            
            repositories = project_data.get('repositories', [])
            if not repositories:
                raise ValueError(f"No repositories found for project {project_id}")
            
            logger.info(f"Creating PRs for {len(repositories)} repositories in project {project_id}")
            
            results = []
            successful_prs = 0
            failed_prs = 0
            
            for repo_data in repositories:
                try:
                    result = await self.create_pr_from_implementation(
                        project_id=project_id,
                        repository_url=repo_data['url'],
                        workspace_path=workspace_path,
                        implementation_summary=implementation_summary,
                        agent_recommendations=agent_recommendations
                    )
                    
                    result['repository_name'] = repo_data['name']
                    results.append(result)
                    
                    if result['success']:
                        successful_prs += 1
                    else:
                        failed_prs += 1
                        
                except Exception as e:
                    logger.error(f"Failed to create PR for repository {repo_data['name']}: {e}")
                    results.append({
                        'success': False,
                        'error': str(e),
                        'repository_name': repo_data['name']
                    })
                    failed_prs += 1
            
            return {
                'project_id': project_id,
                'total_repositories': len(repositories),
                'successful_prs': successful_prs,
                'failed_prs': failed_prs,
                'results': results,
                'summary': f"Created {successful_prs} PRs successfully, {failed_prs} failed"
            }
            
        except Exception as e:
            logger.error(f"Failed to create PRs for project {project_id}: {e}")
            return {
                'project_id': project_id,
                'success': False,
                'error': str(e),
                'results': []
            }

    async def _get_current_branch(self, repo_path: str) -> Optional[str]:
        """Get current branch name from git repository"""
        try:
            from git import Repo
            repo = Repo(repo_path)
            return repo.active_branch.name
        except Exception as e:
            logger.error(f"Failed to get current branch from {repo_path}: {e}")
            return None

    async def update_pr_with_implementation_details(
        self,
        repository_url: str,
        pr_number: int,
        implementation_details: str,
        code_changes_summary: str
    ) -> bool:
        """
        Update existing PR with additional implementation details
        
        Args:
            repository_url: GitHub repository URL
            pr_number: Pull request number
            implementation_details: Detailed implementation notes
            code_changes_summary: Summary of code changes made
            
        Returns:
            True if successful
        """
        try:
            repo_metadata = await self.pr_service.get_repository_metadata(repository_url)
            
            additional_info = f"""
## Implementation Details

{implementation_details}

## Code Changes Summary

{code_changes_summary}

## Generated Information
- **Updated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC
- **Source:** OrbitSpace AI Implementation Agent
"""
            
            success = await self.pr_service.update_pr_description(
                repo_metadata['owner'],
                repo_metadata['repo'],
                pr_number,
                additional_info
            )
            
            if success:
                logger.info(f"Updated PR #{pr_number} with implementation details")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update PR #{pr_number}: {e}")
            return False

    async def get_pr_status_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get status of all pull requests for a project
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of PR status information
        """
        try:
            if not self.db_client:
                return []
            
            # Get PRs from database
            prs = await self.pr_service.get_project_pull_requests(self.db_client, project_id)
            
            # Get current status from GitHub for each PR
            updated_prs = []
            for pr in prs:
                try:
                    # Parse repository URL to get owner/repo
                    owner, repo = self.pr_service._parse_repository_url(pr['pr_url'].split('/pull/')[0])
                    
                    # Get current status from GitHub
                    github_status = await self.pr_service.get_pr_status(owner, repo, pr['pr_number'])
                    
                    # Merge database and GitHub data
                    updated_pr = {
                        **pr,
                        'github_status': github_status,
                        'is_mergeable': github_status.get('mergeable'),
                        'mergeable_state': github_status.get('mergeable_state'),
                        'current_state': github_status.get('state')
                    }
                    updated_prs.append(updated_pr)
                    
                except Exception as e:
                    logger.warning(f"Failed to get GitHub status for PR {pr['pr_number']}: {e}")
                    updated_prs.append(pr)
            
            return updated_prs
            
        except Exception as e:
            logger.error(f"Failed to get PR status for project {project_id}: {e}")
            return []

    async def retry_failed_pr_creation(
        self,
        project_id: str,
        repository_url: str,
        workspace_path: str,
        implementation_summary: str
    ) -> Dict[str, Any]:
        """
        Retry PR creation for a specific repository that previously failed
        
        Args:
            project_id: Project identifier
            repository_url: GitHub repository URL
            workspace_path: Path to workspace
            implementation_summary: Implementation summary
            
        Returns:
            Retry result
        """
        try:
            logger.info(f"Retrying PR creation for {repository_url} in project {project_id}")
            
            result = await self.create_pr_from_implementation(
                project_id=project_id,
                repository_url=repository_url,
                workspace_path=workspace_path,
                implementation_summary=implementation_summary
            )
            
            if result['success']:
                logger.info(f"Successfully retried PR creation for {repository_url}")
            else:
                logger.warning(f"Retry failed for {repository_url}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to retry PR creation for {repository_url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'repository_url': repository_url
            }