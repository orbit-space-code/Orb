"""
AskUser Tool
Present questions to user and wait for answers
"""
from typing import List, Optional, Dict, Any
import json
import asyncio
import uuid
from datetime import datetime
from src.tools.registry import Tool


class AskUserTool(Tool):
    """Present questions to user via UI"""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

    def get_name(self) -> str:
        return "AskUser"

    def get_description(self) -> str:
        return "Ask user a question with multiple choice options"

    async def execute(
        self,
        project_id: str,
        question: str,
        choices: List[str],
        image_url: Optional[str] = None,
        timeout: int = 300  # 5 minutes default
    ) -> Dict[str, Any]:
        """
        Ask user a question and wait for answer

        Args:
            project_id: Project identifier
            question: Question text
            choices: List of choice options
            image_url: Optional image URL (diagram/mockup)
            timeout: Timeout in seconds (default 300)

        Returns:
            Dictionary with answer and metadata
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not configured")

        if not question or len(question.strip()) == 0:
            raise ValueError("Question cannot be empty")

        if not choices or len(choices) < 2:
            raise ValueError("Must provide at least 2 choices")

        if len(choices) > 4:
            raise ValueError("Maximum 4 choices allowed")

        # Generate unique question ID
        question_id = str(uuid.uuid4())

        # Create question object
        question_data = {
            "id": question_id,
            "project_id": project_id,
            "question": question,
            "choices": choices,
            "image_url": image_url,
            "asked_at": datetime.utcnow().isoformat(),
            "answered": False,
            "answer": None
        }

        # Publish question to Redis
        question_key = f"project:{project_id}:question:{question_id}"
        await self.redis_client.set(
            question_key,
            json.dumps(question_data),
            ex=timeout  # Expire after timeout
        )

        # Publish notification
        await self.redis_client.publish(
            f"project:{project_id}:events",
            json.dumps({
                "type": "question",
                "question_id": question_id,
                "data": question_data
            })
        )

        # Wait for answer (poll Redis)
        answer_key = f"project:{project_id}:answer:{question_id}"
        poll_interval = 1  # Poll every second
        elapsed = 0

        while elapsed < timeout:
            # Check for answer
            answer_data = await self.redis_client.get(answer_key)

            if answer_data:
                answer_obj = json.loads(answer_data)

                # Cleanup Redis keys
                await self.redis_client.delete(question_key)
                await self.redis_client.delete(answer_key)

                return {
                    "question_id": question_id,
                    "question": question,
                    "answer": answer_obj.get("answer"),
                    "answered_at": answer_obj.get("answered_at"),
                    "elapsed_seconds": elapsed
                }

            # Wait before next poll
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout reached
        await self.redis_client.delete(question_key)

        raise TimeoutError(
            f"User did not answer question within {timeout} seconds. "
            f"Question: {question}"
        )

    async def submit_answer(
        self,
        project_id: str,
        question_id: str,
        answer: str
    ) -> bool:
        """
        Submit answer to a question (called by Next.js API)

        Args:
            project_id: Project identifier
            question_id: Question identifier
            answer: Selected answer

        Returns:
            True if successful
        """
        if not self.redis_client:
            raise RuntimeError("Redis client not configured")

        # Create answer object
        answer_data = {
            "answer": answer,
            "answered_at": datetime.utcnow().isoformat()
        }

        # Store answer
        answer_key = f"project:{project_id}:answer:{question_id}"
        await self.redis_client.set(
            answer_key,
            json.dumps(answer_data),
            ex=300  # Expire after 5 minutes
        )

        return True
