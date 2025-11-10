"""
Grep Tool
Search file contents using ripgrep (rg)
"""
from typing import List, Dict, Any
import subprocess
import os
from src.tools.registry import Tool


class GrepTool(Tool):
    """Search file contents with regex patterns using ripgrep"""

    def get_name(self) -> str:
        return "Grep"

    def get_description(self) -> str:
        return "Search file contents with regex patterns. Fast searching using ripgrep."

    async def execute(
        self,
        workspace_path: str,
        pattern: str,
        path: str = ".",
        case_sensitive: bool = True,
        file_type: str = None,
        context_lines: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Execute grep search

        Args:
            workspace_path: Root workspace directory
            pattern: Regex pattern to search for
            path: Path to search within (relative to workspace)
            case_sensitive: Whether search is case sensitive
            file_type: Filter by file type (e.g., 'py', 'js', 'ts')
            context_lines: Number of context lines to show

        Returns:
            List of matches with file, line number, and content
        """
        # Validate workspace path
        search_path = os.path.join(workspace_path, path)
        if not self.validate_workspace(search_path, workspace_path):
            raise ValueError("Invalid path: outside workspace")

        if not os.path.exists(search_path):
            raise ValueError(f"Path does not exist: {search_path}")

        # Build ripgrep command
        cmd = ["rg", "--json"]

        # Case sensitivity
        if not case_sensitive:
            cmd.append("-i")

        # File type filter
        if file_type:
            cmd.extend(["-t", file_type])

        # Context lines
        if context_lines > 0:
            cmd.extend(["-C", str(context_lines)])

        # Add pattern and path
        cmd.append(pattern)
        cmd.append(search_path)

        try:
            # Run ripgrep
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Parse JSON output
            matches = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                try:
                    import json
                    data = json.loads(line)

                    # Only process match results
                    if data.get('type') == 'match':
                        match_data = data.get('data', {})
                        path_data = match_data.get('path', {})
                        line_data = match_data.get('line_number')
                        lines_data = match_data.get('lines', {})

                        matches.append({
                            'file': path_data.get('text', ''),
                            'line': line_data,
                            'content': lines_data.get('text', '').rstrip('\n'),
                            'match': True
                        })

                except json.JSONDecodeError:
                    continue

            return matches

        except subprocess.TimeoutExpired:
            raise TimeoutError("Grep search timed out after 30 seconds")
        except FileNotFoundError:
            raise RuntimeError("ripgrep (rg) is not installed")
        except Exception as e:
            raise RuntimeError(f"Grep search failed: {str(e)}")
