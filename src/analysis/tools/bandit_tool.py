"""
Bandit tool for Python security analysis
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from ..base_tool import (
    AnalysisTool,
    ToolResult,
    ToolMetrics,
    Issue,
    Severity,
    IssueCategory,
)


class BanditTool(AnalysisTool):
    """Bandit security scanner for Python"""
    
    def __init__(self):
        super().__init__()
        self.name = "bandit"
        self.version = "1.7.5"
        self.supported_languages = ["python"]
        self.supported_extensions = [".py"]
    
    async def is_available(self) -> bool:
        """Check if Bandit is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "bandit", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False
    
    async def execute(
        self,
        codebase_path: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Execute Bandit on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build Bandit command
            cmd = [
                "bandit",
                "-r", ".",
                "-f", "json",
            ]
            
            # Add config file if specified
            if config and "config_file" in config:
                cmd.extend(["-c", config["config_file"]])
            
            # Execute Bandit
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=codebase_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            completed_at = datetime.now()
            
            # Parse results
            issues = []
            files_analyzed = 0
            lines_analyzed = 0
            
            if stdout:
                try:
                    results = json.loads(stdout.decode())
                    
                    # Get metrics
                    metrics_data = results.get("metrics", {})
                    for file_path, file_metrics in metrics_data.items():
                        if file_path != "_totals":
                            files_analyzed += 1
                            lines_analyzed += file_metrics.get("loc", 0)
                    
                    # Parse issues
                    for result in results.get("results", []):
                        issues.append(self._parse_issue(result))
                        
                except json.JSONDecodeError:
                    pass
            
            execution_time = int((completed_at - started_at).total_seconds() * 1000)
            
            metrics = ToolMetrics(
                execution_time_ms=execution_time,
                files_analyzed=files_analyzed,
                lines_analyzed=lines_analyzed,
                issues_found=len(issues),
            )
            
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status="success",
                started_at=started_at,
                completed_at=completed_at,
                issues=issues,
                metrics=metrics,
                raw_output=stdout.decode() if stdout else None,
            )
            
        except Exception as e:
            completed_at = datetime.now()
            execution_time = int((completed_at - started_at).total_seconds() * 1000)
            
            return ToolResult(
                tool_name=self.name,
                tool_version=self.version,
                status="failed",
                started_at=started_at,
                completed_at=completed_at,
                issues=[],
                metrics=ToolMetrics(
                    execution_time_ms=execution_time,
                    files_analyzed=0,
                    lines_analyzed=0,
                    issues_found=0,
                ),
                error_message=str(e),
            )
    
    def _parse_issue(self, result: Dict) -> Issue:
        """Parse Bandit result into Issue"""
        severity_map = {
            "HIGH": Severity.HIGH,
            "MEDIUM": Severity.MEDIUM,
            "LOW": Severity.LOW,
        }
        
        return Issue(
            file_path=result.get("filename", ""),
            line_number=result.get("line_number"),
            column=result.get("col_offset"),
            severity=severity_map.get(result.get("issue_severity", "MEDIUM"), Severity.MEDIUM),
            category=IssueCategory.SECURITY,
            rule_id=result.get("test_id", ""),
            message=result.get("issue_text", ""),
            description=result.get("test_name", ""),
            code_snippet=result.get("code", ""),
        )
