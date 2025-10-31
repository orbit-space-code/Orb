"""
Meta-Agent / Orchestrator
Coordinates three-phase workflow: Research → Planning → Implementation
"""
from typing import List, Dict, Any, Optional
import asyncio
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MetaAgentError(Exception):
    """Custom exception for MetaAgent errors"""
    pass


class MetaAgent:
    """
    Meta-agent that orchestrates the three-phase AI development workflow
    Manages agent lifecycle, task creation, and event publishing
    """

    def __init__(self, agent_executor, redis_client, workspace_manager, file_manager):
        self.agent_executor = agent_executor
        self.redis_client = redis_client
        self.workspace_manager = workspace_manager
        self.file_manager = file_manager
        self.active_tasks: Dict[str, Any] = {}

    async def _create_task(
        self, project_id: str, agent_name: str, phase: str, user_id: str
    ) -> str:
        """Create and register a new task"""
        try:
            task_id = str(uuid.uuid4())
            task_data = {
                "task_id": task_id,
                "project_id": project_id,
                "agent_name": agent_name,
                "phase": phase,
                "user_id": user_id,
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
            }

            # Store task in Redis
            await self.redis_client.set(f"task:{task_id}", task_data, expiry=86400)
            self.active_tasks[task_id] = task_data

            logger.info(f"Created task {task_id} for {agent_name} in phase {phase}")
            return task_id

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise MetaAgentError(f"Task creation failed: {e}")

    async def _publish_event(
        self, project_id: str, event_type: str, data: Dict[str, Any]
    ):
        """Publish event to Redis for SSE streaming"""
        try:
            event_data = {
                "type": event_type,
                "project_id": project_id,
                "timestamp": datetime.utcnow().isoformat(),
                **data,
            }

            await self.redis_client.publish(
                f"project:{project_id}:events", event_data
            )

            logger.debug(f"Published {event_type} event for project {project_id}")

        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
            # Don't fail the whole operation if event publishing fails

    async def start_research_phase(
        self, project_id: str, user_id: str, feature_request: str
    ) -> Dict[str, Any]:
        """
        Start research phase
        - Creates task
        - Loads research-agent
        - Executes agent asynchronously
        - Publishes events
        """
        try:
            logger.info(f"Starting research phase for project {project_id}")

            # Get workspace path
            workspace_path = self.file_manager.get_workspace_path(project_id)

            # Publish phase start event
            await self._publish_event(
                project_id,
                "phase",
                {
                    "phase": "RESEARCH",
                    "status": "started",
                    "message": "Starting codebase analysis...",
                },
            )

            # Create task
            task_id = await self._create_task(
                project_id, "research-agent", "RESEARCH", user_id
            )

            # Run agent asynchronously
            asyncio.create_task(
                self._run_research_agent(
                    task_id, project_id, workspace_path, feature_request
                )
            )

            return {"task_id": task_id, "phase": "RESEARCH", "status": "started"}

        except Exception as e:
            logger.error(f"Failed to start research phase: {e}")
            await self._publish_event(
                project_id,
                "error",
                {
                    "phase": "RESEARCH",
                    "error": str(e),
                    "message": "Research phase failed to start",
                },
            )
            raise MetaAgentError(f"Research phase failed: {e}")

    async def _run_research_agent(
        self, task_id: str, project_id: str, workspace_path: str, feature_request: str
    ):
        """Execute research agent and handle completion"""
        try:
            logger.info(f"Executing research agent for task {task_id}")

            # Update task status
            await self.redis_client.set(
                f"task:{task_id}", {"status": "active"}, expiry=86400
            )

            # Execute agent
            result = await self.agent_executor.execute_agent(
                task_id=task_id,
                agent_name="research-agent",
                project_id=project_id,
                phase="RESEARCH",
                inputs={
                    "feature_request": feature_request,
                    "workspace_path": workspace_path,
                },
            )

            # Verify research.md was created
            research_content = await self.file_manager.read_research(project_id)
            if not research_content:
                raise MetaAgentError("Research agent did not create research.md")

            # Update task to completed
            await self.redis_client.set(
                f"task:{task_id}", {"status": "completed"}, expiry=86400
            )

            # Publish completion event
            await self._publish_event(
                project_id,
                "phase",
                {
                    "phase": "RESEARCH",
                    "status": "completed",
                    "message": "Research phase complete. Ready for planning.",
                    "task_id": task_id,
                },
            )

            logger.info(f"Research agent completed successfully for task {task_id}")

        except Exception as e:
            logger.error(f"Research agent failed: {e}")
            await self.redis_client.set(
                f"task:{task_id}", {"status": "failed", "error": str(e)}, expiry=86400
            )
            await self._publish_event(
                project_id,
                "error",
                {"phase": "RESEARCH", "task_id": task_id, "error": str(e)},
            )

    async def start_planning_phase(
        self, project_id: str, user_id: str
    ) -> Dict[str, Any]:
        """
        Start planning phase
        - Reads research.md
        - Loads planning-agent
        - Handles questions via AskUserTool
        - Creates planning.md
        """
        try:
            logger.info(f"Starting planning phase for project {project_id}")

            # Verify research.md exists
            research_content = await self.file_manager.read_research(project_id)
            if not research_content:
                raise MetaAgentError(
                    "Research phase not complete - research.md not found"
                )

            workspace_path = self.file_manager.get_workspace_path(project_id)

            # Publish phase start event
            await self._publish_event(
                project_id,
                "phase",
                {
                    "phase": "PLANNING",
                    "status": "started",
                    "message": "Creating implementation plan...",
                },
            )

            # Create task
            task_id = await self._create_task(
                project_id, "planning-agent", "PLANNING", user_id
            )

            # Run agent asynchronously
            asyncio.create_task(
                self._run_planning_agent(task_id, project_id, workspace_path)
            )

            return {"task_id": task_id, "phase": "PLANNING", "status": "started"}

        except Exception as e:
            logger.error(f"Failed to start planning phase: {e}")
            await self._publish_event(
                project_id, "error", {"phase": "PLANNING", "error": str(e)}
            )
            raise MetaAgentError(f"Planning phase failed: {e}")

    async def _run_planning_agent(
        self, task_id: str, project_id: str, workspace_path: str
    ):
        """Execute planning agent"""
        try:
            logger.info(f"Executing planning agent for task {task_id}")

            await self.redis_client.set(
                f"task:{task_id}", {"status": "active"}, expiry=86400
            )

            # Execute agent
            result = await self.agent_executor.execute_agent(
                task_id=task_id,
                agent_name="planning-agent",
                project_id=project_id,
                phase="PLANNING",
                inputs={"workspace_path": workspace_path},
            )

            # Verify planning.md was created
            planning_content = await self.file_manager.read_planning(project_id)
            if not planning_content:
                raise MetaAgentError("Planning agent did not create planning.md")

            await self.redis_client.set(
                f"task:{task_id}", {"status": "completed"}, expiry=86400
            )

            await self._publish_event(
                project_id,
                "phase",
                {
                    "phase": "PLANNING",
                    "status": "completed",
                    "message": "Planning complete. Ready for implementation.",
                    "task_id": task_id,
                },
            )

            logger.info(f"Planning agent completed successfully for task {task_id}")

        except Exception as e:
            logger.error(f"Planning agent failed: {e}")
            await self.redis_client.set(
                f"task:{task_id}", {"status": "failed", "error": str(e)}, expiry=86400
            )
            await self._publish_event(
                project_id,
                "error",
                {"phase": "PLANNING", "task_id": task_id, "error": str(e)},
            )

    async def start_implementation_phase(
        self, project_id: str, user_id: str
    ) -> Dict[str, Any]:
        """
        Start implementation phase
        - Reads planning.md
        - Spawns implementation agent
        - Spawns 3 overwatcher agents in parallel
        - Coordinates execution
        """
        try:
            logger.info(f"Starting implementation phase for project {project_id}")

            # Verify planning.md exists
            planning_content = await self.file_manager.read_planning(project_id)
            if not planning_content:
                raise MetaAgentError(
                    "Planning phase not complete - planning.md not found"
                )

            workspace_path = self.file_manager.get_workspace_path(project_id)

            # Publish phase start event
            await self._publish_event(
                project_id,
                "phase",
                {
                    "phase": "IMPLEMENTATION",
                    "status": "started",
                    "message": "Starting implementation...",
                },
            )

            # Create main task
            task_id = await self._create_task(
                project_id, "implementation-agent", "IMPLEMENTATION", user_id
            )

            # Run implementation with overwatchers
            asyncio.create_task(
                self._run_implementation_with_overwatchers(
                    task_id, project_id, workspace_path, user_id
                )
            )

            return {"task_id": task_id, "phase": "IMPLEMENTATION", "status": "started"}

        except Exception as e:
            logger.error(f"Failed to start implementation phase: {e}")
            await self._publish_event(
                project_id, "error", {"phase": "IMPLEMENTATION", "error": str(e)}
            )
            raise MetaAgentError(f"Implementation phase failed: {e}")

    async def _run_implementation_with_overwatchers(
        self, task_id: str, project_id: str, workspace_path: str, user_id: str
    ):
        """Execute implementation agent with parallel overwatchers"""
        try:
            logger.info(f"Executing implementation with overwatchers for task {task_id}")

            await self.redis_client.set(
                f"task:{task_id}", {"status": "active"}, expiry=86400
            )

            # Spawn overwatcher tasks
            overwatcher_tasks = []

            for agent_name in ["review-agent", "security-agent", "test-agent"]:
                overwatcher_task_id = await self._create_task(
                    project_id, agent_name, "IMPLEMENTATION", user_id
                )
                overwatcher_tasks.append(overwatcher_task_id)

                # Start overwatcher asynchronously
                asyncio.create_task(
                    self._run_overwatcher(
                        overwatcher_task_id, agent_name, project_id, workspace_path
                    )
                )

            # Execute main implementation agent
            result = await self.agent_executor.execute_agent(
                task_id=task_id,
                agent_name="implementation-agent",
                project_id=project_id,
                phase="IMPLEMENTATION",
                inputs={"workspace_path": workspace_path},
            )

            # Mark main task complete
            await self.redis_client.set(
                f"task:{task_id}", {"status": "completed"}, expiry=86400
            )

            # Publish completion event
            await self._publish_event(
                project_id,
                "phase",
                {
                    "phase": "IMPLEMENTATION",
                    "status": "completed",
                    "message": "Implementation complete!",
                    "task_id": task_id,
                },
            )

            # Spawn documentation agent post-implementation
            doc_task_id = await self._create_task(
                project_id, "documentation-agent", "IMPLEMENTATION", user_id
            )
            asyncio.create_task(
                self._run_overwatcher(
                    doc_task_id, "documentation-agent", project_id, workspace_path
                )
            )

            logger.info(f"Implementation completed successfully for task {task_id}")

        except Exception as e:
            logger.error(f"Implementation failed: {e}")
            await self.redis_client.set(
                f"task:{task_id}", {"status": "failed", "error": str(e)}, expiry=86400
            )
            await self._publish_event(
                project_id,
                "error",
                {"phase": "IMPLEMENTATION", "task_id": task_id, "error": str(e)},
            )

    async def _run_overwatcher(
        self, task_id: str, agent_name: str, project_id: str, workspace_path: str
    ):
        """Execute an overwatcher agent"""
        try:
            logger.info(f"Executing overwatcher {agent_name} for task {task_id}")

            await self.redis_client.set(
                f"task:{task_id}", {"status": "active"}, expiry=86400
            )

            result = await self.agent_executor.execute_agent(
                task_id=task_id,
                agent_name=agent_name,
                project_id=project_id,
                phase="IMPLEMENTATION",
                inputs={"workspace_path": workspace_path},
            )

            await self.redis_client.set(
                f"task:{task_id}", {"status": "completed"}, expiry=86400
            )

            await self._publish_event(
                project_id,
                "log",
                {
                    "message": f"{agent_name} completed",
                    "level": "info",
                    "task_id": task_id,
                },
            )

            logger.info(f"Overwatcher {agent_name} completed for task {task_id}")

        except Exception as e:
            logger.error(f"Overwatcher {agent_name} failed: {e}")
            await self.redis_client.set(
                f"task:{task_id}", {"status": "failed", "error": str(e)}, expiry=86400
            )

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task"""
        try:
            task_data = await self.redis_client.get(f"task:{task_id}")
            return task_data
        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            return None

    async def monitor_execution(self, task_id: str) -> Dict[str, Any]:
        """Monitor agent execution status"""
        return await self.get_task_status(task_id)

    async def aggregate_results(self, task_ids: List[str]) -> Dict[str, Any]:
        """Aggregate results from multiple agents"""
        results = {}
        for task_id in task_ids:
            status = await self.get_task_status(task_id)
            if status:
                results[task_id] = status
        return results
