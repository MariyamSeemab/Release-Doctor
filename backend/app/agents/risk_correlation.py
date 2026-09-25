"""Risk Correlation Agent — deduplicates, merges, and identifies root causes.

Section 9 test case: if Code Agent finds a new required DB field,
Database Agent finds no corresponding migration, and Test Agent finds no
migration integration test — this agent MUST merge them into one root-cause
finding: "Application/database schema mismatch risk".
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.models import AgentType, Confidence, Severity


# Correlation rules: (rule_id, title, agent_categories, merged_severity, description_template)
_CORRELATION_RULES: List[Tuple[str, str, List[str], Severity, str]] = [
    (
        "schema_mismatch",
        "Application/database schema mismatch risk",
        ["Database Migration", "Test Coverage"],
        Severity.CRITICAL,
        (
            "Multiple agents detected a coordinated schema mismatch risk: "
            "new database column(s) added to the model, no corresponding migration present, "
            "and no migration integration test. This combination will cause a startup failure "
            "on production deployment and prevent rollback verification."
        ),
    ),
    (
        "unprotected_with_missing_test",
        "Unprotected endpoint with no test coverage",
        ["Authorization", "Test Coverage"],
        Severity.CRITICAL,
        (
            "A new endpoint lacks authorization AND has no corresponding test. "
            "This means the authorization gap cannot be caught by automated testing before release."
        ),
    ),
    (
        "config_deploy_mismatch",
        "New environment variable not deployed and not tested",
        ["Configuration", "Deployment Configuration"],
        Severity.HIGH,
        (
            "A new environment variable is referenced in code but is missing from both "
            "deployment configuration and test fixtures."
        ),
    ),
    (
        "breaking_api_undocumented",
        "Breaking API change with no documentation update",
        ["API Contract", "Documentation"],
        Severity.HIGH,
        (
            "A breaking API contract change was made but the documentation was not updated. "
            "Consumers may not be aware of the change before release."
        ),
    ),
]


class RiskCorrelationAgent(BaseAgent):
    agent_type = AgentType.RISK_CORRELATION

    async def run(
        self,
        change_map: Any,
        artifacts: Optional[List[Any]] = None,
        all_findings: Optional[List[EvidenceFinding]] = None,
    ) -> AgentResult:
        """Correlate findings from all other agents into root-cause findings."""
        source_findings = all_findings or []
        correlated: List[EvidenceFinding] = []
        merged_ids: set[int] = set()  # indices into source_findings that have been merged

        for rule_id, rule_title, rule_categories, merged_severity, description in _CORRELATION_RULES:
            matched: List[Tuple[int, EvidenceFinding]] = []
            for idx, f in enumerate(source_findings):
                if f.category in rule_categories:
                    matched.append((idx, f))

            # Need at least 2 distinct categories matched
            matched_cats = {f.category for _, f in matched}
            if len(matched_cats) >= 2:
                # Build merged finding
                all_evidence = "\n\n".join(
                    f"[{f.source_agent}] {f.title}: {f.evidence_snippet or f.description[:200]}"
                    for _, f in matched
                )
                merged_finding_ids = [str(id(f)) for _, f in matched]
                correlated.append(
                    EvidenceFinding(
                        title=rule_title,
                        severity=merged_severity,
                        confidence=Confidence.HIGH,
                        category="Correlated Risk",
                        description=description,
                        affected_component=", ".join(f.affected_component or "Unknown" for _, f in matched if f.affected_component),
                        evidence_snippet=all_evidence[:1000],
                        why_it_matters="Multiple independent agents confirmed evidence for this risk — correlation indicates a real, systemic problem.",
                        potential_release_impact="Release blocker: coordinated evidence from multiple domains confirms this will cause a production failure.",
                        remediation="Address all linked findings. Resolve the root cause before re-running analysis.",
                        verification_method="Re-run the full analysis after fixes and confirm all linked findings are resolved.",
                        source_agent=self.agent_type.value,
                        extra={
                            "rule_id": rule_id,
                            "merged_from": [f.title for _, f in matched],
                            "is_root_cause": True,
                        },
                    )
                )
                for idx, _ in matched:
                    merged_ids.add(idx)

        # Pass-through unmerged findings (still relevant)
        passthrough = [
            f for idx, f in enumerate(source_findings)
            if idx not in merged_ids
        ]

        # Deduplicate: group findings with identical titles from different agents
        seen_titles: Dict[str, EvidenceFinding] = {}
        deduped: List[EvidenceFinding] = []
        for f in passthrough:
            if f.title in seen_titles:
                # Upgrade severity if duplicate has higher severity
                existing = seen_titles[f.title]
                severity_order = [s.value for s in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFORMATIONAL]]
                if severity_order.index(f.severity.value) < severity_order.index(existing.severity.value):
                    seen_titles[f.title] = f
            else:
                seen_titles[f.title] = f
                deduped.append(f)

        all_output = correlated + deduped

        summary = (
            f"Risk Correlation: {len(source_findings)} raw finding(s) → "
            f"{len(correlated)} merged root-cause finding(s), "
            f"{len(deduped)} pass-through finding(s). "
            f"Total: {len(all_output)}."
        )
        return AgentResult(agent_type=self.agent_type, findings=all_output, summary=summary)
