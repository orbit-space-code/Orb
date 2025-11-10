"""
Advanced Code Generation Service
Handles AI-powered code generation with support for multiple providers
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, AsyncGenerator, TypeVar, cast, TypedDict

import aiohttp
import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from typing_extensions import Literal

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type aliases
T = TypeVar('T')
JsonDict = Dict[str, Any]

# Configuration
DEFAULT_CONFIG = {
    "timeout": 120,
    "max_retries": 3,
    "max_parallel_requests": 5,
    "cache_enabled": True,
    "cache_ttl": 3600,  # 1 hour
    "default_temperature": 0.2,
    "max_tokens": 4096,
    "max_context_length": 8000,
}

# API Endpoints
API_ENDPOINTS = {
    "anthropic": "https://api.anthropic.com/v1/messages",
    "openai": "https://api.openai.com/v1/chat/completions",
    "local": "http://localhost:5000/v1/completions"
}

# Default model
DEFAULT_MODEL = "claude-3-opus-20240229"

class ModelProvider(str, Enum):
    """Supported AI model providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"

@dataclass
class CodeSnippet:
    """Represents a generated code snippet with metadata"""
    code: str
    language: str
    file_path: Optional[Path] = None
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "code": self.code,
            "language": self.language,
            "file_path": str(self.file_path) if self.file_path else None,
            "imports": self.imports,
            "dependencies": self.dependencies,
            "docstring": self.docstring,
            "metadata": self.metadata
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeSnippet':
        """Create from dictionary"""
        return cls(
            code=data['code'],
            language=data['language'],
            file_path=Path(data['file_path']) if data.get('file_path') else None,
            imports=data.get('imports', []),
            dependencies=data.get('dependencies', []),
            docstring=data.get('docstring'),
            metadata=data.get('metadata', {})
        )

class CodeGenerationRequest(BaseModel):
    """Request model for code generation"""
    prompt: str = Field(
        ...,
        description="The prompt describing the code to generate"
    )
    language: str = Field(
        "python",
        description="Target programming language"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for generation"
    )
    template_name: Optional[str] = Field(
        None,
        description="Name of template to use for generation"
    )
    model: str = Field(
        DEFAULT_MODEL,
        description="Model to use for generation"
    )
    temperature: float = Field(
        0.7,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (0.0 to 1.0)"
    )
    max_tokens: int = Field(
        2048,
        gt=0,
        description="Maximum number of tokens to generate"
    )
    top_p: float = Field(
        0.9,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    frequency_penalty: float = Field(
        0.0,
        ge=0.0,
        le=2.0,
        description="Penalty for frequent tokens"
    )
    presence_penalty: float = Field(
        0.0,
        ge=0.0,
        le=2.0,
        description="Penalty for new tokens"
    )
    stop_sequences: Optional[List[str]] = Field(
        None,
        description="Sequences where the API will stop generating"
    )
    n: int = Field(
        1,
        ge=1,
        le=5,
        description="Number of completions to generate"
    )
    stream: bool = Field(
        False,
        description="Whether to stream the response"
    )
    project_root: Optional[Union[str, Path]] = Field(
        None,
        description="Root directory of the project"
    )
    provider: ModelProvider = Field(
        ModelProvider.ANTHROPIC,
        description="AI provider to use"
    )
    project_id: Optional[str] = Field(
        None,
        description="Project ID for context"
    )

    class Config:
        """Pydantic model configuration"""
        json_encoders = {
            Path: lambda p: str(p)
        }
    
    @validator('language')
    def validate_language(cls, v: str) -> str:
        """Validate that the language is supported"""
        valid_languages = [
            'python', 'javascript', 'typescript', 'java', 'c', 'cpp',
            'csharp', 'go', 'rust', 'ruby', 'php', 'swift', 'kotlin',
            'scala', 'dart', 'r', 'shell', 'sql', 'html', 'css', 'json'
        ]
        if v.lower() not in valid_languages:
            raise ValueError(f'Language {v} is not supported. Must be one of: {", ".join(valid_languages)}')
        return v.lower()
    
    @validator('project_root', pre=True)
    def validate_project_root(cls, v: Optional[Union[str, Path]]) -> Optional[Path]:
        """Convert string paths to Path objects"""
        if v is None:
            return None
        if isinstance(v, str):
            return Path(v).resolve()
        if isinstance(v, Path):
            return v.resolve()
        raise ValueError(f"Invalid project root: {v}")

class CodeGenerationResponse(BaseModel):
    """Response model for code generation"""
    generated_code: str
    model_used: str
    provider: str
    tokens_used: int
    finish_reason: str
    latency_ms: float
    metadata: Dict[str, Any] = {}
    warnings: List[str] = []
    
    class Config:
        json_encoders = {
            Path: str,
        }

@dataclass
class CodeGenerator:
    """Advanced code generation with support for multiple AI providers"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-opus-20240229",
        provider: ModelProvider = ModelProvider.ANTHROPIC,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        self.api_key = api_key or os.getenv(f"{provider.upper()}_API_KEY")
        self.model = model
        self.provider = provider
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self._session = None
        
        if not self.api_key and self.provider != ModelProvider.LOCAL:
            raise ValueError(f"API key is required for {self.provider} provider")
            
        self._setup_provider_config()
    
    def _setup_provider_config(self) -> None:
        """Configure provider-specific settings"""
        self.endpoint = API_ENDPOINTS.get(self.provider)
        
        if self.provider == ModelProvider.ANTHROPIC:
            self.max_tokens = min(self.config.get('max_tokens', 4096), 100000)
        elif self.provider == ModelProvider.OPENAI:
            self.max_tokens = min(self.config.get('max_tokens', 4000), 4096)
        else:  # LOCAL
            self.max_tokens = self.config.get('max_tokens', 2048)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _make_request(
        self,
        request: CodeGenerationRequest,
        stream: bool = False
    ) -> Any:
        """Make a request to the AI provider's API with retry logic"""
        start_time = time.time()
        session = await self._get_session()
        
        # Prepare request data based on provider
        if self.provider == ModelProvider.ANTHROPIC:
            return await self._make_anthropic_request(request, session, stream)
        elif self.provider == ModelProvider.OPENAI:
            return await self._make_openai_request(request, session, stream)
        else:  # LOCAL
            return await self._make_local_request(request, session, stream)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session with connection pooling"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config["timeout"])
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_cache_key(self, request: CodeGenerationRequest) -> str:
        """Generate a cache key for the request"""
        cache_data = {
            "prompt": request.prompt,
            "language": request.language,
            "model": request.model,
            "provider": request.provider,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        return hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()

        if self.provider == ModelProvider.ANTHROPIC:
            return await self._make_anthropic_request(request, session, stream)
        elif self.provider == ModelProvider.OPENAI:
            return await self._make_openai_request(request, session, stream)
        else:  # LOCAL
            return await self._make_local_request(request, session, stream)

    async def _make_anthropic_request(
        self,
        request: CodeGenerationRequest,
        session: aiohttp.ClientSession,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Make a request to the Anthropic API"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        messages = self._prepare_messages(request)
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": min(request.max_tokens, self.max_tokens),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": stream
        }
        
        if request.stop_sequences:
            data["stop_sequences"] = request.stop_sequences
            
        async with session.post(
            self.endpoint,
            headers=headers,
            json=data
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"API request failed with status {response.status}: {error_text}")
                
            if stream:
                return await self._handle_anthropic_stream(response)
            else:
                return await response.json()

    async def _make_openai_request(
        self,
        request: CodeGenerationRequest,
        session: aiohttp.ClientSession,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Make a request to the OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = self._prepare_messages(request)
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": min(request.max_tokens, self.max_tokens),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "n": request.n,
            "stream": stream
        }
        
        if request.stop_sequences:
            data["stop"] = request.stop_sequences
            
        async with session.post(
            self.endpoint,
            headers=headers,
            json=data
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"API request failed with status {response.status}: {error_text}")
                
            if stream:
                return await self._handle_openai_stream(response)
            else:
                return await response.json()

    def _prepare_messages(self, request: CodeGenerationRequest) -> List[Dict[str, str]]:
        """Prepare messages for the API request"""
        system_prompt = self._build_system_prompt(request)
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add context if provided
        if request.context:
            context_str = json.dumps(request.context, indent=2)
            messages.append({
                "role": "system",
                "content": f"Additional context:\n{context_str}"
            })
            
        # Add the user's prompt
        messages.append({"role": "user", "content": request.prompt})
        return messages

    def _build_system_prompt(self, request: CodeGenerationRequest) -> str:
        """Build the system prompt with language-specific instructions"""
        language = request.language.lower()
        
        prompts = {
            "python": (
                "You are an expert Python developer. Generate clean, efficient, and well-documented code. "
                "Follow PEP 8 guidelines and include type hints. Add docstrings for all functions and classes."
            ),
            "javascript": (
                "You are an expert JavaScript developer. Generate clean, modern, and efficient code. "
                "Use ES6+ features where appropriate. Include JSDoc comments for all functions and classes."
            ),
            "typescript": (
                "You are an expert TypeScript developer. Generate type-safe, well-structured code. "
                "Use strict typing and follow best practices. Include comprehensive type definitions and JSDoc."
            ),
            "java": (
                "You are an expert Java developer. Generate clean, efficient, and well-documented code. "
                "Follow Java coding conventions and include Javadoc comments for all public classes and methods."
            ),
            "default": (
                f"You are an expert {language} developer. Generate clean, efficient, and well-documented code. "
                "Follow the best practices and conventions for the language."
            )
        }
        
        return prompts.get(language, prompts["default"])

    async def _handle_anthropic_stream(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle streaming response from Anthropic API"""
        result = {
            "content": [{"text": ""}],
            "model": self.model,
            "usage": {"output_tokens": 0},
            "stop_reason": "stop_sequence"
        }
        
        async for line in response.content:
            if line.startswith(b'data: '):
                data = line[6:].strip()
                if data == b'[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if 'delta' in chunk and 'text' in chunk['delta']:
                        result["content"][0]["text"] += chunk['delta']['text']
                        result["usage"]["output_tokens"] += 1
                except json.JSONDecodeError:
                    continue
                    
        return result

    async def _handle_openai_stream(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle streaming response from OpenAI API"""
        result = {
            "choices": [{"message": {"content": ""}}],
            "model": self.model,
            "usage": {"total_tokens": 0},
            "finish_reason": "stop"
        }
        
        async for line in response.content:
            if line.startswith(b'data: '):
                data = line[6:].strip()
                if data == b'[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if 'choices' in chunk and chunk['choices']:
                        delta = chunk['choices'][0].get('delta', {})
                        if 'content' in delta:
                            result["choices"][0]["message"]["content"] += delta['content']
                except json.JSONDecodeError:
                    continue
                    
        return result
    
    async def _make_local_request(
        self,
        request: CodeGenerationRequest,
        session: aiohttp.ClientSession,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Make a request to a local model API"""
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "prompt": request.prompt,
            "max_tokens": min(request.max_tokens, self.max_tokens),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": stream
        }
        
        if request.stop_sequences:
            data["stop"] = request.stop_sequences
            
        async with session.post(
            self.endpoint,
            headers=headers,
            json=data
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Local API request failed with status {response.status}: {error_text}")
                
            return await response.json()

    async def generate_code(
        self,
        request: CodeGenerationRequest
    ) -> CodeGenerationResponse:
        """
        Generate code based on the provided request.
        
        Args:
            request: The code generation request
            
        Returns:
            CodeGenerationResponse: The generated code and metadata
            
        Raises:
            ValueError: If the request is invalid
            Exception: If there's an error during generation
        """
        start_time = time.time()
        
        # Validate the request
        try:
            request = CodeGenerationRequest(**request.dict())
        except Exception as e:
            raise ValueError(f"Invalid request: {str(e)}")
            
        # Check cache if enabled
        cache_key = self._get_cache_key(request)
        if self.config["cache_enabled"]:
            cached_result = await self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
        
        try:
            # Make the API request
            response = await self._make_request(request)
            
            # Process the response based on provider
            if self.provider == ModelProvider.ANTHROPIC:
                generated_code = response["content"][0]["text"]
                tokens_used = response["usage"]["output_tokens"]
                finish_reason = response["stop_reason"]
            elif self.provider == ModelProvider.OPENAI:
                generated_code = response["choices"][0]["message"]["content"]
                tokens_used = response["usage"]["total_tokens"]
                finish_reason = response["choices"][0]["finish_reason"]
            else:  # LOCAL
                generated_code = response["choices"][0]["text"]
                tokens_used = response["usage"]["total_tokens"]
                finish_reason = response["choices"][0].get("finish_reason", "stop")
            
            # Post-process the generated code
            generated_code = self._post_process_code(generated_code, request.language)
            
            # Create the response
            result = CodeGenerationResponse(
                generated_code=generated_code,
                model_used=self.model,
                provider=self.provider.value,
                tokens_used=tokens_used,
                finish_reason=finish_reason,
                latency_ms=(time.time() - start_time) * 1000,
                metadata={
                    "model": self.model,
                    "provider": self.provider.value,
                    "cache_hit": False,
                    "language": request.language
                }
            )
            
            # Cache the result if enabled
            if self.config["cache_enabled"]:
                await self._cache_result(cache_key, result)
                
            return result
            
        except Exception as e:
            logger.error(f"Error generating code: {str(e)}", exc_info=True)
            raise Exception(f"Failed to generate code: {str(e)}")
    
    async def stream_generate(
        self,
        request: CodeGenerationRequest,
        on_chunk: Callable[[str], None]
    ) -> None:
        """
        Stream generated code chunks to a callback function.
        
        Args:
            request: The code generation request
            on_chunk: Callback function that receives chunks of generated code
            
        Raises:
            Exception: If there's an error during streaming
        """
        try:
            # Make a copy of the request with streaming enabled
            stream_request = request.copy(update={"stream": True})
            
            # Make the streaming request
            response = await self._make_request(stream_request, stream=True)
            
            # Process the streaming response
            if self.provider == ModelProvider.ANTHROPIC:
                await self._process_anthropic_stream(response, on_chunk)
            elif self.provider == ModelProvider.OPENAI:
                await self._process_openai_stream(response, on_chunk)
            else:  # LOCAL
                await self._process_local_stream(response, on_chunk)
                
        except Exception as e:
            logger.error(f"Error in stream generation: {str(e)}", exc_info=True)
            raise Exception(f"Stream generation failed: {str(e)}")
    
    async def batch_generate(
        self,
        requests: List[CodeGenerationRequest]
    ) -> List[CodeGenerationResponse]:
        """
        Generate multiple code snippets in parallel.
        
        Args:
            requests: List of code generation requests
            
        Returns:
            List[CodeGenerationResponse]: List of generated code responses
        """
        if not requests:
            return []
            
        # Limit the number of concurrent requests
        semaphore = asyncio.Semaphore(self.config["max_parallel_requests"])
        
        async def process_request(req: CodeGenerationRequest) -> CodeGenerationResponse:
            async with semaphore:
                return await self.generate_code(req)
        
        # Process all requests in parallel
        tasks = [process_request(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def _post_process_code(self, code: str, language: str) -> str:
        """Post-process the generated code"""
        # Remove markdown code blocks if present
        code = re.sub(r'^```(?:\w+)?\s*\n', '', code, flags=re.MULTILINE)
        code = re.sub(r'\n```\s*$', '', code, flags=re.MULTILINE)
        
        # Language-specific post-processing
        if language == 'python':
            # Ensure proper indentation
            code = textwrap.dedent(code)
            
            # Try to parse the code to check for syntax errors
            try:
                ast.parse(code)
            except SyntaxError as e:
                logger.warning(f"Generated Python code has syntax errors: {e}")
        
        return code.strip()
    
    async def _get_cached_result(self, cache_key: str) -> Optional[CodeGenerationResponse]:
        """Get a cached result if it exists"""
        # In a real implementation, this would use Redis or similar
        return None
    
    async def _cache_result(self, cache_key: str, result: CodeGenerationResponse) -> None:
        """Cache a generation result"""
        # In a real implementation, this would use Redis or similar
        pass
    
    async def _process_anthropic_stream(
        self,
        response: aiohttp.ClientResponse,
        on_chunk: Callable[[str], None]
    ) -> None:
        """Process a streaming response from Anthropic"""
        async for line in response.content:
            if line.startswith(b'data: '):
                data = line[6:].strip()
                if data == b'[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if 'delta' in chunk and 'text' in chunk['delta']:
                        await on_chunk(chunk['delta']['text'])
                except json.JSONDecodeError:
                    continue
    
    async def _process_openai_stream(
        self,
        response: aiohttp.ClientResponse,
        on_chunk: Callable[[str], None]
    ) -> None:
        """Process a streaming response from OpenAI"""
        async for line in response.content:
            if line.startswith(b'data: '):
                data = line[6:].strip()
                if data == b'[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if 'choices' in chunk and chunk['choices']:
                        delta = chunk['choices'][0].get('delta', {})
                        if 'content' in delta:
                            await on_chunk(delta['content'])
                except json.JSONDecodeError:
                    continue
    
    async def _process_local_stream(
        self,
        response: aiohttp.ClientResponse,
        on_chunk: Callable[[str], None]
    ) -> None:
        """Process a streaming response from a local model"""
        async for line in response.content:
            if line.startswith(b'data: '):
                data = line[6:].strip()
                if data == b'[DONE]':
                    break
                try:
                    chunk = json.loads(data)
                    if 'text' in chunk:
                        await on_chunk(chunk['text'])
                except json.JSONDecodeError:
                    continue
            
            system_prompt = (
                f"You are an expert software engineer specializing in {request.language}. "
                "Generate clean, efficient, and well-documented code. "
                "Include appropriate error handling and comments explaining complex logic."
            )
            
            if request.template_name:
                system_prompt += f"\nUse the {request.template_name} template as a reference."
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.prompt}
            ]
            
            response = await self._make_request(
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            return CodeGenerationResponse(
                generated_code=response["content"][0]["text"],
                model_used=response["model"],
                tokens_used=response["usage"]["output_tokens"],
                finish_reason=response["stop_reason"],
                metadata={
                    "id": response["id"],
                    "type": response["type"]
                }
            )
            
        except Exception as e:
            raise Exception(f"Failed to generate code: {str(e)}")
    
    async def stream_generate(
        self,
        request: CodeGenerationRequest,
        on_chunk: Callable[[str], None]
    ) -> None:
        """Stream generated code chunks to a callback function"""
        try:
            system_prompt = (
                f"You are an expert software engineer specializing in {request.language}. "
                "Generate clean, efficient, and well-documented code. "
                "Include appropriate error handling and comments explaining complex logic."
            )
            
            if request.template_name:
                system_prompt += f"\nUse the {request.template_name} template as a reference."
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.prompt}
            ]
            
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "accept": "text/event-stream"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": True
            }
            
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    CLAUDE_API_URL,
                    headers=headers,
                    json=data,
                    timeout=60.0
                ) as response:
                    if response.status_code != 200:
                        error_msg = await response.aread()
                        raise Exception(f"API request failed with status {response.status_code}: {error_msg}")
                    
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            data = line[6:].strip()
                            if data == '[DONE]':
                                break
                                
                            try:
                                chunk = json.loads(data)
                                if 'delta' in chunk and 'text' in chunk['delta']:
                                    await on_chunk(chunk['delta']['text'])
                            except json.JSONDecodeError:
                                continue
            
        except Exception as e:
            raise Exception(f"Stream generation failed: {str(e)}")
    
    async def batch_generate(
        self,
        requests: List[CodeGenerationRequest]
    ) -> List[CodeGenerationResponse]:
        """Generate multiple code snippets in parallel"""
        import asyncio
        tasks = [self.generate_code(req) for req in requests]
        return await asyncio.gather(*tasks, return_exceptions=True)
