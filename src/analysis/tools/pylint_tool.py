"""
Pylint tool for Python analysis
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


class PylintTool(AnalysisTool):
    """Pylint static analysis tool for Python"""
    
    def __init__(self):
        super().__init__()
        self.name = "pylint"
        self.version = "3.0.0"
        self.supported_languages = ["python"]
        self.supported_extensions = [".py"]
    
    async def is_available(self) -> bool:
        """Check if Pylint is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "pylint", "--version",
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
        """Execute Pylint on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build Pylint command
            cmd = [
                "pylint",
                ".",
                "--output-format=json",
                "--recursive=y",
            ]
            
            # Add config file if specified
            if config and "rcfile" in config:
                cmd.extend(["--rcfile", config["rcfile"]])
            
            # Execute Pylint
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
            files_analyzed = set()
            lines_analyzed = 0
            
            if stdout:
                try:
                    results = json.loads(stdout.decode())
                    for message in results:
                        issues.append(self._parse_issue(message))
                        files_analyzed.add(message.get("path", ""))
                    
                    # Count total lines
                    for file_path in files_analyzed:
                        full_path = Path(codebase_path) / file_path
                        if full_path.exists():
                            lines_analyzed += len(full_path.read_text().splitlines())
                            
                except json.JSONDecodeError:
                    pass
            
            execution_time = int((completed_at - started_at).total_seconds() * 1000)
            
            metrics = ToolMetrics(
                execution_time_ms=execution_time,
                files_analyzed=len(files_analyzed),
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
    
    def _parse_issue(self, message: Dict) -> Issue:
        """Parse Pylint message into Issue"""
        severity_map = {
            "fatal": Severity.CRITICAL,
            "error": Severity.HIGH,
            "warning": Severity.MEDIUM,
            "convention": Severity.LOW,
            "refactor": Severity.LOW,
            "info": Severity.INFO,
        }
        
        category_map = {
            "C": IssueCategory.STYLE,  # Convention
            "R": IssueCategory.CODE_SMELL,  # Refactor
            "W": IssueCategory.BUG,  # Warning
            "E": IssueCategory.BUG,  # Error
            "F": IssueCategory.BUG,  # Fatal
        }
        
        msg_type = message.get("type", "warning")
        msg_id = message.get("message-id", "")
        category = category_map.get(msg_id[0] if msg_id else "W", IssueCategory.CODE_SMELL)
        
        return Issue(
            file_path=message.get("path", ""),
            line_number=message.get("line"),
            column=message.get("column"),
            severity=severity_map.get(msg_type, Severity.MEDIUM),
            category=category,
            rule_id=msg_id,
            message=message.get("message", ""),
            description=message.get("symbol", ""),
        )
