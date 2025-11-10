"""
Code Generation API Router
Handles all code generation related endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json

from ...services.code_generation import (
    CodeGenerator,
    CodeGenerationRequest,
    CodeGenerationResponse,
    ModelProvider
)
from ...services.project_context import ProjectContext
from ...services.code_quality import CodeQualityAnalyzer

router = APIRouter(prefix="/api/codegen", tags=["codegen"])

# Initialize services
code_generator = CodeGenerator()
quality_analyzer = CodeQualityAnalyzer()

class CodeGenRequest(BaseModel):
    """Request model for code generation"""
    prompt: str
    language: str = "python"
    context: Optional[Dict[str, Any]] = None
    template_name: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False

@router.post("/generate", response_model=CodeGenerationResponse)
async def generate_code(request: CodeGenRequest):
    """Generate code based on the provided prompt and parameters"""
    try:
        # Create code generation request
        gen_request = CodeGenerationRequest(
            prompt=request.prompt,
            language=request.language,
            context=request.context or {},
            template_name=request.template_name,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False
        )
        
        # Generate code
        response = await code_generator.generate_code(gen_request)
        
        # Analyze code quality
        quality_report = await quality_analyzer.analyze_code(
            response.generated_code, 
            request.language
        )
        
        # Add quality report to metadata
        response.metadata["quality_report"] = quality_report.dict()
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/stream")
async def stream_code(request: CodeGenRequest):
    """Stream generated code in real-time"""
    if not request.stream:
        request.stream = True
        
    async def event_generator():
        """Generate SSE events for streaming"""
        try:
            # Create code generation request
            gen_request = CodeGenerationRequest(
                prompt=request.prompt,
                language=request.language,
                context=request.context or {},
                template_name=request.template_name,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True
            )
            
            # Buffer to accumulate code
            code_buffer = []
            
            # Define callback for streaming
            async def on_chunk(chunk: str):
                code_buffer.append(chunk)
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
            # Start streaming
            await code_generator.stream_generate(gen_request, on_chunk)
            
            # Analyze full code after generation
            full_code = "".join(code_buffer)
            quality_report = await quality_analyzer.analyze_code(
                full_code,
                request.language
            )
            
            # Send quality report as final event
            yield f"data: {json.dumps({'quality_report': quality_report.dict()})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/batch")
async def batch_generate(requests: List[CodeGenRequest]):
    """Generate multiple code snippets in parallel"""
    try:
        gen_requests = [
            CodeGenerationRequest(
                prompt=req.prompt,
                language=req.language,
                context=req.context or {},
                template_name=req.template_name,
                model=req.model,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
                stream=False
            )
            for req in requests
        ]
        
        responses = await code_generator.batch_generate(gen_requests)
        return {"results": responses}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Project context endpoints
@router.post("/context/update")
async def update_project_context(
    project_id: str,
    file_paths: List[str],
    context: Dict[str, Any]
):
    """Update project context with additional files and metadata"""
    try:
        project_ctx = ProjectContext(project_id)
        await project_ctx.update_context(file_paths, context)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/context/{project_id}")
async def get_project_context(project_id: str):
    """Get project context"""
    try:
        project_ctx = ProjectContext(project_id)
        context = await project_ctx.get_context()
        return {"context": context}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
