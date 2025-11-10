"""
Configuration settings for the Orb platform
"""
import os
from typing import Optional
from pydantic import BaseSettings, Field, HttpUrl

class Settings(BaseSettings):
    """Application settings"""
    # Application settings
    APP_NAME: str = "Orb"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # API settings
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]
    
    # Claude API settings
    CLAUDE_API_KEY: str = Field(..., env="ANTHROPIC_API_KEY")
    CLAUDE_API_URL: str = "https://api.anthropic.com/v1/messages"
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229")
    CLAUDE_MAX_TOKENS: int = 4096
    CLAUDE_TEMPERATURE: float = 0.7
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./orb.db")
    
    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Authentication settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # File storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    
    # Caching
    CACHE_TTL: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
