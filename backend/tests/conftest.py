"""Pytest configuration — async test setup with in-memory SQLite for speed."""
from __future__ import annotations

import os
import pytest

# Use SQLite for tests (no Postgres required) — must be set before any app import
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="session", autouse=True)
async def create_test_tables():
    """Create all ORM tables in the test SQLite DB before any test runs."""
    from app.database import engine, Base
    import app.models  # noqa: F401 — ensure all models are registered

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
