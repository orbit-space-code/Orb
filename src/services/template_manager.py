"""
Template Manager
Handles code generation templates and patterns
"""
from typing import Dict, List, Optional, Any
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
from enum import Enum
import jinja2
import json

class TemplateType(str, Enum):
    """Types of templates supported"""
    COMPONENT = "component"
    API_ENDPOINT = "api_endpoint"
    DATABASE_MODEL = "database_model"
    TEST = "test"
    CONFIG = "config"
    DOCKERFILE = "dockerfile"
    GITHUB_ACTION = "github_action"

class Template(BaseModel):
    """Template definition"""
    name: str
    type: TemplateType
    description: str
    language: str
    content: str
    variables: Dict[str, Any] = Field(default_factory=dict)
    required_vars: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

class TemplateManager:
    """Manages code generation templates"""
    
    def __init__(self, template_dirs: List[str] = None):
        self.templates: Dict[str, Template] = {}
        self.template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dirs or []),
            autoescape=jinja2.select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from configured directories"""
        # This would load templates from the filesystem
        # For now, we'll define some built-in templates
        self._load_builtin_templates()
    
    def _load_builtin_templates(self):
        """Load built-in templates"""
        templates = [
            Template(
                name="react_component",
                type=TemplateType.COMPONENT,
                description="A React functional component with TypeScript",
                language="typescript",
                content=(
                    "import React from 'react';\n"
                    "\n"
                    "interface {{ component_name }}Props {\n"
                    "  // Add your prop types here\n"
                    "  className?: string;\n"
                    "  children?: React.ReactNode;\n"
                    "}\n"
                    "\n"
                    "export const {{ component_name }}: React.FC<{{ component_name }}Props> = (\n"
                    "  {\n"
                    "    className = '',\n"
                    "    children,\n"
                    "  }\n"
                    ") => {\n"
                    "  return (\n"
                    "    <div className={`{{ component_name | lower }} ${className}`}>{children}</div>\n"
                    "  );\n"
                    "};"
                ),
                required_vars=["component_name"],
                tags=["react", "typescript", "frontend"]
            ),
            Template(
                name="fastapi_endpoint",
                type=TemplateType.API_ENDPOINT,
                description="A FastAPI endpoint with error handling",
                language="python",
                content=(
                    'from fastapi import APIRouter, HTTPException, Depends\n'
                    'from typing import List, Optional\n'
                    'from pydantic import BaseModel\n\n'
                    'router = APIRouter(prefix="{{ endpoint_path }}", tags=["{{ endpoint_tag }}"])\n\n'
                    'class {{ request_model_name }}(BaseModel):\n'
                    '    # Define your request model here\n'
                    '    pass\n\n'
                    'class {{ response_model_name }}(BaseModel):\n'
                    '    # Define your response model here\n'
                    '    pass\n\n'
                    '@router.{{ http_method }}("/", response_model={{ response_model_name }})\n'
                    'async def {{ endpoint_function_name }}(\n'
                    '    request: {{ request_model_name }}\n'
                    ') -> {{ response_model_name }}:\n'
                    '    """\n'
                    '    {{ endpoint_description }}\n'
                    '    """\n'
                    '    try:\n'
                    '        # Your implementation here\n'
                    '        pass\n'
                    '    except Exception as e:\n'
                    '        raise HTTPException(status_code=500, detail=str(e))'
                ),
                required_vars=[
                    "endpoint_path", 
                    "http_method", 
                    "endpoint_function_name",
                    "request_model_name",
                    "response_model_name",
                    "endpoint_tag",
                    "endpoint_description"
                ],
                tags=["python", "fastapi", "backend"]
            )
        ]
        
        for template in templates:
            self.templates[template.name] = template
    
    def get_template(self, name: str) -> Optional[Template]:
        """Get a template by name"""
        return self.templates.get(name)
    
    def list_templates(
        self,
        template_type: Optional[TemplateType] = None,
        language: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Template]:
        """List available templates with optional filtering"""
        templates = list(self.templates.values())
        
        if template_type:
            templates = [t for t in templates if t.type == template_type]
        if language:
            templates = [t for t in templates if t.language.lower() == language.lower()]
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]
            
        return templates
    
    def render_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """Render a template with the given context"""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # Check required variables
        missing_vars = [var for var in template.required_vars if var not in context]
        if missing_vars:
            raise ValueError(f"Missing required variables: {', '.join(missing_vars)}")
        
        # Render the template
        try:
            template = self.template_env.from_string(template.content)
            return template.render(**context)
        except Exception as e:
            raise ValueError(f"Failed to render template {template_name}: {str(e)}")
    
    def save_template(self, template: Template) -> None:
        """Save a new or updated template"""
        self.templates[template.name] = template
        # In a real implementation, this would save to disk
        
    def delete_template(self, name: str) -> bool:
        """Delete a template by name"""
        if name in self.templates:
            del self.templates[name]
            return True
        return False

# Singleton instance
template_manager = TemplateManager()
