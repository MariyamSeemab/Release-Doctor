"""Tests for agent findings normalization and the Section 9 correlation test case."""
from __future__ import annotations

import asyncio
import pytest

from app.agents.base import EvidenceFinding
from app.agents.database import DatabaseAgent
from app.agents.test_qa import TestQAAgent
from app.agents.risk_correlation import RiskCorrelationAgent
from app.models import AgentType, Confidence, Severity
from app.orchestration.release_decision import compute_release_decision
from app.models import OverallStatus


# ── Section 9 Correlation Test Case ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_schema_mismatch_correlation():
    """
    If Code Agent finds new required DB field,
    Database Agent finds no migration, and
    Test Agent finds no migration integration test —
    the Correlation Agent MUST merge them into one root-cause finding.
    """
    # Simulate findings from three different agents
    db_finding = EvidenceFinding(
        title="New database column added without a corresponding migration",
        severity=Severity.CRITICAL,
        confidence=Confidence.HIGH,
        category="Database Migration",
        description="priority_score column added but no migration found.",
        source_agent=AgentType.DATABASE.value,
    )
    test_finding = EvidenceFinding(
        title="Database migration changed without migration integration test",
        severity=Severity.MEDIUM,
        confidence=Confidence.HIGH,
        category="Test Coverage",
        description="No migration test found.",
        source_agent=AgentType.TEST_QA.value,
    )

    corr_agent = RiskCorrelationAgent(repo_path="/demo-repository")
    # Simulate the call with findings from both agents
    result = await corr_agent.run(
        change_map=None,
        artifacts=None,
        all_findings=[db_finding, test_finding],
    )

    # Must produce a merged root-cause finding
    root_cause_findings = [f for f in result.findings if "schema mismatch" in f.title.lower()]
    assert len(root_cause_findings) >= 1, (
        "Risk Correlation Agent must merge DB + Test findings into a schema mismatch root cause"
    )

    merged = root_cause_findings[0]
    assert merged.severity == Severity.CRITICAL
    assert merged.confidence == Confidence.HIGH
    assert merged.source_agent == AgentType.RISK_CORRELATION.value


# ── Release Decision Tests ────────────────────────────────────────────────────

def test_release_decision_blocked():
    findings = [
        EvidenceFinding(
            title="Critical issue",
            severity=Severity.CRITICAL,
            confidence=Confidence.HIGH,
            category="Database Migration",
            description="Blocking",
            source_agent="DATABASE",
        )
    ]
    assert compute_release_decision(findings) == OverallStatus.BLOCKED


def test_release_decision_attention():
    findings = [
        EvidenceFinding(
            title="High risk",
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            category="Security",
            description="Needs review",
            source_agent="SECURITY",
        )
    ]
    assert compute_release_decision(findings) == OverallStatus.ATTENTION_REQUIRED


def test_release_decision_ready():
    assert compute_release_decision([]) == OverallStatus.READY_FOR_RELEASE


def test_release_decision_unverified():
    findings = [
        EvidenceFinding(
            title="Unverified issue",
            severity=Severity.CRITICAL,
            confidence=Confidence.LOW,
            category="Security",
            description="Could not verify",
            source_agent="SECURITY",
        )
    ]
    assert compute_release_decision(findings) == OverallStatus.UNVERIFIED


# ── Finding normalization ─────────────────────────────────────────────────────

def test_finding_to_dict():
    f = EvidenceFinding(
        title="Test finding",
        severity=Severity.HIGH,
        confidence=Confidence.MEDIUM,
        category="Code Quality",
        description="A test finding",
        source_agent="CODE_HEALTH",
    )
    d = f.to_dict()
    assert d["title"] == "Test finding"
    assert d["severity"] == "HIGH"
    assert d["confidence"] == "MEDIUM"
    assert d["source_agent"] == "CODE_HEALTH"
