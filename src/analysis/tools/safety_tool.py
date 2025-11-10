"""
Safety tool for Python dependency vulnerability scanning
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


class SafetyTool(AnalysisTool):
    """Safety vulnerability scanner for Python dependencies"""
    
    def __init__(self):
        super().__init__()
        self.name = "safety"
        self.version = "2.3.5"
        self.supported_languages = ["python"]
        self.supported_extensions = []  # Works on requirements files
    
    async def is_available(self) -> bool:
        """Check if Safety is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "safety", "--version",
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
        """Execute Safety on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build Safety command
            cmd = [
                "safety",
                "check",
                "--json",
                "--file", "requirements.txt",
            ]
            
            # Execute Safety
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
            files_analyzed = 1  # requirements.txt
            
            if stdout:
                try:
                    results = json.loads(stdout.decode())
                    
                    for vuln in results:
                        issues.append(self._parse_issue(vuln))
                        
                except json.JSONDecodeError:
                    pass
            
            execution_time = int((completed_at - started_at).total_seconds() * 1000)
            
            metrics = ToolMetrics(
                execution_time_ms=execution_time,
                files_analyzed=files_analyzed,
                lines_analyzed=0,
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
    
    def _parse_issue(self, vuln: Dict) -> Issue:
        """Parse Safety vulnerability into Issue"""
        package = vuln.get("package", "unknown")
        version = vuln.get("installed_version", "")
        
        return Issue(
            file_path=f"requirements.txt ({package}=={version})",
            line_number=None,
            column=None,
            severity=Severity.HIGH,  # All vulnerabilities are high priority
            category=IssueCategory.SECURITY,
            rule_id=vuln.get("vulnerability_id", ""),
            message=vuln.get("advisory", ""),
            description=vuln.get("description", ""),
            suggestion=f"Upgrade to version {vuln.get('fixed_version', 'latest')}",
        )
