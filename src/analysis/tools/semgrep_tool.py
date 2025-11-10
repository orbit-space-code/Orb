"""
Semgrep tool for SAST (Static Application Security Testing)
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional

from ..base_tool import (
    AnalysisTool,
    ToolResult,
    ToolMetrics,
    Issue,
    Severity,
    IssueCategory,
)


class SemgrepTool(AnalysisTool):
    """Semgrep SAST tool"""
    
    def __init__(self):
        super().__init__()
        self.name = "semgrep"
        self.version = "1.45.0"
        self.supported_languages = ["python", "javascript", "typescript", "java", "go", "ruby"]
        self.supported_extensions = []  # Works on multiple file types
    
    async def is_available(self) -> bool:
        """Check if Semgrep is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "semgrep", "--version",
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
        """Execute Semgrep on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build Semgrep command
            cmd = [
                "semgrep",
                "scan",
                "--config", "auto",
                "--json",
                ".",
            ]
            
            # Add custom config if specified
            if config and "config" in config:
                cmd[2] = config["config"]
            
            # Execute Semgrep
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
                    
                    files_scanned = set()
                    for result in results.get("results", []):
                        issues.append(self._parse_issue(result))
                        files_scanned.add(result.get("path", ""))
                    
                    files_analyzed = len(files_scanned)
                    
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
        """Parse Semgrep result into Issue"""
        severity_map = {
            "ERROR": Severity.HIGH,
            "WARNING": Severity.MEDIUM,
            "INFO": Severity.LOW,
        }
        
        extra = result.get("extra", {})
        severity_str = extra.get("severity", "WARNING")
        
        return Issue(
            file_path=result.get("path", ""),
            line_number=result.get("start", {}).get("line"),
            column=result.get("start", {}).get("col"),
            severity=severity_map.get(severity_str, Severity.MEDIUM),
            category=IssueCategory.SECURITY,
            rule_id=result.get("check_id", ""),
            message=extra.get("message", ""),
            description=extra.get("metadata", {}).get("description", ""),
            suggestion=extra.get("fix", ""),
        )
