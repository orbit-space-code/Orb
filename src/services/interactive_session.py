"""
Interactive session management for code generation.
Handles the state and flow of interactive code generation sessions.
"""
from typing import Dict, List, Optional, Any, AsyncGenerator, Callable
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import os
import json
from pathlib import Path

from pydantic import BaseModel, Field

from .project_context import ProjectContext
from .code_quality import CodeQualityAnalyzer, IssueSeverity

class GenerationStatus(str, Enum):
    """Status of a generation task"""
    PENDING = "pending"
    GENERATING = "generating"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_CLARIFICATION = "needs_clarification"

class CodeSuggestion(BaseModel):
    """A suggested code change or improvement"""
    id: str = Field(default_factory=lambda: f"sug_{hashlib.md5(os.urandom(16)).hexdigest()}")
    message: str
    code: str
    language: str
    severity: IssueSeverity = IssueSeverity.INFO
    line: Optional[int] = None
    col: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CodeReview(BaseModel):
    """Results of a code review"""
    id: str = Field(default_factory=lambda: f"rev_{hashlib.md5(os.urandom(16)).hexdigest()}")
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[CodeSuggestion] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    passed_checks: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class InteractiveSession(BaseModel):
    """Tracks an interactive code generation session"""
    session_id: str = Field(default_factory=lambda: f"sess_{hashlib.md5(os.urandom(16)).hexdigest()}")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: GenerationStatus = Field(GenerationStatus.PENDING)
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    project_context: Optional[ProjectContext] = None
    current_code: str = ""
    current_file: Optional[str] = None
    review: Optional[CodeReview] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    def update(self, **kwargs):
        """Update session with new data"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.utcnow()
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the session"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        self.updated_at = datetime.utcnow()
    
    def update_code(self, new_code: str, file_path: Optional[str] = None):
        """Update the current code and file path"""
        self.current_code = new_code
        if file_path:
            self.current_file = file_path
        self.updated_at = datetime.utcnow()
    
    def add_review(self, issues: List[Dict], suggestions: List[Dict], metrics: Dict):
        """Add a code review to the session"""
        self.review = CodeReview(
            issues=issues,
            suggestions=[CodeSuggestion(**s) for s in suggestions],
            metrics=metrics
        )
        self.status = GenerationStatus.REVIEWING
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "current_file": self.current_file,
            "has_review": self.review is not None,
            "message_count": len(self.messages),
            "context_keys": list(self.context.keys())
        }

class SessionManager:
    """Manages interactive code generation sessions"""
    
    def __init__(self, project_root: Optional[str] = None):
        self.sessions: Dict[str, InteractiveSession] = {}
        self.project_root = Path(project_root or ".").resolve()
        self.quality_analyzer = CodeQualityAnalyzer()
    
    def create_session(
        self, 
        project_context: Optional[ProjectContext] = None,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> InteractiveSession:
        """Create a new interactive session"""
        session = InteractiveSession(
            project_context=project_context or ProjectContext(str(self.project_root)),
            context=initial_context or {}
        )
        self.sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[InteractiveSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)
    
    def update_session(
        self, 
        session_id: str, 
        updates: Dict[str, Any]
    ) -> Optional[InteractiveSession]:
        """Update a session with new data"""
        if session_id in self.sessions:
            self.sessions[session_id].update(**updates)
            return self.sessions[session_id]
        return None
    
    async def analyze_code(
        self, 
        session_id: str, 
        code: str, 
        language: str = "python"
    ) -> Dict[str, Any]:
        """Analyze code and update session with results"""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}
        
        # Update session with current code
        session.update_code(code)
        session.status = GenerationStatus.REVIEWING
        
        # Run code analysis
        analysis = await self.quality_analyzer.analyze(code, language=language)
        
        # Update session with review
        session.add_review(
            issues=analysis.get("issues", []),
            suggestions=analysis.get("suggestions", []),
            metrics=analysis.get("metrics", {})
        )
        
        return analysis
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions"""
        return [sess.to_dict() for sess in self.sessions.values()]
    
    def end_session(self, session_id: str) -> bool:
        """End a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    async def generate_code(
        self,
        session_id: str,
        prompt: str,
        language: str = "python",
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate code in an interactive session"""
        session = self.get_session(session_id)
        if not session:
            yield {"error": "Session not found"}
            return
        
        # Update session status
        session.status = GenerationStatus.GENERATING
        session.add_message("user", prompt)
        
        # TODO: Implement actual code generation with streaming
        # This is a placeholder implementation
        yield {
            "status": "generating",
            "chunk": "# Generated code will appear here\n",
            "session_id": session_id
        }
        
        # Simulate generation completion
        session.status = GenerationStatus.REVIEWING
        session.update_code("# Generated code will appear here\n")
        
        yield {
            "status": "completed",
            "session_id": session_id,
            "message": "Code generation complete"
        }
