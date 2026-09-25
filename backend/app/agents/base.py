"""Base agent interface — all specialized agents implement this contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.models import AgentType, Confidence, Severity


@dataclass
class EvidenceFinding:
    """A single structured finding produced by an agent."""
    title: str
    severity: Severity
    confidence: Confidence
    category: str
    description: str
    affected_component: Optional[str] = None
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    commit_ref: Optional[str] = None
    evidence_snippet: Optional[str] = None
    why_it_matters: Optional[str] = None
    potential_release_impact: Optional[str] = None
    remediation: Optional[str] = None
    verification_method: Optional[str] = None
    source_agent: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "severity": self.severity.value,
            "confidence": self.confidence.value,
            "category": self.category,
            "description": self.description,
            "affected_component": self.affected_component,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "commit_ref": self.commit_ref,
            "evidence_snippet": self.evidence_snippet,
            "why_it_matters": self.why_it_matters,
            "potential_release_impact": self.potential_release_impact,
            "remediation": self.remediation,
            "verification_method": self.verification_method,
            "source_agent": self.source_agent,
        }


@dataclass
class AgentResult:
    agent_type: AgentType
    findings: List[EvidenceFinding] = field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None


class BaseAgent(ABC):
    """Abstract base class for all Release Doctor specialized agents."""

    agent_type: AgentType

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path

    @abstractmethod
    async def run(
        self,
        change_map: Any,
        artifacts: Optional[List[Any]] = None,
    ) -> AgentResult:
        """Run the agent analysis and return structured findings."""
        ...
