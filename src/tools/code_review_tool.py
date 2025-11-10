"""
AI-powered code review tool
"""
import os
import ast
from typing import Dict, Any, List
from src.tools.registry import Tool


class CodeReviewTool(Tool):
    """AI-powered code review and suggestions"""
    
    def __init__(self):
        super().__init__(
            name="code_review",
            description="Perform automated code review and generate suggestions"
        )
    
    async def execute(
        self,
        workspace_path: str,
        target_file: str,
        review_type: str = "comprehensive",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform code review
        
        Args:
            workspace_path: Path to workspace
            target_file: File to review
            review_type: Type of review (comprehensive, security, performance, style)
        """
        file_path = os.path.join(workspace_path, target_file)
        
        if not os.path.exists(file_path):
            return {"error": f"File not found: {target_file}"}
        
        issues = []
        suggestions = []
        
        if review_type in ["comprehensive", "style"]:
            issues.extend(await self._check_style(file_path))
        
        if review_type in ["comprehensive", "security"]:
            issues.extend(await self._check_security(file_path))
        
        if review_type in ["comprehensive", "performance"]:
            issues.extend(await self._check_performance(file_path))
        
        # Generate suggestions
        suggestions = await self._generate_suggestions(issues)
        
        return {
            "file": target_file,
            "review_type": review_type,
            "issues_found": len(issues),
            "issues": issues,
            "suggestions": suggestions,
            "overall_score": self._calculate_score(issues),
        }
    
    async def _check_style(self, file_path: str) -> List[Dict[str, Any]]:
        """Check code style issues"""
        issues = []
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                # Check line length
                if len(line) > 100:
                    issues.append({
                        "line": i,
                        "severity": "low",
                        "category": "style",
                        "message": f"Line too long ({len(line)} > 100 characters)",
                    })
                
                # Check trailing whitespace
                if line.rstrip() != line.rstrip('\n').rstrip('\r'):
                    issues.append({
                        "line": i,
                        "severity": "low",
                        "category": "style",
                        "message": "Trailing whitespace",
                    })
                
                # Check multiple blank lines
                if i > 1 and not line.strip() and not lines[i-2].strip():
                    issues.append({
                        "line": i,
                        "severity": "low",
                        "category": "style",
                        "message": "Multiple consecutive blank lines",
                    })
        
        except Exception:
            pass
        
        return issues
    
    async def _check_security(self, file_path: str) -> List[Dict[str, Any]]:
        """Check security issues"""
        issues = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Check for hardcoded secrets
            secret_patterns = [
                ('password', 'Possible hardcoded password'),
                ('api_key', 'Possible hardcoded API key'),
                ('secret', 'Possible hardcoded secret'),
                ('token', 'Possible hardcoded token'),
            ]
            
            for i, line in enumerate(lines, 1):
                for pattern, message in secret_patterns:
                    if pattern in line.lower() and '=' in line:
                        issues.append({
                            "line": i,
                            "severity": "high",
                            "category": "security",
                            "message": message,
                        })
            
            # Check for eval() usage
            if 'eval(' in content:
                issues.append({
                    "line": None,
                    "severity": "critical",
                    "category": "security",
                    "message": "Use of eval() is dangerous",
                })
            
            # Check for exec() usage
            if 'exec(' in content:
                issues.append({
                    "line": None,
                    "severity": "critical",
                    "category": "security",
                    "message": "Use of exec() is dangerous",
                })
        
        except Exception:
            pass
        
        return issues
    
    async def _check_performance(self, file_path: str) -> List[Dict[str, Any]]:
        """Check performance issues"""
        issues = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Check for nested loops
                if isinstance(node, (ast.For, ast.While)):
                    for child in ast.walk(node):
                        if child != node and isinstance(child, (ast.For, ast.While)):
                            issues.append({
                                "line": node.lineno,
                                "severity": "medium",
                                "category": "performance",
                                "message": "Nested loops detected - consider optimization",
                            })
                            break
                
                # Check for list comprehension opportunities
                if isinstance(node, ast.For):
                    # Simple heuristic: for loop with single append
                    if len(node.body) == 1:
                        stmt = node.body[0]
                        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                            if hasattr(stmt.value.func, 'attr') and stmt.value.func.attr == 'append':
                                issues.append({
                                    "line": node.lineno,
                                    "severity": "low",
                                    "category": "performance",
                                    "message": "Consider using list comprehension",
                                })
        
        except Exception:
            pass
        
        return issues
    
    async def _generate_suggestions(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []
        
        # Count issues by category
        categories = {}
        for issue in issues:
            cat = issue["category"]
            categories[cat] = categories.get(cat, 0) + 1
        
        # Generate suggestions based on issues
        if categories.get("style", 0) > 5:
            suggestions.append("Consider running a code formatter (black, prettier) to fix style issues")
        
        if categories.get("security", 0) > 0:
            suggestions.append("Review security issues immediately - consider using environment variables for secrets")
        
        if categories.get("performance", 0) > 3:
            suggestions.append("Multiple performance issues detected - consider profiling and optimization")
        
        if not suggestions:
            suggestions.append("Code looks good! Consider adding more tests and documentation")
        
        return suggestions
    
    def _calculate_score(self, issues: List[Dict[str, Any]]) -> float:
        """Calculate overall code quality score (0-100)"""
        if not issues:
            return 100.0
        
        # Deduct points based on severity
        score = 100.0
        severity_weights = {
            "critical": 20,
            "high": 10,
            "medium": 5,
            "low": 2,
        }
        
        for issue in issues:
            severity = issue.get("severity", "low")
            score -= severity_weights.get(severity, 2)
        
        return max(0.0, score)
