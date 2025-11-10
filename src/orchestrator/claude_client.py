"""
Claude API Client
Wrapper around Anthropic SDK for agent interactions
"""
from anthropic import AsyncAnthropic
from typing import List, Dict, Any, AsyncIterator, Optional
import os
import json


class ClaudeClient:
    """Client for Claude API interactions"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.client = AsyncAnthropic(api_key=self.api_key)

        # Model configurations
        self.models = {
            "sonnet": "claude-sonnet-4-20250514",
            "haiku": "claude-haiku-4-20250223"
        }

    async def create_message(
        self,
        model: str,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        stream: bool = False
    ) -> Any:
        """
        Create message with Claude

        Args:
            model: Model name ("sonnet" or "haiku" or full model ID)
            system_prompt: System prompt
            messages: List of message dictionaries
            tools: List of tool definitions
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream response

        Returns:
            Message object or stream
        """
        # Resolve model name
        model_id = self.models.get(model, model)

        # Build request parameters
        params = {
            "model": model_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": messages
        }

        # Add tools if provided
        if tools:
            params["tools"] = tools

        # Create message
        if stream:
            return await self.client.messages.create(**params, stream=True)
        else:
            return await self.client.messages.create(**params)

    async def stream_message(
        self,
        model: str,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream message with Claude

        Args:
            Same as create_message

        Yields:
            Parsed event dictionaries
        """
        stream = await self.create_message(
            model=model,
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )

        async for event in stream:
            yield self._parse_stream_event(event)

    def _parse_stream_event(self, event: Any) -> Dict[str, Any]:
        """Parse streaming event"""
        event_type = event.type

        if event_type == "message_start":
            return {
                "type": "message_start",
                "message": event.message
            }

        elif event_type == "content_block_start":
            return {
                "type": "content_start",
                "index": event.index,
                "content_block": event.content_block
            }

        elif event_type == "content_block_delta":
            delta = event.delta

            if delta.type == "text_delta":
                return {
                    "type": "text",
                    "text": delta.text,
                    "index": event.index
                }
            elif delta.type == "input_json_delta":
                return {
                    "type": "tool_input",
                    "partial_json": delta.partial_json,
                    "index": event.index
                }

        elif event_type == "content_block_stop":
            return {
                "type": "content_stop",
                "index": event.index
            }

        elif event_type == "message_delta":
            return {
                "type": "message_delta",
                "delta": event.delta,
                "usage": event.usage
            }

        elif event_type == "message_stop":
            return {
                "type": "message_stop"
            }

        return {
            "type": "unknown",
            "raw": str(event)
        }

    def build_tool_definitions(self, tools: List[Any]) -> List[Dict[str, Any]]:
        """
        Convert Tool objects to Claude API format

        Args:
            tools: List of Tool instances

        Returns:
            List of tool definitions for Claude API
        """
        tool_defs = []

        for tool in tools:
            # Basic tool definition
            tool_def = {
                "name": tool.get_name(),
                "description": tool.get_description(),
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }

            # Add specific properties based on tool type
            if tool.get_name() == "Grep":
                tool_def["input_schema"]["properties"] = {
                    "workspace_path": {"type": "string", "description": "Workspace root path"},
                    "pattern": {"type": "string", "description": "Regex pattern to search"},
                    "path": {"type": "string", "description": "Path to search within"},
                    "case_sensitive": {"type": "boolean", "description": "Case sensitive search"},
                }
                tool_def["input_schema"]["required"] = ["workspace_path", "pattern"]

            elif tool.get_name() == "Glob":
                tool_def["input_schema"]["properties"] = {
                    "workspace_path": {"type": "string", "description": "Workspace root path"},
                    "pattern": {"type": "string", "description": "Glob pattern (e.g., '**/*.py')"}
                }
                tool_def["input_schema"]["required"] = ["workspace_path", "pattern"]

            elif tool.get_name() == "Read":
                tool_def["input_schema"]["properties"] = {
                    "workspace_path": {"type": "string", "description": "Workspace root path"},
                    "file_path": {"type": "string", "description": "File to read (relative path)"},
                    "start_line": {"type": "integer", "description": "Starting line (optional)"},
                    "end_line": {"type": "integer", "description": "Ending line (optional)"}
                }
                tool_def["input_schema"]["required"] = ["workspace_path", "file_path"]

            elif tool.get_name() == "Edit":
                tool_def["input_schema"]["properties"] = {
                    "workspace_path": {"type": "string", "description": "Workspace root path"},
                    "file_path": {"type": "string", "description": "File to edit"},
                    "old_string": {"type": "string", "description": "String to find"},
                    "new_string": {"type": "string", "description": "Replacement string"},
                    "replace_all": {"type": "boolean", "description": "Replace all occurrences"}
                }
                tool_def["input_schema"]["required"] = ["workspace_path", "file_path", "old_string", "new_string"]

            elif tool.get_name() == "Bash":
                tool_def["input_schema"]["properties"] = {
                    "workspace_path": {"type": "string", "description": "Workspace root path"},
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds"}
                }
                tool_def["input_schema"]["required"] = ["workspace_path", "command"]

            elif tool.get_name() == "Git":
                tool_def["input_schema"]["properties"] = {
                    "workspace_path": {"type": "string", "description": "Workspace root path"},
                    "repo_name": {"type": "string", "description": "Repository name"},
                    "operation": {"type": "string", "description": "Operation: status, diff, commit, push"},
                    "message": {"type": "string", "description": "Commit message (for commit)"},
                    "phase": {"type": "string", "description": "Current phase"},
                    "project_id": {"type": "string", "description": "Project ID"}
                }
                tool_def["input_schema"]["required"] = ["workspace_path", "repo_name", "operation"]

            elif tool.get_name() == "TodoWrite":
                tool_def["input_schema"]["properties"] = {
                    "project_id": {"type": "string", "description": "Project identifier"},
                    "todos": {
                        "type": "array",
                        "description": "List of todo items",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                                "activeForm": {"type": "string"}
                            },
                            "required": ["content", "status", "activeForm"]
                        }
                    }
                }
                tool_def["input_schema"]["required"] = ["project_id", "todos"]

            elif tool.get_name() == "AskUser":
                tool_def["input_schema"]["properties"] = {
                    "project_id": {"type": "string", "description": "Project identifier"},
                    "question": {"type": "string", "description": "Question text (max 15 words)"},
                    "choices": {
                        "type": "array",
                        "description": "2-4 choice options",
                        "items": {"type": "string"}
                    },
                    "image_url": {"type": "string", "description": "Optional image URL"}
                }
                tool_def["input_schema"]["required"] = ["project_id", "question", "choices"]

            tool_defs.append(tool_def)

        return tool_defs
