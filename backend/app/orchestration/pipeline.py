"""Full analysis pipeline — wired to Celery, streams events via WebSocket."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import (
    AgentRun,
    AgentStatus,
    AgentType,
    AnalysisStatus,
    Artifact,
    Finding,
    ReleaseAnalysis,
    RemediationTask,
    RiskRelation,
    RelationshipType,
)
from app.orchestration.lead_agent import LeadAgent
from app.orchestration.release_decision import compute_release_decision
from app.repository.analyzer import RepositoryAnalyzer
from app.agents.base import AgentResult, EvidenceFinding

logger = structlog.get_logger(__name__)

# Path to the demo repository (mounted in Docker at /demo-repository)
_DEMO_REPO_PATH = "/demo-repository"


async def run_analysis_pipeline(analysis_id: str) -> dict:
    """Main pipeline — called by the Celery task."""
    async with AsyncSessionLocal() as db:
        analysis = await db.get(ReleaseAnalysis, uuid.UUID(analysis_id))
        if not analysis:
            logger.error("analysis_not_found", analysis_id=analysis_id)
            return {"error": "Analysis not found"}

        # Mark as running
        analysis.status = AnalysisStatus.RUNNING
        analysis.started_at = datetime.now(timezone.utc)
        await db.commit()

        # Determine repo path: use project repository or demo repo
        repo_path = analysis.project.repository if analysis.project and Path(analysis.project.repository).exists() else _DEMO_REPO_PATH

        # Load uploaded artifacts for this analysis
        artifacts: List[Artifact] = []
        result = await db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(Artifact).where(Artifact.analysis_id == analysis.id)
        )
        artifacts = result.scalars().all()

        try:
            # ── Step 1: Build change map ─────────────────────────────────
            logger.info("building_change_map", analysis_id=analysis_id)
            repo = RepositoryAnalyzer(repo_path)
            change_map = repo.build_change_map(analysis.base_ref, analysis.target_ref)
            analysis.change_map = change_map.to_dict()
            await db.commit()

            # ── Step 2: Lead agent selects which agents to run ───────────
            lead = LeadAgent(repo_path)
            selected = lead.select_agents(change_map)
            logger.info("agents_selected", count=len(selected), analysis_id=analysis_id)

            # ── Step 3: Create AgentRun records ──────────────────────────
            agent_run_map: dict[AgentType, AgentRun] = {}
            for agent_type, _ in selected:
                run = AgentRun(analysis_id=analysis.id, agent_type=agent_type)
                db.add(run)
                agent_run_map[agent_type] = run
            await db.commit()

            # ── Step 4: Event callback for WebSocket streaming ───────────
            from app.api.websocket import broadcast

            async def event_callback(event: str, agent_type_str: str, result: Any = None, error: str = "") -> None:
                agent_run = agent_run_map.get(AgentType(agent_type_str))
                if agent_run:
                    if event == "agent_started":
                        agent_run.status = AgentStatus.RUNNING
                        agent_run.started_at = datetime.now(timezone.utc)
                    elif event == "agent_completed":
                        agent_run.status = AgentStatus.COMPLETED
                        agent_run.completed_at = datetime.now(timezone.utc)
                        if result:
                            agent_run.summary = result.summary
                    elif event == "agent_failed":
                        agent_run.status = AgentStatus.FAILED
                        agent_run.error_message = error
                        agent_run.completed_at = datetime.now(timezone.utc)
                    await db.commit()

                await broadcast(analysis_id, {
                    "event": event,
                    "analysis_id": analysis_id,
                    "agent_type": agent_type_str,
                    "error": error,
                })

            # ── Step 5: Run agents in parallel ───────────────────────────
            results = await lead.run_agents_parallel(
                selected, change_map, artifacts=artifacts, event_callback=event_callback
            )

            # ── Step 6: Persist findings ─────────────────────────────────
            all_correlated_findings: List[EvidenceFinding] = []
            corr_result = results.get(AgentType.RISK_CORRELATION)
            if corr_result:
                all_correlated_findings = corr_result.findings

            for ef in all_correlated_findings:
                agent_run = agent_run_map.get(
                    AgentType(ef.source_agent) if ef.source_agent else AgentType.RISK_CORRELATION
                )
                finding = Finding(
                    analysis_id=analysis.id,
                    agent_run_id=agent_run.id if agent_run else None,
                    severity=ef.severity,
                    confidence=ef.confidence,
                    category=ef.category,
                    title=ef.title,
                    description=ef.description,
                    affected_component=ef.affected_component,
                    file_path=ef.file_path,
                    line_start=ef.line_start,
                    line_end=ef.line_end,
                    commit_ref=ef.commit_ref or analysis.target_ref,
                    evidence_snippet=ef.evidence_snippet,
                    why_it_matters=ef.why_it_matters,
                    potential_release_impact=ef.potential_release_impact,
                    remediation=ef.remediation,
                    verification_method=ef.verification_method,
                    source_agent=ef.source_agent,
                    is_root_cause=ef.extra.get("is_root_cause", False),
                    merged_finding_ids=ef.extra.get("merged_from"),
                )
                db.add(finding)
                await db.flush()  # get the ID

                # Create remediation task for CRITICAL/HIGH findings
                if ef.severity.value in ("CRITICAL", "HIGH"):
                    task = RemediationTask(
                        analysis_id=analysis.id,
                        finding_id=finding.id,
                        title=f"Fix: {ef.title}",
                        priority=1 if ef.severity.value == "CRITICAL" else 2,
                    )
                    db.add(task)

                # Notify via WebSocket
                await broadcast(analysis_id, {
                    "event": "finding_added",
                    "analysis_id": analysis_id,
                    "finding": {
                        "id": str(finding.id),
                        "title": ef.title,
                        "severity": ef.severity.value,
                        "category": ef.category,
                    },
                })

            # ── Step 7: Compute release decision ─────────────────────────
            overall = compute_release_decision(all_correlated_findings)
            analysis.overall_status = overall
            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.now(timezone.utc)
            await db.commit()

            await broadcast(analysis_id, {
                "event": "analysis_completed",
                "analysis_id": analysis_id,
                "overall_status": overall.value,
            })

            logger.info("analysis_completed", analysis_id=analysis_id, overall_status=overall.value)
            return {"analysis_id": analysis_id, "overall_status": overall.value, "findings": len(all_correlated_findings)}

        except Exception as exc:
            logger.error("pipeline_failed", analysis_id=analysis_id, error=str(exc))
            analysis.status = AnalysisStatus.FAILED
            analysis.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await broadcast(analysis_id, {"event": "analysis_failed", "analysis_id": analysis_id, "error": str(exc)})
            raise
