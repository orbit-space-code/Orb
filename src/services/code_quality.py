import ast
import astor
import re
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import tokenize
import io

class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class CodeIssue:
    """Represents an issue found during code analysis"""
    message: str
    severity: IssueSeverity
    line: int
    col: int = 0
    end_line: Optional[int] = None
    end_col: Optional[int] = None
    code: str = ""
    suggestion: Optional[str] = None
    category: str = "code_quality"

class CodeQualityAnalyzer:
    """Performs static code analysis and quality checks"""
    
    def __init__(self, language: str = "python"):
        self.language = language
        self._cache: Dict[str, Any] = {}
    
    async def analyze(
        self, 
        code: str, 
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze code for quality issues and metrics
        
        Args:
            code: Source code to analyze
            file_path: Optional file path for context
            
        Returns:
            Dictionary containing analysis results
        """
        if not code.strip():
            return {
                "valid": False,
                "issues": [{
                    "message": "Empty file",
                    "severity": IssueSeverity.WARNING,
                    "line": 1,
                    "col": 1
                }],
                "metrics": {}
            }
        
        # Check syntax first
        syntax_check = await self.check_syntax(code)
        if not syntax_check["valid"]:
            return syntax_check
        
        # Get AST for further analysis
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return self._create_syntax_error(e)
        
        # Run all checks
        issues: List[Dict[str, Any]] = []
        
        # Run basic checks
        issues.extend(await self.check_complexity(tree))
        issues.extend(await self.check_style(code, file_path))
        issues.extend(await self.check_security(tree))
        issues.extend(await self.check_performance(tree))
        
        # Calculate metrics
        metrics = await self.calculate_metrics(code, tree)
        
        return {
            "valid": True,
            "issues": issues,
            "metrics": metrics
        }
    
    async def check_syntax(self, code: str) -> Dict[str, Any]:
        """Check for syntax errors"""
        try:
            ast.parse(code)
            return {"valid": True}
        except SyntaxError as e:
            return self._create_syntax_error(e)
    
    async def check_complexity(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check code complexity metrics"""
        class ComplexityVisitor(ast.NodeVisitor):
            def __init__(self):
                self.issues: List[Dict[str, Any]] = []
                self.complexity = 1
                
            def visit_If(self, node):
                self.complexity += 1
                self.generic_visit(node)
                
            def visit_For(self, node):
                self.complexity += 1
                self.generic_visit(node)
                
            def visit_While(self, node):
                self.complexity += 1
                self.generic_visit(node)
                
            def visit_With(self, node):
                self.complexity += 1
                self.generic_visit(node)
                
            def visit_Try(self, node):
                self.complexity += 1
                self.generic_visit(node)
                
            def visit_FunctionDef(self, node):
                # Check function complexity
                func_complexity = 1
                for n in ast.walk(node):
                    if isinstance(n, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                        func_complexity += 1
                
                if func_complexity > 10:  # Threshold for high complexity
                    self.issues.append({
                        "message": f"Function '{node.name}' is too complex (complexity={func_complexity})",
                        "severity": IssueSeverity.WARNING,
                        "line": node.lineno,
                        "col": node.col_offset,
                        "code": ast.get_source_segment("", node) or "",
                        "suggestion": "Refactor into smaller functions"
                    })
                self.generic_visit(node)
        
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        return visitor.issues
    
    async def check_style(self, code: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Check code style issues"""
        issues: List[Dict[str, Any]] = []
        lines = code.splitlines()
        
        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > 100:  # PEP 8 recommends 79, but 100 is common
                issues.append({
                    "message": f"Line too long ({len(line)} > 100 characters)",
                    "severity": IssueSeverity.WARNING,
                    "line": i,
                    "col": 0,
                    "code": line,
                    "suggestion": "Break the line into multiple lines"
                })
        
        # Check for trailing whitespace
        for i, line in enumerate(lines, 1):
            if line.endswith(' '):
                issues.append({
                    "message": "Trailing whitespace",
                    "severity": IssueSeverity.INFO,
                    "line": i,
                    "col": len(line.rstrip()),
                    "code": line,
                    "suggestion": "Remove trailing whitespace"
                })
        
        # Check for mixed tabs and spaces
        if '\t' in code and '    ' in code:
            issues.append({
                "message": "Mixed tabs and spaces",
                "severity": IssueSeverity.WARNING,
                "line": 1,
                "col": 0,
                "suggestion": "Use either tabs or spaces for indentation, not both"
            })
        
        return issues
    
    async def check_security(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for common security issues"""
        issues: List[Dict[str, Any]] = []
        
        class SecurityVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                # Check for potentially dangerous functions
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in ('eval', 'exec', 'execfile', 'input'):
                        issues.append({
                            "message": f"Use of potentially dangerous function: {func_name}",
                            "severity": IssueSeverity.ERROR,
                            "line": node.lineno,
                            "col": node.col_offset,
                            "code": ast.get_source_segment("", node) or "",
                            "suggestion": f"Avoid using {func_name} with untrusted input"
                        })
                self.generic_visit(node)
        
        SecurityVisitor().visit(tree)
        return issues
    
    async def check_performance(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Check for potential performance issues"""
        issues: List[Dict[str, Any]] = []
        
        class PerformanceVisitor(ast.NodeVisitor):
            def visit_For(self, node):
                # Check for range(len(...)) pattern which is often suboptimal
                if (isinstance(node.iter, ast.Call) and 
                    isinstance(node.iter.func, ast.Name) and 
                    node.iter.func.id == 'range' and 
                    len(node.iter.args) == 1 and
                    isinstance(node.iter.args[0], ast.Call) and
                    isinstance(node.iter.args[0].func, ast.Name) and
                    node.iter.args[0].func.id == 'len'):
                    
                    issues.append({
                        "message": "Potentially suboptimal loop using range(len(...))",
                        "severity": IssueSeverity.INFO,
                        "line": node.lineno,
                        "col": node.col_offset,
                        "code": ast.get_source_segment("", node) or "",
                        "suggestion": "Consider using enumerate() or direct iteration"
                    })
                self.generic_visit(node)
        
        PerformanceVisitor().visit(tree)
        return issues
    
    async def calculate_metrics(self, code: str, tree: ast.AST) -> Dict[str, Any]:
        """Calculate code metrics"""
        class MetricsVisitor(ast.NodeVisitor):
            def __init__(self):
                self.function_count = 0
                self.class_count = 0
                self.complexity = 1
                self.imports: Set[str] = set()
                self.variables: Set[str] = set()
                
            def visit_FunctionDef(self, node):
                self.function_count += 1
                self.generic_visit(node)
                
            def visit_ClassDef(self, node):
                self.class_count += 1
                self.generic_visit(node)
                
            def visit_If(self, node):
                self.complexity += 1
                self.generic_visit(node)
                
            def visit_For(self, node):
                self.complexity += 1
                self.generic_visit(node)
                
            def visit_While(self, node):
                self.complexity += 1
                self.generic_visit(node)
                
            def visit_Import(self, node):
                for name in node.names:
                    self.imports.add(name.name)
                self.generic_visit(node)
                
            def visit_ImportFrom(self, node):
                if node.module:
                    for name in node.names:
                        self.imports.add(f"{node.module}.{name.name}")
                self.generic_visit(node)
                
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    self.variables.add(node.id)
                self.generic_visit(node)
        
        visitor = MetricsVisitor()
        visitor.visit(tree)
        
        lines = code.splitlines()
        loc = len([line for line in lines if line.strip()])
        lloc = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
        
        return {
            "lines_of_code": loc,
            "logical_lines": lloc,
            "function_count": visitor.function_count,
            "class_count": visitor.class_count,
            "complexity": visitor.complexity,
            "imports": sorted(list(visitor.imports)),
            "variables": sorted(list(visitor.variables)),
            "comment_ratio": (loc - lloc) / loc if loc > 0 else 0
        }
    
    def _create_syntax_error(self, error: SyntaxError) -> Dict[str, Any]:
        """Create a response for a syntax error"""
        return {
            "valid": False,
            "issues": [{
                "message": f"Syntax error: {error.msg}",
                "severity": IssueSeverity.ERROR,
                "line": error.lineno or 1,
                "col": error.offset or 1,
                "code": error.text or ""
            }],
            "metrics": {}
        }
