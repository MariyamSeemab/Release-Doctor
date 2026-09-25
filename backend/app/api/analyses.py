"""Analysis endpoints — all analysis routes from Section 6."""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    AgentRun,
    AnalysisComparison,
    Finding,
    ReleaseAnalysis,
    RemediationTask,
    AnalysisStatus,
)
from app.schemas import (
    AgentRunRead,
    AnalysisRead,
    ComparisonRead,
    FindingRead,
    RemediationTaskRead,
    RemediationTaskUpdate,
)
from app.services.comparison import build_comparison
from app.services.impact_map import build_impact_map

router = APIRouter()


@router.get("/{analysis_id}", response_model=AnalysisRead)
async def get_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> AnalysisRead:
    analysis = await db.get(ReleaseAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisRead.model_validate(analysis)


@router.get("/{analysis_id}/agents", response_model=List[AgentRunRead])
async def get_agent_runs(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> List[AgentRunRead]:
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.analysis_id == analysis_id)
        .order_by(AgentRun.started_at)
    )
    return [AgentRunRead.model_validate(r) for r in result.scalars().all()]


@router.get("/{analysis_id}/findings", response_model=List[FindingRead])
async def get_findings(
    analysis_id: uuid.UUID,
    severity: str | None = None,
    agent_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> List[FindingRead]:
    q = select(Finding).where(Finding.analysis_id == analysis_id)
    if severity:
        q = q.where(Finding.severity == severity.upper())
    if agent_type:
        q = q.where(Finding.source_agent == agent_type.upper())
    result = await db.execute(q.order_by(Finding.severity, Finding.created_at))
    return [FindingRead.model_validate(f) for f in result.scalars().all()]


@router.get("/{analysis_id}/findings/{finding_id}", response_model=FindingRead)
async def get_finding(
    analysis_id: uuid.UUID,
    finding_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> FindingRead:
    finding = await db.get(Finding, finding_id)
    if not finding or finding.analysis_id != analysis_id:
        raise HTTPException(status_code=404, detail="Finding not found")
    return FindingRead.model_validate(finding)


@router.get("/{analysis_id}/impact-map", response_model=ImpactMapRead)
async def get_impact_map(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> ImpactMapRead:
    analysis = await db.get(ReleaseAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return await build_impact_map(analysis_id, db)


@router.get("/{analysis_id}/remediation", response_model=List[RemediationTaskRead])
async def get_remediation(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> List[RemediationTaskRead]:
    result = await db.execute(
        select(RemediationTask)
        .where(RemediationTask.analysis_id == analysis_id)
        .order_by(RemediationTask.priority)
    )
    return [RemediationTaskRead.model_validate(t) for t in result.scalars().all()]


@router.patch("/{analysis_id}/remediation/{task_id}", response_model=RemediationTaskRead)
async def update_remediation_task(
    analysis_id: uuid.UUID,
    task_id: uuid.UUID,
    body: RemediationTaskUpdate,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> RemediationTaskRead:
    task = await db.get(RemediationTask, task_id)
    if not task or task.analysis_id != analysis_id:
        raise HTTPException(status_code=404, detail="Task not found")
    if body.status is not None:
        task.status = body.status
    if body.verification is not None:
        task.verification = body.verification
    await db.commit()
    await db.refresh(task)
    return RemediationTaskRead.model_validate(task)


@router.post("/{analysis_id}/rerun", response_model=AnalysisRead, status_code=status.HTTP_201_CREATED)
async def rerun_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> AnalysisRead:
    """Create a new analysis based on the same project/refs and enqueue it."""
    prev = await db.get(ReleaseAnalysis, analysis_id)
    if not prev:
        raise HTTPException(status_code=404, detail="Analysis not found")

    new_analysis = ReleaseAnalysis(
        project_id=prev.project_id,
        base_ref=prev.base_ref,
        target_ref=prev.target_ref,
        status=AnalysisStatus.PENDING,
    )
    db.add(new_analysis)
    await db.commit()
    await db.refresh(new_analysis)

    from app.tasks import run_analysis_task

    run_analysis_task.delay(str(new_analysis.id))
    return AnalysisRead.model_validate(new_analysis)


@router.get("/{analysis_id}/comparison/{previous_analysis_id}", response_model=ComparisonRead)
async def get_comparison(
    analysis_id: uuid.UUID,
    previous_analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> ComparisonRead:
    return await build_comparison(previous_analysis_id, analysis_id, db)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_analysis(
    analysis_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> None:
    analysis = await db.get(ReleaseAnalysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.status not in (AnalysisStatus.PENDING, AnalysisStatus.RUNNING):
        raise HTTPException(status_code=400, detail="Analysis is not in a cancellable state")
    analysis.status = AnalysisStatus.CANCELLED
    await db.commit()
