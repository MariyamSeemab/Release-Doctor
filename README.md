# Release Doctor

> **Multi-agent AI release-readiness analysis.** "Is this software change ready to release?"

Release Doctor runs 11 specialized AI agents in parallel over a real Git repository, correlates their findings into a prioritized evidence-backed report, and lets developers fix issues and re-run diagnosis until the release is **Ready for Release**.

---

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with real secrets (JWT_SECRET is required)

# 2. Start the full stack
docker compose up --build

# 3. Open the app
open http://localhost:3000

# 4. Login with demo credentials
# username: demo  password: demo
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Release Doctor                        │
│                                                         │
│  Next.js Frontend (port 3000)                           │
│    ├── Dashboard, Project Setup, Analysis Workspace     │
│    ├── Findings, Impact Map, Remediation                │
│    └── Comparison, Documents, History                   │
│                                                         │
│  FastAPI Backend (port 8000)                            │
│    ├── REST API + WebSocket streaming                   │
│    ├── JWT auth                                         │
│    └── Celery background worker                         │
│                                                         │
│  Agent Orchestration Pipeline                           │
│    ├── Lead Agent (change map + agent selection)        │
│    ├── 9 Specialized Agents (parallel)                  │
│    └── Risk Correlation Agent (merges + deduplicates)   │
│                                                         │
│  PostgreSQL + Redis                                     │
└─────────────────────────────────────────────────────────┘
```

---

## Agents

| Agent | Domain |
|-------|--------|
| Lead | Change map, agent selection, coordination |
| Code Health | Logic risks, exception handling, secrets |
| Database | Migrations, schema changes, SQL injection |
| Test & QA | Coverage gaps, missing regression tests |
| Security | AuthN/AuthZ, input validation, data flows |
| Configuration | Env vars, Docker, deployment config |
| Dependency | Manifests, CVEs, version conflicts |
| API & Integration | Contract changes, breaking fields |
| Deployment/DevOps | Dockerfiles, CI/CD, health checks |
| Documentation | Docs vs implementation drift |
| Risk Correlation | Deduplication, root-cause merging |

---

## Release Decision States

| State | Meaning |
|-------|---------|
| 🚫 **BLOCKED** | One or more verified critical release blockers |
| ⚠️ **ATTENTION REQUIRED** | High-impact risks need review |
| ✅ **READY FOR RELEASE** | No critical/high blockers remain |
| ❓ **UNVERIFIED** | Important checks could not complete |

---

## Demo Repository

The `demo-repository/` folder contains a sample e-commerce Order Management API with **8 deliberately planted risks**:

1. **Missing DB migration** — `priority_score` column added to model with no Alembic migration
2. **Missing env var** — `ANALYTICS_SERVICE_URL` referenced in code but absent from deployment config
3. **Breaking API change** — `customer_name` field removed from response; frontend still expects it
4. **Missing authorization** — `/api/orders/{id}/refund` endpoint has no auth dependency
5. **Missing tests** — new endpoints have no unit/integration tests
6. **Dependency vulnerability** — `requests==2.28.0` has CVE-2023-32681
7. **Docker not updated** — `analytics-sdk` added to requirements but Dockerfile not rebuilt
8. **Docs not updated** — API spec still documents `customer_name`, refund endpoint not in spec

---

## Development

```bash
# Backend only
cd backend
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend only
cd frontend
npm install
npm run dev

# Tests
cd backend && pytest tests/ -v
cd frontend && npm test
```

---

## Project Structure

```
release-doctor/
├── frontend/          # Next.js 14 + TypeScript + Tailwind
├── backend/           # FastAPI + SQLAlchemy + Celery
├── demo-repository/   # Sample app with planted risks
├── bob_sessions/      # Refined Bob session transcripts
├── docker-compose.yml
└── .env.example
```

---

## Built With IBM Bob 2.0

This project was built using IBM Bob 2.0 agent mode as the primary orchestration mechanism.
See [`bob_sessions/`](./bob_sessions/) for refined transcripts of each build phase.
