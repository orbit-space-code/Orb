from typing import Dict, List, Optional, Any, Set
from pydantic import BaseModel, Field, validator
from pathlib import Path
import json
import ast
from dataclasses import dataclass, field
import astor
from enum import Enum

class PatternSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class CodePattern:
    """Represents a code pattern for recognition and validation"""
    name: str
    description: str
    pattern: str
    severity: PatternSeverity = PatternSeverity.INFO
    suggestion: Optional[str] = None
    languages: List[str] = field(default_factory=lambda: ["python"])
    tags: List[str] = field(default_factory=list)

class ProjectSettings(BaseModel):
    """Project-specific settings and configurations"""
    language: str = "python"
    style_guide: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    file_structure: Dict[str, Any] = Field(default_factory=dict)
    patterns: Dict[str, CodePattern] = Field(default_factory=dict)
    ignored_paths: List[str] = Field(default_factory=lambda: ["__pycache__", ".git", ".venv"])
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            CodePattern: lambda p: {
                "name": p.name,
                "description": p.description,
                "pattern": p.pattern,
                "severity": p.severity,
                "suggestion": p.suggestion,
                "languages": p.languages,
                "tags": p.tags
            }
        }

class ProjectContext:
    """Manages project-wide context and patterns"""
    
    def __init__(self, project_root: str, settings: Optional[ProjectSettings] = None):
        self.project_root = Path(project_root).absolute()
        self.settings = settings or ProjectSettings()
        self._file_cache: Dict[str, str] = {}
        self._ast_cache: Dict[str, ast.AST] = {}
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize the project context by loading configuration"""
        if self._initialized:
            return
            
        # Load project configuration if exists
        config_path = self.project_root / ".codegen" / "config.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.settings = ProjectSettings(**config)
        
        # Load default patterns
        self._load_default_patterns()
        self._initialized = True
        
    def _load_default_patterns(self) -> None:
        """Load default code patterns"""
        patterns = [
            CodePattern(
                name="missing_error_handling",
                description="Missing error handling in function",
                pattern="def [a-zA-Z_]+\([^)]*\):[^\n]*\n(?!\\s*(?:try|if|for|while|with|async))",
                severity=PatternSeverity.WARNING,
                suggestion="Add proper error handling with try/except blocks"
            ),
            CodePattern(
                name="hardcoded_string",
                description="Hardcoded string that should be a constant",
                pattern='"[^"\n]{20,}"',
                severity=PatternSeverity.INFO,
                suggestion="Consider moving string to a constant or configuration"
            )
        ]
        
        for pattern in patterns:
            self.settings.patterns[pattern.name] = pattern
    
    async def analyze_code(
        self, 
        code: str, 
        file_path: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze code against project patterns and style guide"""
        if not self._initialized:
            await self.initialize()
            
        language = language or self.settings.language
        results = {
            "issues": [],
            "suggestions": [],
            "patterns_found": [],
            "metrics": {},
            "file_path": str(file_path) if file_path else None
        }
        
        # Basic syntax check
        try:
            tree = ast.parse(code)
            if file_path:
                self._ast_cache[file_path] = tree
        except SyntaxError as e:
            results["issues"].append({
                "type": "syntax_error",
                "message": f"Syntax error: {str(e)}",
                "line": e.lineno,
                "col": e.offset,
                "severity": "error"
            })
            return results
        
        # Check patterns
        for pattern in self.settings.patterns.values():
            if language not in pattern.languages:
                continue
                
            if self._matches_pattern(code, pattern):
                results["patterns_found"].append(pattern.name)
                
                issue = {
                    "type": "pattern_match",
                    "pattern": pattern.name,
                    "message": pattern.description,
                    "severity": pattern.severity.value,
                    "suggestion": pattern.suggestion
                }
                
                if pattern.severity == PatternSeverity.ERROR:
                    results["issues"].append(issue)
                else:
                    results["suggestions"].append(issue)
        
        # Calculate metrics
        results["metrics"].update(self._calculate_metrics(code, tree))
        
        return results
    
    def _matches_pattern(self, code: str, pattern: CodePattern) -> bool:
        """Check if code matches a specific pattern using regex"""
        import re
        try:
            # Convert simple pattern to regex if needed
            if not pattern.pattern.startswith('^'):
                # Simple pattern matching
                return bool(re.search(pattern.pattern, code, re.MULTILINE | re.DOTALL))
            else:
                # Full regex pattern
                return bool(re.match(pattern.pattern, code, re.MULTILINE | re.DOTALL))
        except re.error:
            return False
    
    def _calculate_metrics(self, code: str, tree: ast.AST) -> Dict[str, Any]:
        """Calculate code metrics"""
        class MetricsVisitor(ast.NodeVisitor):
            def __init__(self):
                self.function_count = 0
                self.class_count = 0
                self.complexity = 1
                self.imports: Set[str] = set()
                
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
        
        visitor = MetricsVisitor()
        visitor.visit(tree)
        
        return {
            "lines_of_code": len(code.splitlines()),
            "function_count": visitor.function_count,
            "class_count": visitor.class_count,
            "complexity": visitor.complexity,
            "imports": sorted(list(visitor.imports))
        }
    
    async def save_config(self) -> None:
        """Save project configuration"""
        config_dir = self.project_root / ".codegen"
        config_dir.mkdir(exist_ok=True)
        
        config_path = config_dir / "config.json"
        with open(config_path, 'w') as f:
            json.dump(json.loads(self.settings.json()), f, indent=2)
    
    def get_available_languages(self) -> List[str]:
        """Get list of supported languages"""
        return ["python"]  # Can be extended
    
    def get_patterns_for_language(self, language: str) -> List[CodePattern]:
        """Get patterns for a specific language"""
        return [
            pattern for pattern in self.settings.patterns.values()
            if language in pattern.languages
        ]
