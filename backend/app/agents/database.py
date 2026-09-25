"""Database Agent — schema changes, migrations, indexes, rollback concerns."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List, Optional

from app.agents.base import AgentResult, BaseAgent, EvidenceFinding
from app.models import AgentType, Confidence, Severity
from app.repository.analyzer import ChangeMap


class DatabaseAgent(BaseAgent):
    agent_type = AgentType.DATABASE

    async def run(self, change_map: ChangeMap, artifacts: Optional[List[Any]] = None) -> AgentResult:
        findings: List[EvidenceFinding] = []

        model_files = change_map.files_matching(["**/models*", "**/model*", "**/*schema*", "**/*.py"])
        migration_files = change_map.files_matching(["**/migrations/**", "**/alembic/**", "**/versions/**"])

        changed_model_paths = {f.path for f in model_files}
        changed_migration_paths = {f.path for f in migration_files}

        # ── Check: model changes without a migration ─────────────────────
        for cf in model_files:
            if not cf.content:
                continue
            # Look for new column definitions in diff
            new_column_pattern = re.compile(
                r'^\+.*(?:Column|mapped_column)\s*\(',
                re.MULTILINE,
            )
            new_columns = new_column_pattern.findall(cf.diff_text or "")
            if new_columns and not migration_files:
                findings.append(EvidenceFinding(
                    title="New database column added without a corresponding migration",
                    severity=Severity.CRITICAL,
                    confidence=Confidence.HIGH,
                    category="Database Migration",
                    description=(
                        f"File `{cf.path}` introduces {len(new_columns)} new column(s) but no migration file "
                        f"was found in this changeset. The production database schema will diverge from the "
                        f"application model on deployment."
                    ),
                    affected_component="Database Schema",
                    file_path=cf.path,
                    evidence_snippet="\n".join(new_columns[:3]),
                    why_it_matters="Without a migration, the application will crash on startup when trying to access the missing column.",
                    potential_release_impact="Application/database schema mismatch → startup failure or data loss.",
                    remediation="Create an Alembic migration for each new column. Test upgrade and downgrade paths.",
                    verification_method="Run `alembic upgrade head` against a copy of production schema and confirm no errors.",
                    source_agent=self.agent_type.value,
                    extra={"new_columns": new_columns, "planted_risk": "missing_migration"},
                ))

        # ── Check: migration without rollback / downgrade ────────────────
        for cf in migration_files:
            if cf.content and "def downgrade" not in cf.content:
                findings.append(EvidenceFinding(
                    title=f"Migration `{cf.path}` is missing a downgrade() function",
                    severity=Severity.MEDIUM,
                    confidence=Confidence.HIGH,
                    category="Database Migration",
                    description="The migration file does not define a `downgrade()` function, making rollback impossible.",
                    file_path=cf.path,
                    why_it_matters="Without a downgrade path, a bad release cannot be quickly rolled back.",
                    remediation="Implement a `downgrade()` function that reverses the migration.",
                    verification_method="Run `alembic downgrade -1` and confirm it executes without error.",
                    source_agent=self.agent_type.value,
                ))

        # ── Check: raw SQL without parameterization ───────────────────────
        for cf in change_map.changed_files:
            if not cf.diff_text:
                continue
            sqli_pattern = re.compile(
                r'execute\s*\(\s*[f"\'].*%s|execute\s*\(\s*f".*\{',
                re.IGNORECASE,
            )
            for i, line in enumerate((cf.diff_text or "").splitlines(), 1):
                if line.startswith("+") and sqli_pattern.search(line):
                    findings.append(EvidenceFinding(
                        title=f"Potential SQL injection via string formatting in {cf.path}",
                        severity=Severity.HIGH,
                        confidence=Confidence.MEDIUM,
                        category="Database Security",
                        description="A raw SQL execute call with string formatting was detected in new code.",
                        file_path=cf.path,
                        line_start=i,
                        evidence_snippet=line.strip(),
                        why_it_matters="String-formatted SQL is vulnerable to injection attacks.",
                        remediation="Use parameterized queries or SQLAlchemy ORM. Never format user input into SQL.",
                        source_agent=self.agent_type.value,
                    ))

        summary = (
            f"Database: checked {len(model_files)} model file(s), "
            f"{len(migration_files)} migration file(s). Found {len(findings)} finding(s)."
        )
        return AgentResult(agent_type=self.agent_type, findings=findings, summary=summary)
