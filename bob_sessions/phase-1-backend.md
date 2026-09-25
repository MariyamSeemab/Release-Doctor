# Phase 1 — Backend Core

**Objective:** SQLAlchemy models, Alembic-style migrations, FastAPI app skeleton, JWT auth, Celery background jobs, WebSocket streaming.

---

## Prompts given

> Build Phase 1 — Backend Core. SQLAlchemy models from Section 5, FastAPI skeleton with all endpoints from Section 6 (stubbed), JWT auth, Celery/RQ background job layer, WebSocket channel for live agent status.

---

## Actions taken

### SQLAlchemy Models (`backend/app/models/__init__.py`)
- Created all 8 models from the spec: `Project`, `ReleaseAnalysis`, `AgentRun`, `Finding`, `Artifact`, `RiskRelation`, `RemediationTask`, `AnalysisComparison`
- Used `DeclarativeBase` with `mapped_column` (SQLAlchemy 2.0 style)
- `Finding` carries all 16 evidence-model fields from spec Section 5
- All enumerations as Python `enum.Enum` + SQLAlchemy `Enum` columns: `OverallStatus`, `AnalysisStatus`, `AgentType`, `Severity`, `Confidence`, `FindingStatus`, `RemediationStatus`, `ArtifactType`, `RelationshipType`
- UUID primary keys throughout

### Database (`backend/app/database.py`)
- `create_async_engine` with `asyncpg` driver
- `async_sessionmaker` for dependency injection
- `Base` as shared `DeclarativeBase`
- `get_db()` async generator for FastAPI `Depends`

### Configuration (`backend/app/config.py`)
- `pydantic-settings` `BaseSettings` — reads from `.env` automatically
- All required env vars with safe defaults

### Logging (`backend/app/logging_config.py`)
- `structlog` with JSON renderer
- stdlib logging bridged to structlog

### Auth (`backend/app/auth.py`)
- `jose` JWT with HS256
- `passlib` bcrypt for password hashing
- `get_current_user` dependency for protected routes
- Prototype single demo user (`demo/demo`) — pluggable interface documented

### Worker (`backend/app/worker.py` + `app/tasks.py`)
- Celery configured with Redis broker
- `run_analysis_task` Celery task that calls `run_analysis_pipeline(analysis_id)` via asyncio

### API Router (`backend/app/api/router.py`)
- Mounts: `/auth`, `/projects`, `/analyses`, `/documents`, `/ws`

### Endpoints implemented
All 13 endpoints from spec Section 6, plus extras:
- `POST /api/auth/token`
- `POST/GET /api/projects`
- `GET /api/projects/{id}`, `GET /api/projects/{id}/history`
- `POST /api/projects/{projectId}/analyses`
- `GET/DELETE /api/analyses/{id}`
- `GET /api/analyses/{id}/agents`
- `GET /api/analyses/{id}/findings` (with severity + agent_type filter params)
- `GET /api/analyses/{id}/findings/{findingId}`
- `GET /api/analyses/{id}/impact-map`
- `GET/PATCH /api/analyses/{id}/remediation`
- `POST /api/analyses/{id}/rerun`
- `GET /api/analyses/{id}/comparison/{previousAnalysisId}`
- `POST /api/documents/upload`
- `WebSocket /api/ws/analyses/{id}`

### Services
- `comparison.py`: computes resolved/new/remaining finding sets by title
- `impact_map.py`: builds React Flow node/edge graph from findings + risk relations

---

## Decisions made

- **Async SQLAlchemy** over sync — required for FastAPI + Celery async workers
- `asyncpg` as the async Postgres driver (not `psycopg3-binary` which was less stable at time of writing)
- WebSocket hub is in-memory dict for prototype — production would use Redis pub/sub
- Auth is pluggable: `get_current_user` is a FastAPI dependency that can be swapped without touching routes
- Celery task calls `asyncio.get_event_loop().run_until_complete()` — acceptable for Celery workers which are sync by default

---

## Outcome

All backend files confirmed created. `uvicorn app.main:app` can start with a valid DATABASE_URL. All endpoints return correct schemas. Tests in `tests/test_api.py` cover health, auth, and CRUD.
