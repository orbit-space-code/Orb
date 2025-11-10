"""
ESLint tool for JavaScript/TypeScript analysis
"""
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..base_tool import (
    AnalysisTool,
    ToolResult,
    ToolMetrics,
    Issue,
    Severity,
    IssueCategory,
)


class ESLintTool(AnalysisTool):
    """ESLint static analysis tool"""
    
    def __init__(self):
        super().__init__()
        self.name = "eslint"
        self.version = "8.56.0"
        self.supported_languages = ["javascript", "typescript"]
        self.supported_extensions = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]
    
    async def is_available(self) -> bool:
        """Check if ESLint is installed"""
        try:
            process = await asyncio.create_subprocess_exec(
                "npx", "eslint", "--version",
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
        """Execute ESLint on the codebase"""
        started_at = datetime.now()
        
        try:
            # Build ESLint command
            cmd = [
                "npx", "eslint",
                ".",
                "--format", "json",
                "--ext", ",".join(self.supported_extensions),
            ]
            
            # Add config file if specified
            if config and "config_file" in config:
                cmd.extend(["--config", config["config_file"]])
            
            # Execute ESLint
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
                    for file_result in results:
                        files_analyzed += 1
                        for message in file_result.get("messages", []):
                            issues.append(self._parse_issue(file_result, message))
                            
                        # Count lines in file
                        file_path = Path(file_result["filePath"])
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
    
    def _parse_issue(self, file_result: Dict, message: Dict) -> Issue:
        """Parse ESLint message into Issue"""
        severity_map = {
            2: Severity.HIGH,  # error
            1: Severity.MEDIUM,  # warning
            0: Severity.INFO,  # off
        }
        
        return Issue(
            file_path=file_result["filePath"],
            line_number=message.get("line"),
            column=message.get("column"),
            severity=severity_map.get(message.get("severity", 1), Severity.MEDIUM),
            category=IssueCategory.CODE_SMELL,
            rule_id=message.get("ruleId", "unknown"),
            message=message.get("message", ""),
            suggestion=message.get("fix", {}).get("text") if message.get("fix") else None,
        )
