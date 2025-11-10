"""
Semantic code search tool using AST and pattern matching
"""
import os
import ast
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from src.tools.registry import Tool


class SemanticSearchTool(Tool):
    """Search code semantically using AST analysis"""
    
    def __init__(self):
        super().__init__(
            name="semantic_search",
            description="Search code semantically by function names, class names, imports, and patterns"
        )
    
    async def execute(
        self,
        workspace_path: str,
        query_type: str,
        query: str,
        language: str = "python",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search code semantically
        
        Args:
            workspace_path: Path to workspace
            query_type: Type of search (function, class, import, variable, decorator)
            query: Search query (name or pattern)
            language: Programming language (python, javascript, etc.)
        """
        results = []
        
        if language == "python":
            results = await self._search_python(workspace_path, query_type, query)
        elif language in ["javascript", "typescript"]:
            results = await self._search_javascript(workspace_path, query_type, query)
        
        return {
            "query_type": query_type,
            "query": query,
            "language": language,
            "results": results,
            "count": len(results),
        }
    
    async def _search_python(
        self,
        workspace_path: str,
        query_type: str,
        query: str,
    ) -> List[Dict[str, Any]]:
        """Search Python code using AST"""
        results = []
        
        for root, dirs, files in os.walk(workspace_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, workspace_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    tree = ast.parse(content)
                    
                    for node in ast.walk(tree):
                        match = None
                        
                        if query_type == "function" and isinstance(node, ast.FunctionDef):
                            if query.lower() in node.name.lower():
                                match = {
                                    "type": "function",
                                    "name": node.name,
                                    "line": node.lineno,
                                    "args": [arg.arg for arg in node.args.args],
                                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                                }
                        
                        elif query_type == "class" and isinstance(node, ast.ClassDef):
                            if query.lower() in node.name.lower():
                                bases = [self._get_name(base) for base in node.bases]
                                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                                match = {
                                    "type": "class",
                                    "name": node.name,
                                    "line": node.lineno,
                                    "bases": bases,
                                    "methods": methods[:5],  # First 5 methods
                                }
                        
                        elif query_type == "import" and isinstance(node, (ast.Import, ast.ImportFrom)):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    if query.lower() in alias.name.lower():
                                        match = {
                                            "type": "import",
                                            "module": alias.name,
                                            "alias": alias.asname,
                                            "line": node.lineno,
                                        }
                            elif isinstance(node, ast.ImportFrom):
                                if query.lower() in (node.module or "").lower():
                                    match = {
                                        "type": "import_from",
                                        "module": node.module,
                                        "names": [alias.name for alias in node.names],
                                        "line": node.lineno,
                                    }
                        
                        elif query_type == "decorator":
                            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                                for decorator in node.decorator_list:
                                    dec_name = self._get_decorator_name(decorator)
                                    if query.lower() in dec_name.lower():
                                        match = {
                                            "type": "decorated_" + ("function" if isinstance(node, ast.FunctionDef) else "class"),
                                            "name": node.name,
                                            "decorator": dec_name,
                                            "line": node.lineno,
                                        }
                        
                        if match:
                            match["file"] = rel_path
                            results.append(match)
                
                except Exception as e:
                    continue
        
        return results
    
    async def _search_javascript(
        self,
        workspace_path: str,
        query_type: str,
        query: str,
    ) -> List[Dict[str, Any]]:
        """Search JavaScript/TypeScript code (basic pattern matching)"""
        results = []
        extensions = ['.js', '.jsx', '.ts', '.tsx']
        
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'dist', 'build']]
            
            for file in files:
                if not any(file.endswith(ext) for ext in extensions):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, workspace_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for i, line in enumerate(lines, 1):
                        match = None
                        
                        if query_type == "function":
                            if f"function {query}" in line or f"const {query} =" in line or f"let {query} =" in line:
                                match = {
                                    "type": "function",
                                    "name": query,
                                    "line": i,
                                    "code": line.strip(),
                                }
                        
                        elif query_type == "class":
                            if f"class {query}" in line:
                                match = {
                                    "type": "class",
                                    "name": query,
                                    "line": i,
                                    "code": line.strip(),
                                }
                        
                        elif query_type == "import":
                            if "import" in line and query in line:
                                match = {
                                    "type": "import",
                                    "line": i,
                                    "code": line.strip(),
                                }
                        
                        if match:
                            match["file"] = rel_path
                            results.append(match)
                
                except Exception:
                    continue
        
        return results
    
    def _get_name(self, node):
        """Get name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)
    
    def _get_decorator_name(self, node):
        """Get decorator name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return "unknown"
