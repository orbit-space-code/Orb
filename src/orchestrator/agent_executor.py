"""
Agent Execution Framework
Handles agent initialization, tool execution loop, and streaming
"""
from typing import Dict, Any, Optional, List
import asyncio
import uuid
from datetime import datetime
import json

from src.plugins.loader import PluginLoader, AgentDefinition
from src.orchestrator.claude_client import ClaudeClient
from src.orchestrator.redis_client import RedisClient
from src.tools.registry import ToolRegistry
from src.tools.grep_tool import GrepTool
from src.tools.glob_tool import GlobTool
from src.tools.read_tool import ReadTool
from src.tools.edit_tool import EditTool
from src.tools.bash_tool import BashTool
from src.tools.git_tool import GitTool
from src.tools.todo_tool import TodoWriteTool
from src.tools.ask_user_tool import AskUserTool
from src.tools.semantic_search_tool import SemanticSearchTool
from src.tools.dependency_analyzer_tool import DependencyAnalyzerTool
from src.tools.architecture_analyzer_tool import ArchitectureAnalyzerTool
from src.tools.refactor_tool import RefactorTool
from src.tools.test_generator_tool import TestGeneratorTool
from src.tools.code_review_tool import CodeReviewTool
from src.files.manager import FileManager


class AgentExecutor:
    """Executes agents with tool calling and streaming"""

    def __init__(
        self,
        plugin_loader: PluginLoader,
        claude_client: ClaudeClient,
        redis_client: RedisClient,
        file_manager: FileManager
    ):
        self.plugin_loader = plugin_loader
        self.claude = claude_client
        self.redis = redis_client
        self.file_manager = file_manager

        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self):
        """Register all available tools"""
        # Basic tools
        self.tool_registry.register(GrepTool())
        self.tool_registry.register(GlobTool())
        self.tool_registry.register(ReadTool())
        self.tool_registry.register(EditTool())
        self.tool_registry.register(BashTool())
        self.tool_registry.register(GitTool())
        self.tool_registry.register(TodoWriteTool(self.redis))
        self.tool_registry.register(AskUserTool(self.redis))
        
        # Advanced research tools
        self.tool_registry.register(SemanticSearchTool())
        self.tool_registry.register(DependencyAnalyzerTool())
        self.tool_registry.register(ArchitectureAnalyzerTool())
        
        # Advanced implementation tools
        self.tool_registry.register(RefactorTool())
        self.tool_registry.register(TestGeneratorTool())
        self.tool_registry.register(CodeReviewTool())

    async def execute_agent(
        self,
        task_id: str,
        agent_name: str,
        project_id: str,
        phase: str,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute agent with tool calling loop

        Args:
            task_id: Task identifier (passed from meta-agent)
            agent_name: Name of agent to execute
            project_id: Project identifier
            phase: Current phase (research/planning/implementation)
            inputs: Agent inputs (feature_request, etc.)

        Returns:
            Result dictionary
        """
        # Load agent definition
        agent_def = self.plugin_loader.get_agent(agent_name)
        if not agent_def:
            raise ValueError(f"Agent not found: {agent_name}")

        # Execute agent and return result
        return await self._run_agent(
            task_id=task_id,
            agent_def=agent_def,
            project_id=project_id,
            phase=phase,
            inputs=inputs
        )

    async def _run_agent(
        self,
        task_id: str,
        agent_def: AgentDefinition,
        project_id: str,
        phase: str,
        inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run agent execution loop"""
        try:

            # Get workspace path
            workspace_path = self.file_manager.get_workspace_path(project_id)

            # Build system prompt from agent definition
            system_prompt = self._build_system_prompt(agent_def, project_id, workspace_path, inputs)

            # Get tools for this agent
            tools = self._get_agent_tools(agent_def)

            # Build tool definitions for Claude
            tool_defs = self.claude.build_tool_definitions(tools)

            # Initialize conversation
            messages: List[Dict[str, Any]] = [
                {
                    "role": "user",
                    "content": self._build_initial_message(inputs)
                }
            ]

            # Publish start event
            await self._publish_event(project_id, "agent_start", {
                "task_id": task_id,
                "agent": agent_def.name,
                "phase": phase
            })

            # Main agent loop
            max_iterations = 50  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1

                # Call Claude
                response = await self.claude.create_message(
                    model=agent_def.model,
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=tool_defs,
                    max_tokens=4096
                )

                # Add assistant response to messages
                assistant_message = {
                    "role": "assistant",
                    "content": response.content
                }
                messages.append(assistant_message)

                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Agent finished
                    break

                elif response.stop_reason == "tool_use":
                    # Execute tools
                    tool_results = await self._execute_tools(
                        response.content,
                        project_id,
                        workspace_path
                    )

                    # Add tool results to messages
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })

                elif response.stop_reason == "max_tokens":
                    # Continue conversation
                    continue

                else:
                    break

            # Extract final text content
            final_output = self._extract_text_content(messages)

            # Publish completion event
            await self._publish_event(project_id, "agent_complete", {
                "task_id": task_id,
                "agent": agent_def.name,
                "iterations": iteration
            })

            # Return result
            return {
                "success": True,
                "output": final_output,
                "iterations": iteration
            }

        except Exception as e:
            # Publish error event
            await self._publish_event(project_id, "agent_error", {
                "task_id": task_id,
                "error": str(e)
            })

            # Raise exception to be handled by caller
            raise

    def _build_system_prompt(
        self,
        agent_def: AgentDefinition,
        project_id: str,
        workspace_path: str,
        inputs: Dict[str, Any]
    ) -> str:
        """Build system prompt for agent"""
        prompt = agent_def.instructions

        # Add context
        context = f"""

## Execution Context

- **Project ID:** {project_id}
- **Workspace Path:** {workspace_path}
- **Feature Request:** {inputs.get('feature_request', 'N/A')}

"""
        return prompt + context

    def _build_initial_message(self, inputs: Dict[str, Any]) -> str:
        """Build initial user message"""
        feature_request = inputs.get('feature_request', '')

        return f"""Begin your work.

Feature Request: {feature_request}

Follow your instructions systematically. Use the tools available to you."""

    def _get_agent_tools(self, agent_def: AgentDefinition) -> List:
        """Get tool instances for agent"""
        tools = []

        for tool_name in agent_def.tools:
            try:
                tool = self.tool_registry.get_tool(tool_name)
                tools.append(tool)
            except ValueError:
                print(f"Warning: Tool '{tool_name}' not found")

        return tools

    async def _execute_tools(
        self,
        content: List[Any],
        project_id: str,
        workspace_path: str
    ) -> List[Dict[str, Any]]:
        """Execute tool calls and return results"""
        tool_results = []

        for block in content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                # Publish tool use event
                await self._publish_event(project_id, "tool_use", {
                    "tool": tool_name,
                    "input": tool_input
                })

                try:
                    # Get tool
                    tool = self.tool_registry.get_tool(tool_name)

                    # Ask-before-build approval gate for risky tools
                    risky_tools = {"edit", "bash", "git", "refactor", "testgenerator"}
                    normalized_tool = (tool_name or "").lower()
                    if normalized_tool in risky_tools:
                        try:
                            ask_tool = self.tool_registry.get_tool("AskUser")
                            # Build concise question with redacted/trimmed input
                            try:
                                summarized_input = json.dumps(tool_input)[:800]
                            except Exception:
                                summarized_input = str(tool_input)[:800]

                            question = (
                                f"Approve the following tool action?\n\n"
                                f"Tool: {tool_name}\n"
                                f"Workspace: {workspace_path}\n"
                                f"Input: {summarized_input}"
                            )
                            approval = await ask_tool.execute(
                                project_id=project_id,
                                question=question,
                                choices=["Approve", "Reject", "Modify plan"],
                                image_url=None,
                                timeout=300
                            )

                            decision = (approval or {}).get("answer", "Reject")
                            if decision != "Approve":
                                # Publish user-declined event
                                await self._publish_event(project_id, "tool_skipped", {
                                    "tool": tool_name,
                                    "reason": f"User decision: {decision}"
                                })
                                # Return a tool_result back to the model so it can adapt
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": tool_use_id,
                                    "content": json.dumps({
                                        "status": "skipped",
                                        "reason": f"User decision: {decision}",
                                    }, indent=2)
                                })
                                continue
                        except Exception:
                            # If AskUser is unavailable, default to safety: skip risky action
                            await self._publish_event(project_id, "tool_skipped", {
                                "tool": tool_name,
                                "reason": "AskUser unavailable; skipping risky action"
                            })
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": json.dumps({
                                    "status": "skipped",
                                    "reason": "AskUser unavailable; skipping risky action",
                                }, indent=2)
                            })
                            continue

                    # Execute tool
                    result = await tool.execute(**tool_input)

                    # Publish tool result event
                    await self._publish_event(project_id, "tool_result", {
                        "tool": tool_name,
                        "success": True
                    })

                    # Add to results
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(result, indent=2)
                    })

                except Exception as e:
                    # Publish tool error event
                    await self._publish_event(project_id, "tool_error", {
                        "tool": tool_name,
                        "error": str(e)
                    })

                    # Add error to results
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": f"Error: {str(e)}",
                        "is_error": True
                    })

        return tool_results

    async def _publish_event(
        self,
        project_id: str,
        event_type: str,
        data: Dict[str, Any]
    ):
        """Publish event to Redis for SSE streaming"""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }

        await self.redis.publish(f"project:{project_id}:events", event)

    def _extract_text_content(self, messages: List[Dict[str, Any]]) -> str:
        """Extract text content from message history"""
        text_parts = []

        for msg in messages:
            if msg["role"] == "assistant":
                content = msg.get("content", [])

                if isinstance(content, list):
                    for block in content:
                        if hasattr(block, 'type') and block.type == "text":
                            text_parts.append(block.text)
                        elif isinstance(block, dict) and block.get("type") == "text":
                            text_parts.append(block.get("text", ""))

        return "\n\n".join(text_parts)
