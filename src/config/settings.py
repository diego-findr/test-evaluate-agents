"""
Application settings and configuration
"""

import logging
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration using pydantic-settings for type-safe environment variables."""
    
    openai_api_key: str = Field(..., description="OpenAI API Key")
    openai_model: str = Field(default="gpt-4o-mini", description="OpenAI model to use")
    openai_temperature: float = Field(default=0.2, description="LLM temperature")
    log_level: str = Field(default="INFO", description="Logging level")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def setup_logging(settings: Settings):
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler()]
    )

