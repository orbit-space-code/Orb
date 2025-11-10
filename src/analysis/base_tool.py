"""
Base class for all analysis tools
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime


class Severity(str, Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IssueCategory(str, Enum):
    """Issue categories"""
    SECURITY = "security"
    BUG = "bug"
    CODE_SMELL = "code_smell"
    STYLE = "style"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"


class Issue(BaseModel):
    """Represents a single issue found by a tool"""
    file_path: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    severity: Severity
    category: IssueCategory
    rule_id: str
    message: str
    description: Optional[str] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


class ToolMetrics(BaseModel):
    """Metrics collected during tool execution"""
    execution_time_ms: int
    files_analyzed: int
    lines_analyzed: int
    issues_found: int
    memory_used_mb: Optional[float] = None


class ToolResult(BaseModel):
    """Result from a tool execution"""
    tool_name: str
    tool_version: str
    status: str  # success, failed, skipped
    started_at: datetime
    completed_at: datetime
    issues: List[Issue] = []
    metrics: ToolMetrics
    error_message: Optional[str] = None
    raw_output: Optional[str] = None


class AnalysisTool(ABC):
    """Base class for all analysis tools"""
    
    def __init__(self):
        self.name = self.__class__.__name__.replace("Tool", "").lower()
        self.version = "1.0.0"
        self.supported_languages: List[str] = []
        self.supported_extensions: List[str] = []
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the tool is installed and available"""
        pass
    
    @abstractmethod
    async def execute(
        self,
        codebase_path: str,
        config: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute the analysis tool on the codebase
        
        Args:
            codebase_path: Path to the codebase to analyze
            config: Optional tool-specific configuration
            
        Returns:
            ToolResult with issues and metrics
        """
        pass
    
    def should_analyze_file(self, file_path: str) -> bool:
        """Check if this tool should analyze the given file"""
        if not self.supported_extensions:
            return True
        return any(file_path.endswith(ext) for ext in self.supported_extensions)
    
    def get_info(self) -> Dict[str, Any]:
        """Get tool information"""
        return {
            "name": self.name,
            "version": self.version,
            "supported_languages": self.supported_languages,
            "supported_extensions": self.supported_extensions,
        }
