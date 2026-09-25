"""SQLAlchemy ORM models for Release Doctor."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Enumerations ──────────────────────────────────────────────────────────────


class OverallStatus(str, enum.Enum):
    BLOCKED = "BLOCKED"
    ATTENTION_REQUIRED = "ATTENTION_REQUIRED"
    READY_FOR_RELEASE = "READY_FOR_RELEASE"
    UNVERIFIED = "UNVERIFIED"


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentType(str, enum.Enum):
    LEAD = "LEAD"
    CODE_HEALTH = "CODE_HEALTH"
    DATABASE = "DATABASE"
    TEST_QA = "TEST_QA"
    SECURITY = "SECURITY"
    CONFIGURATION = "CONFIGURATION"
    DEPENDENCY = "DEPENDENCY"
    API_INTEGRATION = "API_INTEGRATION"
    DEPLOYMENT_DEVOPS = "DEPLOYMENT_DEVOPS"
    DOCUMENTATION = "DOCUMENTATION"
    RISK_CORRELATION = "RISK_CORRELATION"


class AgentStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class Severity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class Confidence(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class FindingStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    RECHECK_REQUIRED = "RECHECK_REQUIRED"
    ACCEPTED = "ACCEPTED"


class RemediationStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    RECHECK_REQUIRED = "RECHECK_REQUIRED"


class ArtifactType(str, enum.Enum):
    REQUIREMENT = "REQUIREMENT"
    API_SPEC = "API_SPEC"
    ARCHITECTURE = "ARCHITECTURE"
    RELEASE_NOTES = "RELEASE_NOTES"
    OTHER = "OTHER"


class RelationshipType(str, enum.Enum):
    ROOT_CAUSE = "ROOT_CAUSE"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    DUPLICATE = "DUPLICATE"
    RELATED = "RELATED"


# ── Models ────────────────────────────────────────────────────────────────────


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    repository: Mapped[str] = mapped_column(String(1024), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    stack: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    analyses: Mapped[list["ReleaseAnalysis"]] = relationship("ReleaseAnalysis", back_populates="project")


class ReleaseAnalysis(Base):
    __tablename__ = "release_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    base_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False
    )
    overall_status: Mapped[Optional[OverallStatus]] = mapped_column(
        Enum(OverallStatus), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    change_map: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="analyses")
    agent_runs: Mapped[list["AgentRun"]] = relationship("AgentRun", back_populates="analysis")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="analysis")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="analysis")
    risk_relations: Mapped[list["RiskRelation"]] = relationship("RiskRelation", back_populates="analysis")
    remediation_tasks: Mapped[list["RemediationTask"]] = relationship("RemediationTask", back_populates="analysis")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("release_analyses.id"), nullable=False)
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False)
    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus), default=AgentStatus.PENDING, nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    analysis: Mapped["ReleaseAnalysis"] = relationship("ReleaseAnalysis", back_populates="agent_runs")
    findings: Mapped[list["Finding"]] = relationship("Finding", back_populates="agent_run")


class Finding(Base):
    """Full evidence-model finding as specified in Section 5."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("release_analyses.id"), nullable=False)
    agent_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=True
    )

    # Core evidence model fields
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)
    confidence: Mapped[Confidence] = mapped_column(Enum(Confidence), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_component: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    commit_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    evidence_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    why_it_matters: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    potential_release_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_method: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus), default=FindingStatus.OPEN, nullable=False
    )
    is_root_cause: Mapped[bool] = mapped_column(Boolean, default=False)
    merged_finding_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    analysis: Mapped["ReleaseAnalysis"] = relationship("ReleaseAnalysis", back_populates="findings")
    agent_run: Mapped[Optional["AgentRun"]] = relationship("AgentRun", back_populates="findings")
    risk_relations: Mapped[list["RiskRelation"]] = relationship(
        "RiskRelation", foreign_keys="RiskRelation.finding_id", back_populates="finding"
    )
    remediation_tasks: Mapped[list["RemediationTask"]] = relationship(
        "RemediationTask", back_populates="finding"
    )


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("release_analyses.id"), nullable=False)
    type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analysis: Mapped["ReleaseAnalysis"] = relationship("ReleaseAnalysis", back_populates="artifacts")


class RiskRelation(Base):
    __tablename__ = "risk_relations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("release_analyses.id"), nullable=False)
    finding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("findings.id"), nullable=False)
    related_finding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("findings.id"), nullable=False)
    relationship_type: Mapped[RelationshipType] = mapped_column(Enum(RelationshipType), nullable=False)

    analysis: Mapped["ReleaseAnalysis"] = relationship("ReleaseAnalysis", back_populates="risk_relations")
    finding: Mapped["Finding"] = relationship("Finding", foreign_keys=[finding_id], back_populates="risk_relations")
    related_finding: Mapped["Finding"] = relationship("Finding", foreign_keys=[related_finding_id])


class RemediationTask(Base):
    __tablename__ = "remediation_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("release_analyses.id"), nullable=False)
    finding_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("findings.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    status: Mapped[RemediationStatus] = mapped_column(
        Enum(RemediationStatus), default=RemediationStatus.OPEN, nullable=False
    )
    verification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    analysis: Mapped["ReleaseAnalysis"] = relationship("ReleaseAnalysis", back_populates="remediation_tasks")
    finding: Mapped[Optional["Finding"]] = relationship("Finding", back_populates="remediation_tasks")


class AnalysisComparison(Base):
    __tablename__ = "analysis_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    previous_analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("release_analyses.id"), nullable=False
    )
    current_analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("release_analyses.id"), nullable=False
    )
    resolved_count: Mapped[int] = mapped_column(Integer, default=0)
    new_count: Mapped[int] = mapped_column(Integer, default=0)
    remaining_count: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    previous_analysis: Mapped["ReleaseAnalysis"] = relationship(
        "ReleaseAnalysis", foreign_keys=[previous_analysis_id]
    )
    current_analysis: Mapped["ReleaseAnalysis"] = relationship(
        "ReleaseAnalysis", foreign_keys=[current_analysis_id]
    )
