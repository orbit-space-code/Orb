"""
GitLeaks tool for secret scanning
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


class GitleaksTool(AnalysisTool):
    """GitLeaks secret scanner"""
    
    def __init__(self):
        super().__init__()
        self.name = "gitleaks"
        self.version = "8.18.0"
        self.supported_languages = []  # Works on all files
        self.supported_extensions = []
    
    async def is_available(self) -> bool:
        """Check if GitLeaks is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "gitleaks", "version",
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
        """Execute GitLeaks on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build GitLeaks command
            cmd = [
                "gitleaks",
                "detect",
                "--source", ".",
                "--report-format", "json",
                "--report-path", "/tmp/gitleaks-report.json",
                "--no-git",
            ]
            
            # Execute GitLeaks
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
            
            try:
                with open("/tmp/gitleaks-report.json", "r") as f:
                    results = json.load(f)
                    
                    files_scanned = set()
                    for finding in results:
                        issues.append(self._parse_issue(finding))
                        files_scanned.add(finding.get("File", ""))
                    
                    files_analyzed = len(files_scanned)
                    
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            
            execution_time = int((completed_at - started_at).total_seconds() * 1000)
            
            metrics = ToolMetrics(
                execution_time_ms=execution_time,
                files_analyzed=files_analyzed,
                lines_analyzed=0,  # N/A for secret scanning
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
    
    def _parse_issue(self, finding: Dict) -> Issue:
        """Parse GitLeaks finding into Issue"""
        return Issue(
            file_path=finding.get("File", "unknown"),
            line_number=finding.get("StartLine"),
            column=finding.get("StartColumn"),
            severity=Severity.CRITICAL,  # All secrets are critical
            category=IssueCategory.SECURITY,
            rule_id=finding.get("RuleID", "secret-detected"),
            message=f"Secret detected: {finding.get('Description', 'Potential secret found')}",
            description=finding.get("Match", ""),
            suggestion="Remove the secret and use environment variables or secret management",
        )
