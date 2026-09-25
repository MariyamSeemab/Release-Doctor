"""Dependency Agent — manifests, lockfiles, version conflicts, CVEs."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.models import AgentType, Confidence, Severity
from app.repository.analyzer import ChangeMap

# Known vulnerable version ranges (simplified static list for demo — in production,
# integrate with a real vulnerability DB like OSV or safety-db)
_KNOWN_VULNS: Dict[str, List[Tuple[str, str, str]]] = {
    # (package_name, vulnerable_range_description, CVE)
    "django": [("< 4.2.0", "Multiple XSS and CSRF vulnerabilities", "CVE-2023-xxxx")],
    "flask": [("< 2.3.0", "Werkzeug WSGI path traversal", "CVE-2023-25577")],
    "requests": [("< 2.31.0", "Credential leakage on redirect", "CVE-2023-32681")],
    "pillow": [("< 10.0.0", "Arbitrary code execution via crafted image", "CVE-2023-44271")],
    "cryptography": [("< 41.0.0", "NULL pointer dereference", "CVE-2023-49083")],
}


class DependencyAgent(BaseAgent):
    agent_type = AgentType.DEPENDENCY

    async def run(self, change_map: ChangeMap, artifacts: Optional[List[Any]] = None) -> AgentResult:
        findings: List[EvidenceFinding] = []

        manifest_files = change_map.files_matching(
            ["**/requirements*.txt", "**/package.json", "**/package-lock.json",
             "**/Pipfile", "**/pyproject.toml", "**/poetry.lock"]
        )

        for cf in manifest_files:
            if not cf.content:
                continue

            # ── Check: direct version pinning conflicts (requirements.txt) ──
            if "requirements" in cf.path:
                version_map: Dict[str, List[str]] = {}
                for line in cf.content.splitlines():
                    m = re.match(r'^([a-zA-Z0-9_\-]+)\s*([=<>!~]+)\s*([\d\.]+)', line.strip())
                    if m:
                        pkg, op, ver = m.group(1).lower(), m.group(2), m.group(3)
                        version_map.setdefault(pkg, []).append(f"{op}{ver}")

                # ── Check: known vulnerable packages ────────────────────
                for pkg, constraint_list in version_map.items():
                    if pkg in _KNOWN_VULNS:
                        for vuln_range, vuln_desc, cve in _KNOWN_VULNS[pkg]:
                            findings.append(EvidenceFinding(
                                title=f"Dependency `{pkg}` may be affected by {cve}",
                                severity=Severity.HIGH,
                                confidence=Confidence.MEDIUM,
                                category="Dependency Vulnerability",
                                description=(
                                    f"Package `{pkg}` (pinned as `{''.join(constraint_list)}`) "
                                    f"has a known vulnerability: {vuln_desc} ({cve}). "
                                    f"Vulnerable range: {vuln_range}."
                                ),
                                file_path=cf.path,
                                evidence_snippet=f"{pkg}{''.join(constraint_list)}",
                                why_it_matters=f"Known CVE in dependency may expose the application to attack.",
                                remediation=f"Upgrade `{pkg}` to a patched version. Check {cve} for details.",
                                verification_method=f"Run `pip-audit` or `safety check` and confirm no remaining CVEs.",
                                source_agent=self.agent_type.value,
                            ))

            # ── Check: package.json for new deps added without lockfile update ──
            if cf.path.endswith("package.json"):
                new_deps = re.findall(r'^\+\s+"([^"]+)":\s*"([^"]+)"', cf.diff_text or "", re.MULTILINE)
                lock_changed = any("package-lock.json" in f.path or "yarn.lock" in f.path for f in change_map.changed_files)
                if new_deps and not lock_changed:
                    findings.append(EvidenceFinding(
                        title="package.json updated but lockfile not regenerated",
                        severity=Severity.HIGH,
                        confidence=Confidence.HIGH,
                        category="Dependency Integrity",
                        description=(
                            f"{len(new_deps)} new dependency entries added to `{cf.path}` "
                            f"but `package-lock.json` was not updated in this changeset."
                        ),
                        file_path=cf.path,
                        evidence_snippet="\n".join(f"{k}: {v}" for k, v in new_deps[:3]),
                        why_it_matters="Stale lockfile leads to non-deterministic installs and potential version drift.",
                        potential_release_impact="CI and production may install different versions, introducing undiscovered bugs.",
                        remediation="Run `npm install` to regenerate the lockfile and commit it.",
                        verification_method="Confirm `package-lock.json` is present and committed alongside `package.json` changes.",
                        source_agent=self.agent_type.value,
                        extra={"planted_risk": "dependency_conflict"},
                    ))

        summary = (
            f"Dependencies: examined {len(manifest_files)} manifest file(s). Found {len(findings)} finding(s)."
        )
        return AgentResult(agent_type=self.agent_type, findings=findings, summary=summary)
