"""Configuration management using Pydantic settings."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # LLM Provider API Keys
    groq_api_key: str
    google_api_key: str
    openai_api_key: str = ""  # Optional
    huggingface_api_key: str = ""  # Optional - FREE tier available!
    
    # Gateway Configuration
    gateway_api_key: str
    log_level: str = "INFO"
    environment: str = "development"
    
    # LLM Provider Settings
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_model: str = "gemini-3-pro-preview"
    openai_model: str = "gpt-3.5-turbo"
    huggingface_model: str = "google/flan-t5-large"
    ollama_model: str = "llama3.2"  # Local, FREE, unlimited!
    
    # Cache Configuration
    redis_url: str = "redis://localhost:6379"
    cache_similarity_threshold: float = 0.95  # 95% similar = cache hit
    cache_ttl: int = 3600  # 1 hour
    
    # Sandbox Configuration
    sandbox_timeout: int = 30  # seconds
    sandbox_memory_limit: str = "256m"
    sandbox_cpu_limit: float = 0.5
    sandbox_network_disabled: bool = True
    
    # Rate Limiting
    max_requests_per_minute: int = 10  # Global fallback
    groq_rpm: int = 30
    gemini_rpm: int = 6  # Strict free tier limit
    openai_rpm: int = 60
    huggingface_rpm: int = 30
    ollama_rpm: int = 60
    request_timeout: int = 120  # seconds
    
    # Docker Settings
    docker_host: str = "unix://var/run/docker.sock"
    cleanup_containers: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
