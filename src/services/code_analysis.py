"""
Code Analysis Service
Provides static and dynamic code analysis capabilities
"""
from typing import Dict, List, Optional, Any, Tuple
import ast
import astor
import subprocess
import re
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import json

class IssueSeverity(str, Enum):
    """Severity levels for code issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class CodeIssue:
    """Represents an issue found during code analysis"""
    file_path: str
    line: int
    column: int
    message: str
    severity: IssueSeverity
    rule_id: str
    category: str
    fix_suggestion: Optional[str] = None

class CodeAnalyzer:
    """Performs static and dynamic code analysis"""
    
    def __init__(self):
        self.ignored_patterns = [
            "__pycache__",
            "node_modules",
            ".git",
            "venv",
            "env"
        ]
    
    async def analyze_file(self, file_path: str) -> List[CodeIssue]:
        """Analyze a single file for issues"""
        issues = []
        
        # Skip ignored files/directories
        if any(pattern in file_path for pattern in self.ignored_patterns):
            return issues
            
        try:
            # Get file extension
            ext = Path(file_path).suffix.lower()
            
            # Dispatch to appropriate analyzer
            if ext == '.py':
                issues.extend(await self._analyze_python_file(file_path))
            elif ext in ('.js', '.jsx', '.ts', '.tsx'):
                issues.extend(await self._analyze_javascript_file(file_path))
            elif ext in ('.html', '.css'):
                issues.extend(await self._analyze_web_file(file_path))
                
        except Exception as e:
            issues.append(CodeIssue(
                file_path=file_path,
                line=0,
                column=0,
                message=f"Failed to analyze file: {str(e)}",
                severity=IssueSeverity.ERROR,
                rule_id="ANALYSIS_ERROR",
                category="analysis"
            ))
            
        return issues
    
    async def _analyze_python_file(self, file_path: str) -> List[CodeIssue]:
        """Analyze a Python file for issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse the AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                issues.append(CodeIssue(
                    file_path=file_path,
                    line=e.lineno,
                    column=e.offset or 0,
                    message=f"Syntax error: {e.msg}",
                    severity=IssueSeverity.ERROR,
                    rule_id="PYTHON_SYNTAX_ERROR",
                    category="syntax"
                ))
                return issues
                
            # Check for common issues
            for node in ast.walk(tree):
                # Check for bare except clauses
                if (isinstance(node, ast.ExceptHandler) and 
                        node.type is None and 
                        not any(isinstance(n, ast.Raise) for n in ast.walk(node))):
                    issues.append(CodeIssue(
                        file_path=file_path,
                        line=node.lineno,
                        column=node.col_offset,
                        message="Bare except clause used",
                        severity=IssueSeverity.WARNING,
                        rule_id="PYTHON_BARE_EXCEPT",
                        category="error_handling",
                        fix_suggestion="Specify the exception type to catch"
                    ))
                    
                # Check for hardcoded strings
                if (isinstance(node, ast.Str) and 
                        len(node.s) > 20 and 
                        not any(isinstance(parent, ast.Constant) for parent in ast.walk(node))):
                    issues.append(CodeIssue(
                        file_path=file_path,
                        line=node.lineno,
                        column=node.col_offset,
                        message="Consider moving long string to a constant",
                        severity=IssueSeverity.INFO,
                        rule_id="PYTHON_LONG_STRING",
                        category="maintainability"
                    ))
                    
        except Exception as e:
            issues.append(CodeIssue(
                file_path=file_path,
                line=0,
                column=0,
                message=f"Error analyzing Python file: {str(e)}",
                severity=IssueSeverity.ERROR,
                rule_id="PYTHON_ANALYSIS_ERROR",
                category="analysis"
            ))
            
        return issues
    
    async def _analyze_javascript_file(self, file_path: str) -> List[CodeIssue]:
        """Analyze a JavaScript/TypeScript file for issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for console.log statements
            for i, line in enumerate(content.split('\n'), 1):
                if 'console.log(' in line and not line.strip().startswith('//'):
                    issues.append(CodeIssue(
                        file_path=file_path,
                        line=i,
                        column=line.find('console.log(') + 1,
                        message="console.log statement found in production code",
                        severity=IssueSeverity.WARNING,
                        rule_id="JS_CONSOLE_LOG",
                        category="debugging",
                        fix_suggestion="Use a proper logging library in production code"
                    ))
                    
        except Exception as e:
            issues.append(CodeIssue(
                file_path=file_path,
                line=0,
                column=0,
                message=f"Error analyzing JavaScript file: {str(e)}",
                severity=IssueSeverity.ERROR,
                rule_id="JS_ANALYSIS_ERROR",
                category="analysis"
            ))
            
        return issues
    
    async def _analyze_web_file(self, file_path: str) -> List[CodeIssue]:
        """Analyze HTML/CSS files for issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            ext = Path(file_path).suffix.lower()
            
            if ext == '.html':
                # Check for missing alt attributes on images
                img_tags = re.finditer(r'<img[^>]*>', content)
                for match in img_tags:
                    if 'alt=' not in match.group(0):
                        line = content[:match.start()].count('\n') + 1
                        issues.append(CodeIssue(
                            file_path=file_path,
                            line=line,
                            column=match.start() - content[:match.start()].rfind('\n'),
                            message="Image missing alt attribute",
                            severity=IssueSeverity.WARNING,
                            rule_id="HTML_MISSING_ALT",
                            category="accessibility",
                            fix_suggestion="Add an alt attribute to the image tag"
                        ))
                        
            elif ext == '.css':
                # Check for !important usage
                for i, line in enumerate(content.split('\n'), 1):
                    if '!important' in line and not line.strip().startswith('/*'):
                        issues.append(CodeIssue(
                            file_path=file_path,
                            line=i,
                            column=line.find('!important') + 1,
                            message="!important flag used in CSS",
                            severity=IssueSeverity.WARNING,
                            rule_id="CSS_IMPORTANT_FLAG",
                            category="maintainability",
                            fix_suggestion="Avoid using !important, consider improving selector specificity"
                        ))
                        
        except Exception as e:
            issues.append(CodeIssue(
                file_path=file_path,
                line=0,
                column=0,
                message=f"Error analyzing web file: {str(e)}",
                severity=IssueSeverity.ERROR,
                rule_id="WEB_ANALYSIS_ERROR",
                category="analysis"
            ))
            
        return issues
    
    async def analyze_directory(self, directory: str) -> Dict[str, List[CodeIssue]]:
        """Analyze all files in a directory"""
        issues = {}
        
        for file_path in Path(directory).rglob('*'):
            if file_path.is_file():
                file_issues = await self.analyze_file(str(file_path))
                if file_issues:
                    issues[str(file_path)] = file_issues
                    
        return issues
    
    async def get_code_metrics(self, file_path: str) -> Dict[str, Any]:
        """Get code metrics for a file"""
        metrics = {
            "file_path": file_path,
            "lines_of_code": 0,
            "functions": 0,
            "classes": 0,
            "complexity": 0,
            "imports": 0,
            "dependencies": []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Basic metrics
            metrics["lines_of_code"] = len(content.split('\n'))
            
            # Language-specific metrics
            if file_path.endswith('.py'):
                tree = ast.parse(content)
                
                # Count functions and classes
                metrics["functions"] = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
                metrics["classes"] = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
                
                # Count imports
                metrics["imports"] = sum(1 for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)))
                
                # Extract imports for dependency analysis
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        metrics["dependencies"].extend(alias.name for alias in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            metrics["dependencies"].append(node.module)
                            
        except Exception as e:
            metrics["error"] = str(e)
            
        return metrics

# Singleton instance
code_analyzer = CodeAnalyzer()
