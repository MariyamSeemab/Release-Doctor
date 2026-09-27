# Release Doctor — AWS CDK Infrastructure

Deploys the full Release Doctor stack (Next.js frontend + FastAPI backend) to **AWS ECS Fargate** behind a single **Application Load Balancer**, with the JWT secret in **AWS Secrets Manager**.

This is a **cost-optimized** deployment for demos/hackathons: it uses **SQLite in-container** (the app's built-in zero-infra database mode) and **no NAT gateway**, so the standing footprint is just an ALB + two small Fargate tasks. It's an alternative to the Railway + Vercel path in the root README. Everything lives in one CloudFormation stack.

## Architecture

```
                       Internet
                          │
              ┌───────────▼────────────┐
              │  Application Load       │   :80  (public subnets)
              │  Balancer (ALB)         │
              └─────┬─────────────┬─────┘
     /api/*, /docs, │             │  everything else ( / )
     /redoc,        │             │
     /openapi.json, │             │
     /health        │             │
              ┌──────▼─────┐  ┌────▼────────┐
              │  Backend   │  │  Frontend   │   (public subnets, Fargate,
              │  FastAPI   │  │  Next.js    │    public IP — no NAT gateway)
              │  :8000     │  │  :3000      │
              └──────┬─────┘  └─────────────┘
                     │
              SQLite (in-container)

Secrets Manager: JWT signing secret (injected at runtime)
```

### Key decisions

- **Single ALB** fronts both services. The frontend and API share one origin, so no cross-origin/CORS surprises and WebSockets (`/api/ws/*`) work over the same listener (ALB natively upgrades WebSocket connections).
- **SQLite, not RDS.** The backend runs on SQLite inside the container (`DATABASE_URL=sqlite+aiosqlite:///...`), the app's documented zero-infra mode. This removes the biggest cost and the slow (~15 min) RDS provisioning. The backend runs as a **single task** because SQLite is per-container — do not scale it horizontally. To scale out, switch to RDS + a shared `DATABASE_URL` (see "Scaling to RDS" below).
- **No NAT gateway.** Tasks run in **public subnets with a public IP** so they can pull images and reach the internet directly. NAT gateways are a large hidden monthly cost; this avoids them.
- **Inline task mode** (`USE_INLINE_TASKS=true`) — analyses run inside the FastAPI process using `asyncio`. No Redis/Celery/ElastiCache is provisioned.
- **Secrets Manager** holds the auto-generated JWT secret. Nothing sensitive is in source or CDK context.
- The **frontend uses same-origin at runtime.** Next.js inlines `NEXT_PUBLIC_*` at build time, but the ALB URL is only known at deploy time — so `frontend/lib/api.ts` falls back to `window.location` (this ALB) when those vars are unset.

## Prerequisites

- **Node.js 18+** and npm
- **AWS CLI** configured with credentials (`aws sts get-caller-identity` should succeed)
- **Docker** running locally (CDK builds the container images during synth/deploy)
- An AWS account **bootstrapped** for CDK in your target region

## Deploy

```bash
cd infra/aws-cdk
npm install

# One-time per account/region:
npx cdk bootstrap aws://<ACCOUNT_ID>/<REGION>

# Preview the CloudFormation template (no AWS calls that cost money):
npm run synth

# See what will be created:
npx cdk diff

# Deploy (builds images, pushes to ECR, creates all resources):
npx cdk deploy
```

On success, CloudFormation prints outputs:

| Output | Description |
|--------|-------------|
| `AppURL` | Public URL for the app (frontend + API) |
| `ApiDocsURL` | Swagger UI (`/docs`) |
| `HealthURL` | Backend health check (`/health`) |

Log in with the demo credentials: `demo` / `demo`.

## Running the end-to-end demo on AWS

The backend image bundles the sample **OrderFlow** app (`demo-repository/`) and,
on first container start, initializes it as a git repo with two commits so the
agents have a real diff to analyze:

- `clean` — the clean baseline
- `risky` — the same app with 8 planted release risks

To run the flagship demo after deploying:

1. Open `AppURL`, log in with `demo` / `demo`.
2. Click **+ Analyze a Release** and create a project:
   - Name: `OrderFlow`
   - Repository: `/demo-repository`
   - Default branch: `master`
   - Base ref: `clean`
   - Target ref: `risky`
3. Start the analysis. All relevant agents run and surface the 8 planted risks
   plus the correlated schema-mismatch root cause.

> Use the stable tag names `clean` and `risky` (not commit SHAs). The SHAs vary
> by build because of line-ending normalization; the tags are always correct.

## Configuration

Override defaults at deploy time with `-c key=value`:

| Context key | Default | Description |
|-------------|---------|-------------|
| `account` | from credentials | Target AWS account ID |
| `region` | `us-east-1` | Target region |
| `backendCpu` | `512` | Backend task CPU units |
| `backendMemory` | `1024` | Backend task memory (MiB) |

Example:

```bash
npx cdk deploy -c region=eu-west-1 -c backendMemory=2048
```

> The backend is fixed at a single task (SQLite is per-container), so there is no `desiredCount` knob for it.

## Cost note

This stack provisions billable resources: an ALB and two small Fargate tasks. There is **no RDS and no NAT gateway** (the two biggest costs in a typical setup), so expect a rough baseline of roughly **$20-35/month** at the default sizing (region-dependent, mostly the ALB + Fargate). Run `npx cdk destroy` to tear everything down when you are done.

```bash
npx cdk destroy
```

> Because the database is SQLite inside the container, it is ephemeral — data does not survive a task replacement or redeploy. That is fine for the demo. For durable storage, move to RDS (below).

## Scaling to RDS + Redis (optional, for production)

The lean stack trades durability and horizontal scale for cost and speed. To productionize:

1. **Durable database:** add an `rds.DatabaseInstance` (Postgres) in isolated subnets, inject its credentials from Secrets Manager as `DB_*` env vars, and let `backend/entrypoint.sh` compose `DATABASE_URL` (it already supports this). Remove the SQLite `DATABASE_URL` env. This also lets the backend scale to multiple tasks. Note: RDS in private/isolated subnets requires a NAT gateway (or VPC endpoints) for image pulls.
2. **Distributed workers:** add an ElastiCache Redis cluster, set `USE_INLINE_TASKS=false` and `REDIS_URL`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND`, and add a Celery worker Fargate service running `celery -A app.worker worker --loglevel=info --concurrency=2`.

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|-------------------|
| `docker` errors during `cdk deploy` | Docker daemon not running, or building on ARM Mac — the assets pin `LINUX_AMD64`, so buildx emulation must be available |
| Backend task cycles / circuit breaker triggers | Check the `BackendLogs` CloudWatch log group. The container must answer `200` on `/health`. Past causes (now fixed): missing `aiosqlite`, a FastAPI 204 route with a body |
| `502 Bad Gateway` from the ALB | Target group has no healthy targets yet; give the tasks a minute to start and pass health checks |
| Analysis data disappeared | Expected — SQLite is in-container and ephemeral. Move to RDS for durability |
| `ROLLBACK_COMPLETE` stuck stack | Delete it (`aws cloudformation delete-stack`) before re-deploying; a `ROLLBACK_COMPLETE` stack cannot be updated |
