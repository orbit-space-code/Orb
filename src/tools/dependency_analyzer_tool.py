"""
Dependency analysis tool for understanding project dependencies
"""
import os
import json
import re
from typing import Dict, Any, List, Set
from pathlib import Path
from src.tools.registry import Tool


class DependencyAnalyzerTool(Tool):
    """Analyze project dependencies and their relationships"""
    
    def __init__(self):
        super().__init__(
            name="dependency_analyzer",
            description="Analyze project dependencies, imports, and module relationships"
        )
    
    async def execute(
        self,
        workspace_path: str,
        analysis_type: str = "all",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analyze dependencies
        
        Args:
            workspace_path: Path to workspace
            analysis_type: Type of analysis (all, npm, pip, imports, graph)
        """
        results = {
            "npm_dependencies": {},
            "python_dependencies": {},
            "import_graph": {},
            "circular_dependencies": [],
            "unused_dependencies": [],
        }
        
        if analysis_type in ["all", "npm"]:
            results["npm_dependencies"] = await self._analyze_npm(workspace_path)
        
        if analysis_type in ["all", "pip"]:
            results["python_dependencies"] = await self._analyze_pip(workspace_path)
        
        if analysis_type in ["all", "imports", "graph"]:
            results["import_graph"] = await self._analyze_imports(workspace_path)
            results["circular_dependencies"] = self._find_circular_deps(results["import_graph"])
        
        return results
    
    async def _analyze_npm(self, workspace_path: str) -> Dict[str, Any]:
        """Analyze NPM dependencies"""
        package_json_path = os.path.join(workspace_path, "package.json")
        
        if not os.path.exists(package_json_path):
            return {"error": "package.json not found"}
        
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            dependencies = package_data.get("dependencies", {})
            dev_dependencies = package_data.get("devDependencies", {})
            
            return {
                "total_dependencies": len(dependencies),
                "total_dev_dependencies": len(dev_dependencies),
                "dependencies": dependencies,
                "dev_dependencies": dev_dependencies,
                "scripts": package_data.get("scripts", {}),
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _analyze_pip(self, workspace_path: str) -> Dict[str, Any]:
        """Analyze Python dependencies"""
        requirements_files = [
            "requirements.txt",
            "requirements-dev.txt",
            "setup.py",
            "pyproject.toml",
        ]
        
        dependencies = []
        
        for req_file in requirements_files:
            req_path = os.path.join(workspace_path, req_file)
            if os.path.exists(req_path):
                try:
                    with open(req_path, 'r') as f:
                        content = f.read()
                    
                    if req_file.endswith('.txt'):
                        # Parse requirements.txt
                        for line in content.splitlines():
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Extract package name and version
                                match = re.match(r'([a-zA-Z0-9\-_]+)([>=<~!]+.*)?', line)
                                if match:
                                    dependencies.append({
                                        "name": match.group(1),
                                        "version": match.group(2) or "any",
                                        "source": req_file,
                                    })
                except Exception:
                    continue
        
        return {
            "total_dependencies": len(dependencies),
            "dependencies": dependencies,
        }
    
    async def _analyze_imports(self, workspace_path: str) -> Dict[str, List[str]]:
        """Analyze import relationships"""
        import_graph = {}
        
        # Analyze Python imports
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv']]
            
            for file in files:
                if not file.endswith('.py'):
                    continue
                
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, workspace_path)
                module_name = rel_path.replace(os.sep, '.').replace('.py', '')
                
                imports = set()
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            
                            # Match: import module
                            if line.startswith('import '):
                                parts = line.split()
                                if len(parts) >= 2:
                                    imports.add(parts[1].split('.')[0])
                            
                            # Match: from module import ...
                            elif line.startswith('from '):
                                match = re.match(r'from\s+([a-zA-Z0-9_.]+)', line)
                                if match:
                                    imports.add(match.group(1).split('.')[0])
                    
                    if imports:
                        import_graph[module_name] = list(imports)
                
                except Exception:
                    continue
        
        return import_graph
    
    def _find_circular_deps(self, import_graph: Dict[str, List[str]]) -> List[List[str]]:
        """Find circular dependencies"""
        circular = []
        visited = set()
        
        def dfs(node: str, path: List[str]) -> None:
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if cycle not in circular and list(reversed(cycle)) not in circular:
                    circular.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for neighbor in import_graph.get(node, []):
                if neighbor in import_graph:  # Only check internal modules
                    dfs(neighbor, path.copy())
        
        for module in import_graph:
            dfs(module, [])
        
        return circular
