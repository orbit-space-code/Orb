"""
Architecture analysis tool for understanding codebase structure
"""
import os
import ast
from typing import Dict, Any, List
from collections import defaultdict
from src.tools.registry import Tool


class ArchitectureAnalyzerTool(Tool):
    """Analyze codebase architecture and patterns"""
    
    def __init__(self):
        super().__init__(
            name="architecture_analyzer",
            description="Analyze codebase architecture, design patterns, and structure"
        )
    
    async def execute(
        self,
        workspace_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze architecture
        
        Args:
            workspace_path: Path to workspace
        """
        results = {
            "project_structure": await self._analyze_structure(workspace_path),
            "design_patterns": await self._detect_patterns(workspace_path),
            "complexity_metrics": await self._calculate_complexity(workspace_path),
            "code_statistics": await self._gather_statistics(workspace_path),
        }
        
        return results
    
    async def _analyze_structure(self, workspace_path: str) -> Dict[str, Any]:
        """Analyze project structure"""
        structure = {
            "directories": [],
            "key_files": [],
            "frameworks_detected": [],
        }
        
        # Detect frameworks
        if os.path.exists(os.path.join(workspace_path, "package.json")):
            structure["frameworks_detected"].append("Node.js")
            
            if os.path.exists(os.path.join(workspace_path, "next.config.js")):
                structure["frameworks_detected"].append("Next.js")
            elif os.path.exists(os.path.join(workspace_path, "angular.json")):
                structure["frameworks_detected"].append("Angular")
            elif any(f.startswith("vue.config") for f in os.listdir(workspace_path)):
                structure["frameworks_detected"].append("Vue.js")
        
        if os.path.exists(os.path.join(workspace_path, "requirements.txt")):
            structure["frameworks_detected"].append("Python")
            
            # Check for specific frameworks
            try:
                with open(os.path.join(workspace_path, "requirements.txt"), 'r') as f:
                    content = f.read().lower()
                    if "django" in content:
                        structure["frameworks_detected"].append("Django")
                    elif "flask" in content:
                        structure["frameworks_detected"].append("Flask")
                    elif "fastapi" in content:
                        structure["frameworks_detected"].append("FastAPI")
            except:
                pass
        
        # Analyze directory structure
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'dist', 'build']]
            
            rel_path = os.path.relpath(root, workspace_path)
            if rel_path != '.':
                structure["directories"].append(rel_path)
            
            # Identify key files
            for file in files:
                if file in ["README.md", "package.json", "requirements.txt", "Dockerfile", "docker-compose.yml"]:
                    structure["key_files"].append(os.path.join(rel_path, file))
        
        return structure
    
    async def _detect_patterns(self, workspace_path: str) -> Dict[str, List[str]]:
        """Detect design patterns"""
        patterns = defaultdict(list)
        
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules']]
            
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
                        # Detect Singleton pattern
                        if isinstance(node, ast.ClassDef):
                            for item in node.body:
                                if isinstance(item, ast.FunctionDef) and item.name == '__new__':
                                    patterns["Singleton"].append(f"{rel_path}:{node.name}")
                        
                        # Detect Factory pattern
                        if isinstance(node, ast.FunctionDef):
                            if 'factory' in node.name.lower() or 'create' in node.name.lower():
                                patterns["Factory"].append(f"{rel_path}:{node.name}")
                        
                        # Detect Decorator pattern
                        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                            if node.decorator_list:
                                patterns["Decorator"].append(f"{rel_path}:{node.name}")
                        
                        # Detect Observer pattern
                        if isinstance(node, ast.ClassDef):
                            method_names = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                            if 'subscribe' in method_names or 'notify' in method_names:
                                patterns["Observer"].append(f"{rel_path}:{node.name}")
                
                except Exception:
                    continue
        
        return dict(patterns)
    
    async def _calculate_complexity(self, workspace_path: str) -> Dict[str, Any]:
        """Calculate complexity metrics"""
        metrics = {
            "total_functions": 0,
            "total_classes": 0,
            "avg_function_length": 0,
            "max_function_length": 0,
            "complex_functions": [],  # Functions with high complexity
        }
        
        function_lengths = []
        
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules']]
            
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
                        if isinstance(node, ast.FunctionDef):
                            metrics["total_functions"] += 1
                            
                            # Calculate function length
                            if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
                                length = node.end_lineno - node.lineno
                                function_lengths.append(length)
                                
                                if length > metrics["max_function_length"]:
                                    metrics["max_function_length"] = length
                                
                                # Flag complex functions (>50 lines)
                                if length > 50:
                                    metrics["complex_functions"].append({
                                        "file": rel_path,
                                        "function": node.name,
                                        "lines": length,
                                    })
                        
                        elif isinstance(node, ast.ClassDef):
                            metrics["total_classes"] += 1
                
                except Exception:
                    continue
        
        if function_lengths:
            metrics["avg_function_length"] = sum(function_lengths) / len(function_lengths)
        
        return metrics
    
    async def _gather_statistics(self, workspace_path: str) -> Dict[str, Any]:
        """Gather code statistics"""
        stats = {
            "total_files": 0,
            "total_lines": 0,
            "files_by_type": defaultdict(int),
            "lines_by_type": defaultdict(int),
        }
        
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv']]
            
            for file in files:
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1]
                
                stats["total_files"] += 1
                stats["files_by_type"][ext] += 1
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        stats["total_lines"] += lines
                        stats["lines_by_type"][ext] += lines
                except:
                    continue
        
        stats["files_by_type"] = dict(stats["files_by_type"])
        stats["lines_by_type"] = dict(stats["lines_by_type"])
        
        return stats
