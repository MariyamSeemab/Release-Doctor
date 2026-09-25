"""Project endpoints: POST /projects, GET /projects, GET /projects/{id}/history,
POST /projects/{id}/analyses (create analysis)."""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import Project, ReleaseAnalysis, AnalysisStatus
from app.schemas import AnalysisCreate, AnalysisRead, ProjectCreate, ProjectRead

router = APIRouter()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> ProjectRead:
    project = Project(**body.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return ProjectRead.model_validate(project)


@router.get("", response_model=List[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> List[ProjectRead]:
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return [ProjectRead.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> ProjectRead:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectRead.model_validate(project)


@router.get("/{project_id}/history", response_model=List[AnalysisRead])
async def project_history(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> List[AnalysisRead]:
    result = await db.execute(
        select(ReleaseAnalysis)
        .where(ReleaseAnalysis.project_id == project_id)
        .order_by(ReleaseAnalysis.created_at.desc())
    )
    analyses = result.scalars().all()
    return [AnalysisRead.model_validate(a) for a in analyses]


@router.post("/{project_id}/analyses", response_model=AnalysisRead, status_code=status.HTTP_201_CREATED)
async def create_analysis(
    project_id: uuid.UUID,
    body: AnalysisCreate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> AnalysisRead:
    """Start a new release-readiness analysis (triggers background pipeline)."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    analysis = ReleaseAnalysis(
        project_id=project_id,
        base_ref=body.base_ref,
        target_ref=body.target_ref,
        status=AnalysisStatus.PENDING,
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    from app.tasks import run_analysis_task
    run_analysis_task.delay(str(analysis.id))

    return AnalysisRead.model_validate(analysis)
