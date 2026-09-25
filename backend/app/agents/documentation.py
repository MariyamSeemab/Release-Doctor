"""Documentation/Requirement Agent — compares docs against implementation."""
from __future__ import annotations

import re
from typing import Any, List, Optional

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.models import AgentType, Confidence, Severity
from app.repository.analyzer import ChangeMap


class DocumentationAgent(BaseAgent):
    agent_type = AgentType.DOCUMENTATION

    async def run(self, change_map: ChangeMap, artifacts: Optional[List[Any]] = None) -> AgentResult:
        findings: List[EvidenceFinding] = []

        doc_files = change_map.files_matching([
            "**/docs/**", "**/README*", "**/*.md", "**/*.rst",
            "**/*.yaml", "**/*.yml",  # OpenAPI specs
        ])
        source_files = [cf for cf in change_map.changed_files if cf.path.endswith((".py", ".ts", ".js"))]

        # ── Check: source changed but no docs updated ────────────────────
        api_source_changed = change_map.files_matching(["**/api/**", "**/routes/**", "**/endpoints/**"])
        docs_changed = bool(doc_files)

        if api_source_changed and not docs_changed:
            findings.append(EvidenceFinding(
                title="API source changed but no documentation updated",
                severity=Severity.MEDIUM,
                confidence=Confidence.HIGH,
                category="Documentation",
                description=(
                    f"{len(api_source_changed)} API source file(s) changed but no documentation files were modified. "
                    f"The documentation may be stale relative to the implementation."
                ),
                affected_component="API Documentation",
                why_it_matters="Stale documentation misleads consumers and breaks documentation-contract governance.",
                potential_release_impact="Integration teams building against outdated docs will encounter unexpected API behaviour.",
                remediation="Update README, OpenAPI spec, or API reference docs to match the implementation changes.",
                verification_method="Diff the OpenAPI spec auto-generated from the current code against the committed spec.",
                source_agent=self.agent_type.value,
                extra={"planted_risk": "docs_not_updated"},
            ))

        # ── Check: artifacts (uploaded docs) vs implementation ──────────
        if artifacts:
            for artifact in artifacts:
                content = getattr(artifact, "content", "") or ""
                if not content:
                    continue

                # Simple check: look for endpoint paths mentioned in doc
                # that don't exist in changed API files
                doc_endpoints = set(re.findall(r'(?:GET|POST|PUT|PATCH|DELETE)\s+(/\S+)', content, re.IGNORECASE))
                code_endpoints: set = set()
                for cf in source_files:
                    if cf.content:
                        for m in re.finditer(r'@\w+\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']', cf.content, re.IGNORECASE):
                            code_endpoints.add(m.group(2))

                undocumented = code_endpoints - {e.lower() for e in doc_endpoints}
                if undocumented:
                    findings.append(EvidenceFinding(
                        title=f"Endpoints in code not present in uploaded requirement document `{artifact.name}`",
                        severity=Severity.LOW,
                        confidence=Confidence.LOW,
                        category="Documentation",
                        description=f"The following endpoints were found in code but not in the document: {', '.join(list(undocumented)[:5])}",
                        affected_component="API Documentation",
                        why_it_matters="Undocumented endpoints may violate requirement contracts.",
                        remediation="Update the requirement document to include new endpoints or confirm they are intentional additions.",
                        verification_method="Review the endpoint list against the requirement specification.",
                        source_agent=self.agent_type.value,
                    ))

        summary = (
            f"Documentation: {len(doc_files)} doc file(s) changed, "
            f"{len(source_files)} source file(s) changed. Found {len(findings)} finding(s)."
        )
        return AgentResult(agent_type=self.agent_type, findings=findings, summary=summary)
