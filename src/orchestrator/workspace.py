"""
Workspace Management
Handles workspace creation, initialization, and cleanup
"""
import os
import shutil
from typing import Dict, Any, List
from datetime import datetime
import asyncio
from src.files.manager import FileManager
from src.git.repository import RepositoryManager


class WorkspaceManager:
    """Manages project workspaces"""

    def __init__(self, workspace_root: str = "/workspaces"):
        self.workspace_root = workspace_root
        self.file_manager = FileManager(workspace_root)
        self.repo_manager = RepositoryManager(workspace_root)

    async def initialize_workspace(
        self,
        project_id: str,
        user_id: str,
        feature_request: str,
        repository_urls: List[str]
    ) -> Dict[str, Any]:
        """
        Initialize complete workspace for a project

        Args:
            project_id: Unique project identifier
            user_id: User identifier
            feature_request: User's feature request description
            repository_urls: List of GitHub repository URLs

        Returns:
            Dictionary with workspace_path and repository information
        """
        # Create workspace directory structure
        workspace_path = self.file_manager.get_workspace_path(project_id)

        # Prepare metadata
        metadata = {
            "project_id": project_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "feature_request": feature_request,
            "repositories": [],
            "current_phase": "idle",
            "status": "active"
        }

        # Create workspace with metadata
        await self.file_manager.create_workspace(project_id, metadata)

        # Clone repositories and create branches
        repositories = []
        for repo_url in repository_urls:
            try:
                # Extract repo name from URL
                repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')

                # Clone repository
                repo_path = await self.repo_manager.clone_repository(
                    repository_url=repo_url,
                    workspace_path=workspace_path,
                    github_token=None  # Will be passed from Next.js
                )

                # Create feature branch
                branch_name = await self.repo_manager.create_feature_branch(
                    repo_path=repo_path,
                    project_id=project_id,
                    feature_slug=self._slugify(feature_request[:50])
                )

                repositories.append({
                    "name": repo_name,
                    "url": repo_url,
                    "branch": branch_name,
                    "path": repo_path
                })

            except Exception as e:
                # Log error but continue with other repos
                print(f"Error cloning repository {repo_url}: {str(e)}")
                repositories.append({
                    "name": repo_name,
                    "url": repo_url,
                    "branch": None,
                    "path": None,
                    "error": str(e)
                })

        # Update metadata with repository information
        metadata["repositories"] = repositories
        await self.file_manager.update_session(project_id, {
            "phase": "idle",
            "phase_started_at": None,
            "current_agent": None,
            "pending_question": None,
            "decisions_made": []
        })

        return {
            "workspace_path": workspace_path,
            "repositories": repositories,
            "metadata": metadata
        }

    async def cleanup_workspace(self, project_id: str) -> bool:
        """
        Clean up workspace directory

        Args:
            project_id: Project identifier

        Returns:
            True if successful
        """
        try:
            workspace_path = self.file_manager.get_workspace_path(project_id)

            if os.path.exists(workspace_path):
                # Remove entire workspace directory
                shutil.rmtree(workspace_path)
                return True

            return False

        except Exception as e:
            print(f"Error cleaning up workspace {project_id}: {str(e)}")
            return False

    async def get_workspace_info(self, project_id: str) -> Dict[str, Any]:
        """
        Get workspace information

        Args:
            project_id: Project identifier

        Returns:
            Workspace metadata
        """
        try:
            metadata = await self.file_manager.get_metadata(project_id)
            workspace_path = self.file_manager.get_workspace_path(project_id)

            # Check if workspace exists
            exists = os.path.exists(workspace_path)

            # Get workspace size
            size = self._get_directory_size(workspace_path) if exists else 0

            return {
                "project_id": project_id,
                "workspace_path": workspace_path,
                "exists": exists,
                "size_bytes": size,
                "metadata": metadata
            }

        except Exception as e:
            return {
                "project_id": project_id,
                "error": str(e)
            }

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')

    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total += os.path.getsize(filepath)
        except Exception:
            pass
        return total
