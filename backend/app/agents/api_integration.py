"""API & Integration Agent — endpoint/contract changes, traces consumers."""
from __future__ import annotations

import re
from typing import Any, List, Optional

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.models import AgentType, Confidence, Severity
from app.repository.analyzer import ChangeMap


class APIIntegrationAgent(BaseAgent):
    agent_type = AgentType.API_INTEGRATION

    async def run(self, change_map: ChangeMap, artifacts: Optional[List[Any]] = None) -> AgentResult:
        findings: List[EvidenceFinding] = []

        # Find all changed API/route files
        api_files = change_map.files_matching(["**/api/**", "**/routes/**", "**/views/**", "**/endpoints/**"])
        frontend_files = change_map.files_matching(["**/frontend/**", "**/client/**", "**/*.ts", "**/*.tsx", "**/*.js"])

        # ── Check: response field removed or renamed in a route ─────────
        removed_field_pattern = re.compile(r'^-.*(?:"|\')(\w+)(?:"|\'):\s', re.MULTILINE)
        added_field_pattern = re.compile(r'^\+.*(?:"|\')(\w+)(?:"|\'):\s', re.MULTILINE)

        for cf in api_files:
            if not cf.diff_text:
                continue
            removed_fields = set(removed_field_pattern.findall(cf.diff_text))
            added_fields = set(added_field_pattern.findall(cf.diff_text))
            # Fields that were removed and not re-added = breaking removal
            breaking = removed_fields - added_fields

            # Also check for serializer/schema field removals in Python
            schema_field_removed = re.compile(r'^-\s+\w+\s*(?:=\s*(?:fields\.|serializers\.|Column|mapped_column))', re.MULTILINE)
            schema_removals = schema_field_removed.findall(cf.diff_text)

            if breaking or schema_removals:
                # Check if any frontend file references the removed field
                affected_consumers = []
                for field_name in list(breaking)[:5]:
                    for fc in frontend_files:
                        if fc.content and field_name in fc.content:
                            affected_consumers.append(f"{fc.path} uses `{field_name}`")

                findings.append(EvidenceFinding(
                    title=f"Breaking API response change in `{cf.path}` — field(s) removed",
                    severity=Severity.CRITICAL,
                    confidence=Confidence.HIGH,
                    category="API Contract",
                    description=(
                        f"Fields removed from API response: {', '.join(list(breaking)[:5])}. "
                        + (f"Affected frontend consumers: {'; '.join(affected_consumers[:3])}." if affected_consumers else "")
                    ),
                    affected_component="API Response Contract",
                    file_path=cf.path,
                    evidence_snippet="\n".join(list(breaking)[:3]),
                    why_it_matters="Removing a response field breaks all clients that depend on it without a major version bump.",
                    potential_release_impact="Frontend consumers will receive undefined/null for expected fields, causing UI breakage.",
                    remediation="Version the API endpoint or deprecate fields rather than removing them. Update all consumers first.",
                    verification_method="Run frontend integration/E2E tests and confirm no 'undefined' errors for affected fields.",
                    source_agent=self.agent_type.value,
                    extra={"removed_fields": list(breaking), "planted_risk": "breaking_api_change"},
                ))

        # ── Check: new endpoint with no API docs update ──────────────────
        openapi_changed = any("openapi" in cf.path.lower() or "swagger" in cf.path.lower() for cf in change_map.changed_files)
        new_routes_in_backend = sum(
            len(re.findall(r'^\+.*@\w+\.(get|post|put|patch|delete)\(', cf.diff_text or "", re.MULTILINE))
            for cf in api_files
        )
        if new_routes_in_backend > 0 and not openapi_changed:
            findings.append(EvidenceFinding(
                title="New API endpoints added without updating API documentation",
                severity=Severity.MEDIUM,
                confidence=Confidence.MEDIUM,
                category="API Documentation",
                description=f"{new_routes_in_backend} new route(s) added but no OpenAPI/Swagger spec was updated.",
                why_it_matters="Undocumented endpoints are invisible to consumers and violate API contract governance.",
                remediation="Update the OpenAPI spec or ensure auto-generated docs are regenerated and reviewed.",
                source_agent=self.agent_type.value,
            ))

        summary = (
            f"API & Integration: examined {len(api_files)} API file(s), "
            f"{len(frontend_files)} consumer file(s). Found {len(findings)} finding(s)."
        )
        return AgentResult(agent_type=self.agent_type, findings=findings, summary=summary)
