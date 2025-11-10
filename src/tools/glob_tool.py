"""
Glob Tool
Find files matching glob patterns
"""
from typing import List
import glob
import os
from src.tools.registry import Tool


class GlobTool(Tool):
    """Find files matching glob patterns"""

    def get_name(self) -> str:
        return "Glob"

    def get_description(self) -> str:
        return "Find files matching glob patterns (e.g., '**/*.py', 'src/**/*.ts')"

    async def execute(
        self,
        workspace_path: str,
        pattern: str
    ) -> List[str]:
        """
        Execute glob pattern matching

        Args:
            workspace_path: Root workspace directory
            pattern: Glob pattern (e.g., '**/*.py')

        Returns:
            List of matching file paths (relative to workspace)
        """
        # Validate workspace path
        if not self.validate_workspace(workspace_path, workspace_path):
            raise ValueError("Invalid workspace path")

        if not os.path.exists(workspace_path):
            raise ValueError(f"Workspace does not exist: {workspace_path}")

        # Build full pattern path
        full_pattern = os.path.join(workspace_path, pattern)

        try:
            # Execute glob with recursive support
            matches = glob.glob(full_pattern, recursive=True)

            # Convert to relative paths and filter out directories
            relative_matches = []
            for match in matches:
                # Only include files, not directories
                if os.path.isfile(match):
                    # Convert to relative path
                    rel_path = os.path.relpath(match, workspace_path)
                    relative_matches.append(rel_path)

            # Sort for consistent ordering
            relative_matches.sort()

            return relative_matches

        except Exception as e:
            raise RuntimeError(f"Glob pattern matching failed: {str(e)}")
