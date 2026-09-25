"""
Tests for orchestration pipeline logic — without a running DB.
Tests partial agent failures, finding normalization, and release decision edge cases.
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.base import AgentResult, EvidenceFinding
from app.agents.code_health import CodeHealthAgent
from app.agents.database import DatabaseAgent
from app.agents.security import SecurityAgent
from app.agents.risk_correlation import RiskCorrelationAgent
from app.orchestration.lead_agent import LeadAgent
from app.orchestration.release_decision import compute_release_decision
from app.models import AgentType, Confidence, Severity, OverallStatus
from app.repository.analyzer import ChangeMap, ChangedFile


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_finding(title: str, severity: Severity, confidence: Confidence, category: str, agent: str) -> EvidenceFinding:
    return EvidenceFinding(
        title=title,
        severity=severity,
        confidence=confidence,
        category=category,
        description=f"Test finding: {title}",
        source_agent=agent,
    )


def make_change_map(files: list[tuple[str, str]]) -> ChangeMap:
    """Create a ChangeMap with specified (path, content) pairs."""
    cm = ChangeMap(base_ref="main", target_ref="feature/test")
    for path, content in files:
        cm.changed_files.append(
            ChangedFile(
                path=path,
                change_type="M",
                content=content,
                diff_text=f"+{content[:200]}",
            )
        )
    return cm


# ── Agent-level tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_code_health_detects_bare_except():
    content = "def foo():\n    try:\n        pass\n    except:\n        pass\n"
    cm = make_change_map([("app/utils.py", content)])
    agent = CodeHealthAgent(repo_path="/demo-repository")
    result = await agent.run(cm)
    bare_excepts = [f for f in result.findings if "bare exception" in f.title.lower() or "exception handler" in f.title.lower()]
    assert len(bare_excepts) >= 1, f"Expected bare except finding. Got: {[f.title for f in result.findings]}"


@pytest.mark.asyncio
async def test_database_agent_detects_missing_migration():
    # Model file with new column, no migration file in change_map
    content = "priority_score = Column(Float, nullable=False)\n"
    diff = "+    priority_score = Column(Float, nullable=False)\n"
    cm = make_change_map([("app/models.py", content)])
    cm.changed_files[0].diff_text = diff
    agent = DatabaseAgent(repo_path="/demo-repository")
    result = await agent.run(cm)
    migration_findings = [f for f in result.findings if "migration" in f.title.lower()]
    assert len(migration_findings) >= 1, "Database agent must detect missing migration"
    assert migration_findings[0].severity == Severity.CRITICAL


@pytest.mark.asyncio
async def test_security_agent_detects_missing_auth():
    content = "@app.post('/api/orders/{id}/refund')\ndef refund_order(order_id: int):\n    return {}\n"
    diff = "+@app.post('/api/orders/{id}/refund')\n+def refund_order(order_id: int):\n+    return {}\n"
    cm = make_change_map([("app/routes.py", content)])
    cm.changed_files[0].diff_text = diff
    agent = SecurityAgent(repo_path="/demo-repository")
    result = await agent.run(cm)
    auth_findings = [f for f in result.findings if "authorization" in f.title.lower() or "auth" in f.title.lower()]
    assert len(auth_findings) >= 1, "Security agent must detect missing authorization"
    assert auth_findings[0].severity == Severity.CRITICAL


# ── Section 9: Full correlation merge test ────────────────────────────────────

@pytest.mark.asyncio
async def test_schema_mismatch_correlation_full():
    """
    Section 9 test case:
    Code Agent (or Database Agent) finds new required DB field,
    Database Agent finds no migration,
    Test Agent finds no migration test.
    → Risk Correlation Agent MUST merge into 'Application/database schema mismatch risk'.
    """
    findings = [
        make_finding(
            "New database column added without a corresponding migration",
            Severity.CRITICAL,
            Confidence.HIGH,
            "Database Migration",
            AgentType.DATABASE.value,
        ),
        make_finding(
            "Database migration changed without migration integration test",
            Severity.MEDIUM,
            Confidence.HIGH,
            "Test Coverage",
            AgentType.TEST_QA.value,
        ),
    ]

    agent = RiskCorrelationAgent(repo_path="/demo-repository")
    result = await agent.run(change_map=None, artifacts=None, all_findings=findings)

    merged = [f for f in result.findings if "schema mismatch" in f.title.lower()]
    assert len(merged) >= 1, "Must produce schema mismatch root-cause finding"
    assert merged[0].severity == Severity.CRITICAL
    assert merged[0].confidence == Confidence.HIGH
    assert merged[0].source_agent == AgentType.RISK_CORRELATION.value


# ── Partial agent failure handling ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lead_agent_survives_partial_failure():
    """
    If one specialized agent raises an exception,
    the pipeline must still return results from all other agents.
    """
    class BrokenAgent(SecurityAgent):
        async def run(self, change_map, artifacts=None):
            raise RuntimeError("Simulated agent failure")

    from app.orchestration.lead_agent import LeadAgent, _AGENT_REGISTRY
    import app.orchestration.lead_agent as la_module

    cm = make_change_map([("app/api.py", "@app.post('/test')\ndef test(): pass")])

    lead = LeadAgent(repo_path="/demo-repository")

    # Manually construct the selected list with one broken agent
    broken_entry = (AgentType.SECURITY, BrokenAgent("/demo-repository"))
    working_entry = (AgentType.DATABASE, DatabaseAgent("/demo-repository"))

    events = []
    async def cb(event, agent_type, result=None, error=""):
        events.append((event, agent_type))

    results = await lead.run_agents_parallel(
        [broken_entry, working_entry],
        cm,
        artifacts=None,
        event_callback=cb,
    )

    # Broken agent result should have error set, not crash the pipeline
    assert AgentType.SECURITY in results
    assert results[AgentType.SECURITY].error is not None

    # Working agent should still produce a result
    assert AgentType.DATABASE in results
    assert results[AgentType.DATABASE].error is None

    # Events should contain failure event for broken agent
    failure_events = [e for e in events if e[0] == "agent_failed"]
    assert len(failure_events) >= 1


# ── Release decision: all 4 states ───────────────────────────────────────────

def test_all_four_release_states():
    # BLOCKED
    assert compute_release_decision([
        make_finding("X", Severity.CRITICAL, Confidence.HIGH, "X", "X")
    ]) == OverallStatus.BLOCKED

    # ATTENTION_REQUIRED
    assert compute_release_decision([
        make_finding("X", Severity.HIGH, Confidence.HIGH, "X", "X")
    ]) == OverallStatus.ATTENTION_REQUIRED

    # READY_FOR_RELEASE
    assert compute_release_decision([]) == OverallStatus.READY_FOR_RELEASE

    # UNVERIFIED
    assert compute_release_decision([
        make_finding("X", Severity.CRITICAL, Confidence.LOW, "X", "X")
    ]) == OverallStatus.UNVERIFIED


# ── Finding normalization ─────────────────────────────────────────────────────

def test_finding_to_dict_roundtrip():
    f = make_finding("Title", Severity.HIGH, Confidence.MEDIUM, "Security", "SECURITY")
    f.file_path = "app/routes.py"
    f.line_start = 42
    f.evidence_snippet = "bad_code()"

    d = f.to_dict()
    assert d["title"] == "Title"
    assert d["severity"] == "HIGH"
    assert d["confidence"] == "MEDIUM"
    assert d["source_agent"] == "SECURITY"
    assert d["file_path"] == "app/routes.py"
    assert d["line_start"] == 42
    assert d["evidence_snippet"] == "bad_code()"


def test_finding_extra_is_not_in_dict():
    """Extra metadata should NOT leak into the serialized dict."""
    f = make_finding("X", Severity.LOW, Confidence.LOW, "X", "X")
    f.extra = {"planted_risk": "test", "internal": True}
    d = f.to_dict()
    assert "extra" not in d
    assert "planted_risk" not in d
