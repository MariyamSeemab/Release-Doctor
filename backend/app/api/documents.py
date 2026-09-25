"""Document upload endpoint."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Artifact, ArtifactType, ReleaseAnalysis
from app.schemas import ArtifactRead

router = APIRouter()

UPLOAD_DIR = Path("/tmp/release-doctor-uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post("/upload", response_model=ArtifactRead, status_code=201)
async def upload_document(
    analysis_id: uuid.UUID = Form(...),
    artifact_type: ArtifactType = Form(ArtifactType.OTHER),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> ArtifactRead:
    analysis = await db.get(ReleaseAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 20 MB)")

    dest = UPLOAD_DIR / f"{uuid.uuid4()}_{file.filename}"
    dest.write_bytes(contents)

    artifact = Artifact(
        analysis_id=analysis_id,
        type=artifact_type,
        name=file.filename or "upload",
        reference=str(dest),
        metadata_={"size": len(contents), "content_type": file.content_type},
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return ArtifactRead.model_validate(artifact)
