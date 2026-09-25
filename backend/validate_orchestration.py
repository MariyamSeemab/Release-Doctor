"""Standalone orchestration test runner — no DB or web framework required."""
import sys, types, asyncio

sys.path.insert(0, ".")

# Minimal stubs
db_mod = types.ModuleType("app.database")
db_mod.Base = object
db_mod.get_db = None
sys.modules["app.database"] = db_mod

try:
    import structlog
except ImportError:
    sm = types.ModuleType("structlog")
    sm.get_logger = lambda *a: type("L", (), {k: print for k in ("info", "error", "warning")})()
    sys.modules["structlog"] = sm

from app.agents.base import AgentResult, EvidenceFinding
from app.agents.code_health import CodeHealthAgent
from app.agents.database import DatabaseAgent
from app.agents.security import SecurityAgent
from app.agents.risk_correlation import RiskCorrelationAgent
from app.orchestration.lead_agent import LeadAgent
from app.orchestration.release_decision import compute_release_decision
from app.models import AgentType, Confidence, Severity, OverallStatus
from app.repository.analyzer import ChangeMap, ChangedFile


def make_cm(files):
    cm = ChangeMap(base_ref="main", target_ref="feature/test")
    for path, content, diff in files:
        cm.changed_files.append(ChangedFile(path=path, change_type="M", content=content, diff_text=diff))
    return cm


TESTS = []

def test(fn):
    TESTS.append(fn)
    return fn


@test
async def test_code_health_bare_except():
    content = "def foo():\n    try:\n        pass\n    except:\n        pass\n"
    cm = make_cm([("app/utils.py", content, f"+{content}")])
    result = await CodeHealthAgent("/demo-repository").run(cm)
    found = [f for f in result.findings if "exception" in f.title.lower()]
    assert len(found) >= 1, f"bare except not found. findings: {[f.title for f in result.findings]}"
    print("  code_health bare_except: PASSED")


@test
async def test_db_missing_migration():
    content = "priority_score = Column(Float, nullable=False)"
    diff = "+    priority_score = Column(Float, nullable=False)\n"
    cm = make_cm([("app/models.py", content, diff)])
    result = await DatabaseAgent("/demo-repository").run(cm)
    found = [f for f in result.findings if "migration" in f.title.lower()]
    assert len(found) >= 1, f"missing migration not found. findings: {[f.title for f in result.findings]}"
    assert found[0].severity == Severity.CRITICAL
    print("  database missing_migration: PASSED")


@test
async def test_security_missing_auth():
    content = "@app.post('/api/refund')\ndef refund(order_id: int):\n    return {}\n"
    diff = "+@app.post('/api/refund')\n+def refund(order_id: int):\n+    return {}\n"
    cm = make_cm([("app/routes.py", content, diff)])
    result = await SecurityAgent("/demo-repository").run(cm)
    found = [f for f in result.findings if "auth" in f.title.lower()]
    assert len(found) >= 1, f"missing auth not found. findings: {[f.title for f in result.findings]}"
    assert found[0].severity == Severity.CRITICAL
    print("  security missing_auth: PASSED")


@test
async def test_partial_agent_failure():
    """Broken agent must not crash the pipeline — others still produce results."""
    class BrokenAgent(SecurityAgent):
        async def run(self, change_map, artifacts=None):
            raise RuntimeError("Simulated failure")

    cm = make_cm([("app/api.py", "@app.post('/test')\ndef t(): pass", "+@app.post\n")])
    lead = LeadAgent("/demo-repository")

    events = []
    async def cb(event, agent_type, result=None, error=""):
        events.append((event, agent_type))

    results = await lead.run_agents_parallel(
        [(AgentType.SECURITY, BrokenAgent("/demo-repository")),
         (AgentType.DATABASE, DatabaseAgent("/demo-repository"))],
        cm, artifacts=None, event_callback=cb,
    )

    assert AgentType.SECURITY in results
    assert results[AgentType.SECURITY].error is not None, "Broken agent must record error"
    assert AgentType.DATABASE in results
    assert results[AgentType.DATABASE].error is None, "Working agent must succeed"
    failures = [e for e in events if e[0] == "agent_failed"]
    assert len(failures) >= 1, "Must emit agent_failed event"
    print("  partial_agent_failure: PASSED")


@test
async def test_all_four_release_states():
    def mf(sev, conf):
        return EvidenceFinding(title="X", severity=sev, confidence=conf, category="X", description="X", source_agent="X")

    assert compute_release_decision([mf(Severity.CRITICAL, Confidence.HIGH)]) == OverallStatus.BLOCKED
    assert compute_release_decision([mf(Severity.HIGH, Confidence.HIGH)]) == OverallStatus.ATTENTION_REQUIRED
    assert compute_release_decision([]) == OverallStatus.READY_FOR_RELEASE
    assert compute_release_decision([mf(Severity.CRITICAL, Confidence.LOW)]) == OverallStatus.UNVERIFIED
    print("  all_four_release_states: PASSED")


@test
async def test_section9_correlation():
    findings = [
        EvidenceFinding(title="New database column added without a corresponding migration",
                        severity=Severity.CRITICAL, confidence=Confidence.HIGH,
                        category="Database Migration", description="X", source_agent=AgentType.DATABASE.value),
        EvidenceFinding(title="Database migration changed without migration integration test",
                        severity=Severity.MEDIUM, confidence=Confidence.HIGH,
                        category="Test Coverage", description="X", source_agent=AgentType.TEST_QA.value),
    ]
    result = await RiskCorrelationAgent("/demo-repository").run(None, None, all_findings=findings)
    merged = [f for f in result.findings if "schema mismatch" in f.title.lower()]
    assert len(merged) >= 1
    assert merged[0].severity == Severity.CRITICAL
    assert merged[0].source_agent == AgentType.RISK_CORRELATION.value
    print("  section9_correlation: PASSED")


async def run_all():
    print("Running orchestration validation tests...")
    passed = 0
    failed = 0
    for fn in TESTS:
        try:
            await fn()
            passed += 1
        except AssertionError as e:
            print(f"  FAILED — {fn.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR  — {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed.")
    if failed:
        sys.exit(1)


asyncio.run(run_all())
