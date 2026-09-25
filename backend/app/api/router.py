"""Top-level API router — mounts all sub-routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api import auth, projects, analyses, documents, websocket

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
