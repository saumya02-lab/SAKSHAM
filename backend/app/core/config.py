from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "SAKSHAM"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://nexus:nexus_dev@postgres:5432/nexus"

    # Redis
    REDIS_URL: str = "redis://redis:6379"

    # ChromaDB
    CHROMA_URL: str = "http://chroma:8000"

    # Auth
    JWT_SECRET: str = "change-this-to-a-random-secret-in-production"
    JWT_EXPIRES_MIN: int = 60
    JWT_ALGORITHM: str = "HS256"

    # LLM
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Per-agent model overrides (leave blank to use provider default)
    RESEARCH_MODEL: str = ""
    CODING_MODEL: str = ""
    EMAIL_MODEL: str = ""
    ROUTING_MODEL: str = ""

    # Search
    SEARCH_API_KEY: Optional[str] = None
    SERPER_API_KEY: Optional[str] = None

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Upload
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024  # 20MB

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
