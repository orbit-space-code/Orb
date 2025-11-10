"""
Prettier tool for code formatting checks
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


class PrettierTool(AnalysisTool):
    """Prettier code formatter checker"""
    
    def __init__(self):
        super().__init__()
        self.name = "prettier"
        self.version = "3.0.0"
        self.supported_languages = ["javascript", "typescript", "css", "html", "json", "markdown"]
        self.supported_extensions = [
            ".js", ".jsx", ".ts", ".tsx", ".css", ".scss", ".html",
            ".json", ".md", ".yaml", ".yml"
        ]
    
    async def is_available(self) -> bool:
        """Check if Prettier is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "npx", "prettier", "--version",
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
        """Execute Prettier check on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build Prettier command (check mode)
            cmd = [
                "npx", "prettier",
                ".",
                "--check",
                "--list-different",
            ]
            
            # Add config file if specified
            if config and "config_file" in config:
                cmd.extend(["--config", config["config_file"]])
            
            # Execute Prettier
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
                # Prettier outputs list of files that need formatting
                unformatted_files = stdout.decode().strip().split("\n")
                for file_path in unformatted_files:
                    if file_path:
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
            rule_id="prettier/format",
            message="File is not formatted according to Prettier rules",
            suggestion="Run 'prettier --write' to format this file",
        )
