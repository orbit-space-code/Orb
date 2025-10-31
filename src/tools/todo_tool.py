"""
TodoWrite Tool
Manage agent task lists
"""
from typing import List, Dict
import json
from src.tools.registry import Tool


class TodoWriteTool(Tool):
    """Manage agent task lists"""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

    def get_name(self) -> str:
        return "TodoWrite"

    def get_description(self) -> str:
        return "Manage task lists with status tracking (pending/in_progress/completed)"

    async def execute(
        self,
        project_id: str,
        todos: List[Dict[str, str]]
    ) -> Dict[str, any]:
        """
        Update todo list

        Args:
            project_id: Project identifier
            todos: List of todo items with 'content', 'status', 'activeForm'

        Returns:
            Success confirmation with todo count
        """
        # Validate todos structure
        for i, todo in enumerate(todos):
            if 'content' not in todo:
                raise ValueError(f"Todo {i} missing 'content' field")
            if 'status' not in todo:
                raise ValueError(f"Todo {i} missing 'status' field")
            if 'activeForm' not in todo:
                raise ValueError(f"Todo {i} missing 'activeForm' field")

            # Validate status
            valid_statuses = ['pending', 'in_progress', 'completed']
            if todo['status'] not in valid_statuses:
                raise ValueError(
                    f"Todo {i} has invalid status: {todo['status']}. "
                    f"Must be one of: {', '.join(valid_statuses)}"
                )

        # Count statuses
        status_counts = {
            'pending': sum(1 for t in todos if t['status'] == 'pending'),
            'in_progress': sum(1 for t in todos if t['status'] == 'in_progress'),
            'completed': sum(1 for t in todos if t['status'] == 'completed'),
        }

        # Store in Redis if client available
        if self.redis_client:
            key = f"project:{project_id}:todos"
            value = json.dumps(todos)

            try:
                await self.redis_client.set(key, value)
            except Exception as e:
                print(f"Warning: Could not store todos in Redis: {str(e)}")

        return {
            "success": True,
            "project_id": project_id,
            "total_todos": len(todos),
            "pending": status_counts['pending'],
            "in_progress": status_counts['in_progress'],
            "completed": status_counts['completed'],
            "progress_percentage": round(
                (status_counts['completed'] / len(todos) * 100) if todos else 0,
                1
            )
        }

    async def get_todos(self, project_id: str) -> List[Dict[str, str]]:
        """
        Retrieve todos for project

        Args:
            project_id: Project identifier

        Returns:
            List of todos
        """
        if not self.redis_client:
            return []

        try:
            key = f"project:{project_id}:todos"
            value = await self.redis_client.get(key)

            if value:
                return json.loads(value)

            return []

        except Exception as e:
            print(f"Warning: Could not retrieve todos from Redis: {str(e)}")
            return []
