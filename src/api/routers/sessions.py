"""
Interactive Session API
Handles interactive coding sessions with the AI assistant
"""
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
import json
import logging

from ...services.session_manager import (
    session_manager,
    CodeSession,
    SessionState,
    MessageRole,
    CodeExecutionResult
)
from ...services.project_context import ProjectContext
from ...auth.dependencies import get_current_user

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
logger = logging.getLogger(__name__)

# Request/Response Models
class SessionCreate(BaseModel):
    """Request model for creating a new session"""
    project_id: Optional[str] = None
    initial_context: Optional[Dict[str, Any]] = None

class SessionResponse(BaseModel):
    """Response model for session operations"""
    session_id: str
    user_id: str
    project_id: Optional[str]
    created_at: str
    updated_at: str
    state: str
    message_count: int
    code_snippet_count: int
    context_keys: List[str]

class MessageRequest(BaseModel):
    """Request model for sending a message"""
    content: str
    metadata: Optional[Dict[str, Any]] = None

class MessageResponse(BaseModel):
    """Response model for chat messages"""
    message_id: str
    role: str
    content: str
    timestamp: str
    metadata: Dict[str, Any]

class CodeExecutionRequest(BaseModel):
    """Request model for executing code"""
    code: str
    language: str = "python"
    snippet_id: Optional[str] = None

# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Add a new WebSocket connection"""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast(self, session_id: str, message: Dict[str, Any]):
        """Send a message to all connections for a session"""
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message: {e}")
                    self.disconnect(session_id, connection)

# Create WebSocket manager
ws_manager = ConnectionManager()

# REST API Endpoints
@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new interactive coding session"""
    try:
        session = await session_manager.create_session(
            user_id=current_user["id"],
            project_id=session_data.project_id,
            initial_context=session_data.initial_context or {}
        )
        return session.to_dict()
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )

@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get session details"""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session"
        )
    
    return session.to_dict()

@router.post("/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: str,
    message: MessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to the session"""
    try:
        # Process the message and get the response
        responses = []
        async for response in session_manager.process_user_message(
            session_id=session_id,
            message=message.content,
            user_id=current_user["id"]
        ):
            responses.append(response)
            
            # Broadcast to WebSocket connections
            await ws_manager.broadcast(session_id, {
                "type": "message_update",
                "data": response
            })
        
        # Return the last response (or handle as needed)
        return responses[-1] if responses else {"status": "processed"}
        
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )

@router.post("/{session_id}/execute", response_model=CodeExecutionResult)
async def execute_code(
    session_id: str,
    execution: CodeExecutionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Execute code in the session's context"""
    try:
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        if session.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session"
            )
        
        # Execute the code
        result = await session_manager.execute_code(
            session_id=session_id,
            code=execution.code,
            language=execution.language
        )
        
        # Broadcast execution result to WebSocket connections
        await ws_manager.broadcast(session_id, {
            "type": "execution_result",
            "data": {
                "snippet_id": execution.snippet_id,
                "result": {
                    "output": result.output,
                    "error": result.error,
                    "execution_time": result.execution_time,
                    "success": result.success
                }
            }
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute code: {str(e)}"
        )

# WebSocket Endpoint
@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: str
):
    """WebSocket endpoint for real-time session updates"""
    # In a real implementation, validate the token and get the user
    # For now, we'll accept any token
    
    session = await session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Add WebSocket connection
    await ws_manager.connect(session_id, websocket)
    
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        ws_manager.disconnect(session_id, websocket)
