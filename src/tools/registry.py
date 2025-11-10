"""
Tool Registry
Manages tool registration, validation, and execution
"""
from typing import Dict, Any, Callable, List
from abc import ABC, abstractmethod


class Tool(ABC):
    """Base class for all tools"""
    
    def __init__(self, name: str = None, description: str = None):
        self._name = name
        self._description = description

    def get_name(self) -> str:
        """Return tool name"""
        return self._name if self._name else self.__class__.__name__.replace("Tool", "").lower()

    def get_description(self) -> str:
        """Return tool description"""
        return self._description if self._description else "No description available"

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute tool with provided arguments"""
        pass

    def validate_workspace(self, path: str, workspace_root: str) -> bool:
        """
        Validate that path is within workspace (security check)

        Args:
            path: Path to validate
            workspace_root: Root workspace directory

        Returns:
            True if path is safe
        """
        import os
        abs_path = os.path.abspath(path)
        abs_workspace = os.path.abspath(workspace_root)
        return abs_path.startswith(abs_workspace)


class ToolRegistry:
    """Registry for managing available tools"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool"""
        self.tools[tool.get_name()] = tool

    def get_tool(self, name: str) -> Tool:
        """Get tool by name"""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found")
        return self.tools[name]

    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self.tools.keys())
