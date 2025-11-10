"""
Code Generation API Endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from typing import List, Optional
import asyncio
import json

from src.services.code_generation import (
    CodeGenerator,
    CodeGenerationRequest,
    CodeGenerationResponse
)
from src.config import settings
from src.services.template_manager import template_manager

router = APIRouter(
    prefix="/code",
    tags=["code"],
    dependencies=[]
)

# Initialize code generator with Claude
code_generator = CodeGenerator(
    api_key=settings.CLAUDE_API_KEY,
    model=settings.CLAUDE_MODEL
)

@router.post("/generate", response_model=CodeGenerationResponse)
async def generate_code(request: CodeGenerationRequest):
    """
    Generate code based on the provided prompt and parameters
    """
    try:
        # If a template is specified, apply it
        if request.template_name:
            template = template_manager.get_template(request.template_name)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template '{request.template_name}' not found"
                )
            
            # Apply template context if provided
            if request.context:
                try:
                    prompt = template_manager.render_template(
                        request.template_name,
                        request.context
                    )
                    request.prompt = prompt
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to render template: {str(e)}"
                    )
        
        # Generate the code
        return await code_generator.generate_code(request)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/generate/stream")
async def stream_generate_code(request: CodeGenerationRequest):
    """
    Stream generated code in real-time
    """
    try:
        # If a template is specified, apply it
        if request.template_name:
            template = template_manager.get_template(request.template_name)
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template '{request.template_name}' not found"
                )
            
            # Apply template context if provided
            if request.context:
                try:
                    prompt = template_manager.render_template(
                        request.template_name,
                        request.context
                    )
                    request.prompt = prompt
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Failed to render template: {str(e)}"
                    )
        
        # Create a queue to stream the generated content
        queue = asyncio.Queue()
        
        # Define the callback function for streaming
        async def on_chunk(chunk: str):
            await queue.put(f"data: {json.dumps({'chunk': chunk})}\n\n")
        
        # Start the generation in the background
        async def generate():
            try:
                await code_generator.stream_generate(request, on_chunk)
                await queue.put("data: [DONE]\n\n")
            except Exception as e:
                error_msg = f"Error during generation: {str(e)}"
                await queue.put(f"data: {json.dumps({'error': error_msg})}\n\n")
                await queue.put("data: [DONE]\n\n")
            finally:
                await queue.put(None)  # Signal the end of the stream
        
        # Start the generation in the background
        asyncio.create_task(generate())
        
        # Stream the response
        async def event_generator():
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
                await asyncio.sleep(0.01)  # Small delay to prevent high CPU usage
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/batch-generate", response_model=List[CodeGenerationResponse])
async def batch_generate(requests: List[CodeGenerationRequest]):
    """
    Generate multiple code snippets in parallel
    """
    try:
        # Process each request to apply templates if needed
        processed_requests = []
        
        for req in requests:
            # If a template is specified, apply it
            if req.template_name:
                template = template_manager.get_template(req.template_name)
                if not template:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Template '{req.template_name}' not found"
                    )
                
                # Apply template context if provided
                if req.context:
                    try:
                        prompt = template_manager.render_template(
                            req.template_name,
                            req.context
                        )
                        req.prompt = prompt
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Failed to render template: {str(e)}"
                        )
            
            processed_requests.append(req)
        
        # Generate all responses in parallel
        return await code_generator.batch_generate(processed_requests)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
