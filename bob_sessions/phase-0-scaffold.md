# Phase 0 — Scaffold

**Date:** Phase 0 of the Release Doctor build  
**Objective:** Create the full repository tree, docker-compose, .env.example, CI skeleton, and bob_sessions directory.

---

## Prompt given to Bob

> Check E:\RELEASE DOCTOR\BOB_BUILD_SPEC.md and start building. Follow the phases in order. Phase 0 first: scaffold the exact directory tree from Section 4, wire docker-compose, write .env.example with all required variables, create the GitHub Actions CI skeleton, and create the bob_sessions/ folder.

---

## Actions taken

1. Read `BOB_BUILD_SPEC.md` — confirmed the full spec (13 sections, 7 build phases).
2. Created the full directory tree via PowerShell `New-Item` loop:
   - `frontend/app`, `frontend/components`, `frontend/features/{dashboard,analysis,findings,impact-map,remediation}`, `frontend/lib`
   - `backend/app/{api,models,schemas,services,agents,orchestration,repository,documents,risk_engine}`, `backend/tests`
   - `demo-repository/{frontend,backend,migrations,tests,docs,deployment}`
   - `bob_sessions/`, `.github/workflows/`
3. Created `docker-compose.yml` wiring:
   - `postgres:16-alpine` with healthcheck
   - `redis:7-alpine` with healthcheck
   - `backend` (FastAPI + uvicorn, depends on postgres + redis)
   - `celery_worker` (same image, different command)
   - `frontend` (Next.js, depends on backend)
   - Named volume `pgdata`
4. Created `.env.example` with all required variables:
   - POSTGRES_USER/PASSWORD/DB, JWT_SECRET/ALGORITHM/EXPIRE_MINUTES
   - REDIS_URL, CELERY_BROKER_URL/RESULT_BACKEND
   - DATABASE_URL, LOG_LEVEL, CORS_ORIGINS
   - NEXT_PUBLIC_API_URL, NEXT_PUBLIC_WS_URL
   - IBM_BOB_API_KEY, IBM_BOB_ENDPOINT, OPENAI_API_KEY
   - OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME
5. Created `.github/workflows/ci.yml` with three jobs:
   - `backend-lint-test`: Python 3.12, Ruff + Black + Mypy + pytest, with Postgres and Redis services
   - `frontend-lint-test`: Node 20, ESLint + tsc + Vitest
   - `e2e`: Playwright, only on PRs, docker-compose up full stack

---

## Decisions made

- Used `postgres:16-alpine` (not 15) — latest stable, smaller image
- Used `asyncpg` driver for SQLAlchemy async support (`postgresql+asyncpg://` in DATABASE_URL)
- Separate `celery_worker` service so the API container stays stateless
- GitHub Actions `e2e` job only runs on `pull_request` to keep push CI fast
- `.env.example` uses `ANALYTICS_SERVICE_URL` deliberately absent — this is planted risk #2

---

## Outcome

All directories and files confirmed created. `docker-compose up` can be run from `release-doctor/` immediately after backend and frontend images are built.
