"""
Code Quality Dashboard API
Provides endpoints for accessing code quality metrics and visualizations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from enum import Enum
import logging

from ...services.code_quality_dashboard import (
    CodeQualityDashboard,
    TimeRange,
    MetricTrend
)
from ...services.project_context import ProjectContext
from ...auth.dependencies import get_current_user

router = APIRouter(prefix="/api/quality", tags=["quality"])
logger = logging.getLogger(__name__)

# Request/Response Models
class QualityMetric(str, Enum):
    """Available quality metrics"""
    OVERALL_SCORE = "overall_score"
    ISSUES = "issues"
    COVERAGE = "coverage"
    COMPLEXITY = "complexity"

class IssueSeverity(str, Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@router.get("/overview/{project_id}")
async def get_quality_overview(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get an overview of code quality metrics for a project"""
    try:
        dashboard = CodeQualityDashboard(project_id)
        return await dashboard.get_overview()
    except Exception as e:
        logger.error(f"Error getting quality overview: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quality overview: {str(e)}"
        )

@router.get("/files/{project_id}")
async def list_project_files(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all files in the project with quality metrics"""
    try:
        project_ctx = ProjectContext(project_id)
        files = await project_ctx.list_project_files()
        
        dashboard = CodeQualityDashboard(project_id)
        file_metrics = []
        
        for file_path in files:
            try:
                analysis = await dashboard.get_file_analysis(file_path)
                file_metrics.append({
                    "path": file_path,
                    "score": analysis["analysis"]["score"],
                    "issues": len(analysis["analysis"]["issues"]),
                    "complexity": analysis["analysis"]["complexity"],
                    "coverage": analysis["analysis"]["coverage"]
                })
            except Exception as e:
                logger.warning(f"Skipping file {file_path}: {str(e)}")
        
        return {"files": file_metrics}
        
    except Exception as e:
        logger.error(f"Error listing project files: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list project files: {str(e)}"
        )

@router.get("/files/{project_id}/{file_path:path}")
async def get_file_quality(
    project_id: str,
    file_path: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed quality analysis for a specific file"""
    try:
        dashboard = CodeQualityDashboard(project_id)
        return await dashboard.get_file_analysis(file_path)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting file quality: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file quality: {str(e)}"
        )

@router.get("/issues/{project_id}")
async def get_issues(
    project_id: str,
    severity: Optional[IssueSeverity] = None,
    category: Optional[str] = None,
    file: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get code quality issues with filtering options"""
    try:
        dashboard = CodeQualityDashboard(project_id)
        issues_data = await dashboard.get_issues(severity=severity.value if severity else None)
        
        # Apply additional filters
        filtered_issues = []
        for file_issues in issues_data.get("by_file", []):
            if file and file not in file_issues["file"]:
                continue
                
            for issue in file_issues.get("issues", []):
                if category and issue.get("category") != category:
                    continue
                filtered_issues.append({
                    **issue,
                    "file": file_issues["file"]
                })
        
        return {
            "total_issues": len(filtered_issues),
            "issues": filtered_issues,
            "filters": {
                "severity": severity.value if severity else None,
                "category": category,
                "file": file
            },
            "summary": {
                "by_severity": issues_data.get("by_severity", {}),
                "by_category": issues_data.get("by_category", {})
            }
        }
    except Exception as e:
        logger.error(f"Error getting issues: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get issues: {str(e)}"
        )

@router.get("/debt/{project_id}")
async def get_tech_debt(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get technical debt analysis"""
    try:
        dashboard = CodeQualityDashboard(project_id)
        return await dashboard.get_tech_debt()
    except Exception as e:
        logger.error(f"Error getting tech debt: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get technical debt: {str(e)}"
        )

@router.get("/trends/{project_id}/{metric}")
async def get_metric_trends(
    project_id: str,
    metric: QualityMetric,
    time_range: TimeRange = TimeRange.MONTH,
    current_user: dict = Depends(get_current_user)
):
    """Get historical trends for a specific metric"""
    try:
        dashboard = CodeQualityDashboard(project_id)
        return await dashboard.get_trends(metric.value, time_range)
    except Exception as e:
        logger.error(f"Error getting trends: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trends: {str(e)}"
        )

@router.get("/suggestions/{project_id}")
async def get_improvement_suggestions(
    project_id: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Get code improvement suggestions"""
    try:
        dashboard = CodeQualityDashboard(project_id)
        
        # Get all files in the project
        project_ctx = ProjectContext(project_id)
        files = await project_ctx.list_project_files()
        
        # Get suggestions for each file
        all_suggestions = []
        for file_path in files[:20]:  # Limit to first 20 files for performance
            try:
                analysis = await dashboard.get_file_analysis(file_path)
                for suggestion in analysis.get("suggestions", []):
                    all_suggestions.append({
                        **suggestion,
                        "file": file_path
                    })
            except Exception as e:
                logger.warning(f"Skipping file {file_path}: {str(e)}")
        
        # Sort by severity (critical, high, medium, low, info)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        all_suggestions.sort(key=lambda x: severity_order.get(x["severity"].lower(), 99))
        
        return {
            "suggestions": all_suggestions[:limit],
            "total_suggestions": len(all_suggestions)
        }
        
    except Exception as e:
        logger.error(f"Error getting suggestions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )
