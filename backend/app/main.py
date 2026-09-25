"""Release Doctor Backend — Application Entry Point."""
from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.router import api_router
from app.database import engine, Base
from app.logging_config import configure_logging
from app.observability import setup_tracing

configure_logging()
logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Release Doctor API",
        description="Multi-agent AI release-readiness analysis",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    # Global exception handler — never expose stack traces to clients
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", path=str(request.url), error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal error occurred. Check server logs for details."},
        )

    @app.on_event("startup")
    async def on_startup() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        setup_tracing(app)
        logger.info("release_doctor_started", version="0.1.0")

    @app.get("/health", tags=["meta"])
    async def health() -> dict:
        return {"status": "ok", "service": "release-doctor-api"}

    return app


app = create_app()
