# Release Doctor — AWS CDK Infrastructure

Deploys the full Release Doctor stack (Next.js frontend + FastAPI backend + PostgreSQL) to **AWS ECS Fargate** behind a single **Application Load Balancer**, with credentials in **AWS Secrets Manager**.

This is an alternative to the Railway + Vercel path documented in the root README. Everything lives in one CloudFormation stack.

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
              │  Backend   │  │  Frontend   │   (private subnets, Fargate)
              │  FastAPI   │  │  Next.js    │
              │  :8000     │  │  :3000      │
              └──────┬─────┘  └─────────────┘
                     │
              ┌──────▼──────┐
              │ RDS         │   (isolated subnets)
              │ PostgreSQL  │
              └─────────────┘

Secrets Manager: JWT signing secret + RDS credentials (injected at runtime)
```

### Key decisions

- **Single ALB** fronts both services. The frontend and API share one origin, so no cross-origin/CORS surprises and WebSockets (`/api/ws/*`) work over the same listener (ALB natively upgrades WebSocket connections).
- **Inline task mode** (`USE_INLINE_TASKS=true`) — analyses run inside the FastAPI process using `asyncio`. No Redis/Celery/ElastiCache is provisioned, which keeps the cost and footprint minimal. See "Adding Redis" below to scale out.
- **Secrets Manager** holds the JWT secret (auto-generated) and the RDS credentials (auto-generated). Nothing sensitive is in source or CDK context.
- The **frontend image is built with the ALB URL baked in** (`NEXT_PUBLIC_API_URL` / `NEXT_PUBLIC_WS_URL` build args), because Next.js inlines `NEXT_PUBLIC_*` at build time.

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
| `DbSecretArn` | ARN of the RDS credentials secret |

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
| `desiredCount` | `1` | Fargate task count per service |
| `dbAllocatedStorage` | `20` | RDS storage (GB) |
| `backendCpu` | `512` | Backend task CPU units |
| `backendMemory` | `1024` | Backend task memory (MiB) |

Example:

```bash
npx cdk deploy -c region=eu-west-1 -c desiredCount=2 -c backendMemory=2048
```

## Cost note

This stack provisions billable resources: an ALB, a NAT gateway, an RDS instance, and Fargate tasks. Expect a rough baseline in the low tens of USD per month at the default sizing (region-dependent). Run `npx cdk destroy` to tear everything down when you are done.

```bash
npx cdk destroy
```

> The RDS instance uses `RemovalPolicy.DESTROY` and `deletionProtection: false` for easy teardown (demo/hackathon default). For production, switch both — set the DB to `RETAIN` and enable deletion protection in `lib/release-doctor-stack.ts`.

## Adding Redis (optional, for scale-out)

Inline task mode runs analyses in the API process, which is fine for a single backend task. To distribute analysis work across multiple backend tasks:

1. Add an `aws-elasticache` Redis cluster construct to the stack in the private subnets.
2. Grant the backend service security group access to the Redis port.
3. Set `USE_INLINE_TASKS=false`, and `REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` to the cluster endpoint.
4. Add a third Fargate service running the Celery worker command:
   `celery -A app.worker worker --loglevel=info --concurrency=2`

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|-------------------|
| `docker` errors during `cdk deploy` | Docker daemon not running, or building on ARM Mac — the assets pin `LINUX_AMD64`, so buildx emulation must be available |
| Backend tasks cycle / fail health checks | Check the `BackendLogs` CloudWatch log group. Common cause: RDS not reachable — confirm the security group rule was created |
| `502 Bad Gateway` from the ALB | Target group has no healthy targets yet; give the tasks a minute to start and pass health checks |
| Frontend shows API errors | The ALB URL was not baked into the frontend image. Re-deploy so the image rebuilds with the correct `NEXT_PUBLIC_*` build args |
| `Export ... cannot be deleted` on update | Cross-stack reference deadlock — not expected in this single-stack design, but if refactoring, deploy in two steps |
