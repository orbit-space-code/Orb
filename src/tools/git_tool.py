"""
Git Tool
Wrapper for git operations
"""
from typing import Dict, Any
import os
from src.tools.registry import Tool
from src.git.repository import RepositoryManager


class GitTool(Tool):
    """Git operations wrapper"""

    def get_name(self) -> str:
        return "Git"

    def get_description(self) -> str:
        return "Perform git operations (status, diff, commit, push)"

    async def execute(
        self,
        workspace_path: str,
        repo_name: str,
        operation: str,
        **params
    ) -> Dict[str, Any]:
        """
        Execute git operation

        Args:
            workspace_path: Root workspace directory
            repo_name: Repository name
            operation: Git operation (status, diff, commit, push)
            **params: Operation-specific parameters

        Returns:
            Operation result
        """
        # Validate workspace
        if not self.validate_workspace(workspace_path, workspace_path):
            raise ValueError("Invalid workspace path")

        # Build repo path
        repo_path = os.path.join(workspace_path, repo_name)

        if not os.path.exists(repo_path):
            raise ValueError(f"Repository does not exist: {repo_name}")

        # Initialize repository manager
        repo_manager = RepositoryManager(workspace_path)

        # Execute operation
        if operation == "status":
            return await repo_manager.get_status(repo_path)

        elif operation == "diff":
            diff = await repo_manager.get_diff(repo_path)
            return {"diff": diff}

        elif operation == "commit":
            message = params.get("message")
            phase = params.get("phase", "unknown")
            project_id = params.get("project_id", "unknown")

            if not message:
                raise ValueError("Commit message is required")

            commit_sha = await repo_manager.commit_changes(
                repo_path=repo_path,
                message=message,
                phase=phase,
                project_id=project_id
            )

            return {
                "success": True,
                "commit_sha": commit_sha,
                "message": message
            }

        elif operation == "push":
            success = await repo_manager.push_branch(repo_path)
            return {"success": success}

        else:
            raise ValueError(f"Unknown git operation: {operation}")
