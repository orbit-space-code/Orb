"""
Rate limiting middleware for FastAPI
"""
from fastapi import Request, HTTPException
from typing import Dict, Optional
import time
from collections import defaultdict
import asyncio


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Storage: {user_id: {window: [timestamps]}}
        self.requests: Dict[str, Dict[str, list]] = defaultdict(lambda: {"minute": [], "hour": []})
        self.lock = asyncio.Lock()
    
    async def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user has exceeded rate limits
        
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self.lock:
            current_time = time.time()
            user_requests = self.requests[user_id]
            
            # Clean old requests
            user_requests["minute"] = [
                t for t in user_requests["minute"]
                if current_time - t < 60
            ]
            user_requests["hour"] = [
                t for t in user_requests["hour"]
                if current_time - t < 3600
            ]
            
            # Check limits
            if len(user_requests["minute"]) >= self.requests_per_minute:
                return False
            
            if len(user_requests["hour"]) >= self.requests_per_hour:
                return False
            
            # Add current request
            user_requests["minute"].append(current_time)
            user_requests["hour"].append(current_time)
            
            return True
    
    async def get_remaining(self, user_id: str) -> Dict[str, int]:
        """Get remaining requests for user"""
        async with self.lock:
            current_time = time.time()
            user_requests = self.requests[user_id]
            
            # Clean old requests
            minute_requests = [
                t for t in user_requests["minute"]
                if current_time - t < 60
            ]
            hour_requests = [
                t for t in user_requests["hour"]
                if current_time - t < 3600
            ]
            
            return {
                "minute_remaining": self.requests_per_minute - len(minute_requests),
                "hour_remaining": self.requests_per_hour - len(hour_requests),
            }


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_minute=60,
    requests_per_hour=1000,
)


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware for rate limiting"""
    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)
    
    # Get user ID from request (you'll need to implement auth)
    user_id = request.headers.get("X-User-ID", "anonymous")
    
    # Check rate limit
    if not await rate_limiter.check_rate_limit(user_id):
        remaining = await rate_limiter.get_remaining(user_id)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "remaining": remaining,
            }
        )
    
    # Add rate limit headers to response
    response = await call_next(request)
    remaining = await rate_limiter.get_remaining(user_id)
    response.headers["X-RateLimit-Remaining-Minute"] = str(remaining["minute_remaining"])
    response.headers["X-RateLimit-Remaining-Hour"] = str(remaining["hour_remaining"])
    
    return response
