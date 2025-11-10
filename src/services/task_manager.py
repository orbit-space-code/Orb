"""
Task Manager
Manages tasks and their status for the Orb platform
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid
import asyncio

class TaskStatus(str, Enum):
    """Status of a task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    """Priority of a task"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class TaskDependency:
    """Represents a dependency between tasks"""
    task_id: str
    required_status: TaskStatus = TaskStatus.COMPLETED

@dataclass
class Task:
    """Represents a task in the system"""
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    assignee: Optional[str] = None
    dependencies: List[TaskDependency] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_status(self, status: TaskStatus):
        """Update the task status and timestamps"""
        self.status = status
        self.updated_at = datetime.utcnow()
    
    def add_dependency(self, task_id: str, required_status: TaskStatus = TaskStatus.COMPLETED):
        """Add a dependency to this task"""
        self.dependencies.append(TaskDependency(task_id=task_id, required_status=required_status))
    
    def is_blocked(self, task_registry: 'TaskManager') -> bool:
        """Check if this task is blocked by its dependencies"""
        for dep in self.dependencies:
            task = task_registry.get_task(dep.task_id)
            if not task or task.status != dep.required_status:
                return True
        return False

class TaskManager:
    """Manages tasks and their lifecycle"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()
    
    async def create_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: Optional[datetime] = None,
        assignee: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """Create a new task"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            assignee=assignee,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        async with self._lock:
            self.tasks[task_id] = task
            
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self.tasks.get(task_id)
    
    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Task]:
        """Update a task's status"""
        async with self._lock:
            task = self.tasks.get(task_id)
            if task:
                task.update_status(status)
                if metadata:
                    task.metadata.update(metadata)
                return task
        return None
    
    async def add_dependency(
        self,
        task_id: str,
        depends_on_id: str,
        required_status: TaskStatus = TaskStatus.COMPLETED
    ) -> bool:
        """Add a dependency between tasks"""
        async with self._lock:
            task = self.tasks.get(task_id)
            depends_on = self.tasks.get(depends_on_id)
            
            if not task or not depends_on:
                return False
                
            # Check for circular dependencies
            if self._creates_circular_dependency(task_id, depends_on_id):
                return False
                
            task.add_dependency(depends_on_id, required_status)
            return True
    
    def _creates_circular_dependency(self, task_id: str, depends_on_id: str) -> bool:
        """Check if adding a dependency would create a circular reference"""
        visited = set()
        to_visit = [depends_on_id]
        
        while to_visit:
            current_id = to_visit.pop()
            if current_id == task_id:
                return True
                
            if current_id in visited:
                continue
                
            visited.add(current_id)
            current_task = self.tasks.get(current_id)
            if current_task:
                to_visit.extend(dep.task_id for dep in current_task.dependencies)
                
        return False
    
    async def get_tasks(
        self,
        status: Optional[TaskStatus] = None,
        assignee: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
        tag: Optional[str] = None
    ) -> List[Task]:
        """Get tasks matching the specified filters"""
        result = []
        
        for task in self.tasks.values():
            if status and task.status != status:
                continue
            if assignee and task.assignee != assignee:
                continue
            if priority and task.priority != priority:
                continue
            if tag and tag not in task.tags:
                continue
                
            result.append(task)
            
        return result
    
    async def get_blocked_tasks(self) -> List[Task]:
        """Get all tasks that are currently blocked by their dependencies"""
        return [task for task in self.tasks.values() if task.status == TaskStatus.BLOCKED or task.is_blocked(self)]
    
    async def process_task_queue(self):
        """Process the task queue and update task statuses"""
        while True:
            # Find tasks that are pending but not blocked
            for task in self.tasks.values():
                if task.status == TaskStatus.PENDING and not task.is_blocked(self):
                    task.update_status(TaskStatus.IN_PROGRESS)
                    
            # Check for tasks that are blocked
            for task in self.tasks.values():
                if task.status == TaskStatus.IN_PROGRESS and task.is_blocked(self):
                    task.update_status(TaskStatus.BLOCKED)
                    
            # Sleep for a bit before checking again
            await asyncio.sleep(5)

# Singleton instance
task_manager = TaskManager()
