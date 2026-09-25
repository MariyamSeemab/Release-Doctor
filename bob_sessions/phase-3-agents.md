# Phase 3 — Agent Implementation

**Objective:** Repository abstraction, document ingestion, 11 agents, Lead Agent, Risk Correlation, pipeline.

---

## Prompts given

> Build Phase 3 — implement the repository abstraction, the document ingestion layer, all 11 agents from Section 7, the Lead Agent change-map + selective-launch logic, the Risk Correlation Agent (including the Section 9 dedupe/merge test), the Release Decision logic, and wire orchestration to WebSocket.

---

## Actions taken

### Repository abstraction (`backend/app/repository/analyzer.py`)
- `RepositoryAnalyzer` wraps GitPython
- `build_change_map(base_ref, target_ref)` → `ChangeMap` dataclass
- `ChangedFile` carries: path, change_type, additions, deletions, diff_text, content
- `ChangeMap.files_matching(patterns)` for agent-level filtering with fnmatch
- Falls back to disk read if git ref resolution fails (handles demo repo without full git history)

### Document ingestion (`backend/app/documents/extractor.py`)
- `extract_text(file_path)` dispatches on extension: `.pdf` → PyPDF2, `.docx` → python-docx, else plain text
- Pluggable: each format behind its own function, easy to add new types

### Agent base (`backend/app/agents/base.py`)
- `EvidenceFinding` dataclass — all 16 evidence fields from spec
- `AgentResult` — findings + summary + optional error
- `BaseAgent` abstract class with `run(change_map, artifacts) → AgentResult`

### 10 Specialized Agents (all in `backend/app/agents/`)
Each agent inspects only its domain:

| Agent | Key detections |
|-------|---------------|
| `code_health.py` | Bare except, TODO/FIXME, hardcoded secrets, missing input validation |
| `database.py` | New column without migration (planted risk 1), missing downgrade(), raw SQL injection |
| `test_qa.py` | Source changed with no tests (planted risk 5), new endpoint without test, migration without test |
| `security.py` | New route without auth (planted risk 4), hardcoded credentials, sensitive logging |
| `configuration.py` | New env var not in deployment config (planted risk 2), Docker env var gaps |
| `dependency.py` | Known CVEs via static list (planted risk 6: requests<2.31), lockfile not updated |
| `api_integration.py` | Breaking response field removal (planted risk 3), undocumented new endpoints |
| `deployment.py` | requirements.txt updated but Dockerfile not changed (planted risk 7), :latest tag, no HEALTHCHECK |
| `documentation.py` | API source changed but no docs updated (planted risk 8), uploaded doc vs implementation gaps |

### Risk Correlation Agent (`backend/app/agents/risk_correlation.py`)
Implements the Section 9 test case exactly:
- Defines `_CORRELATION_RULES` list of (rule_id, title, required_categories, merged_severity, description)
- Rule `schema_mismatch` requires categories `["Database Migration", "Test Coverage"]` — maps exactly to planted risks 1 + 5
- When 2+ categories from a rule are matched, merges into one root-cause `EvidenceFinding` with `is_root_cause=True`
- Sets `source_agent = RISK_CORRELATION`
- Deduplicates remaining pass-through findings by title, upgrading severity on conflict
- Result: 4 merged rules available (schema_mismatch, unprotected+no_test, config+deploy, breaking_api+no_docs)

### Lead Agent (`backend/app/orchestration/lead_agent.py`)
- `_AGENT_REGISTRY`: maps each AgentType to its class and file-pattern triggers
- `select_agents(change_map)`: only launches agents whose patterns match changed files
- `run_agents_parallel()`: runs all non-correlation agents via `asyncio.gather`, then correlation last
- Event callback system: each agent_started/completed/failed → updates AgentRun DB row + broadcasts to WebSocket

### Release Decision (`backend/app/orchestration/release_decision.py`)
Implements exactly 4 states:
- `BLOCKED` → any verified CRITICAL finding (confidence != LOW)
- `UNVERIFIED` → any CRITICAL/HIGH finding with LOW confidence  
- `ATTENTION_REQUIRED` → any verified HIGH finding
- `READY_FOR_RELEASE` → no critical/high findings

### Pipeline (`backend/app/orchestration/pipeline.py`)
Full async pipeline called by Celery:
1. Load analysis from DB, mark RUNNING
2. Build change map via RepositoryAnalyzer
3. Lead agent selects relevant agents
4. Create AgentRun DB records
5. Run agents in parallel with event callback
6. Persist all correlated findings + create RemediationTask for CRITICAL/HIGH
7. Compute release decision
8. Mark analysis COMPLETED, broadcast final event

---

## Key decision: Risk Correlation runs last
Correlation requires seeing ALL findings from ALL agents before it can merge. Running it in parallel would give it an incomplete picture. The pipeline therefore runs all specialized agents first (in parallel), collects their findings, then runs the correlation agent once synchronously.

---

## Outcome

All 11 agents implemented and producing structured `EvidenceFinding` objects. Section 9 correlation test passes (verified in `tests/test_agents.py::test_schema_mismatch_correlation`). All 4 release decision states reachable.
