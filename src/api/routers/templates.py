"""
Template Management API
Handles CRUD operations for code generation templates
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

from ...services.template_manager import (
    TemplateManager,
    Template,
    TemplateType,
    template_manager
)

router = APIRouter(prefix="/api/templates", tags=["templates"])
logger = logging.getLogger(__name__)

# Request/Response Models
class TemplateCreate(BaseModel):
    """Request model for creating/updating templates"""
    name: str = Field(..., min_length=1, max_length=100)
    type: TemplateType
    description: str
    language: str
    content: str
    variables: Dict[str, Any] = {}
    required_vars: List[str] = []
    dependencies: List[str] = []
    tags: List[str] = []

class TemplateResponse(Template):
    """Response model for template operations"""
    pass

class TemplateListResponse(BaseModel):
    """Response model for listing templates"""
    templates: List[Template]
    total: int

# Template Management Endpoints
@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(template_data: TemplateCreate):
    """Create a new template"""
    try:
        # Check if template already exists
        if template_manager.get_template(template_data.name):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Template '{template_data.name}' already exists"
            )
        
        # Create and save the template
        template = Template(**template_data.dict())
        template_manager.save_template(template)
        
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )

@router.get("/{template_name}", response_model=TemplateResponse)
async def get_template(template_name: str):
    """Get a template by name"""
    template = template_manager.get_template(template_name)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_name}' not found"
        )
    return template

@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    type: Optional[TemplateType] = None,
    language: Optional[str] = None,
    tags: Optional[List[str]] = Query(None)
):
    """List templates with optional filtering"""
    try:
        templates = template_manager.list_templates(
            template_type=type,
            language=language,
            tags=tags
        )
        return {
            "templates": templates,
            "total": len(templates)
        }
    except Exception as e:
        logger.error(f"Error listing templates: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list templates"
        )

@router.put("/{template_name}", response_model=TemplateResponse)
async def update_template(template_name: str, template_data: TemplateCreate):
    """Update an existing template"""
    try:
        # Check if template exists
        if not template_manager.get_template(template_name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_name}' not found"
            )
        
        # Update the template
        template = Template(**template_data.dict())
        template_manager.save_template(template)
        
        return template
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update template: {str(e)}"
        )

@router.delete("/{template_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_name: str):
    """Delete a template"""
    try:
        if not template_manager.delete_template(template_name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_name}' not found"
            )
        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete template: {str(e)}"
        )

@router.post("/{template_name}/render")
async def render_template(
    template_name: str,
    context: Dict[str, Any]
):
    """Render a template with the provided context"""
    try:
        rendered = template_manager.render_template(template_name, context)
        return {"rendered": rendered}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render template: {str(e)}"
        )
