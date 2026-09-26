"""Application configuration via pydantic-settings."""
from __future__ import annotations

from typing import Any, List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        # Don't try to JSON-decode plain string env vars for list fields —
        # we handle that ourselves in the _parse_cors validator below.
        env_ignore_empty=True,
    )

    # Database — Railway provides postgres:// or postgresql:// but asyncpg
    # needs postgresql+asyncpg://.  The validator below patches it automatically.
    database_url: str = "postgresql+asyncpg://releasedoctor:releasedoctor@localhost:5432/releasedoctor"

    @field_validator("database_url", mode="before")
    @classmethod
    def _fix_db_scheme(cls, v: Any) -> Any:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # JWT
    jwt_secret: str = "changeme-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # CORS — stored as a plain string internally; property below exposes List[str].
    # Accepts comma-separated values: CORS_ORIGINS=https://foo.vercel.app,http://localhost:3000
    cors_origins_raw: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    @property
    def cors_origins(self) -> List[str]:
        raw = self.cors_origins_raw.strip().strip("[]")
        return [o.strip().strip("\"'") for o in raw.split(",") if o.strip()]

    # Logging / observability
    log_level: str = "INFO"
    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "release-doctor"

    # AI / Orchestration
    ibm_bob_api_key: str = ""
    ibm_bob_endpoint: str = ""
    openai_api_key: str = ""

    # Deployment mode: set USE_INLINE_TASKS=true to run analyses in-process
    # instead of via Celery (useful when Redis is unavailable on free-tier hosts)
    use_inline_tasks: bool = False


settings = Settings()
