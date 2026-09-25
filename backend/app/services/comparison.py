"""Comparison service — computes resolved/new/remaining findings between two analyses."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AnalysisComparison, Finding, FindingStatus
from app.schemas import ComparisonRead


async def build_comparison(
    previous_id: uuid.UUID,
    current_id: uuid.UUID,
    db: AsyncSession,
) -> ComparisonRead:
    prev_findings = (
        await db.execute(select(Finding).where(Finding.analysis_id == previous_id))
    ).scalars().all()
    curr_findings = (
        await db.execute(select(Finding).where(Finding.analysis_id == current_id))
    ).scalars().all()

    prev_titles = {f.title for f in prev_findings}
    curr_titles = {f.title for f in curr_findings}

    resolved = prev_titles - curr_titles
    new = curr_titles - prev_titles
    remaining = prev_titles & curr_titles

    # Check if comparison already exists
    existing = (
        await db.execute(
            select(AnalysisComparison).where(
                AnalysisComparison.previous_analysis_id == previous_id,
                AnalysisComparison.current_analysis_id == current_id,
            )
        )
    ).scalar_one_or_none()

    if not existing:
        comparison = AnalysisComparison(
            previous_analysis_id=previous_id,
            current_analysis_id=current_id,
            resolved_count=len(resolved),
            new_count=len(new),
            remaining_count=len(remaining),
            details={
                "resolved": list(resolved),
                "new": list(new),
                "remaining": list(remaining),
            },
        )
        db.add(comparison)
        await db.commit()
        await db.refresh(comparison)
    else:
        comparison = existing

    return ComparisonRead.model_validate(comparison)
