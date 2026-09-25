"""Test & QA Agent — maps changed behaviour to tests, finds missing coverage."""
from __future__ import annotations

import re
from typing import Any, List, Optional

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.models import AgentType, Confidence, Severity
from app.repository.analyzer import ChangeMap


class TestQAAgent(BaseAgent):
    agent_type = AgentType.TEST_QA

    async def run(self, change_map: ChangeMap, artifacts: Optional[List[Any]] = None) -> AgentResult:
        findings: List[EvidenceFinding] = []

        test_files = change_map.files_matching(["**/test*", "**/tests/**", "**/*_test.py", "**/*.test.*", "**/*.spec.*"])
        source_files = [
            cf for cf in change_map.changed_files
            if not any(t in cf.path for t in ("test", "spec", "__pycache__", ".pyc"))
        ]

        test_paths = {f.path for f in test_files}

        # ── Check: source files changed with zero test file changes ─────
        if source_files and not test_files:
            findings.append(EvidenceFinding(
                title="Source code changed with no corresponding test updates",
                severity=Severity.HIGH,
                confidence=Confidence.HIGH,
                category="Test Coverage",
                description=(
                    f"{len(source_files)} source file(s) changed but no test files were modified. "
                    f"Changed files: {', '.join(f.path for f in source_files[:5])}."
                ),
                affected_component="Test Suite",
                why_it_matters="Untested changes increase regression risk and may break existing behaviour silently.",
                potential_release_impact="Regressions introduced by the change may reach production undetected.",
                remediation="Add or update unit/integration tests covering the changed code paths.",
                verification_method="Run the test suite after the change and confirm coverage for changed functions.",
                source_agent=self.agent_type.value,
                extra={"planted_risk": "missing_tests"},
            ))

        # ── Check: new endpoints/functions without corresponding test ────
        new_endpoint_pattern = re.compile(r'^\+.*@\w+\.(get|post|put|patch|delete)\(', re.MULTILINE)
        for cf in source_files:
            if not cf.diff_text:
                continue
            new_endpoints = new_endpoint_pattern.findall(cf.diff_text)
            if new_endpoints:
                # Check if any test file covers this module
                module_name = cf.path.replace("/", "_").replace(".py", "")
                covered = any(module_name in tp or cf.path.split("/")[-1].replace(".py","") in tp for tp in test_paths)
                if not covered:
                    findings.append(EvidenceFinding(
                        title=f"New endpoint(s) in `{cf.path}` have no corresponding test",
                        severity=Severity.HIGH,
                        confidence=Confidence.MEDIUM,
                        category="Test Coverage",
                        description=f"{len(new_endpoints)} new endpoint(s) detected in `{cf.path}` but no test file appears to cover this module.",
                        file_path=cf.path,
                        why_it_matters="New endpoints without integration tests may have undiscovered contract violations or auth bypasses.",
                        remediation="Write integration tests for each new endpoint, including authentication, happy path, and error cases.",
                        verification_method="Run `pytest` and check that each new route has at least one test.",
                        source_agent=self.agent_type.value,
                    ))

        # ── Check: migration files without migration tests ───────────────
        migration_changed = change_map.files_matching(["**/migrations/**", "**/versions/**"])
        migration_tests = [f for f in test_files if "migrat" in f.path]
        if migration_changed and not migration_tests:
            findings.append(EvidenceFinding(
                title="Database migration changed without migration integration test",
                severity=Severity.MEDIUM,
                confidence=Confidence.HIGH,
                category="Test Coverage",
                description="Migration files were modified but no migration test was added or updated.",
                affected_component="Database Migrations",
                why_it_matters="Untested migrations may fail on production schema, causing deployment outages.",
                remediation="Add an integration test that runs `alembic upgrade head` against a test database.",
                verification_method="Run migration tests in CI against a clean database.",
                source_agent=self.agent_type.value,
                extra={"planted_risk": "missing_migration_test"},
            ))

        summary = (
            f"Test & QA: {len(source_files)} source file(s) changed, "
            f"{len(test_files)} test file(s) changed. Found {len(findings)} finding(s)."
        )
        return AgentResult(agent_type=self.agent_type, findings=findings, summary=summary)
