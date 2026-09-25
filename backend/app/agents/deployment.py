"""Deployment/DevOps Agent — Dockerfiles, CI/CD, health checks, manifests."""
from __future__ import annotations

import re
from typing import Any, List, Optional

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.models import AgentType, Confidence, Severity
from app.repository.analyzer import ChangeMap


class DeploymentAgent(BaseAgent):
    agent_type = AgentType.DEPLOYMENT_DEVOPS

    async def run(self, change_map: ChangeMap, artifacts: Optional[List[Any]] = None) -> AgentResult:
        findings: List[EvidenceFinding] = []

        docker_files = change_map.files_matching(["**/Dockerfile*", "**/docker-compose*", "**/.dockerignore"])
        ci_files = change_map.files_matching(["**/.github/workflows/**", "**/.gitlab-ci*", "**/Jenkinsfile*"])
        deployment_files = change_map.files_matching(["**/deployment/**", "**/k8s/**", "**/helm/**", "**/manifests/**"])
        source_files = [cf for cf in change_map.changed_files if cf.path.endswith((".py", ".js", ".ts"))]

        # ── Check: new Python dep but Dockerfile pip install not updated ─
        req_changed = change_map.files_matching(["**/requirements*.txt"])
        if req_changed and not docker_files:
            findings.append(EvidenceFinding(
                title="requirements.txt updated but Dockerfile not changed",
                severity=Severity.HIGH,
                confidence=Confidence.HIGH,
                category="Deployment Configuration",
                description=(
                    "Python dependencies were updated but no Dockerfile was modified. "
                    "The Docker image may not include the new dependencies."
                ),
                affected_component="Docker Image",
                why_it_matters="A stale Docker image won't contain the new dependencies, causing import errors in production.",
                potential_release_impact="Production deployment fails on startup with ModuleNotFoundError.",
                remediation="Rebuild the Docker image after updating requirements.txt. Confirm `pip install -r requirements.txt` runs in the Dockerfile.",
                verification_method="Run `docker build` and confirm the new package is installed in the image.",
                source_agent=self.agent_type.value,
                extra={"planted_risk": "docker_not_updated"},
            ))

        # ── Check: Dockerfile uses `latest` tag for base image ───────────
        for cf in docker_files:
            if not cf.content:
                continue
            for i, line in enumerate(cf.content.splitlines(), 1):
                if re.match(r'FROM\s+\S+:latest', line.strip(), re.IGNORECASE):
                    findings.append(EvidenceFinding(
                        title=f"Dockerfile uses unpinned `:latest` tag in `{cf.path}`",
                        severity=Severity.MEDIUM,
                        confidence=Confidence.HIGH,
                        category="Deployment Configuration",
                        description=f"Line {i}: `{line.strip()}` — using `:latest` makes builds non-reproducible.",
                        file_path=cf.path,
                        line_start=i,
                        evidence_snippet=line.strip(),
                        why_it_matters="`:latest` tags can change silently, introducing unexpected behaviour in production builds.",
                        remediation="Pin the base image to a specific digest or semantic version tag.",
                        source_agent=self.agent_type.value,
                    ))

        # ── Check: no health check defined in Dockerfile ─────────────────
        for cf in docker_files:
            if cf.content and "HEALTHCHECK" not in cf.content.upper():
                findings.append(EvidenceFinding(
                    title=f"No HEALTHCHECK instruction in `{cf.path}`",
                    severity=Severity.LOW,
                    confidence=Confidence.HIGH,
                    category="Deployment Configuration",
                    description="The Dockerfile does not define a HEALTHCHECK. Container orchestrators cannot detect unhealthy instances.",
                    file_path=cf.path,
                    why_it_matters="Without a health check, a crashed-but-running container receives traffic.",
                    remediation="Add a `HEALTHCHECK CMD` instruction that probes the /health endpoint.",
                    source_agent=self.agent_type.value,
                ))

        # ── Check: CI changed but tests not enabled ───────────────────────
        for cf in ci_files:
            if cf.content and "test" not in cf.content.lower() and "pytest" not in cf.content.lower():
                findings.append(EvidenceFinding(
                    title=f"CI pipeline `{cf.path}` does not appear to run tests",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    category="CI/CD",
                    description="The CI configuration was modified but no test step was found.",
                    file_path=cf.path,
                    why_it_matters="CI without tests provides no regression protection.",
                    remediation="Ensure the CI pipeline runs the full test suite on every push.",
                    source_agent=self.agent_type.value,
                ))

        summary = (
            f"Deployment: checked {len(docker_files)} Docker file(s), "
            f"{len(ci_files)} CI file(s). Found {len(findings)} finding(s)."
        )
        return AgentResult(agent_type=self.agent_type, findings=findings, summary=summary)
