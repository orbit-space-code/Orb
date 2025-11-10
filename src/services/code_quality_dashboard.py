"""
Code Quality Dashboard Service
Provides insights and visualizations for code quality metrics
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import asyncio
from dataclasses import dataclass, field
from pathlib import Path
import json
import logging

from pydantic import BaseModel, Field
import numpy as np
import pandas as pd

from .code_quality import CodeQualityAnalyzer, CodeQualityReport, QualityIssue
from .project_context import ProjectContext

logger = logging.getLogger(__name__)

class TimeRange(str, Enum):
    """Time ranges for code quality trends"""
    DAY = "24h"
    WEEK = "7d"
    MONTH = "30d"
    QUARTER = "90d"
    YEAR = "365d"

class MetricTrend(str, Enum):
    """Trend direction for metrics"""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"

@dataclass
class MetricSummary:
    """Summary of a single metric"""
    name: str
    value: float
    previous_value: Optional[float] = None
    target: Optional[float] = None
    trend: MetricTrend = MetricTrend.STABLE
    change_percentage: Optional[float] = None
    unit: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "previous_value": self.previous_value,
            "target": self.target,
            "trend": self.trend,
            "change_percentage": self.change_percentage,
            "unit": self.unit,
            "description": self.description
        }

@dataclass
class FileQuality:
    """Quality metrics for a single file"""
    file_path: str
    score: float
    issues: List[QualityIssue]
    complexity: Optional[float] = None
    coverage: Optional[float] = None
    maintainability_index: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "score": self.score,
            "complexity": self.complexity,
            "coverage": self.coverage,
            "maintainability_index": self.maintainability_index,
            "issue_count": len(self.issues),
            "issues": [issue.dict() for issue in self.issues]
        }

class CodeQualityDashboard:
    """Generates code quality dashboards and insights"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.quality_analyzer = CodeQualityAnalyzer()
        self.project_context = ProjectContext(project_id)
        self.metrics_history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    async def get_overview(self) -> Dict[str, Any]:
        """Get an overview of code quality metrics"""
        # Get latest code quality report
        report = await self._get_latest_report()
        
        # Calculate metrics
        metrics = [
            self._calculate_metric("Overall Score", report.overall_score, 0.9, "0-1 score"),
            self._calculate_metric(
                "Issues", 
                len(report.issues), 
                target=0, 
                lower_is_better=True,
                unit="issues"
            ),
            self._calculate_metric(
                "Test Coverage", 
                report.test_coverage * 100 if report.test_coverage else 0, 
                target=80,
                unit="%"
            ),
            self._calculate_metric(
                "Complexity", 
                report.average_complexity,
                target=10,
                lower_is_better=True,
                unit="avg"
            )
        ]
        
        # Get trend data
        trends = await self._get_metric_trends()
        
        # Get issue distribution
        issue_dist = self._get_issue_distribution(report.issues)
        
        return {
            "overview": {
                "project_name": self.project_id,
                "last_analyzed": report.timestamp.isoformat(),
                "metrics": [m.to_dict() for m in metrics],
                "trends": trends,
                "issue_distribution": issue_dist
            }
        }
    
    async def get_file_analysis(self, file_path: str) -> Dict[str, Any]:
        """Get detailed analysis for a specific file"""
        # Analyze the file
        file_content = await self.project_context.get_file_content(file_path)
        if not file_content:
            raise ValueError(f"File not found: {file_path}")
        
        # Get file-specific quality report
        report = await self.quality_analyzer.analyze_code(
            code=file_content,
            language=self._get_language_from_extension(file_path),
            file_path=file_path
        )
        
        # Convert to file quality object
        file_quality = FileQuality(
            file_path=file_path,
            score=report.overall_score,
            issues=report.issues,
            complexity=report.average_complexity,
            coverage=report.test_coverage,
            maintainability_index=report.maintainability_index
        )
        
        # Get historical data for this file
        history = await self._get_file_history(file_path)
        
        return {
            "file_path": file_path,
            "analysis": file_quality.to_dict(),
            "history": history,
            "suggestions": self._generate_suggestions(file_quality)
        }
    
    async def get_issues(self, severity: Optional[str] = None) -> Dict[str, Any]:
        """Get all issues, optionally filtered by severity"""
        report = await self._get_latest_report()
        
        issues = report.issues
        if severity:
            issues = [i for i in issues if i.severity == severity]
        
        # Group by file
        issues_by_file: Dict[str, List[Dict[str, Any]]] = {}
        for issue in issues:
            if issue.file_path not in issues_by_file:
                issues_by_file[issue.file_path] = []
            issues_by_file[issue.file_path].append(issue.dict())
        
        return {
            "total_issues": len(issues),
            "by_severity": self._count_by_severity(issues),
            "by_category": self._count_by_category(issues),
            "by_file": [
                {"file": file, "count": len(file_issues), "issues": file_issues}
                for file, file_issues in issues_by_file.items()
            ]
        }
    
    async def get_tech_debt(self) -> Dict[str, Any]:
        """Calculate technical debt metrics"""
        report = await self._get_latest_report()
        
        # Simple technical debt calculation
        # In a real implementation, this would be more sophisticated
        debt_score = sum(
            (3 if i.severity == "high" else 2 if i.severity == "medium" else 1) * 0.1
            for i in report.issues
        )
        
        return {
            "debt_score": min(100, debt_score * 100),  # Convert to percentage
            "debt_items": len(report.issues),
            "estimated_effort": len(report.issues) * 0.5,  # In hours
            "by_category": self._count_by_category(report.issues)
        }
    
    async def get_trends(self, metric: str, time_range: TimeRange = TimeRange.MONTH) -> Dict[str, Any]:
        """Get historical trends for a specific metric"""
        # In a real implementation, this would query a time-series database
        # For now, we'll generate some sample data
        end_date = datetime.utcnow()
        
        if time_range == TimeRange.DAY:
            start_date = end_date - timedelta(days=1)
            points = 24  # Hourly points
        elif time_range == TimeRange.WEEK:
            start_date = end_date - timedelta(weeks=1)
            points = 7  # Daily points
        elif time_range == TimeRange.MONTH:
            start_date = end_date - timedelta(days=30)
            points = 30  # Daily points
        elif time_range == TimeRange.QUARTER:
            start_date = end_date - timedelta(days=90)
            points = 12  # Weekly points
        else:  # YEAR
            start_date = end_date - timedelta(days=365)
            points = 12  # Monthly points
        
        # Generate timestamps
        timestamps = pd.date_range(start_date, end_date, periods=points)
        
        # Generate sample data based on metric
        if metric == "overall_score":
            values = np.linspace(0.7, 0.9, points) + np.random.normal(0, 0.02, points)
            values = np.clip(values, 0, 1)  # Keep between 0 and 1
        elif metric == "issues":
            values = np.linspace(100, 20, points) + np.random.normal(0, 5, points)
            values = np.maximum(values, 0)  # No negative issues
        elif metric == "coverage":
            values = np.linspace(60, 85, points) + np.random.normal(0, 2, points)
            values = np.clip(values, 0, 100)  # 0-100%
        else:  # complexity
            values = np.linspace(15, 8, points) + np.random.normal(0, 0.5, points)
            values = np.maximum(values, 1)  # At least 1
        
        return {
            "metric": metric,
            "time_range": time_range.value,
            "data": [
                {"timestamp": ts.isoformat(), "value": float(val)}
                for ts, val in zip(timestamps, values)
            ],
            "current_value": float(values[-1]),
            "change": float((values[-1] - values[0]) / values[0] * 100)  # Percentage change
        }
    
    async def _get_latest_report(self) -> CodeQualityReport:
        """Get the latest code quality report for the project"""
        # In a real implementation, this would load from a database
        # For now, we'll analyze the current codebase
        files = await self.project_context.list_project_files()
        reports = []
        
        for file_path in files:
            try:
                content = await self.project_context.get_file_content(file_path)
                if not content:
                    continue
                    
                report = await self.quality_analyzer.analyze_code(
                    code=content,
                    language=self._get_language_from_extension(file_path),
                    file_path=file_path
                )
                reports.append(report)
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {str(e)}")
        
        if not reports:
            return CodeQualityReport(overall_score=0, issues=[])
        
        # Combine reports
        combined_issues = []
        for r in reports:
            combined_issues.extend(r.issues)
        
        avg_score = sum(r.overall_score for r in reports) / len(reports)
        avg_complexity = sum(r.average_complexity for r in reports if r.average_complexity) / max(1, len([r for r in reports if r.average_complexity is not None]))
        
        return CodeQualityReport(
            overall_score=avg_score,
            issues=combined_issues,
            average_complexity=avg_complexity,
            timestamp=datetime.utcnow()
        )
    
    async def _get_file_history(self, file_path: str) -> List[Dict[str, Any]]:
        """Get historical data for a file"""
        # In a real implementation, this would query version control history
        # For now, return empty list
        return []
    
    def _calculate_metric(
        self, 
        name: str, 
        value: float, 
        target: Optional[float] = None,
        lower_is_better: bool = False,
        unit: str = ""
    ) -> MetricSummary:
        """Calculate metric summary with trend information"""
        # In a real implementation, this would compare with historical data
        # For now, we'll generate some sample trends
        import random
        
        previous_value = value * random.uniform(0.9, 1.1)  # Random variation
        change = ((value - previous_value) / previous_value * 100) if previous_value else 0
        
        if abs(change) < 2:
            trend = MetricTrend.STABLE
        elif (change > 0 and not lower_is_better) or (change < 0 and lower_is_better):
            trend = MetricTrend.IMPROVING
        else:
            trend = MetricTrend.DEGRADING
        
        return MetricSummary(
            name=name,
            value=value,
            previous_value=previous_value,
            target=target,
            trend=trend,
            change_percentage=change,
            unit=unit
        )
    
    def _get_issue_distribution(self, issues: List[QualityIssue]) -> Dict[str, Any]:
        """Get distribution of issues by severity and category"""
        by_severity = self._count_by_severity(issues)
        by_category = self._count_by_category(issues)
        
        return {
            "by_severity": by_severity,
            "by_category": by_category,
            "total_issues": len(issues)
        }
    
    @staticmethod
    def _count_by_severity(issues: List[QualityIssue]) -> Dict[str, int]:
        """Count issues by severity"""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for issue in issues:
            counts[issue.severity] += 1
        return counts
    
    @staticmethod
    def _count_by_category(issues: List[QualityIssue]) -> Dict[str, int]:
        """Count issues by category"""
        counts = {}
        for issue in issues:
            counts[issue.category] = counts.get(issue.category, 0) + 1
        return counts
    
    @staticmethod
    def _generate_suggestions(file_quality: FileQuality) -> List[Dict[str, Any]]:
        """Generate improvement suggestions based on code quality"""
        suggestions = []
        
        # Complexity suggestions
        if file_quality.complexity and file_quality.complexity > 10:
            suggestions.append({
                "type": "complexity",
                "message": f"High cyclomatic complexity ({file_quality.complexity:.1f}). Consider refactoring into smaller functions.",
                "severity": "high",
                "file": file_quality.file_path
            })
        
        # Coverage suggestions
        if file_quality.coverage is not None and file_quality.coverage < 80:
            suggestions.append({
                "type": "coverage",
                "message": f"Low test coverage ({file_quality.coverage:.1f}%). Aim for at least 80% coverage.",
                "severity": "medium",
                "file": file_quality.file_path
            })
        
        # Issue-specific suggestions
        for issue in file_quality.issues:
            if issue.severity in ["high", "critical"]:
                suggestions.append({
                    "type": "issue",
                    "message": f"{issue.message} ({issue.rule_id})",
                    "severity": issue.severity,
                    "file": issue.file_path,
                    "line": issue.line,
                    "column": issue.column
                })
        
        return suggestions
    
    @staticmethod
    def _get_language_from_extension(file_path: str) -> str:
        """Get language from file extension"""
        ext = Path(file_path).suffix.lower()
        if ext in ['.py']:
            return 'python'
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            return 'typescript' if ext in ['.ts', '.tsx'] else 'javascript'
        elif ext in ['.java']:
            return 'java'
        elif ext in ['.go']:
            return 'go'
        elif ext in ['.rs']:
            return 'rust'
        else:
            return 'text'
