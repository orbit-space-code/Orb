"""
RuboCop tool for Ruby analysis
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


class RubocopTool(AnalysisTool):
    """RuboCop static analysis tool for Ruby"""
    
    def __init__(self):
        super().__init__()
        self.name = "rubocop"
        self.version = "1.57.0"
        self.supported_languages = ["ruby"]
        self.supported_extensions = [".rb", ".rake"]
    
    async def is_available(self) -> bool:
        """Check if RuboCop is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "rubocop", "--version",
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
        """Execute RuboCop on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build RuboCop command
            cmd = [
                "rubocop",
                ".",
                "--format", "json",
            ]
            
            # Add config file if specified
            if config and "config_file" in config:
                cmd.extend(["--config", config["config_file"]])
            
            # Execute RuboCop
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
                    
                    for file_result in results.get("files", []):
                        files_analyzed += 1
                        
                        # Parse offenses
                        for offense in file_result.get("offenses", []):
                            issues.append(self._parse_issue(file_result["path"], offense))
                        
                        # Count lines
                        file_path = Path(codebase_path) / file_result["path"]
                        if file_path.exists():
                            lines_analyzed += len(file_path.read_text().splitlines())
                            
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
    
    def _parse_issue(self, file_path: str, offense: Dict) -> Issue:
        """Parse RuboCop offense into Issue"""
        severity_map = {
            "fatal": Severity.CRITICAL,
            "error": Severity.HIGH,
            "warning": Severity.MEDIUM,
            "convention": Severity.LOW,
            "refactor": Severity.LOW,
            "info": Severity.INFO,
        }
        
        return Issue(
            file_path=file_path,
            line_number=offense.get("location", {}).get("line"),
            column=offense.get("location", {}).get("column"),
            severity=severity_map.get(offense.get("severity", "warning"), Severity.MEDIUM),
            category=IssueCategory.CODE_SMELL,
            rule_id=offense.get("cop_name", "unknown"),
            message=offense.get("message", ""),
            suggestion=offense.get("correctable") and "Auto-correctable with rubocop -a",
        )
