"""
Redis Client
Handles Redis connections, pub/sub, and task queue operations
"""
import redis.asyncio as redis
import json
from typing import Dict, Any, Optional, AsyncIterator
import os


class RedisClient:
    """Redis client for task queue and pub/sub"""

    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client: Optional[redis.Redis] = None
        self.pubsub = None

    async def connect(self):
        """Establish Redis connection"""
        if not self.client:
            self.client = await redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True
            )

    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            self.client = None

    async def ping(self) -> bool:
        """Test Redis connection"""
        try:
            await self.connect()
            return await self.client.ping()
        except Exception:
            return False

    # Key-Value Operations
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """Set key-value pair with optional expiration"""
        await self.connect()
        await self.client.set(key, value, ex=ex)

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        await self.connect()
        return await self.client.get(key)

    async def delete(self, *keys: str):
        """Delete one or more keys"""
        await self.connect()
        await self.client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        await self.connect()
        return await self.client.exists(key) > 0

    # Pub/Sub Operations
    async def publish(self, channel: str, message: Dict[str, Any]):
        """Publish message to channel"""
        await self.connect()
        await self.client.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to channel and yield messages"""
        await self.connect()
        pubsub = self.client.pubsub()

        try:
            await pubsub.subscribe(channel)

            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        yield data
                    except json.JSONDecodeError:
                        continue

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    # Task Queue Operations
    async def enqueue_task(self, queue: str, task: Dict[str, Any]):
        """Add task to queue"""
        await self.connect()
        await self.client.rpush(queue, json.dumps(task))

    async def dequeue_task(self, queue: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """Remove and return task from queue (blocking)"""
        await self.connect()

        result = await self.client.blpop(queue, timeout=timeout)

        if result:
            _, task_data = result
            return json.loads(task_data)

        return None

    async def get_queue_length(self, queue: str) -> int:
        """Get number of items in queue"""
        await self.connect()
        return await self.client.llen(queue)

    async def peek_task(self, queue: str) -> Optional[Dict[str, Any]]:
        """View first task without removing it"""
        await self.connect()

        task_data = await self.client.lindex(queue, 0)

        if task_data:
            return json.loads(task_data)

        return None

    # Task Status Operations
    async def set_task_status(
        self,
        task_id: str,
        status: str,
        data: Optional[Dict[str, Any]] = None
    ):
        """Set task status"""
        await self.connect()

        key = f"task:{task_id}:status"
        value = {
            "status": status,
            "data": data or {}
        }

        await self.client.set(key, json.dumps(value), ex=3600)  # 1 hour expiry

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        await self.connect()

        key = f"task:{task_id}:status"
        value = await self.client.get(key)

        if value:
            return json.loads(value)

        return None

    # Project Data Operations
    async def set_project_data(
        self,
        project_id: str,
        key: str,
        data: Dict[str, Any],
        ex: Optional[int] = None
    ):
        """Store project-specific data"""
        await self.connect()

        redis_key = f"project:{project_id}:{key}"
        await self.client.set(redis_key, json.dumps(data), ex=ex)

    async def get_project_data(
        self,
        project_id: str,
        key: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve project-specific data"""
        await self.connect()

        redis_key = f"project:{project_id}:{key}"
        value = await self.client.get(redis_key)

        if value:
            return json.loads(value)

        return None

    # List Operations
    async def lpush(self, key: str, *values: str):
        """Push values to left of list"""
        await self.connect()
        await self.client.lpush(key, *values)

    async def rpush(self, key: str, *values: str):
        """Push values to right of list"""
        await self.connect()
        await self.client.rpush(key, *values)

    async def lrange(self, key: str, start: int, end: int) -> list:
        """Get range of list elements"""
        await self.connect()
        return await self.client.lrange(key, start, end)

    # Hash Operations
    async def hset(self, key: str, field: str, value: str):
        """Set hash field"""
        await self.connect()
        await self.client.hset(key, field, value)

    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field"""
        await self.connect()
        return await self.client.hget(key, field)

    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields"""
        await self.connect()
        return await self.client.hgetall(key)


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """Get global Redis client instance"""
    global _redis_client

    if _redis_client is None:
        _redis_client = RedisClient()

    return _redis_client
