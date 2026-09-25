"""Standalone validation of core agent logic — no DB or web framework needed."""
import sys, asyncio, types

sys.path.insert(0, ".")

# Minimal stubs to avoid import chain
db_mod = types.ModuleType("app.database")
db_mod.Base = object
db_mod.get_db = None
sys.modules["app.database"] = db_mod

try:
    import structlog
except ImportError:
    structlog_mod = types.ModuleType("structlog")
    structlog_mod.get_logger = lambda *a: type("L", (), {"info": print, "error": print, "warning": print})()
    sys.modules["structlog"] = structlog_mod

from app.agents.base import EvidenceFinding
from app.agents.risk_correlation import RiskCorrelationAgent
from app.orchestration.release_decision import compute_release_decision
from app.models import Severity, Confidence, AgentType, OverallStatus


def test_section9_correlation():
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

    agent = RiskCorrelationAgent(repo_path="/demo-repository")
    result = asyncio.run(agent.run(change_map=None, artifacts=None, all_findings=[db_finding, test_finding]))

    root_causes = [f for f in result.findings if "schema mismatch" in f.title.lower()]
    assert len(root_causes) >= 1, f"Expected root cause finding. Got: {[f.title for f in result.findings]}"
    rc = root_causes[0]
    assert rc.severity == Severity.CRITICAL
    assert rc.confidence == Confidence.HIGH
    assert rc.source_agent == AgentType.RISK_CORRELATION.value
    print(f'  Section 9 correlation: PASSED -> "{rc.title}"')


def test_release_decisions():
    critical = EvidenceFinding(
        title="Critical", severity=Severity.CRITICAL, confidence=Confidence.HIGH, category="X", description="X", source_agent="X"
    )
    high = EvidenceFinding(
        title="High", severity=Severity.HIGH, confidence=Confidence.HIGH, category="X", description="X", source_agent="X"
    )
    unverified = EvidenceFinding(
        title="Unverified", severity=Severity.CRITICAL, confidence=Confidence.LOW, category="X", description="X", source_agent="X"
    )

    assert compute_release_decision([critical]) == OverallStatus.BLOCKED, "Expected BLOCKED"
    print("  BLOCKED state: PASSED")

    assert compute_release_decision([high]) == OverallStatus.ATTENTION_REQUIRED, "Expected ATTENTION_REQUIRED"
    print("  ATTENTION_REQUIRED state: PASSED")

    assert compute_release_decision([]) == OverallStatus.READY_FOR_RELEASE, "Expected READY_FOR_RELEASE"
    print("  READY_FOR_RELEASE state: PASSED")

    assert compute_release_decision([unverified]) == OverallStatus.UNVERIFIED, "Expected UNVERIFIED"
    print("  UNVERIFIED state: PASSED")


if __name__ == "__main__":
    print("Running core logic validation...")
    test_section9_correlation()
    test_release_decisions()
    print("\nAll tests PASSED.")
