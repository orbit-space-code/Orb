"""
Read Tool
Read file contents with optional line range
"""
from typing import Optional
import os
import aiofiles
from src.tools.registry import Tool


class ReadTool(Tool):
    """Read file contents"""

    def get_name(self) -> str:
        return "Read"

    def get_description(self) -> str:
        return "Read file contents with optional line range"

    async def execute(
        self,
        workspace_path: str,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None
    ) -> str:
        """
        Read file contents

        Args:
            workspace_path: Root workspace directory
            file_path: Path to file (relative to workspace)
            start_line: Starting line number (1-indexed, optional)
            end_line: Ending line number (1-indexed, optional)

        Returns:
            File contents (with line numbers if range specified)
        """
        # Build full file path
        full_path = os.path.join(workspace_path, file_path)

        # Validate path
        if not self.validate_workspace(full_path, workspace_path):
            raise ValueError("Invalid file path: outside workspace")

        if not os.path.exists(full_path):
            raise ValueError(f"File does not exist: {file_path}")

        if not os.path.isfile(full_path):
            raise ValueError(f"Path is not a file: {file_path}")

        # Check file size (limit to 1MB)
        file_size = os.path.getsize(full_path)
        max_size = int(os.getenv("MAX_FILE_READ_SIZE_MB", "1")) * 1024 * 1024
        if file_size > max_size:
            raise ValueError(f"File too large: {file_size} bytes (max {max_size} bytes)")

        # Check if file is binary
        try:
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                # Read file contents
                content = await f.read()

            # If no line range specified, return full content
            if start_line is None and end_line is None:
                # Add line numbers for display
                lines = content.split('\n')
                numbered_lines = [f"{i+1:6d}\t{line}" for i, line in enumerate(lines)]
                return '\n'.join(numbered_lines)

            # Apply line range
            lines = content.split('\n')
            total_lines = len(lines)

            # Validate line numbers
            start_line = start_line or 1
            end_line = end_line or total_lines

            if start_line < 1:
                start_line = 1
            if end_line > total_lines:
                end_line = total_lines
            if start_line > end_line:
                raise ValueError(f"Invalid line range: {start_line} to {end_line}")

            # Extract requested lines (convert to 0-indexed)
            selected_lines = lines[start_line-1:end_line]

            # Add line numbers
            numbered_lines = [
                f"{i+start_line:6d}\t{line}"
                for i, line in enumerate(selected_lines)
            ]

            return '\n'.join(numbered_lines)

        except UnicodeDecodeError:
            raise ValueError("File appears to be binary (not text)")
        except Exception as e:
            raise RuntimeError(f"Failed to read file: {str(e)}")
