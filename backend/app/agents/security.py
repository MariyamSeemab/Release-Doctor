"""Security Agent — AuthN/AuthZ, injection, secrets, unsafe data flows."""
from __future__ import annotations

import re
from typing import Any, List, Optional

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.models import AgentType, Confidence, Severity
from app.repository.analyzer import ChangeMap

# Patterns that suggest an endpoint lacks auth dependency
_AUTH_PATTERNS = re.compile(
    r'Depends\s*\(\s*(get_current_user|require_auth|jwt_required|oauth2_scheme)',
    re.IGNORECASE,
)
_ROUTE_PATTERN = re.compile(r'@\w+\.(get|post|put|patch|delete)\s*\(', re.IGNORECASE)
_SECRET_PATTERN = re.compile(
    r'(?:password|secret|api_key|token|private_key)\s*=\s*["\'][^"\']{4,}["\']',
    re.IGNORECASE,
)
_SENSITIVE_LOG = re.compile(
    r'(?:log|print|logger)\s*.*(?:password|secret|token|credit_card)',
    re.IGNORECASE,
)


class SecurityAgent(BaseAgent):
    agent_type = AgentType.SECURITY

    async def run(self, change_map: ChangeMap, artifacts: Optional[List[Any]] = None) -> AgentResult:
        findings: List[EvidenceFinding] = []

        for cf in change_map.changed_files:
            if not cf.content:
                continue

            lines = cf.content.splitlines()
            diff_lines = (cf.diff_text or "").splitlines()

            # ── Check: new route without auth dependency ─────────────────
            if cf.path.endswith(".py"):
                route_matches = _ROUTE_PATTERN.findall(cf.diff_text or "")
                has_auth = bool(_AUTH_PATTERNS.search(cf.content))
                if route_matches and not has_auth:
                    findings.append(EvidenceFinding(
                        title=f"New endpoint in `{cf.path}` has no authorization dependency",
                        severity=Severity.CRITICAL,
                        confidence=Confidence.HIGH,
                        category="Authorization",
                        description=(
                            f"`{cf.path}` introduces {len(route_matches)} new route(s) but no "
                            f"`get_current_user` or equivalent auth dependency was found in the file."
                        ),
                        file_path=cf.path,
                        why_it_matters="Unprotected endpoints allow unauthenticated access to sensitive operations or data.",
                        potential_release_impact="Data breach or unauthorized write access if the endpoint reaches production unprotected.",
                        remediation="Add `Depends(get_current_user)` (or equivalent) to every new endpoint that handles authenticated data.",
                        verification_method="Confirm the endpoint returns 401 when called without a valid JWT.",
                        source_agent=self.agent_type.value,
                        extra={"planted_risk": "missing_auth"},
                    ))

            # ── Check: hardcoded secrets ─────────────────────────────────
            for i, line in enumerate(lines, 1):
                if _SECRET_PATTERN.search(line) and "os.environ" not in line and "getenv" not in line:
                    findings.append(EvidenceFinding(
                        title=f"Hardcoded credential in `{cf.path}:{i}`",
                        severity=Severity.CRITICAL,
                        confidence=Confidence.MEDIUM,
                        category="Secrets Exposure",
                        description="A string literal matching a credential pattern was found in the changed file.",
                        file_path=cf.path,
                        line_start=i,
                        evidence_snippet=re.sub(r'=\s*["\'][^"\']+["\']', '= "***"', line.strip()),
                        why_it_matters="Hardcoded credentials in source code are exposed to anyone with repository access.",
                        remediation="Remove the hardcoded value, rotate the credential, and load it from an environment variable.",
                        verification_method="Run `git grep -i password` and confirm no plaintext values remain.",
                        source_agent=self.agent_type.value,
                    ))

            # ── Check: sensitive data written to logs ────────────────────
            for i, line in enumerate(lines, 1):
                if _SENSITIVE_LOG.search(line):
                    findings.append(EvidenceFinding(
                        title=f"Sensitive data potentially logged in `{cf.path}:{i}`",
                        severity=Severity.HIGH,
                        confidence=Confidence.MEDIUM,
                        category="Sensitive Data Exposure",
                        description="A log/print statement referencing a sensitive field was detected.",
                        file_path=cf.path,
                        line_start=i,
                        evidence_snippet=line.strip(),
                        why_it_matters="Sensitive data in logs can be exposed via log aggregation systems.",
                        remediation="Remove sensitive fields from log statements or mask them before logging.",
                        source_agent=self.agent_type.value,
                    ))

        summary = (
            f"Security: scanned {len(change_map.changed_files)} file(s). Found {len(findings)} finding(s)."
        )
        return AgentResult(agent_type=self.agent_type, findings=findings, summary=summary)
