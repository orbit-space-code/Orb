"""
Snyk tool for dependency vulnerability scanning
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


class SnykTool(AnalysisTool):
    """Snyk vulnerability scanner"""
    
    def __init__(self):
        super().__init__()
        self.name = "snyk"
        self.version = "1.1292.0"
        self.supported_languages = ["javascript", "typescript", "python", "java", "ruby", "go"]
        self.supported_extensions = []  # Works on dependency files
    
    async def is_available(self) -> bool:
        """Check if Snyk is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "snyk", "--version",
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
        """Execute Snyk on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build Snyk command
            cmd = [
                "snyk", "test",
                "--json",
            ]
            
            # Add severity threshold if specified
            if config and "severity_threshold" in config:
                cmd.extend(["--severity-threshold", config["severity_threshold"]])
            
            # Execute Snyk
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
            
            if stdout:
                try:
                    results = json.loads(stdout.decode())
                    
                    # Count dependencies
                    files_analyzed = results.get("dependencyCount", 0)
                    
                    # Parse vulnerabilities
                    for vuln in results.get("vulnerabilities", []):
                        issues.append(self._parse_issue(vuln))
                        
                except json.JSONDecodeError:
                    pass
            
            execution_time = int((completed_at - started_at).total_seconds() * 1000)
            
            metrics = ToolMetrics(
                execution_time_ms=execution_time,
                files_analyzed=files_analyzed,
                lines_analyzed=0,  # N/A for dependency scanning
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
        """Parse Snyk vulnerability into Issue"""
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
        }
        
        package_name = vuln.get("packageName", "unknown")
        version = vuln.get("version", "")
        
        return Issue(
            file_path=f"dependency: {package_name}@{version}",
            line_number=None,
            column=None,
            severity=severity_map.get(vuln.get("severity", "medium"), Severity.MEDIUM),
            category=IssueCategory.SECURITY,
            rule_id=vuln.get("id", ""),
            message=vuln.get("title", ""),
            description=vuln.get("description", ""),
            suggestion=f"Upgrade to {vuln.get('fixedIn', ['latest'])[0]}" if vuln.get("fixedIn") else None,
        )
