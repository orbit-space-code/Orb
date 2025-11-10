"""
Prometheus metrics collection
"""
from fastapi import Request
from typing import Dict, Any
import time
from collections import defaultdict
import asyncio


class MetricsCollector:
    """Collect application metrics"""
    
    def __init__(self):
        self.request_count = defaultdict(int)
        self.request_duration = defaultdict(list)
        self.error_count = defaultdict(int)
        self.analysis_count = 0
        self.analysis_duration = []
        self.tool_execution_count = defaultdict(int)
        self.tool_execution_duration = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
    ):
        """Record HTTP request metrics"""
        async with self.lock:
            key = f"{method}:{path}"
            self.request_count[key] += 1
            self.request_duration[key].append(duration)
            
            if status_code >= 400:
                self.error_count[key] += 1
    
    async def record_analysis(self, duration: float, tool_count: int):
        """Record analysis session metrics"""
        async with self.lock:
            self.analysis_count += 1
            self.analysis_duration.append(duration)
    
    async def record_tool_execution(
        self,
        tool_name: str,
        duration: float,
        success: bool,
    ):
        """Record tool execution metrics"""
        async with self.lock:
            self.tool_execution_count[tool_name] += 1
            self.tool_execution_duration[tool_name].append(duration)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        async with self.lock:
            # Calculate averages
            avg_request_duration = {}
            for key, durations in self.request_duration.items():
                if durations:
                    avg_request_duration[key] = sum(durations) / len(durations)
            
            avg_analysis_duration = (
                sum(self.analysis_duration) / len(self.analysis_duration)
                if self.analysis_duration else 0
            )
            
            avg_tool_duration = {}
            for tool, durations in self.tool_execution_duration.items():
                if durations:
                    avg_tool_duration[tool] = sum(durations) / len(durations)
            
            return {
                "requests": {
                    "total": sum(self.request_count.values()),
                    "by_endpoint": dict(self.request_count),
                    "avg_duration_ms": avg_request_duration,
                    "errors": dict(self.error_count),
                },
                "analysis": {
                    "total_sessions": self.analysis_count,
                    "avg_duration_seconds": avg_analysis_duration,
                },
                "tools": {
                    "execution_count": dict(self.tool_execution_count),
                    "avg_duration_ms": avg_tool_duration,
                },
            }
    
    async def export_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        metrics = await self.get_metrics()
        
        lines = []
        
        # Request metrics
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        for endpoint, count in metrics["requests"]["by_endpoint"].items():
            lines.append(f'http_requests_total{{endpoint="{endpoint}"}} {count}')
        
        # Error metrics
        lines.append("# HELP http_errors_total Total HTTP errors")
        lines.append("# TYPE http_errors_total counter")
        for endpoint, count in metrics["requests"]["errors"].items():
            lines.append(f'http_errors_total{{endpoint="{endpoint}"}} {count}')
        
        # Analysis metrics
        lines.append("# HELP analysis_sessions_total Total analysis sessions")
        lines.append("# TYPE analysis_sessions_total counter")
        lines.append(f'analysis_sessions_total {metrics["analysis"]["total_sessions"]}')
        
        lines.append("# HELP analysis_duration_seconds Average analysis duration")
        lines.append("# TYPE analysis_duration_seconds gauge")
        lines.append(f'analysis_duration_seconds {metrics["analysis"]["avg_duration_seconds"]}')
        
        # Tool metrics
        lines.append("# HELP tool_executions_total Total tool executions")
        lines.append("# TYPE tool_executions_total counter")
        for tool, count in metrics["tools"]["execution_count"].items():
            lines.append(f'tool_executions_total{{tool="{tool}"}} {count}')
        
        return "\n".join(lines)


# Global metrics collector
metrics_collector = MetricsCollector()


async def metrics_middleware(request: Request, call_next):
    """FastAPI middleware for metrics collection"""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration = (time.time() - start_time) * 1000  # ms
        
        await metrics_collector.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
        )
        
        return response
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        await metrics_collector.record_request(
            method=request.method,
            path=request.url.path,
            status_code=500,
            duration=duration,
        )
        raise


async def get_metrics() -> Dict[str, Any]:
    """Get current metrics"""
    return await metrics_collector.get_metrics()


async def get_prometheus_metrics() -> str:
    """Get metrics in Prometheus format"""
    return await metrics_collector.export_prometheus()
