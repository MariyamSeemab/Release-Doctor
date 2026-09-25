"""Lead Release Doctor Agent — builds change map, decides which agents to run."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Tuple, Type

import structlog

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.agents.code_health import CodeHealthAgent
from app.agents.database import DatabaseAgent
from app.agents.test_qa import TestQAAgent
from app.agents.security import SecurityAgent
from app.agents.configuration import ConfigurationAgent
from app.agents.dependency import DependencyAgent
from app.agents.api_integration import APIIntegrationAgent
from app.agents.deployment import DeploymentAgent
from app.agents.documentation import DocumentationAgent
from app.agents.risk_correlation import RiskCorrelationAgent
from app.models import AgentType
from app.repository.analyzer import ChangeMap

logger = structlog.get_logger(__name__)

# Agent registry — maps AgentType to class and file pattern triggers
_AGENT_REGISTRY: List[Tuple[AgentType, Type[BaseAgent], List[str]]] = [
    (AgentType.CODE_HEALTH, CodeHealthAgent, ["*.py", "*.js", "*.ts", "*.go", "*.java"]),
    (AgentType.DATABASE, DatabaseAgent, ["**/models*", "**/migrations/**", "**/*.sql", "**/schema*"]),
    (AgentType.TEST_QA, TestQAAgent, ["**/*test*", "**/*.py", "**/*.ts", "**/*.js"]),
    (AgentType.SECURITY, SecurityAgent, ["*.py", "*.js", "*.ts", "**/.env*", "**/config*"]),
    (AgentType.CONFIGURATION, ConfigurationAgent, ["**/.env*", "**/config*", "**/docker*", "**/*.yml", "**/*.yaml"]),
    (AgentType.DEPENDENCY, DependencyAgent, ["**/requirements*.txt", "**/package*.json", "**/Pipfile*", "**/pyproject.toml"]),
    (AgentType.API_INTEGRATION, APIIntegrationAgent, ["**/api/**", "**/routes/**", "**/endpoints/**", "**/*.ts", "**/*.tsx"]),
    (AgentType.DEPLOYMENT_DEVOPS, DeploymentAgent, ["**/Dockerfile*", "**/docker-compose*", "**/.github/**", "**/k8s/**"]),
    (AgentType.DOCUMENTATION, DocumentationAgent, ["**/*.md", "**/*.rst", "**/docs/**", "**/*.yaml"]),
]


class LeadAgent:
    """Understands the change, decides which agents are relevant, coordinates them."""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path

    def select_agents(self, change_map: ChangeMap) -> List[Tuple[AgentType, BaseAgent]]:
        """Return the subset of agents relevant to the changed files."""
        import fnmatch

        changed_paths = [cf.path for cf in change_map.changed_files]
        selected: List[Tuple[AgentType, BaseAgent]] = []

        for agent_type, agent_cls, patterns in _AGENT_REGISTRY:
            relevant = False
            for path in changed_paths:
                if any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(path.split("/")[-1], p) for p in patterns):
                    relevant = True
                    break
            if relevant:
                selected.append((agent_type, agent_cls(self.repo_path)))
                logger.info("agent_selected", agent=agent_type.value, reason="matched_changed_files")

        # Always run correlation if we have any other agents
        if selected:
            selected.append((AgentType.RISK_CORRELATION, RiskCorrelationAgent(self.repo_path)))

        return selected

    async def run_agents_parallel(
        self,
        selected: List[Tuple[AgentType, BaseAgent]],
        change_map: ChangeMap,
        artifacts: Optional[List[Any]] = None,
        event_callback: Optional[Any] = None,
    ) -> Dict[AgentType, AgentResult]:
        """Run all selected agents in parallel (excluding correlation which runs last)."""
        non_correlation = [(at, agent) for at, agent in selected if at != AgentType.RISK_CORRELATION]
        correlation_entry = next(((at, agent) for at, agent in selected if at == AgentType.RISK_CORRELATION), None)

        async def run_one(agent_type: AgentType, agent: BaseAgent) -> Tuple[AgentType, AgentResult]:
            if event_callback:
                await event_callback("agent_started", agent_type.value)
            try:
                result = await agent.run(change_map, artifacts)
                if event_callback:
                    await event_callback("agent_completed", agent_type.value, result)
                return agent_type, result
            except Exception as exc:
                logger.error("agent_failed", agent=agent_type.value, error=str(exc))
                if event_callback:
                    await event_callback("agent_failed", agent_type.value, None, str(exc))
                return agent_type, AgentResult(agent_type=agent_type, error=str(exc))

        # Run specialized agents in parallel
        tasks = [run_one(at, agent) for at, agent in non_correlation]
        raw_results = await asyncio.gather(*tasks)
        results: Dict[AgentType, AgentResult] = dict(raw_results)

        # Collect all findings for correlation
        all_findings: List[EvidenceFinding] = []
        for result in results.values():
            all_findings.extend(result.findings)

        # Run correlation last with all findings
        if correlation_entry:
            corr_type, corr_agent = correlation_entry
            if event_callback:
                await event_callback("agent_started", corr_type.value)
            corr_result = await corr_agent.run(change_map, artifacts, all_findings=all_findings)
            if event_callback:
                await event_callback("agent_completed", corr_type.value, corr_result)
            results[corr_type] = corr_result

        return results
