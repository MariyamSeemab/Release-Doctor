"""Pydantic schemas for request/response validation."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.models import (
    AgentStatus,
    AgentType,
    AnalysisStatus,
    ArtifactType,
    Confidence,
    FindingStatus,
    OverallStatus,
    RelationshipType,
    RemediationStatus,
    Severity,
)


# ── Base ──────────────────────────────────────────────────────────────────────

class TimestampMixin(BaseModel):
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Project ───────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    repository: str
    default_branch: str = "main"
    stack: Optional[Dict[str, Any]] = None


class ProjectRead(TimestampMixin):
    id: uuid.UUID
    name: str
    repository: str
    default_branch: str
    stack: Optional[Dict[str, Any]]
    updated_at: datetime


# ── Analysis ──────────────────────────────────────────────────────────────────

class AnalysisCreate(BaseModel):
    base_ref: str
    target_ref: str


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    base_ref: str
    target_ref: str
    status: AnalysisStatus
    overall_status: Optional[OverallStatus]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    change_map: Optional[Dict[str, Any]]
    created_at: datetime


# ── AgentRun ──────────────────────────────────────────────────────────────────

class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    agent_type: AgentType
    status: AgentStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    summary: Optional[str]
    error_message: Optional[str]


# ── Finding ───────────────────────────────────────────────────────────────────

class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    agent_run_id: Optional[uuid.UUID]
    severity: Severity
    confidence: Confidence
    category: str
    title: str
    description: str
    affected_component: Optional[str]
    file_path: Optional[str]
    line_start: Optional[int]
    line_end: Optional[int]
    commit_ref: Optional[str]
    evidence_snippet: Optional[str]
    why_it_matters: Optional[str]
    potential_release_impact: Optional[str]
    remediation: Optional[str]
    verification_method: Optional[str]
    source_agent: Optional[str]
    status: FindingStatus
    is_root_cause: bool
    merged_finding_ids: Optional[List[str]]
    created_at: datetime
    updated_at: datetime


# ── Artifact ──────────────────────────────────────────────────────────────────

class ArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    type: ArtifactType
    name: str
    reference: Optional[str]
    created_at: datetime


# ── Risk Relation ─────────────────────────────────────────────────────────────

class RiskRelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    related_finding_id: uuid.UUID
    relationship_type: RelationshipType


# ── Remediation Task ──────────────────────────────────────────────────────────

class RemediationTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    analysis_id: uuid.UUID
    finding_id: Optional[uuid.UUID]
    title: str
    priority: int
    status: RemediationStatus
    verification: Optional[str]
    created_at: datetime
    updated_at: datetime


class RemediationTaskUpdate(BaseModel):
    status: Optional[RemediationStatus] = None
    verification: Optional[str] = None


# ── Impact Map ────────────────────────────────────────────────────────────────

class ImpactNode(BaseModel):
    id: str
    type: str  # file | api | component | test | config | database | deployment | risk
    label: str
    data: Optional[Dict[str, Any]] = None


class ImpactEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None


class ImpactMapRead(BaseModel):
    nodes: List[ImpactNode]
    edges: List[ImpactEdge]


# ── Comparison ────────────────────────────────────────────────────────────────

class ComparisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    previous_analysis_id: uuid.UUID
    current_analysis_id: uuid.UUID
    resolved_count: int
    new_count: int
    remaining_count: int
    details: Optional[Dict[str, Any]]
    created_at: datetime


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── SSE / WS Events ───────────────────────────────────────────────────────────

class AnalysisEvent(BaseModel):
    event: str  # agent_started | agent_completed | agent_failed | finding_added | analysis_completed
    analysis_id: str
    agent_type: Optional[str] = None
    finding_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
