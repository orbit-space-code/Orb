"""
Analysis execution engine - orchestrates tool execution and result aggregation
"""
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .base_tool import AnalysisTool, ToolResult, Severity, IssueCategory
from .tools import (
    ESLintTool,
    PylintTool,
    BanditTool,
    SnykTool,
    PrettierTool,
    BlackTool,
    RubocopTool,
    GitleaksTool,
    SafetyTool,
    SemgrepTool,
    Flake8Tool,
)


class AnalysisMode:
    """Analysis mode configurations"""
    NORMAL = {
        "name": "normal",
        "duration_estimate": 300,  # 5 minutes
        "tools": ["eslint", "pylint", "flake8", "prettier", "black"],
        "parallel": True,
    }
    STANDARD = {
        "name": "standard",
        "duration_estimate": 1200,  # 20 minutes
        "tools": ["eslint", "pylint", "flake8", "bandit", "snyk", "safety", "prettier", "black", "rubocop"],
        "parallel": True,
    }
    DEEP = {
        "name": "deep",
        "duration_estimate": 3600,  # 60 minutes
        "tools": ["eslint", "pylint", "flake8", "bandit", "snyk", "safety", "prettier", "black", "rubocop", "gitleaks", "semgrep"],
        "parallel": True,
        "deep_scan": True,
    }


class AnalysisEngine:
    """Main analysis execution engine"""
    
    def __init__(self):
        self.tools_registry: Dict[str, AnalysisTool] = {
            "eslint": ESLintTool(),
            "pylint": PylintTool(),
            "bandit": BanditTool(),
            "snyk": SnykTool(),
            "prettier": PrettierTool(),
            "black": BlackTool(),
            "rubocop": RubocopTool(),
            "gitleaks": GitleaksTool(),
            "safety": SafetyTool(),
            "semgrep": SemgrepTool(),
            "flake8": Flake8Tool(),
        }
    
    async def run_analysis(
        self,
        session_id: str,
        codebase_path: str,
        mode: str = "standard",
        selected_tools: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Run analysis on a codebase
        
        Args:
            session_id: Unique session identifier
            codebase_path: Path to the codebase
            mode: Analysis mode (normal, standard, deep)
            selected_tools: List of tool names to run (overrides mode)
            config: Tool-specific configurations
            progress_callback: Callback for progress updates
            
        Returns:
            Analysis results with aggregated data
        """
        started_at = datetime.now()
        
        # Get mode configuration
        mode_config = getattr(AnalysisMode, mode.upper(), AnalysisMode.STANDARD)
        tools_to_run = selected_tools or mode_config["tools"]
        
        # Filter available tools
        available_tools = []
        for tool_name in tools_to_run:
            if tool_name in self.tools_registry:
                tool = self.tools_registry[tool_name]
                if await tool.is_available():
                    available_tools.append(tool)
                else:
                    if progress_callback:
                        await progress_callback({
                            "type": "tool_unavailable",
                            "tool": tool_name,
                            "message": f"{tool_name} is not installed or available",
                        })
        
        if not available_tools:
            return {
                "session_id": session_id,
                "status": "failed",
                "error": "No analysis tools available",
                "started_at": started_at.isoformat(),
                "completed_at": datetime.now().isoformat(),
            }
        
        # Execute tools
        if progress_callback:
            await progress_callback({
                "type": "analysis_started",
                "session_id": session_id,
                "tools_count": len(available_tools),
                "tools": [t.name for t in available_tools],
            })
        
        results = []
        if mode_config.get("parallel", True):
            # Run tools in parallel
            tasks = [
                self._run_tool_with_progress(
                    tool, codebase_path, config, progress_callback
                )
                for tool in available_tools
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Run tools sequentially
            for tool in available_tools:
                result = await self._run_tool_with_progress(
                    tool, codebase_path, config, progress_callback
                )
                results.append(result)
        
        completed_at = datetime.now()
        
        # Aggregate results
        aggregated = self._aggregate_results(
            session_id, results, started_at, completed_at
        )
        
        if progress_callback:
            await progress_callback({
                "type": "analysis_completed",
                "session_id": session_id,
                "summary": aggregated["summary"],
            })
        
        return aggregated
    
    async def _run_tool_with_progress(
        self,
        tool: AnalysisTool,
        codebase_path: str,
        config: Optional[Dict[str, Any]],
        progress_callback: Optional[callable],
    ) -> ToolResult:
        """Run a single tool with progress updates"""
        if progress_callback:
            await progress_callback({
                "type": "tool_started",
                "tool": tool.name,
                "message": f"Running {tool.name}...",
            })
        
        try:
            tool_config = config.get(tool.name) if config else None
            result = await tool.execute(codebase_path, tool_config)
            
            if progress_callback:
                await progress_callback({
                    "type": "tool_completed",
                    "tool": tool.name,
                    "status": result.status,
                    "issues_found": result.metrics.issues_found,
                })
            
            return result
        except Exception as e:
            if progress_callback:
                await progress_callback({
                    "type": "tool_failed",
                    "tool": tool.name,
                    "error": str(e),
                })
            raise
    
    def _aggregate_results(
        self,
        session_id: str,
        results: List[ToolResult],
        started_at: datetime,
        completed_at: datetime,
    ) -> Dict[str, Any]:
        """Aggregate results from all tools"""
        
        # Filter out exceptions
        valid_results = [r for r in results if isinstance(r, ToolResult)]
        
        # Collect all issues
        all_issues = []
        for result in valid_results:
            all_issues.extend(result.issues)
        
        # Calculate summary statistics
        total_issues = len(all_issues)
        issues_by_severity = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 0,
            Severity.MEDIUM: 0,
            Severity.LOW: 0,
            Severity.INFO: 0,
        }
        issues_by_category = {
            IssueCategory.SECURITY: 0,
            IssueCategory.BUG: 0,
            IssueCategory.CODE_SMELL: 0,
            IssueCategory.STYLE: 0,
            IssueCategory.PERFORMANCE: 0,
            IssueCategory.DOCUMENTATION: 0,
            IssueCategory.COMPLEXITY: 0,
            IssueCategory.DUPLICATION: 0,
        }
        
        for issue in all_issues:
            issues_by_severity[issue.severity] += 1
            issues_by_category[issue.category] += 1
        
        # Calculate total metrics
        total_files = sum(r.metrics.files_analyzed for r in valid_results)
        total_lines = sum(r.metrics.lines_analyzed for r in valid_results)
        total_execution_time = sum(r.metrics.execution_time_ms for r in valid_results)
        
        # Determine overall status
        has_critical = issues_by_severity[Severity.CRITICAL] > 0
        has_high = issues_by_severity[Severity.HIGH] > 0
        
        if has_critical:
            status = "critical_issues_found"
        elif has_high:
            status = "high_issues_found"
        elif total_issues > 0:
            status = "issues_found"
        else:
            status = "passed"
        
        return {
            "session_id": session_id,
            "status": status,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": (completed_at - started_at).total_seconds(),
            "summary": {
                "total_issues": total_issues,
                "critical_issues": issues_by_severity[Severity.CRITICAL],
                "high_issues": issues_by_severity[Severity.HIGH],
                "medium_issues": issues_by_severity[Severity.MEDIUM],
                "low_issues": issues_by_severity[Severity.LOW],
                "info_issues": issues_by_severity[Severity.INFO],
                "security_issues": issues_by_category[IssueCategory.SECURITY],
                "bug_issues": issues_by_category[IssueCategory.BUG],
                "code_smell_issues": issues_by_category[IssueCategory.CODE_SMELL],
                "style_issues": issues_by_category[IssueCategory.STYLE],
                "files_analyzed": total_files,
                "lines_analyzed": total_lines,
                "execution_time_ms": total_execution_time,
            },
            "tools": [
                {
                    "name": r.tool_name,
                    "version": r.tool_version,
                    "status": r.status,
                    "issues_found": r.metrics.issues_found,
                    "execution_time_ms": r.metrics.execution_time_ms,
                }
                for r in valid_results
            ],
            "issues": [
                {
                    "file_path": issue.file_path,
                    "line_number": issue.line_number,
                    "column": issue.column,
                    "severity": issue.severity,
                    "category": issue.category,
                    "rule_id": issue.rule_id,
                    "message": issue.message,
                    "description": issue.description,
                    "suggestion": issue.suggestion,
                }
                for issue in all_issues
            ],
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools"""
        return [tool.get_info() for tool in self.tools_registry.values()]
