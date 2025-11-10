"""
Flake8 tool for Python style checking
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


class Flake8Tool(AnalysisTool):
    """Flake8 Python style checker"""
    
    def __init__(self):
        super().__init__()
        self.name = "flake8"
        self.version = "6.1.0"
        self.supported_languages = ["python"]
        self.supported_extensions = [".py"]
    
    async def is_available(self) -> bool:
        """Check if Flake8 is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "flake8", "--version",
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
        """Execute Flake8 on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build Flake8 command
            cmd = [
                "flake8",
                ".",
                "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
            ]
            
            # Add config file if specified
            if config and "config_file" in config:
                cmd.extend(["--config", config["config_file"]])
            
            # Execute Flake8
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
                for line in stdout.decode().splitlines():
                    if line.strip():
                        issue = self._parse_line(line)
                        if issue:
                            issues.append(issue)
                            files_analyzed.add(issue.file_path)
                
                # Count lines in analyzed files
                for file_path in files_analyzed:
                    full_path = Path(codebase_path) / file_path
                    if full_path.exists():
                        try:
                            lines_analyzed += len(full_path.read_text().splitlines())
                        except:
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
    
    def _parse_line(self, line: str) -> Optional[Issue]:
        """Parse Flake8 output line into Issue"""
        try:
            # Format: path:line:col: code message
            parts = line.split(":", 3)
            if len(parts) < 4:
                return None
            
            file_path = parts[0]
            line_number = int(parts[1])
            column = int(parts[2])
            
            # Parse code and message
            message_parts = parts[3].strip().split(" ", 1)
            code = message_parts[0]
            message = message_parts[1] if len(message_parts) > 1 else ""
            
            # Determine severity based on code
            if code.startswith("E9") or code.startswith("F"):
                severity = Severity.HIGH
            elif code.startswith("E"):
                severity = Severity.MEDIUM
            elif code.startswith("W"):
                severity = Severity.LOW
            else:
                severity = Severity.INFO
            
            return Issue(
                file_path=file_path,
                line_number=line_number,
                column=column,
                severity=severity,
                category=IssueCategory.STYLE,
                rule_id=code,
                message=message,
            )
        except Exception:
            return None
