"""
FastAPI routes for codebase analysis
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio

from src.analysis.engine import AnalysisEngine
from src.analysis.report_generator import ReportGenerator
from src.analysis.cost_tracker import CostTracker
from src.orchestrator.redis_client import get_redis_client

router = APIRouter(prefix="/analysis", tags=["analysis"])

# Global instances
analysis_engine = AnalysisEngine()
report_generator = ReportGenerator()


class StartAnalysisRequest(BaseModel):
    session_id: str
    codebase_id: str
    codebase_path: str
    mode: str = "standard"
    tools: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class IndexCodebaseRequest(BaseModel):
    codebase_id: str
    source_type: str
    source_url: Optional[str] = None


@router.post("/start")
async def start_analysis(
    request: StartAnalysisRequest,
    background_tasks: BackgroundTasks,
):
    """Start a new analysis session"""
    try:
        # Add analysis task to background
        background_tasks.add_task(
            run_analysis_task,
            request.session_id,
            request.codebase_path,
            request.mode,
            request.tools,
            request.config,
        )
        
        return {
            "session_id": request.session_id,
            "status": "started",
            "message": "Analysis started successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/cancel")
async def cancel_analysis(session_id: str):
    """Cancel a running analysis session"""
    try:
        redis = get_redis_client()
        await redis.publish(
            f"analysis:{session_id}",
            {
                "type": "analysis_cancelled",
                "session_id": session_id,
            }
        )
        
        return {
            "session_id": session_id,
            "status": "cancelled",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def get_available_tools():
    """Get list of available analysis tools"""
    try:
        tools = analysis_engine.get_available_tools()
        return {"tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_analysis_task(
    session_id: str,
    codebase_path: str,
    mode: str,
    tools: Optional[List[str]],
    config: Optional[Dict[str, Any]],
):
    """Background task to run analysis"""
    redis = get_redis_client()
    
    async def progress_callback(event: Dict[str, Any]):
        """Publish progress updates to Redis"""
        await redis.publish(f"analysis:{session_id}", event)
    
    try:
        # Estimate cost
        estimated_cost = CostTracker.estimate_cost(
            tools=tools or [],
            estimated_lines=10000,
        )
        
        await progress_callback({
            "type": "cost_estimate",
            "estimated_cost": float(estimated_cost),
        })
        
        # Update status to running
        await progress_callback({
            "type": "status_update",
            "status": "RUNNING",
        })
        
        # Run analysis
        results = await analysis_engine.run_analysis(
            session_id=session_id,
            codebase_path=codebase_path,
            mode=mode,
            selected_tools=tools,
            config=config,
            progress_callback=progress_callback,
        )
        
        # Calculate actual cost
        actual_cost = CostTracker.calculate_actual_cost(results.get("tools", []))
        cost_breakdown = CostTracker.get_cost_breakdown(results.get("tools", []))
        
        results["cost"] = {
            "estimated": float(estimated_cost),
            "actual": float(actual_cost),
            "breakdown": cost_breakdown,
        }
        
        # Generate reports
        await progress_callback({
            "type": "generating_reports",
            "message": "Generating analysis reports...",
        })
        
        # Save reports
        reports_dir = f"/tmp/analysis/{session_id}"
        import os
        os.makedirs(reports_dir, exist_ok=True)
        
        json_report = report_generator.generate_json_report(
            results,
            f"{reports_dir}/report.json"
        )
        
        html_report = report_generator.generate_html_report(
            results,
            f"{reports_dir}/report.html"
        )
        
        md_report = report_generator.generate_markdown_report(
            results,
            f"{reports_dir}/report.md"
        )
        
        # Update status to completed
        await progress_callback({
            "type": "status_update",
            "status": "COMPLETED",
            "results": results,
            "reports": {
                "json": json_report,
                "html": html_report,
                "markdown": md_report,
            },
        })
        
        # Store results in Redis for quick access
        await redis.set(
            f"analysis:results:{session_id}",
            results,
            ex=86400,  # 24 hours
        )
        
    except Exception as e:
        # Update status to failed
        await progress_callback({
            "type": "status_update",
            "status": "FAILED",
            "error": str(e),
        })
        raise


@router.post("/codebases/{codebase_id}/index")
async def index_codebase(
    codebase_id: str,
    request: IndexCodebaseRequest,
    background_tasks: BackgroundTasks,
):
    """Index a codebase for analysis"""
    try:
        # Add indexing task to background
        background_tasks.add_task(
            index_codebase_task,
            codebase_id,
            request.source_type,
            request.source_url,
        )
        
        return {
            "codebase_id": codebase_id,
            "status": "indexing_started",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def index_codebase_task(
    codebase_id: str,
    source_type: str,
    source_url: Optional[str],
):
    """Background task to index codebase"""
    redis = get_redis_client()
    
    try:
        # Publish indexing started event
        await redis.publish(
            f"codebase:{codebase_id}",
            {
                "type": "indexing_started",
                "codebase_id": codebase_id,
            }
        )
        
        # TODO: Implement actual indexing logic
        # - Clone/download codebase
        # - Detect languages and frameworks
        # - Count files and lines
        # - Store metadata
        
        await asyncio.sleep(2)  # Simulate indexing
        
        # Publish indexing completed event
        await redis.publish(
            f"codebase:{codebase_id}",
            {
                "type": "indexing_completed",
                "codebase_id": codebase_id,
                "metadata": {
                    "languages": ["javascript", "python"],
                    "frameworks": ["nextjs", "fastapi"],
                    "file_count": 150,
                    "line_count": 5000,
                },
            }
        )
        
    except Exception as e:
        await redis.publish(
            f"codebase:{codebase_id}",
            {
                "type": "indexing_failed",
                "codebase_id": codebase_id,
                "error": str(e),
            }
        )
        raise
