<div align="center">

# ⚕ Release Doctor

### Multi-agent AI release-readiness analysis

**"Is this software change ready to release?"**

Release Doctor orchestrates 11 specialized AI agents in parallel over a real Git repository, correlates their findings into a prioritized, evidence-backed report, and guides developers through remediation — until every blocker is resolved and the release is marked **Ready to Ship**.

<br/>

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat-square)](https://sqlalchemy.org)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

<br/>

| 🌐 Frontend | ⚡ Backend API | 📖 API Docs | 🔑 Demo Login |
|:-----------:|:-------------:|:-----------:|:------------:|
| `http://localhost:3000` | `http://localhost:8000` | [`/docs`](http://localhost:8000/docs) | `demo` / `demo` |

</div>

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Agent Pipeline](#agent-pipeline)
- [Release Decision States](#release-decision-states)
- [Demo Repository](#demo-repository)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Local — No Docker](#local--no-docker-recommended-for-quick-start)
  - [Local — Docker Compose](#local--docker-compose)
- [Deployment](#deployment-railway--vercel)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Development](#development)
- [Built With IBM Bob 2.0](#built-with-ibm-bob-20)

---

## Overview

Modern software releases are complex — a single change touches databases, APIs, security boundaries, CI/CD pipelines, documentation, and downstream dependencies simultaneously. Manual code review misses cross-cutting risks. Release Doctor solves this by running a **coordinated swarm of AI agents** that each own a specific domain, then correlates their findings to surface root causes and cascading risks a single reviewer would never catch.

The result is an **evidence-backed release decision** — not a vague score, but a structured report with file paths, line numbers, code snippets, root-cause analysis, and an actionable remediation checklist.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **11 Specialized Agents** | Each agent owns a domain: security, database, tests, dependencies, deployment, API contracts, configuration, code health, documentation, and risk correlation |
| **Parallel Execution** | All agents run concurrently via `asyncio.gather` — a full analysis completes in seconds |
| **Evidence Model** | Every finding includes: title, severity, confidence, affected component, file path, line range, code snippet, why it matters, potential release impact, remediation, and verification method |
| **Risk Correlation** | A dedicated correlation agent deduplicates findings across agents, identifies root causes, and merges cascading risks into unified findings |
| **4 Release States** | `BLOCKED`, `ATTENTION REQUIRED`, `READY FOR RELEASE`, `UNVERIFIED` — computed from the correlated finding set |
| **Real-time Streaming** | WebSocket live updates as each agent completes — no polling |
| **Remediation Workflow** | Every CRITICAL/HIGH finding generates a remediation task with verification steps and status tracking |
| **Re-run & Compare** | Re-run analyses after fixes and get a structured diff showing resolved, new, and remaining findings |
| **Document Ingestion** | Upload requirements, API specs, or architecture docs — agents use them as additional context |
| **Impact Map** | Visual dependency graph showing how findings relate across components |
| **JWT Authentication** | Stateless auth with configurable expiry |
| **Zero-infra Local Mode** | Runs on SQLite + inline tasks — no PostgreSQL or Redis required for local development |

---

## Agent Pipeline

The pipeline executes in three stages:

```
Git Diff (base_ref → target_ref)
        │
        ▼
┌───────────────────┐
│    Lead Agent     │  Builds change map, selects relevant agents
└─────────┬─────────┘
          │
          ▼  asyncio.gather (all agents run in parallel)
┌─────────────────────────────────────────────────────────────┐
│                    Specialized Agents                       │
│                                                             │
│  🔬 Code Health      🗄️  Database       🧪 Test & QA        │
│  🔒 Security         ⚙️  Configuration  📦 Dependency        │
│  🔌 API Integration  🚀 Deployment     📄 Documentation     │
└──────────────────────────┬──────────────────────────────────┘
                           │  Raw findings (List[EvidenceFinding])
                           ▼
              ┌────────────────────────┐
              │  Risk Correlation      │  Deduplicates, merges, 
              │  Agent                 │  identifies root causes
              └────────────┬───────────┘
                           │  Correlated findings
                           ▼
              ┌────────────────────────┐
              │  Release Decision      │  BLOCKED / ATTENTION /
              │  Engine                │  READY / UNVERIFIED
              └────────────────────────┘
```

### Agent Responsibilities

| Agent | Domain | Example Findings |
|-------|--------|-----------------|
| **Lead** | Change map, agent selection, coordination | Identifies which agents are relevant to the diff |
| **Code Health** | Logic risks, exception handling, hardcoded secrets | Bare `except:` clauses, missing null checks, API keys in source |
| **Database** | Schema changes, missing migrations, SQL injection | Column added to model with no Alembic migration |
| **Test & QA** | Coverage gaps, untested endpoints, missing regression tests | New endpoint with zero test coverage |
| **Security** | AuthN/AuthZ, input validation, injection vectors, data flows | Endpoint missing auth dependency, unsanitized input |
| **Configuration** | Env vars, feature flags, Docker config consistency | `ANALYTICS_SERVICE_URL` referenced in code but not in `.env` |
| **Dependency** | Manifest changes, CVEs, version conflicts | `requests==2.28.0` — CVE-2023-32681 (CVSS 7.5) |
| **API & Integration** | Contract changes, breaking fields, backward compatibility | `customer_name` removed from response schema |
| **Deployment/DevOps** | Dockerfiles, CI/CD pipelines, health checks | New dependency added to `requirements.txt` but not `Dockerfile` |
| **Documentation** | API spec drift, missing docs for new endpoints | Refund endpoint missing from OpenAPI spec |
| **Risk Correlation** | Deduplication, root-cause merging, cross-cutting risks | DB migration + test failure merged into schema-mismatch root cause |

---

## Release Decision States

The release decision is computed from the set of correlated findings after all agents complete:

| State | Icon | Trigger Condition |
|-------|------|------------------|
| **BLOCKED** | 🚫 | One or more findings with `severity=CRITICAL` and `confidence=HIGH` |
| **ATTENTION REQUIRED** | ⚠️ | One or more findings with `severity=HIGH` and `confidence=HIGH` |
| **READY FOR RELEASE** | ✅ | No CRITICAL or HIGH confidence findings remain |
| **UNVERIFIED** | ❓ | CRITICAL findings exist but all have `confidence=LOW` — important checks could not complete |

States are evaluated in priority order: BLOCKED → UNVERIFIED → ATTENTION REQUIRED → READY FOR RELEASE.

---

## Demo Repository

The `demo-repository/` folder contains a sample **Order Management API** for an e-commerce platform. It represents a realistic feature branch (`main` → `feature/order-priority`) with **8 deliberately planted risks** across different domains — designed to exercise all 11 agents:

| # | Risk | Domain | Expected Finding |
|---|------|--------|-----------------|
| 1 | `priority_score` column added to ORM model with no Alembic migration | Database | 🚫 CRITICAL |
| 2 | `ANALYTICS_SERVICE_URL` referenced in application code but absent from all deployment configs | Configuration | ⚠️ HIGH |
| 3 | `customer_name` field removed from order response; frontend still references it | API & Integration | 🚫 CRITICAL |
| 4 | `/api/orders/{id}/refund` endpoint has no authentication dependency | Security | 🚫 CRITICAL |
| 5 | New `priority` and `refund` endpoints have zero unit or integration test coverage | Test & QA | ⚠️ HIGH |
| 6 | `requests==2.28.0` in requirements — known CVE-2023-32681 (SSRF, CVSS 7.5) | Dependency | ⚠️ HIGH |
| 7 | `analytics-sdk` added to `requirements.txt` but Dockerfile not updated/rebuilt | Deployment | ⚠️ HIGH |
| 8 | OpenAPI spec still documents `customer_name`; refund endpoint not in spec at all | Documentation | ℹ️ MEDIUM |

The Risk Correlation agent also identifies a **9th cross-cutting finding**: risks #1 and #5 together constitute a schema/application mismatch root cause that neither the Database nor Test agent could identify alone.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Release Doctor                            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Next.js 14 Frontend  (port 3000)                       │    │
│  │                                                         │    │
│  │   /                    Dashboard + project overview     │    │
│  │   /login               JWT authentication              │    │
│  │   /projects/setup      Create project + start analysis │    │
│  │   /analyses/[id]       Live analysis workspace         │    │
│  │   /analyses/[id]/health        Health summary          │    │
│  │   /analyses/[id]/findings      Full findings list      │    │
│  │   /analyses/[id]/impact-map    Risk dependency graph   │    │
│  │   /analyses/[id]/remediation   Remediation checklist   │    │
│  │   /analyses/[id]/comparison    Before/after diff       │    │
│  │   /analyses/[id]/documents     Document upload/view    │    │
│  │   /projects/[id]/history       Analysis history        │    │
│  └───────────────────────────┬─────────────────────────────┘    │
│                              │  REST + WebSocket                │
│  ┌───────────────────────────▼─────────────────────────────┐    │
│  │  FastAPI Backend  (port 8000)                           │    │
│  │                                                         │    │
│  │   /api/auth          JWT token issuance                 │    │
│  │   /api/projects      Project CRUD                       │    │
│  │   /api/analyses      Analysis lifecycle                 │    │
│  │   /api/documents     Document ingestion                 │    │
│  │   /api/ws            WebSocket event stream             │    │
│  │   /health            Health check                       │    │
│  │   /docs              Interactive OpenAPI docs           │    │
│  └───────────────────────────┬─────────────────────────────┘    │
│                              │                                   │
│         ┌────────────────────┼──────────────────┐               │
│         │                   │                  │               │
│  ┌──────▼──────┐    ┌───────▼──────┐   ┌──────▼──────┐        │
│  │  PostgreSQL │    │    Redis     │   │   Celery    │        │
│  │  (or SQLite)│    │  (optional)  │   │   Worker    │        │
│  │             │    │  pub/sub +   │   │  (optional) │        │
│  │  Persistent │    │  task broker │   │  Pipeline   │        │
│  │  storage    │    │              │   │  executor   │        │
│  └─────────────┘    └──────────────┘   └─────────────┘        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

> Redis and Celery are optional. When `USE_INLINE_TASKS=true`, analyses run directly in the FastAPI process using `asyncio` — no separate worker needed. This is the default for local development.

---

## Tech Stack

### Backend

| Layer | Technology |
|-------|-----------|
| Web framework | FastAPI 0.111 + Uvicorn |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Database | PostgreSQL 16 (production) / SQLite (local dev) |
| Task queue | Celery 5.4 + Redis 7 (optional — inline fallback available) |
| Auth | JWT via `python-jose` + `passlib[bcrypt]` |
| Validation | Pydantic v2 + pydantic-settings |
| Git analysis | GitPython |
| Document parsing | PyPDF2 + python-docx |
| Observability | structlog + OpenTelemetry (optional) |
| Testing | pytest + pytest-asyncio |

### Frontend

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 14 (App Router) |
| Language | TypeScript 5.5 |
| Styling | Tailwind CSS 3.4 |
| Data viz | Recharts + ReactFlow |
| HTTP | Native `fetch` with typed wrapper |
| Real-time | Native WebSocket |
| Testing | Vitest + Testing Library + Playwright |

---

## Getting Started

### Prerequisites

- **Python 3.11+** and `pip`
- **Node.js 18+** and `npm`

No database installation required for local development — the app uses SQLite by default.

---

### Local — No Docker (Recommended for Quick Start)

**1. Clone the repository**

```bash
git clone https://github.com/your-org/release-doctor.git
cd release-doctor
```

**2. Configure environment**

```bash
cp .env.example .env
```

The default `.env` is pre-configured for local development with SQLite and inline tasks — no edits needed to get started.

**3. Install backend dependencies**

```bash
cd backend
pip install -r requirements.txt
```

> `tree-sitter` requires C++ build tools and can be skipped — it is listed in requirements but not used at runtime. If the build fails on your machine, install everything else and proceed.

**4. Start the backend**

```bash
# From the backend/ directory
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The database is created automatically on first startup. You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**5. Start the frontend** (new terminal)

```bash
cd frontend
npm install   # skip if node_modules already exists
npm run dev
```

**6. Open the app**

| URL | Description |
|-----|-------------|
| http://localhost:3000 | Frontend application |
| http://localhost:8000/docs | Interactive API documentation |
| http://localhost:8000/health | Backend health check |

**7. Log in**

```
Username: demo
Password: demo
```

---

### Local — Docker Compose

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
# 1. Clone and configure
git clone https://github.com/your-org/release-doctor.git
cd release-doctor
cp .env.example .env

# 2. Start the full stack (PostgreSQL + Redis + Backend + Celery Worker + Frontend)
docker compose up --build

# 3. Open the app
open http://localhost:3000
```

Services started:

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 3000 | Next.js application |
| `backend` | 8000 | FastAPI + Uvicorn |
| `celery_worker` | — | Background analysis worker |
| `postgres` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 |

---

## Deployment (AWS — ECS Fargate)

Deploy the entire stack to AWS with a single CloudFormation stack managed by AWS CDK. The frontend, backend, and PostgreSQL run behind one Application Load Balancer; credentials live in AWS Secrets Manager.

```bash
cd infra/aws-cdk
npm install
npx cdk bootstrap aws://<ACCOUNT_ID>/<REGION>   # one-time per account/region
npx cdk deploy                                   # builds images, provisions everything
```

CDK prints an `AppURL` output — open it and log in with `demo` / `demo`.

- **Backend + frontend** run as ECS Fargate services in public subnets (public IP, no NAT gateway).
- **SQLite in-container** — the app's zero-infra database mode. No RDS, so it's cheap (~$20-35/mo) and deploys in ~4 min. Data is ephemeral; see the infra README's "Scaling to RDS" for durable storage.
- **JWT secret** auto-generated in AWS Secrets Manager.
- **WebSocket streaming** works over the same ALB — no extra config.
- **Inline task mode** is on (`USE_INLINE_TASKS=true`), so no Redis is provisioned.
- **The demo works out of the box.** The backend image bundles `demo-repository/` and initializes it as a two-commit git repo on startup. Create a project pointing at `/demo-repository` with base ref `clean` and target ref `risky` to run the full 8-risk analysis. See the infra README's "Running the end-to-end demo on AWS".

Full guide, configuration options, cost notes, and teardown: [`infra/aws-cdk/README.md`](./infra/aws-cdk/README.md).

Tear down with `npx cdk destroy` from `infra/aws-cdk`.

---

## Deployment (Railway + Vercel)

An alternative deployment path. **Free tier available** — Railway provides $5 in trial credit, Vercel is free.

### Step 1 — Backend on Railway

#### 1a. Create a Railway project

1. Go to [railway.app/new](https://railway.app/new) → **Deploy from GitHub repo**
2. Select this repository — Railway detects `railway.toml` automatically

#### 1b. Add PostgreSQL

In your Railway project dashboard:
- Click **+ New** → **Database** → **Add PostgreSQL**
- Railway auto-injects `DATABASE_URL` into your backend service

#### 1c. Add Redis (optional)

- Click **+ New** → **Database** → **Add Redis**
- Copy the `REDIS_URL` value

> **Skipping Redis?** Set `USE_INLINE_TASKS=true` in your backend service variables. Analyses run inside the FastAPI process without Celery — all features remain fully functional.

#### 1d. Set environment variables

In your Railway backend service → **Variables** tab:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Auto-injected from PostgreSQL plugin |
| `REDIS_URL` | From Redis plugin (or omit if using inline tasks) |
| `CELERY_BROKER_URL` | Same as `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | Same as `REDIS_URL` with `/1` suffix |
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CORS_ORIGINS_RAW` | Your Vercel URL (set after Step 2) |
| `USE_INLINE_TASKS` | `true` if skipping Redis, otherwise `false` |
| `LOG_LEVEL` | `INFO` |

The backend runs `alembic upgrade head` automatically on every startup — no manual migration needed.

#### 1e. Add a Celery worker (optional, requires Redis)

1. In the same Railway project → **+ New** → **GitHub Repo** (same repo)
2. Override start command: `celery -A app.worker worker --loglevel=info --concurrency=2`
3. Set the same environment variables as the backend service

### Step 2 — Frontend on Vercel

1. Go to [vercel.com/new](https://vercel.com/new) → **Import Git Repository**
2. Select this repository
3. Set **Root Directory** to `frontend`
4. Framework preset: **Next.js** (auto-detected)
5. Add environment variables:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | `https://your-service.up.railway.app` |
| `NEXT_PUBLIC_WS_URL` | `wss://your-service.up.railway.app` |

6. Click **Deploy**

> These values are baked into the JavaScript bundle at build time. If you change your backend URL, trigger a new Vercel deployment.

### Step 3 — Connect CORS

Once Vercel assigns your frontend URL:
1. Railway backend → **Variables** → set `CORS_ORIGINS_RAW` to your Vercel URL
2. Railway redeploys automatically

### Step 4 — Verify

```bash
# Health check
curl https://your-backend.up.railway.app/health
# {"status": "ok", "service": "release-doctor-api"}

# Authentication
curl -X POST https://your-backend.up.railway.app/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo"}'
# {"access_token": "eyJ...", "token_type": "bearer"}
```

---

## API Reference

The full interactive API documentation is available at `/docs` (Swagger UI) and `/redoc` when the backend is running.

### Core Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/token` | Obtain a JWT access token |
| `GET` | `/api/projects` | List all projects |
| `POST` | `/api/projects` | Create a new project |
| `POST` | `/api/projects/{id}/analyses` | Start a new analysis |
| `GET` | `/api/projects/{id}/history` | Analysis history for a project |
| `GET` | `/api/analyses/{id}` | Get analysis status and summary |
| `GET` | `/api/analyses/{id}/agents` | Agent run statuses |
| `GET` | `/api/analyses/{id}/findings` | All findings (filterable by severity/agent) |
| `GET` | `/api/analyses/{id}/findings/{fid}` | Single finding detail |
| `GET` | `/api/analyses/{id}/impact-map` | Risk dependency graph |
| `GET` | `/api/analyses/{id}/remediation` | Remediation task list |
| `PATCH` | `/api/analyses/{id}/remediation/{tid}` | Update remediation task status |
| `POST` | `/api/analyses/{id}/rerun` | Re-run analysis |
| `GET` | `/api/analyses/{id}/comparison/{prev}` | Compare two analyses |
| `DELETE` | `/api/analyses/{id}` | Cancel a running analysis |
| `WS` | `/api/ws/analyses/{id}` | Real-time event stream |

### Authentication

All endpoints except `/health` and `/api/auth/token` require a Bearer token:

```http
Authorization: Bearer <access_token>
```

---

## Project Structure

```
release-doctor/
│
├── frontend/                      # Next.js 14 + TypeScript + Tailwind
│   ├── app/                       # App Router pages
│   │   ├── page.tsx               # Dashboard
│   │   ├── login/                 # Authentication
│   │   ├── projects/              # Project setup + history
│   │   └── analyses/[id]/         # Analysis workspace + sub-pages
│   ├── components/                # Shared UI components
│   │   ├── AuthGuard.tsx          # JWT auth guard (wraps all protected pages)
│   │   ├── Header.tsx             # Navigation
│   │   └── ui/                    # StatusBadge, SeverityBadge, Card, etc.
│   ├── lib/
│   │   └── api.ts                 # Typed API client + WebSocket helper
│   ├── vercel.json                # Vercel deployment config
│   └── next.config.js
│
├── backend/                       # FastAPI + SQLAlchemy + Celery
│   ├── app/
│   │   ├── agents/                # 11 specialized agent implementations
│   │   │   ├── base.py            # BaseAgent + EvidenceFinding dataclass
│   │   │   ├── lead_agent.py      # Orchestration + agent selection
│   │   │   ├── code_health.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   ├── test_qa.py
│   │   │   ├── configuration.py
│   │   │   ├── dependency.py
│   │   │   ├── api_integration.py
│   │   │   ├── deployment.py
│   │   │   ├── documentation.py
│   │   │   └── risk_correlation.py
│   │   ├── api/                   # FastAPI route handlers
│   │   ├── models/                # SQLAlchemy ORM models
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── orchestration/         # Pipeline, lead agent, release decision
│   │   ├── repository/            # GitPython wrapper + change map
│   │   ├── services/              # Comparison + impact map builders
│   │   ├── config.py              # Pydantic-settings configuration
│   │   ├── database.py            # Async SQLAlchemy engine setup
│   │   ├── auth.py                # JWT + demo user
│   │   ├── events.py              # Redis pub/sub event bus
│   │   ├── tasks.py               # Celery task + inline fallback dispatcher
│   │   └── worker.py              # Celery app configuration
│   ├── alembic/                   # Database migrations
│   ├── tests/                     # pytest test suite
│   ├── railway.toml               # Railway deployment config
│   ├── Procfile                   # web + worker process definitions
│   └── Dockerfile
│
├── demo-repository/               # Sample Order Management API with 8 planted risks
│   ├── backend/                   # Flask API (the app being analyzed)
│   ├── frontend/                  # React app referencing removed fields
│   ├── migrations/                # Missing the priority_score migration
│   ├── deployment/                # Configs missing ANALYTICS_SERVICE_URL
│   ├── docs/                      # Outdated OpenAPI spec
│   └── tests/                     # Missing tests for new endpoints
│
├── bob_sessions/                  # IBM Bob 2.0 build transcripts (phases 0–7)
├── docker-compose.yml             # Full local stack
├── railway.toml                   # Root Railway config
└── .env.example                   # All environment variables documented
```

---

## Environment Variables

Full reference — copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./release_doctor.db` | ✅ | Database connection string. Auto-converts `postgres://` to `postgresql+asyncpg://` |
| `JWT_SECRET` | `changeme-in-production` | ✅ for prod | Secret key for JWT signing. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_EXPIRE_MINUTES` | `60` | | Token expiry in minutes |
| `CORS_ORIGINS_RAW` | `http://localhost:3000` | | Comma-separated allowed origins. E.g. `https://app.vercel.app,http://localhost:3000` |
| `REDIS_URL` | `redis://localhost:6379/0` | | Redis connection URL. Only needed when `USE_INLINE_TASKS=false` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | | Celery broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | | Celery result backend URL |
| `USE_INLINE_TASKS` | `false` | | Set `true` to run analyses in the FastAPI process without Redis/Celery |
| `LOG_LEVEL` | `INFO` | | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `OPENAI_API_KEY` | _(empty)_ | | Optional. Enables LLM-powered agent reasoning. Agents run static analysis without it |
| `IBM_BOB_API_KEY` | _(empty)_ | | Optional. IBM Bob 2.0 API key |
| `IBM_BOB_ENDPOINT` | _(empty)_ | | Optional. IBM Bob 2.0 endpoint URL |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | _(empty)_ | | Optional. OpenTelemetry collector endpoint |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | ✅ for prod | Backend URL — baked into frontend bundle at build time |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | ✅ for prod | WebSocket URL — baked into frontend bundle at build time |

---

## Development

### Running Tests

```bash
# Backend unit + integration tests
cd backend
pytest tests/ -v

# Backend logic validation (no database required)
python validate_logic.py
python validate_orchestration.py

# Frontend unit tests
cd frontend
npm test

# Frontend end-to-end tests (requires running backend + frontend)
npm run test:e2e
```

### Code Style

```bash
# Backend
cd backend
pip install -r requirements-dev.txt
ruff check .           # lint
mypy app/              # type check

# Frontend
cd frontend
npm run lint           # ESLint
npm run typecheck      # TypeScript
```

### Adding a New Agent

1. Create `backend/app/agents/my_agent.py` extending `BaseAgent`
2. Implement the `async def run(self, change_map, artifacts) -> AgentResult` method
3. Add the agent type to `AgentType` enum in `models/__init__.py`
4. Register it in `LeadAgent._AGENT_REGISTRY` with file glob patterns
5. The pipeline automatically discovers and runs it

---

## Built With IBM Bob 2.0

Release Doctor was built end-to-end using **IBM Bob 2.0** in agent mode as the primary development tool. The entire system — backend, frontend, agents, orchestration pipeline, database schema, and test suite — was produced through structured sessions across 8 build phases.

| Phase | Session File | What Was Built |
|-------|-------------|----------------|
| 0 | [`phase-0-scaffold.md`](./bob_sessions/phase-0-scaffold.md) | Project scaffold, docker-compose, CI skeleton, env config |
| 1 | [`phase-1-backend.md`](./bob_sessions/phase-1-backend.md) | SQLAlchemy models, FastAPI endpoints, JWT auth, Celery, WebSocket |
| 2 | [`phase-2-demo-repo.md`](./bob_sessions/phase-2-demo-repo.md) | Demo repository with 8 planted risks across all agent domains |
| 3 | [`phase-3-agents.md`](./bob_sessions/phase-3-agents.md) | All 11 agents, Lead Agent orchestration, Risk Correlation, pipeline |
| 4 | [`phase-4-frontend.md`](./bob_sessions/phase-4-frontend.md) | 11 Next.js pages, typed API client, UI component library |
| 5 | [`phase-5-ux.md`](./bob_sessions/phase-5-ux.md) | Dashboard UX, live agent activity panel, health sections |
| 6 | [`phase-6-hardening.md`](./bob_sessions/phase-6-hardening.md) | Error states, cancellation, test suite, observability |
| 7 | [`phase-7-demo.md`](./bob_sessions/phase-7-demo.md) | Demo script, end-to-end verification, acceptance checklist |

See [`bob_sessions/`](./bob_sessions/) for complete session transcripts, and [`BOB_BUILD_SPEC.md`](./BOB_BUILD_SPEC.md) for the full product specification used as context throughout the build.

---

<div align="center">

Built for the **IBM Bob 2.0 Hackathon**

*"Don't ship what you can't explain."*

</div>
