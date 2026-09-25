"""Configuration Agent — env vars, Docker/K8s config, runtime settings."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Optional

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.models import AgentType, Confidence, Severity
from app.repository.analyzer import ChangeMap


class ConfigurationAgent(BaseAgent):
    agent_type = AgentType.CONFIGURATION

    async def run(self, change_map: ChangeMap, artifacts: Optional[List[Any]] = None) -> AgentResult:
        findings: List[EvidenceFinding] = []

        # Collect all env-var references from Python/JS source files
        env_refs: set[str] = set()
        for cf in change_map.changed_files:
            if not cf.content:
                continue
            # Python: os.environ["KEY"] or os.getenv("KEY") or settings.KEY
            for match in re.finditer(r'os\.(?:environ|getenv)\s*[\[\(]\s*["\']([A-Z_][A-Z0-9_]+)["\']', cf.content):
                env_refs.add(match.group(1))
            # JS/TS: process.env.KEY
            for match in re.finditer(r'process\.env\.([A-Z_][A-Z0-9_]+)', cf.content):
                env_refs.add(match.group(1))

        # Read .env.example to find documented vars
        documented_vars: set[str] = set()
        env_example = next(
            (cf for cf in change_map.changed_files if ".env" in cf.path),
            None,
        )
        # Also read from disk
        env_disk_paths = [Path(self.repo_path) / ".env.example", Path(self.repo_path) / ".env"]
        for ep in env_disk_paths:
            if ep.exists():
                for line in ep.read_text().splitlines():
                    m = re.match(r'^([A-Z_][A-Z0-9_]+)\s*=', line)
                    if m:
                        documented_vars.add(m.group(1))

        # Check Docker / compose files for env declarations
        docker_vars: set[str] = set()
        for cf in change_map.changed_files:
            if "docker" in cf.path.lower() or "compose" in cf.path.lower():
                for match in re.finditer(r'^\s*-?\s*([A-Z_][A-Z0-9_]+)\s*(?:=|:)', cf.content or "", re.MULTILINE):
                    docker_vars.add(match.group(1))

        # ── Check: env var in code but not in deployment config ──────────
        deployment_files = change_map.files_matching(["**/docker*", "**/compose*", "**/.env*", "**/deployment/**"])
        deployment_changed = bool(deployment_files)

        for cf in change_map.changed_files:
            if not cf.diff_text:
                continue
            new_env_refs: set[str] = set()
            for match in re.finditer(
                r'os\.(?:environ|getenv)\s*[\[\(]\s*["\']([A-Z_][A-Z0-9_]+)["\']|process\.env\.([A-Z_][A-Z0-9_]+)',
                cf.diff_text,
            ):
                key = match.group(1) or match.group(2)
                if key:
                    new_env_refs.add(key)

            for var in new_env_refs:
                if var not in documented_vars and var not in docker_vars:
                    findings.append(EvidenceFinding(
                        title=f"New env var `{var}` referenced in code but missing from deployment config",
                        severity=Severity.HIGH,
                        confidence=Confidence.HIGH,
                        category="Configuration",
                        description=(
                            f"The environment variable `{var}` is referenced in `{cf.path}` "
                            f"but was not found in .env.example, docker-compose, or deployment configuration."
                        ),
                        affected_component="Runtime Configuration",
                        file_path=cf.path,
                        evidence_snippet=f"{var} referenced but not declared in deployment config",
                        why_it_matters="A missing env var causes an application crash (KeyError/undefined) at runtime.",
                        potential_release_impact="Application startup failure or undefined behaviour in production.",
                        remediation=f"Add `{var}` to .env.example, docker-compose environment section, and deployment manifests.",
                        verification_method=f"Deploy to a staging environment and confirm `{var}` is present and non-empty.",
                        source_agent=self.agent_type.value,
                        extra={"var": var, "planted_risk": "missing_env_var"},
                    ))

        summary = (
            f"Configuration: found {len(env_refs)} env var ref(s), "
            f"{len(documented_vars)} documented. Found {len(findings)} finding(s)."
        )
        return AgentResult(agent_type=self.agent_type, findings=findings, summary=summary)
