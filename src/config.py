import os
import sys
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator

class Settings(BaseSettings):
    """Application configuration with validation.
    
    Configuration is loaded from .env file in the project root.
    See .env.example for a complete configuration template.
    """
    
    # ===== Application Metadata =====
    APP_NAME: str = "LuxSelect"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    
    # ===== AI Configuration =====
    OPENAI_API_KEY: str = Field(
        default="", 
        description="OpenAI-compatible API Key (Required)",
        min_length=10
    )
    OPENAI_BASE_URL: str = Field(
        default="https://api.openai.com/v1", 
        description="OpenAI Base URL"
    )
    AI_MODEL: str = Field(
        default="gpt-3.5-turbo", 
        description="Model to use",
        min_length=1
    )
    AI_TIMEOUT: int = Field(
        default=30,
        ge=5,
        le=120,
        description="API timeout in seconds"
    )
    AI_MAX_TOKENS: int = Field(
        default=500,
        ge=100,
        le=2000,
        description="Maximum tokens in AI response"
    )
    AI_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="AI temperature (creativity)"
    )
    
    # ===== Interaction Configuration =====
    SELECTION_DELAY: float = Field(
        default=0.05,
        ge=0.01,
        le=0.5,
        description="Delay before copying selected text"
    )
    DRAG_THRESHOLD: int = Field(
        default=5,
        ge=2,
        le=50,
        description="Minimum drag distance in pixels"
    )
    DEBOUNCE_INTERVAL: float = Field(
        default=0.5,
        ge=0.1,
        le=2.0,
        description="Time window for debouncing selections"
    )
    
    # Legacy field for backward compatibility
    DOUBLE_CLICK_THRESHOLD: float = Field(default=0.5, ge=0.1, le=2.0)
    
    # ===== Privacy Settings =====
    ENABLE_PRIVACY_FILTER: bool = Field(
        default=True,
        description="Enable sensitive data filtering"
    )
    
    # ===== Performance Settings =====
    ENABLE_CACHE: bool = Field(
        default=True,
        description="Enable response caching"
    )
    CACHE_MAX_SIZE: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Maximum cache entries"
    )
    
    # ===== Exclusion Settings =====
    EXCLUDED_WINDOWS: str = Field(
        default="",
        description="Comma-separated list of excluded window titles"
    )
    
    # ===== Advanced Settings =====
    LOG_DIR: str = Field(
        default="",
        description="Log directory (empty for default)"
    )
    LOG_MAX_SIZE_MB: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum log file size in MB"
    )
    LOG_BACKUP_COUNT: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of backup log files"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields in .env
    )
    
    @field_validator('OPENAI_API_KEY')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key format."""
        if not v or v == "sk-your-actual-api-key-here":
            raise ValueError(
                "OPENAI_API_KEY is required. Please set it in your .env file. "
                "See .env.example for reference."
            )
        if len(v) < 10:
            raise ValueError("OPENAI_API_KEY seems too short. Please check your configuration.")
        return v
    
    @field_validator('OPENAI_BASE_URL')
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate and normalize base URL."""
        if not v.startswith('http://') and not v.startswith('https://'):
            raise ValueError("OPENAI_BASE_URL must start with http:// or https://")
        # Remove trailing slash for consistency
        return v.rstrip('/')
    
    @field_validator('EXCLUDED_WINDOWS')
    @classmethod
    def parse_excluded_windows(cls, v: str) -> str:
        """Parse and validate excluded windows list."""
        # Just store as string, will be parsed at runtime
        return v.strip()
    
    def get_excluded_windows_list(self) -> List[str]:
        """Get excluded windows as a list."""
        if not self.EXCLUDED_WINDOWS:
            return []
        return [w.strip() for w in self.EXCLUDED_WINDOWS.split(',') if w.strip()]
    
    def get_log_dir(self) -> Path:
        """Get the log directory path."""
        if self.LOG_DIR:
            return Path(self.LOG_DIR)
        # Default: ~/.luxselect/logs
        return Path.home() / ".luxselect" / "logs"


def load_settings() -> Settings:
    """Load and validate settings with friendly error messages."""
    try:
        settings = Settings()
        return settings
    except Exception as e:
        print(f"\n❌ Configuration Error: {e}\n")
        print("💡 Tips:")
        print("   1. Make sure you have a .env file in the project root")
        print("   2. Copy .env.example to .env: copy .env.example .env")
        print("   3. Edit .env and set your OPENAI_API_KEY")
        print("   4. See .env.example for all available options\n")
        print(f"   Current directory: {os.getcwd()}")
        print(f"   Looking for .env at: {Path('.env').absolute()}\n")
        sys.exit(1)


# Load settings on module import
settings = load_settings()
