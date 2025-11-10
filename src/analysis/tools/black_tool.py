"""
Black tool for Python code formatting checks
"""
import asyncio
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


class BlackTool(AnalysisTool):
    """Black Python code formatter checker"""
    
    def __init__(self):
        super().__init__()
        self.name = "black"
        self.version = "23.0.0"
        self.supported_languages = ["python"]
        self.supported_extensions = [".py"]
    
    async def is_available(self) -> bool:
        """Check if Black is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "black", "--version",
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
        """Execute Black check on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build Black command (check mode)
            cmd = [
                "black",
                ".",
                "--check",
                "--diff",
            ]
            
            # Add config file if specified
            if config and "config_file" in config:
                cmd.extend(["--config", config["config_file"]])
            
            # Execute Black
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
                # Black outputs "would reformat" messages
                output = stdout.decode()
                for line in output.split("\n"):
                    if "would reformat" in line:
                        # Extract file path
                        parts = line.split()
                        if len(parts) >= 2:
                            file_path = parts[2] if len(parts) > 2 else parts[1]
                            issues.append(self._create_issue(file_path))
                            files_analyzed += 1
                            
                            # Count lines
                            full_path = Path(codebase_path) / file_path
                            if full_path.exists():
                                try:
                                    lines_analyzed += len(full_path.read_text().splitlines())
                                except:
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
    
    def _create_issue(self, file_path: str) -> Issue:
        """Create issue for unformatted file"""
        return Issue(
            file_path=file_path,
            line_number=None,
            column=None,
            severity=Severity.LOW,
            category=IssueCategory.STYLE,
            rule_id="black/format",
            message="File is not formatted according to Black rules",
            suggestion="Run 'black' to format this file",
        )
