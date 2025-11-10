"""
Error tracking with Sentry integration
"""
import os
from typing import Optional
from fastapi import Request
import traceback


class ErrorTracker:
    """Error tracking and reporting"""
    
    def __init__(self):
        self.sentry_enabled = False
        self.sentry_dsn = os.getenv("SENTRY_DSN")
        
        if self.sentry_dsn:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.fastapi import FastApiIntegration
                from sentry_sdk.integrations.redis import RedisIntegration
                
                sentry_sdk.init(
                    dsn=self.sentry_dsn,
                    environment=os.getenv("ENVIRONMENT", "development"),
                    traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
                    integrations=[
                        FastApiIntegration(),
                        RedisIntegration(),
                    ],
                )
                self.sentry_enabled = True
                print("✓ Sentry error tracking enabled")
            except ImportError:
                print("⚠️ Sentry SDK not installed, error tracking disabled")
            except Exception as e:
                print(f"⚠️ Failed to initialize Sentry: {e}")
    
    def capture_exception(
        self,
        exception: Exception,
        context: Optional[dict] = None,
    ):
        """Capture an exception"""
        if self.sentry_enabled:
            try:
                import sentry_sdk
                
                if context:
                    with sentry_sdk.push_scope() as scope:
                        for key, value in context.items():
                            scope.set_context(key, value)
                        sentry_sdk.capture_exception(exception)
                else:
                    sentry_sdk.capture_exception(exception)
            except Exception as e:
                print(f"Failed to capture exception in Sentry: {e}")
        
        # Always log to console
        print(f"ERROR: {exception}")
        print(traceback.format_exc())
    
    def capture_message(
        self,
        message: str,
        level: str = "info",
        context: Optional[dict] = None,
    ):
        """Capture a message"""
        if self.sentry_enabled:
            try:
                import sentry_sdk
                
                if context:
                    with sentry_sdk.push_scope() as scope:
                        for key, value in context.items():
                            scope.set_context(key, value)
                        sentry_sdk.capture_message(message, level=level)
                else:
                    sentry_sdk.capture_message(message, level=level)
            except Exception as e:
                print(f"Failed to capture message in Sentry: {e}")
        
        print(f"{level.upper()}: {message}")


# Global error tracker instance
error_tracker = ErrorTracker()


async def error_tracking_middleware(request: Request, call_next):
    """FastAPI middleware for error tracking"""
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        # Capture exception with request context
        error_tracker.capture_exception(
            e,
            context={
                "request": {
                    "method": request.method,
                    "url": str(request.url),
                    "headers": dict(request.headers),
                    "client": request.client.host if request.client else None,
                }
            }
        )
        raise
