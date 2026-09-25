"""Code Health Agent — inspects logic risks, validation gaps, exception handling."""
from __future__ import annotations

import re
from typing import Any, List, Optional

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.models import AgentType, Confidence, Severity
from app.repository.analyzer import ChangeMap


class CodeHealthAgent(BaseAgent):
    agent_type = AgentType.CODE_HEALTH

    async def run(self, change_map: ChangeMap, artifacts: Optional[List[Any]] = None) -> AgentResult:
        findings: List[EvidenceFinding] = []

        for cf in change_map.changed_files:
            if not cf.content:
                continue

            content = cf.content
            lines = content.splitlines()

            # ── Check: bare except clauses ──────────────────────────────
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped in ("except:", "except Exception:") and "log" not in content[max(0, content.find(line)-200):content.find(line)+200]:
                    findings.append(EvidenceFinding(
                        title="Bare exception handler without logging",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.HIGH,
                        category="Exception Handling",
                        description=f"A bare except clause was found in `{cf.path}` at line {i}. Silent exception swallowing can mask critical failures.",
                        file_path=cf.path,
                        line_start=i,
                        evidence_snippet=line,
                        why_it_matters="Silent failures are hard to diagnose in production.",
                        potential_release_impact="Runtime errors may be silently ignored, causing data inconsistency.",
                        remediation="Replace bare `except:` with specific exception types and add structured logging.",
                        verification_method="Search for `except:` in the changed file and confirm each has logging.",
                        source_agent=self.agent_type.value,
                    ))

            # ── Check: TODO / FIXME / HACK in changed lines ─────────────
            todo_pattern = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)
            for i, line in enumerate(lines, 1):
                if todo_pattern.search(line) and line.strip().startswith(("+", "+")):
                    findings.append(EvidenceFinding(
                        title=f"Unresolved TODO/FIXME in new code ({cf.path}:{i})",
                        severity=Severity.LOW,
                        confidence=Confidence.HIGH,
                        category="Code Quality",
                        description=f"New code introduces an unresolved marker at line {i}.",
                        file_path=cf.path,
                        line_start=i,
                        evidence_snippet=line.strip(),
                        why_it_matters="Unresolved markers indicate incomplete implementation.",
                        remediation="Resolve or remove the TODO before release.",
                        source_agent=self.agent_type.value,
                    ))

            # ── Check: hardcoded secrets / credentials ───────────────────
            secret_pattern = re.compile(
                r'(password|secret|api_key|token|passwd)\s*=\s*["\'][^"\']{4,}["\']',
                re.IGNORECASE,
            )
            for i, line in enumerate(lines, 1):
                if secret_pattern.search(line) and "os.environ" not in line and "getenv" not in line:
                    findings.append(EvidenceFinding(
                        title=f"Potential hardcoded credential in {cf.path}:{i}",
                        severity=Severity.HIGH,
                        confidence=Confidence.MEDIUM,
                        category="Security / Code",
                        description="A string assignment matching a credential pattern was detected in changed code.",
                        file_path=cf.path,
                        line_start=i,
                        evidence_snippet=re.sub(r'=\s*["\'][^"\']+["\']', '= "***"', line.strip()),
                        why_it_matters="Hardcoded credentials are exposed in version control.",
                        remediation="Move credential to environment variable; rotate the exposed value.",
                        verification_method="Search for the pattern and confirm no plaintext secrets are committed.",
                        source_agent=self.agent_type.value,
                    ))

            # ── Check: missing input validation on new endpoints ─────────
            if cf.path.endswith(".py"):
                new_route_pattern = re.compile(r'@\w+\.(get|post|put|patch|delete)\(')
                has_validation = "pydantic" in content or "BaseModel" in content or "Annotated" in content
                if new_route_pattern.search(cf.diff_text or "") and not has_validation:
                    findings.append(EvidenceFinding(
                        title=f"New route in {cf.path} may lack input validation",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.LOW,
                        category="Input Validation",
                        description="A new route handler was added but no Pydantic model or validation import was detected in the file.",
                        file_path=cf.path,
                        why_it_matters="Routes without input validation are vulnerable to malformed/malicious payloads.",
                        remediation="Add Pydantic request body models or parameter validators to new endpoints.",
                        verification_method="Inspect the new endpoint handler and confirm request body is validated.",
                        source_agent=self.agent_type.value,
                    ))

        summary = f"Code Health: examined {len(change_map.changed_files)} changed files, found {len(findings)} findings."
        return AgentResult(agent_type=self.agent_type, findings=findings, summary=summary)
