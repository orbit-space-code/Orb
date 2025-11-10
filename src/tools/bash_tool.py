"""
Bash Tool
Execute shell commands with security restrictions
"""
import subprocess
import os
from typing import Dict
from src.tools.registry import Tool


class BashTool(Tool):
    """Execute shell commands with security restrictions"""

    def get_name(self) -> str:
        return "Bash"

    def get_description(self) -> str:
        return "Execute shell commands with timeout and command restrictions"

    def __init__(self):
        # Get allowed commands from environment
        allowed = os.getenv("ALLOWED_BASH_COMMANDS", "ls,cat,grep,git,npm,python,node,pytest,jest")
        self.allowed_commands = set(allowed.split(','))

        # Commands that are never allowed
        self.blocked_commands = {
            'rm', 'rmdir', 'del', 'format', 'mkfs',
            'dd', 'fdisk', 'parted',
            'shutdown', 'reboot', 'halt',
            'sudo', 'su',
            'curl', 'wget', 'nc', 'netcat',  # Network commands
        }

        # Get timeout from environment
        self.timeout = int(os.getenv("BASH_TIMEOUT_SECONDS", "60"))

    async def execute(
        self,
        workspace_path: str,
        command: str,
        timeout: int = None
    ) -> Dict[str, any]:
        """
        Execute bash command

        Args:
            workspace_path: Root workspace directory
            command: Command to execute
            timeout: Timeout in seconds (default from env)

        Returns:
            Dictionary with stdout, stderr, exit_code
        """
        # Validate workspace path
        if not self.validate_workspace(workspace_path, workspace_path):
            raise ValueError("Invalid workspace path")

        if not os.path.exists(workspace_path):
            raise ValueError(f"Workspace does not exist: {workspace_path}")

        # Extract base command
        base_command = command.strip().split()[0] if command.strip() else ""

        # Security checks
        if not base_command:
            raise ValueError("Empty command")

        # Check if command is blocked
        if base_command in self.blocked_commands:
            raise ValueError(f"Command '{base_command}' is blocked for security reasons")

        # Check if command is allowed
        if base_command not in self.allowed_commands:
            raise ValueError(
                f"Command '{base_command}' is not in the allowed list: "
                f"{', '.join(sorted(self.allowed_commands))}"
            )

        # Additional dangerous pattern checks
        dangerous_patterns = [
            'rm -rf /',
            'rm -rf *',
            '> /dev/',
            'mkfs',
            'dd if=',
            ':(){ :|:& };:',  # Fork bomb
        ]

        for pattern in dangerous_patterns:
            if pattern in command:
                raise ValueError(f"Command contains dangerous pattern: {pattern}")

        # Use provided timeout or default
        exec_timeout = timeout if timeout is not None else self.timeout

        try:
            # Execute command in workspace directory
            result = subprocess.run(
                command,
                shell=True,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=exec_timeout,
                env={
                    **os.environ,
                    'PWD': workspace_path,
                    'HOME': workspace_path,
                }
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }

        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Command timed out after {exec_timeout} seconds")
        except Exception as e:
            raise RuntimeError(f"Failed to execute command: {str(e)}")
