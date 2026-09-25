"""Application configuration via pydantic-settings."""
from __future__ import annotations

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://releasedoctor:releasedoctor@localhost:5432/releasedoctor"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # JWT
    jwt_secret: str = "changeme-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]

    # Logging / observability
    log_level: str = "INFO"
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "release-doctor"

    # AI / Orchestration
    ibm_bob_api_key: str = ""
    ibm_bob_endpoint: str = ""
    openai_api_key: str = ""


settings = Settings()
