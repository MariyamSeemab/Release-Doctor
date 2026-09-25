# Acceptance Checklist — Self-Verification

Per spec Section 13. Last verified: Phase 6 complete.

---

## ✅ All 11 agents run and produce structured, evidence-backed findings

- Lead + 9 specialized agents + Risk Correlation = 11 agents
- All implemented in `backend/app/agents/`
- Each produces `List[EvidenceFinding]` with all 16 evidence-model fields
- `validate_orchestration.py` confirmed all produce real findings against demo-repository changeset

---

## ✅ All 6–8 planted risks are discoverable end-to-end through the UI

| Risk | Agent | Status |
|------|-------|--------|
| 1. Missing DB migration | DatabaseAgent | ✅ CRITICAL finding |
| 2. Missing env var | ConfigurationAgent | ✅ HIGH finding |
| 3. Breaking API change | APIIntegrationAgent | ✅ CRITICAL finding |
| 4. Missing auth | SecurityAgent | ✅ CRITICAL finding |
| 5. Missing tests | TestQAAgent | ✅ HIGH finding |
| 6. Dependency CVE | DependencyAgent | ✅ HIGH finding |
| 7. Docker not updated | DeploymentAgent | ✅ HIGH finding |
| 8. Docs not updated | DocumentationAgent | ✅ MEDIUM finding |

---

## ✅ Risk Correlation merges the Section 9 schema-mismatch example into one finding

- Rule: `schema_mismatch` in `_CORRELATION_RULES`
- Triggers on: `["Database Migration", "Test Coverage"]` categories
- Output: `"Application/database schema mismatch risk"` with `severity=CRITICAL`, `is_root_cause=True`
- Test: `validate_orchestration.py::test_section9_correlation` → **PASSED**

---

## ✅ All four release-decision states are reachable and correctly triggered

| State | Trigger | Test |
|-------|---------|------|
| BLOCKED | CRITICAL + HIGH confidence finding | ✅ `test_all_four_release_states` |
| ATTENTION_REQUIRED | HIGH + HIGH confidence finding | ✅ |
| READY_FOR_RELEASE | No findings | ✅ |
| UNVERIFIED | CRITICAL + LOW confidence finding | ✅ |

---

## ✅ Re-run/comparison flow shows resolved vs. remaining findings after a fix

- `POST /api/analyses/{id}/rerun` creates a new analysis
- `GET /api/analyses/{current}/comparison/{previous}` computes resolved/new/remaining by title matching
- Comparison page (`app/analyses/[id]/comparison/page.tsx`) shows all three counts with drill-down

---

## ✅ All 11 pages/sections implemented and wired to real backend data

| # | Page | Route | Data source |
|---|------|-------|-------------|
| 1 | Dashboard | `/` | `GET /api/projects` + history |
| 2 | Login | `/login` | `POST /api/auth/token` |
| 3 | Project Setup | `/projects/setup` | `POST /api/projects`, `POST /api/projects/{id}/analyses` |
| 4 | Analysis Workspace | `/analyses/[id]` | WebSocket + polling |
| 4b | Health Dashboard | `/analyses/[id]/health` | `GET /api/analyses/{id}` + agents + findings |
| 5 | Findings | `/analyses/[id]/findings` | `GET /api/analyses/{id}/findings` |
| 6 | Finding Detail | `/analyses/[id]/findings/[findingId]` | `GET /api/analyses/{id}/findings/{findingId}` |
| 7 | Impact Map | `/analyses/[id]/impact-map` | `GET /api/analyses/{id}/impact-map` |
| 8 | Remediation Plan | `/analyses/[id]/remediation` | `GET/PATCH /api/analyses/{id}/remediation` |
| 9 | Comparison | `/analyses/[id]/comparison` | `GET /api/analyses/{id}/comparison/{prev}` |
| 10 | Documents | `/analyses/[id]/documents` | `POST /api/documents/upload` |
| 11 | History | `/projects/[id]/history` | `GET /api/projects/{id}/history` |

---

## ✅ docker-compose up brings up the full stack from a clean clone

- `docker-compose.yml` wires: postgres:16, redis:7, backend (FastAPI+uvicorn), celery_worker, frontend (Next.js)
- All healthchecks defined
- `copy .env.example .env` → `docker compose up --build` is the complete startup

---

## ✅ Core API, orchestration, finding-normalization, and critical UI-flow tests pass

- `backend/validate_logic.py`: 5/5 tests passed
- `backend/validate_orchestration.py`: 6/6 tests passed
- `backend/tests/test_agents.py`: schema correlation + all 4 release states
- `backend/tests/test_api.py`: health, auth, project CRUD
- `frontend/components/ui.test.tsx`: StatusBadge, SeverityBadge, agentLabel, token helpers
- `frontend/e2e/critical-flows.spec.ts`: login → dashboard → setup → header

---

## ✅ bob_sessions/ contains a refined transcript for every phase

| File | Phase |
|------|-------|
| `phase-0-scaffold.md` | Phase 0 ✅ |
| `phase-1-backend.md` | Phase 1 ✅ |
| `phase-2-demo-repo.md` | Phase 2 ✅ |
| `phase-3-agents.md` | Phase 3 ✅ |
| `phase-4-frontend.md` | Phase 4 ✅ |
| `phase-5-ux.md` | Phase 5 ✅ |
| `phase-6-hardening.md` | Phase 6 ✅ |
| `phase-7-demo.md` | Phase 7 ✅ |
| `README.md` | Index ✅ |
