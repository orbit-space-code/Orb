"""
Edit Tool
Modify file contents with search-and-replace
"""
import os
import shutil
import aiofiles
from typing import Optional
from src.tools.registry import Tool


class EditTool(Tool):
    """Edit file contents with search-and-replace"""

    def get_name(self) -> str:
        return "Edit"

    def get_description(self) -> str:
        return "Modify file contents using search-and-replace"

    async def execute(
        self,
        workspace_path: str,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False
    ) -> dict:
        """
        Edit file with search-and-replace

        Args:
            workspace_path: Root workspace directory
            file_path: Path to file (relative to workspace)
            old_string: String to search for
            new_string: String to replace with
            replace_all: Replace all occurrences (default: only first)

        Returns:
            Dictionary with success status and preview
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

        # Create backup
        backup_path = full_path + ".backup"
        shutil.copy2(full_path, backup_path)

        try:
            # Read file contents
            async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
                content = await f.read()

            # Check if old_string exists
            if old_string not in content:
                # Restore from backup
                shutil.copy2(backup_path, full_path)
                os.remove(backup_path)
                raise ValueError(f"String not found in file: {old_string[:100]}...")

            # Count occurrences
            count = content.count(old_string)

            if not replace_all and count > 1:
                # Restore from backup
                shutil.copy2(backup_path, full_path)
                os.remove(backup_path)
                raise ValueError(
                    f"String appears {count} times in file. "
                    f"Use replace_all=true to replace all occurrences, "
                    f"or provide a more specific old_string"
                )

            # Perform replacement
            if replace_all:
                new_content = content.replace(old_string, new_string)
                replacements = count
            else:
                new_content = content.replace(old_string, new_string, 1)
                replacements = 1

            # Write new content
            async with aiofiles.open(full_path, 'w', encoding='utf-8') as f:
                await f.write(new_content)

            # Remove backup on success
            os.remove(backup_path)

            # Generate preview (show changed lines)
            old_lines = content.split('\n')
            new_lines = new_content.split('\n')

            preview_lines = []
            for i, (old_line, new_line) in enumerate(zip(old_lines, new_lines), 1):
                if old_line != new_line:
                    preview_lines.append(f"Line {i}:")
                    preview_lines.append(f"  - {old_line}")
                    preview_lines.append(f"  + {new_line}")

            # Limit preview to first 10 changed lines
            if len(preview_lines) > 30:
                preview_lines = preview_lines[:30] + [f"... ({len(preview_lines)//3 - 10} more changes)"]

            return {
                "success": True,
                "file": file_path,
                "replacements": replacements,
                "preview": '\n'.join(preview_lines) if preview_lines else "No changes to display"
            }

        except UnicodeDecodeError:
            # Restore from backup
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, full_path)
                os.remove(backup_path)
            raise ValueError("File appears to be binary (not text)")

        except Exception as e:
            # Restore from backup on any error
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, full_path)
                os.remove(backup_path)
            raise RuntimeError(f"Failed to edit file: {str(e)}")
