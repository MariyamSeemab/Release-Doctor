"""Impact map builder — constructs the React Flow node/edge graph for an analysis."""
from __future__ import annotations

import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Finding, ReleaseAnalysis, RiskRelation
from app.schemas import ImpactEdge, ImpactMapRead, ImpactNode


async def build_impact_map(analysis_id: uuid.UUID, db: AsyncSession) -> ImpactMapRead:
    findings_result = await db.execute(
        select(Finding).where(Finding.analysis_id == analysis_id)
    )
    findings = findings_result.scalars().all()

    relations_result = await db.execute(
        select(RiskRelation).where(RiskRelation.analysis_id == analysis_id)
    )
    relations = relations_result.scalars().all()

    nodes: List[ImpactNode] = []
    edges: List[ImpactEdge] = []
    seen_files: set = set()

    for f in findings:
        # Finding node
        nodes.append(
            ImpactNode(
                id=str(f.id),
                type="risk",
                label=f.title,
                data={
                    "severity": f.severity.value,
                    "category": f.category,
                    "source_agent": f.source_agent,
                },
            )
        )

        # File node (deduplicated)
        if f.file_path and f.file_path not in seen_files:
            seen_files.add(f.file_path)
            file_node_id = f"file:{f.file_path}"
            nodes.append(
                ImpactNode(id=file_node_id, type="file", label=f.file_path, data={})
            )
            edges.append(
                ImpactEdge(
                    id=f"e-file-{f.id}",
                    source=file_node_id,
                    target=str(f.id),
                    label="has risk",
                )
            )

    # Risk relation edges
    for rel in relations:
        edges.append(
            ImpactEdge(
                id=str(rel.id),
                source=str(rel.finding_id),
                target=str(rel.related_finding_id),
                label=rel.relationship_type.value,
            )
        )

    return ImpactMapRead(nodes=nodes, edges=edges)
