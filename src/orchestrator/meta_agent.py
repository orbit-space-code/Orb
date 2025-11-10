"""
Meta-Agent / Orchestrator
Coordinates three-phase workflow: Research → Planning → Implementation
"""
from typing import List, Dict, Any, Optional
import asyncio
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MetaAgentError(Exception):
    """Custom exception for MetaAgent errors"""
    pass


class MetaAgent:
    """
    Meta-agent that orchestrates the three-phase AI development workflow
    Manages agent lifecycle, task creation, and event publishing
    """

    def __init__(self, agent_executor, redis_client, workspace_manager, file_manager, pr_service=None, db_client=None):
        self.agent_executor = agent_executor
        self.redis_client = redis_client
        self.workspace_manager = workspace_manager
        self.file_manager = file_manager
        self.pr_service = pr_service
        self.db_client = db_client
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

            # Create pull request if PR service is available
            if self.pr_service:
                asyncio.create_task(
                    self._create_pull_request_for_project(
                        project_id, workspace_path, implementation_summary
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

    async def _create_pull_request_for_project(
        self, project_id: str, workspace_path: str, implementation_summary: str = None
    ):
        """Create pull request after implementation completion using real automation service"""
        try:
            from ..github.pr_automation import PRAutomationService
            
            logger.info(f"Creating pull request for project {project_id}")
            
            # Publish PR creation start event
            await self._publish_event(
                project_id,
                "pr_creation",
                {
                    "status": "started",
                    "message": "Creating pull request...",
                },
            )
            
            # Get implementation summary
            if not implementation_summary:
                try:
                    # Try to get from planning.md first
                    planning_content = await self.file_manager.read_planning(project_id)
                    if planning_content:
                        lines = planning_content.split('\n')
                        for line in lines:
                            if line.strip() and not line.startswith('#'):
                                implementation_summary = line.strip()[:200]
                                break
                    
                    # Fallback to project description
                    if not implementation_summary and self.db_client:
                        project_data = await self.db_client.project.findUnique({
                            'where': {'id': project_id}
                        })
                        implementation_summary = project_data.get('description', 'Feature implementation')
                        
                except Exception as e:
                    logger.warning(f"Could not get implementation summary: {e}")
                    implementation_summary = "AI-generated feature implementation"
            
            # Create PR automation service
            pr_automation = PRAutomationService(self.pr_service, self.db_client)
            
            # Create PRs for all repositories in the project
            pr_results = await pr_automation.create_prs_for_project(
                project_id=project_id,
                workspace_path=workspace_path,
                implementation_summary=implementation_summary,
                agent_recommendations=None  # Could be enhanced to collect from agents
            )
            
            # Publish results
            if pr_results.get('successful_prs', 0) > 0 or pr_results.get('failed_prs', 0) > 0:
                await self._publish_event(
                    project_id,
                    "pr_creation",
                    {
                        "status": "completed",
                        "message": pr_results.get('summary', 'PR creation completed'),
                        "pull_requests": pr_results.get('results', []),
                        "successful": pr_results.get('successful_prs', 0),
                        "failed": pr_results.get('failed_prs', 0),
                        "total_repositories": pr_results.get('total_repositories', 0)
                    },
                )
                
                # Update project status
                await self._update_project_status_with_prs(project_id, pr_results.get('results', []))
            else:
                await self._publish_event(
                    project_id,
                    "pr_creation",
                    {
                        "status": "skipped",
                        "message": "No changes found to create pull requests",
                    },
                )
            
        except Exception as e:
            logger.error(f"Failed to create pull request for project {project_id}: {e}")
            await self._publish_event(
                project_id,
                "pr_creation",
                {
                    "status": "failed",
                    "error": str(e),
                    "message": "Pull request creation failed",
                },
            )

    async def _update_project_status_with_prs(self, project_id: str, pr_results: List[Dict[str, Any]]):
        """Update project status to include PR information"""
        try:
            if not self.db_client:
                return
            
            # Store PR creation results in Redis for UI updates
            pr_data = {
                'project_id': project_id,
                'pull_requests': pr_results,
                'created_at': datetime.utcnow().isoformat()
            }
            
            await self.redis_client.set(
                f"project:{project_id}:pull_requests",
                pr_data,
                expiry=86400  # 24 hours
            )
            
            logger.info(f"Updated project {project_id} status with PR information")
            
        except Exception as e:
            logger.error(f"Failed to update project status with PRs: {e}")

    async def handle_pr_creation_failure(self, project_id: str, error: str):
        """Handle PR creation failure gracefully"""
        try:
            logger.warning(f"Handling PR creation failure for project {project_id}: {error}")
            
            # Store failure information
            failure_data = {
                'project_id': project_id,
                'error': error,
                'timestamp': datetime.utcnow().isoformat(),
                'retry_count': 0
            }
            
            await self.redis_client.set(
                f"project:{project_id}:pr_failure",
                failure_data,
                expiry=86400  # 24 hours
            )
            
            # Publish failure event for UI
            await self._publish_event(
                project_id,
                "pr_creation_failure",
                {
                    "error": error,
                    "message": "Pull request creation failed, but implementation is complete",
                    "retry_available": True
                },
            )
            
        except Exception as e:
            logger.error(f"Failed to handle PR creation failure: {e}")

    async def retry_pr_creation(self, project_id: str) -> Dict[str, Any]:
        """Retry PR creation for a project"""
        try:
            logger.info(f"Retrying PR creation for project {project_id}")
            
            # Get failure data
            failure_data = await self.redis_client.get(f"project:{project_id}:pr_failure")
            if not failure_data:
                return {"success": False, "error": "No failed PR creation found"}
            
            # Check retry count
            retry_count = failure_data.get('retry_count', 0)
            if retry_count >= 3:
                return {"success": False, "error": "Maximum retry attempts exceeded"}
            
            # Update retry count
            failure_data['retry_count'] = retry_count + 1
            await self.redis_client.set(
                f"project:{project_id}:pr_failure",
                failure_data,
                expiry=86400
            )
            
            # Get workspace path
            workspace_path = self.file_manager.get_workspace_path(project_id)
            
            # Retry PR creation
            await self._create_pull_request_for_project(project_id, workspace_path)
            
            return {"success": True, "retry_count": retry_count + 1}
            
        except Exception as e:
            logger.error(f"Failed to retry PR creation: {e}")
            return {"success": False, "error": str(e)}
