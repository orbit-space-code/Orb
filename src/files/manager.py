"""
File Management System
Handles workspace creation, research.md, planning.md, metadata
"""
from typing import Dict, Any, Optional
import os
import json
import aiofiles
from datetime import datetime


class FileManager:
    """Manages workspace files and metadata"""

    def __init__(self, workspace_root: str = "/workspaces"):
        self.workspace_root = workspace_root

    def get_workspace_path(self, project_id: str) -> str:
        """Get workspace path for project"""
        return os.path.join(self.workspace_root, project_id)

    async def create_workspace(self, project_id: str, metadata: Dict[str, Any]) -> str:
        """
        Create workspace directory structure

        Args:
            project_id: Project identifier
            metadata: Project metadata

        Returns:
            Workspace path
        """
        workspace_path = self.get_workspace_path(project_id)
        os.makedirs(workspace_path, exist_ok=True)

        # Create .OrbitSpace directory
        OrbitSpace_dir = os.path.join(workspace_path, ".OrbitSpace")
        os.makedirs(OrbitSpace_dir, exist_ok=True)
        os.makedirs(os.path.join(OrbitSpace_dir, "logs"), exist_ok=True)

        # Write metadata.json
        metadata_path = os.path.join(OrbitSpace_dir, "metadata.json")
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(metadata, indent=2))

        # Initialize session.json
        session_data = {
            "phase": "idle",
            "phase_started_at": None,
            "current_agent": None,
            "pending_question": None,
            "decisions_made": []
        }
        session_path = os.path.join(OrbitSpace_dir, "session.json")
        async with aiofiles.open(session_path, "w") as f:
            await f.write(json.dumps(session_data, indent=2))

        return workspace_path

    async def read_research(self, project_id: str) -> Optional[str]:
        """Read research.md content"""
        research_path = os.path.join(
            self.get_workspace_path(project_id),
            "research.md"
        )
        if not os.path.exists(research_path):
            return None

        async with aiofiles.open(research_path, "r") as f:
            return await f.read()

    async def write_research(self, project_id: str, content: str):
        """Write research.md content"""
        research_path = os.path.join(
            self.get_workspace_path(project_id),
            "research.md"
        )
        async with aiofiles.open(research_path, "w") as f:
            await f.write(content)

    async def read_planning(self, project_id: str) -> Optional[str]:
        """Read planning.md content"""
        planning_path = os.path.join(
            self.get_workspace_path(project_id),
            "planning.md"
        )
        if not os.path.exists(planning_path):
            return None

        async with aiofiles.open(planning_path, "r") as f:
            return await f.read()

    async def write_planning(self, project_id: str, content: str):
        """Write planning.md content"""
        planning_path = os.path.join(
            self.get_workspace_path(project_id),
            "planning.md"
        )
        async with aiofiles.open(planning_path, "w") as f:
            await f.write(content)

    async def get_metadata(self, project_id: str) -> Dict[str, Any]:
        """Read metadata.json"""
        metadata_path = os.path.join(
            self.get_workspace_path(project_id),
            ".OrbitSpace",
            "metadata.json"
        )
        async with aiofiles.open(metadata_path, "r") as f:
            content = await f.read()
            return json.loads(content)

    async def update_session(self, project_id: str, session_data: Dict[str, Any]):
        """Update session.json"""
        session_path = os.path.join(
            self.get_workspace_path(project_id),
            ".OrbitSpace",
            "session.json"
        )
        async with aiofiles.open(session_path, "w") as f:
            await f.write(json.dumps(session_data, indent=2))
