"""
Session Manager
Handles interactive coding sessions with context preservation
"""
import uuid
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import asyncio

from .code_generation import CodeGenerator, CodeGenerationRequest, CodeSnippet
from .project_context import ProjectContext
from .code_quality import CodeQualityAnalyzer

class MessageRole(str, Enum):
    """Roles for chat messages"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    CODE = "code"
    ERROR = "error"

class ChatMessage(BaseModel):
    """A message in the chat history"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CodeExecutionResult(BaseModel):
    """Result of executing generated code"""
    output: str
    error: Optional[str] = None
    execution_time: float
    success: bool

class CodeEdit(BaseModel):
    """Represents an edit to a code file"""
    file_path: str
    old_content: Optional[str] = None
    new_content: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CodeReview(BaseModel):
    """Code review feedback"""
    comments: List[Dict[str, Any]]
    overall_score: float  # 0-1
    suggestions: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SessionState(str, Enum):
    """Possible session states"""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class CodeSession(BaseModel):
    """Represents an interactive coding session"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    project_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    state: SessionState = SessionState.ACTIVE
    messages: List[ChatMessage] = Field(default_factory=list)
    code_snippets: Dict[str, CodeSnippet] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def add_message(self, role: MessageRole, content: str, **metadata) -> ChatMessage:
        """Add a message to the session"""
        message = ChatMessage(role=role, content=content, metadata=metadata)
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        return message
    
    def add_code_snippet(self, code_snippet: CodeSnippet) -> str:
        """Add a code snippet to the session"""
        snippet_id = f"snippet_{len(self.code_snippets) + 1}"
        self.code_snippets[snippet_id] = code_snippet
        return snippet_id
    
    def get_chat_history(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """Get recent chat history"""
        recent_messages = self.messages[-max_messages:]
        return [
            {"role": msg.role, "content": msg.content, **msg.metadata}
            for msg in recent_messages
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "state": self.state,
            "message_count": len(self.messages),
            "code_snippet_count": len(self.code_snippets),
            "context_keys": list(self.context.keys()),
        }

class SessionManager:
    """Manages interactive coding sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, CodeSession] = {}
        self.code_generator = CodeGenerator()
        self.quality_analyzer = CodeQualityAnalyzer()
        self.session_timeout = timedelta(hours=2)  # Default session timeout
    
    async def create_session(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> CodeSession:
        """Create a new interactive coding session"""
        session = CodeSession(user_id=user_id, project_id=project_id)
        
        # Initialize project context if project_id is provided
        if project_id:
            project_ctx = ProjectContext(project_id)
            project_info = await project_ctx.get_context()
            session.context["project"] = project_info
        
        # Add initial system message
        system_message = (
            "You are an AI coding assistant. You help users write, debug, and improve code. "
            "You can generate code, explain concepts, and provide suggestions. "
            "Always ensure your code is well-documented and follows best practices."
        )
        session.add_message(MessageRole.SYSTEM, system_message)
        
        # Store the session
        self.sessions[session.session_id] = session
        return session
    
    async def get_session(self, session_id: str) -> Optional[CodeSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)
    
    async def end_session(self, session_id: str) -> bool:
        """End a session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.state = SessionState.COMPLETED
            session.updated_at = datetime.utcnow()
            return True
        return False
    
    async def process_user_message(
        self,
        session_id: str,
        message: str,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user message and yield responses"""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if user_id and session.user_id != user_id:
            raise PermissionError("Not authorized to access this session")
        
        # Add user message to history
        session.add_message(MessageRole.USER, message)
        
        # Generate response using code generator
        gen_request = CodeGenerationRequest(
            prompt=message,
            language=session.context.get("language", "python"),
            context={
                "session_id": session_id,
                "project_id": session.project_id,
                "chat_history": session.get_chat_history(),
                **session.context
            },
            stream=True
        )
        
        # Stream the response
        response_text = ""
        code_blocks = []
        current_block = None
        
        async def on_chunk(chunk: str):
            nonlocal response_text, current_block
            response_text += chunk
            
            # Simple code block detection (in a real implementation, use more robust parsing)
            if "```" in chunk:
                if current_block is None:
                    current_block = {"language": "", "code": ""}
                else:
                    code_blocks.append(current_block)
                    current_block = None
            elif current_block is not None:
                if not current_block["language"] and "\n" in chunk:
                    current_block["language"] = chunk.split("\n")[0].strip() or "text"
                else:
                    current_block["code"] += chunk
            
            yield {"type": "text", "content": chunk}
        
        # Stream the response
        await self.code_generator.stream_generate(gen_request, on_chunk)
        
        # Add assistant response to history
        session.add_message(MessageRole.ASSISTANT, response_text)
        
        # Process any generated code blocks
        for block in code_blocks:
            if block["code"].strip():
                snippet = CodeSnippet(
                    code=block["code"].strip(),
                    language=block["language"],
                    metadata={"generated_from": session_id}
                )
                snippet_id = session.add_code_snippet(snippet)
                
                yield {
                    "type": "code",
                    "snippet_id": snippet_id,
                    "language": block["language"],
                    "code": block["code"]
                }
    
    async def execute_code(
        self,
        session_id: str,
        code: str,
        language: str = "python"
    ) -> CodeExecutionResult:
        """Execute code in a sandboxed environment"""
        # In a real implementation, this would use a secure sandbox
        start_time = time.time()
        try:
            # This is a placeholder - in a real implementation, use a secure sandbox
            # like Pyodide for browser execution or a container for server-side execution
            if language == "python":
                # Simple Python execution (very basic, for demo only)
                local_vars = {}
                global_vars = {"__builtins__": {}}
                
                # Allow only safe builtins
                safe_builtins = {
                    'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
                    'chr', 'complex', 'dict', 'divmod', 'enumerate', 'filter', 'float',
                    'format', 'frozenset', 'hash', 'hex', 'int', 'iter', 'len', 'list',
                    'map', 'max', 'min', 'next', 'oct', 'ord', 'pow', 'print', 'range',
                    'repr', 'reversed', 'round', 'set', 'slice', 'sorted', 'str', 'sum',
                    'tuple', 'type', 'zip'
                }
                
                for name in safe_builtins:
                    if name in __builtins__:
                        global_vars[name] = getattr(__builtins__, name)
                
                # Execute in a separate thread with timeout
                def execute():
                    try:
                        exec(code, global_vars, local_vars)
                        return {"success": True, "output": ""}
                    except Exception as e:
                        return {"success": False, "output": str(e)}
                
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(execute)
                    try:
                        result = future.result(timeout=10)  # 10 second timeout
                        success = result["success"]
                        output = result["output"]
                    except concurrent.futures.TimeoutError:
                        success = False
                        output = "Execution timed out after 10 seconds"
                
                execution_time = time.time() - start_time
                return CodeExecutionResult(
                    output=output,
                    error=None if success else output,
                    execution_time=execution_time,
                    success=success
                )
            else:
                return CodeExecutionResult(
                    output="",
                    error=f"Unsupported language: {language}",
                    execution_time=time.time() - start_time,
                    success=False
                )
                
        except Exception as e:
            return CodeExecutionResult(
                output="",
                error=str(e),
                execution_time=time.time() - start_time,
                success=False
            )

# Singleton instance
session_manager = SessionManager()
