# Release Doctor on AWS — Manual Setup & Command Reference

A learning-oriented walkthrough of how Release Doctor was deployed to AWS, the exact commands used, and how to do the equivalent by hand. It covers two paths:

1. **The CDK path** (what we actually used — one command deploys everything).
2. **The manual path** (do the same thing step by step with the AWS CLI, to understand what CDK creates under the hood).

> Region used throughout: `us-east-1`. Account: your own (`aws sts get-caller-identity` shows it).
> Everything below assumes the lean design: **ECS Fargate + ALB + SQLite**, no RDS, no NAT gateway.

---

## Table of Contents

- [0. Prerequisites](#0-prerequisites)
- [1. Concepts — what gets created and why](#1-concepts--what-gets-created-and-why)
- [2. The CDK path (what we used)](#2-the-cdk-path-what-we-used)
- [3. The manual path (AWS CLI, step by step)](#3-the-manual-path-aws-cli-step-by-step)
- [4. Verifying the deployment](#4-verifying-the-deployment)
- [5. Auditing what is running (cost check)](#5-auditing-what-is-running-cost-check)
- [6. Tearing everything down](#6-tearing-everything-down)
- [7. Troubleshooting log — real errors we hit](#7-troubleshooting-log--real-errors-we-hit)
- [8. Command cheat sheet](#8-command-cheat-sheet)

---

## 0. Prerequisites

| Tool | Check | Notes |
|------|-------|-------|
| AWS CLI | `aws --version` | v2 recommended |
| AWS credentials | `aws sts get-caller-identity` | must return your account ID |
| Docker | `docker version` | must be running (images are built locally) |
| Node.js + npm | `node -v` (18+) | for the CDK app |

Confirm your identity and region before anything else:

```bash
aws sts get-caller-identity
# { "Account": "466742534146", "Arn": "arn:aws:iam::.../DD-IAM-ADMIN", ... }
```

---

## 1. Concepts — what gets created and why

The app is two containers behind one load balancer:

```
Internet
   │
[ Application Load Balancer ]  :80   (public subnets)
   │  path rules:
   │   /api/*, /docs, /redoc, /openapi.json, /health  → backend target group
   │   everything else ( / )                          → frontend target group
   ├──────────────┐
[ Backend task ]  [ Frontend task ]   ECS Fargate, public subnets, public IP
   :8000            :3000
   │
 SQLite (inside the backend container — no RDS)
```

Building blocks (AWS resource → purpose):

| Resource | Purpose |
|----------|---------|
| **ECR repository** | Stores the Docker images CDK/you build |
| **VPC + 2 public subnets + internet gateway** | Network for the tasks; public so they can pull images without a NAT gateway |
| **ECS cluster** | Logical group for the Fargate services |
| **Task definitions** (backend, frontend) | Describe the container image, CPU/memory, env vars, ports |
| **ECS services** | Keep the desired number of tasks running |
| **Application Load Balancer + listener + 2 target groups** | Public entry point; routes `/api/*` to backend, rest to frontend |
| **Security groups** | ALB open to the internet on :80; tasks accept traffic only from the ALB |
| **Secrets Manager secret** | Holds the generated JWT signing secret |
| **IAM roles** (execution + task) | Let ECS pull images/secrets and let the app read its secret |
| **CloudWatch log groups** | Container logs |

---

## 2. The CDK path (what we used)

This is the fast path. From `infra/aws-cdk/`:

```bash
# 1. Install the CDK app's dependencies
npm install

# 2. Point CDK at your account/region (once per shell)
#    PowerShell:
$env:CDK_DEFAULT_ACCOUNT = "466742534146"
$env:CDK_DEFAULT_REGION  = "us-east-1"
#    bash/zsh:
export CDK_DEFAULT_ACCOUNT=466742534146
export CDK_DEFAULT_REGION=us-east-1

# 3. Bootstrap the account/region for CDK (one time per account+region).
#    Creates the CDK "toolkit" stack: an S3 bucket, an ECR repo, and roles
#    CDK uses to publish assets and deploy.
npx cdk bootstrap aws://466742534146/us-east-1

# 4. See the generated CloudFormation without deploying (also builds images)
npx cdk synth

# 5. Preview the change set
npx cdk diff

# 6. Deploy — builds both images, pushes to ECR, creates ~42 resources
npx cdk deploy --require-approval never
```

On success CDK prints outputs, e.g.:

```
ReleaseDoctorStack.AppURL     = http://Releas-Alb16-XXXX.us-east-1.elb.amazonaws.com
ReleaseDoctorStack.ApiDocsURL = http://Releas-Alb16-XXXX.us-east-1.elb.amazonaws.com/docs
ReleaseDoctorStack.HealthURL  = http://Releas-Alb16-XXXX.us-east-1.elb.amazonaws.com/health
```

Open `AppURL`, log in with `demo` / `demo`.

### What each CDK command maps to

| CDK command | What it really does |
|-------------|---------------------|
| `cdk bootstrap` | Deploys the `CDKToolkit` CloudFormation stack (S3 asset bucket + ECR repo + roles) |
| `cdk synth` | Runs your TypeScript, builds Docker images, and emits CloudFormation JSON into `cdk.out/` |
| `cdk deploy` | Publishes image assets to ECR, then creates/updates the CloudFormation stack |
| `cdk destroy` | Deletes the CloudFormation stack (and everything in it) |

---

## 3. The manual path (AWS CLI, step by step)

This reproduces the same stack by hand so you can see every piece. Names use a `rd-` prefix so they don't collide with the CDK version. Run from the **repo root**.

> Tip: on Windows PowerShell, backticks are used for line continuation below; on bash use `\`. To keep it copy-paste safe, each block is written as single lines where practical.

### 3.1 Create an ECR repository and push the images

```bash
# Variables
$ACCOUNT = "466742534146"; $REGION = "us-east-1"
$ECR = "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"

# Create one repo (or two — here we use one repo with two tags)
aws ecr create-repository --repository-name rd-app --region $REGION

# Authenticate Docker to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR

# Build the BACKEND image (root context — bundles the demo repository)
docker build -f Dockerfile.backend -t "$ECR/rd-app:backend" .

# Build the FRONTEND image.
# NOTE: on the ALB there is no fixed URL until the ALB exists, and the
# frontend reads the API from the same origin at runtime, so no build arg is
# strictly required here. If you deploy the frontend on a *different* origin,
# pass --build-arg NEXT_PUBLIC_API_URL=... --build-arg NEXT_PUBLIC_WS_URL=...
docker build -f frontend/Dockerfile -t "$ECR/rd-app:frontend" frontend

# Push both
docker push "$ECR/rd-app:backend"
docker push "$ECR/rd-app:frontend"
```

### 3.2 Create the network (VPC, subnets, internet gateway, routes)

```bash
# VPC
$VPC = (aws ec2 create-vpc --cidr-block 10.0.0.0/16 --region $REGION --query Vpc.VpcId --output text)
aws ec2 modify-vpc-attribute --vpc-id $VPC --enable-dns-hostnames --region $REGION

# Two public subnets in two AZs
$SUBNET1 = (aws ec2 create-subnet --vpc-id $VPC --cidr-block 10.0.0.0/24 --availability-zone ${REGION}a --region $REGION --query Subnet.SubnetId --output text)
$SUBNET2 = (aws ec2 create-subnet --vpc-id $VPC --cidr-block 10.0.1.0/24 --availability-zone ${REGION}b --region $REGION --query Subnet.SubnetId --output text)

# Give tasks public IPs automatically
aws ec2 modify-subnet-attribute --subnet-id $SUBNET1 --map-public-ip-on-launch --region $REGION
aws ec2 modify-subnet-attribute --subnet-id $SUBNET2 --map-public-ip-on-launch --region $REGION

# Internet gateway + attach
$IGW = (aws ec2 create-internet-gateway --region $REGION --query InternetGateway.InternetGatewayId --output text)
aws ec2 attach-internet-gateway --internet-gateway-id $IGW --vpc-id $VPC --region $REGION

# Route table with default route to the IGW, associated to both subnets
$RT = (aws ec2 create-route-table --vpc-id $VPC --region $REGION --query RouteTable.RouteTableId --output text)
aws ec2 create-route --route-table-id $RT --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW --region $REGION
aws ec2 associate-route-table --route-table-id $RT --subnet-id $SUBNET1 --region $REGION
aws ec2 associate-route-table --route-table-id $RT --subnet-id $SUBNET2 --region $REGION
```

### 3.3 Security groups

```bash
# ALB SG: allow HTTP :80 from anywhere
$ALB_SG = (aws ec2 create-security-group --group-name rd-alb-sg --description "RD ALB" --vpc-id $VPC --region $REGION --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $ALB_SG --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $REGION

# Task SG: allow :8000 and :3000 only from the ALB SG
$TASK_SG = (aws ec2 create-security-group --group-name rd-task-sg --description "RD tasks" --vpc-id $VPC --region $REGION --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $TASK_SG --protocol tcp --port 8000 --source-group $ALB_SG --region $REGION
aws ec2 authorize-security-group-ingress --group-id $TASK_SG --protocol tcp --port 3000 --source-group $ALB_SG --region $REGION
```

### 3.4 Secrets Manager — JWT secret

```bash
# Generate a random secret and store it
$JWT = (aws secretsmanager create-secret --name rd/jwt-secret --secret-string (python -c "import secrets;print(secrets.token_hex(32))") --region $REGION --query ARN --output text)
```

### 3.5 IAM roles (execution + task)

```bash
# Trust policy shared by both roles
$TRUST = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}'

# Execution role — lets ECS pull images and read secrets at launch
aws iam create-role --role-name rd-exec-role --assume-role-policy-document $TRUST
aws iam attach-role-policy --role-name rd-exec-role --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
# Allow reading the JWT secret
aws iam put-role-policy --role-name rd-exec-role --policy-name read-jwt --policy-document "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":\"secretsmanager:GetSecretValue\",\"Resource\":\"$JWT\"}]}"

# Task role — runtime identity for the app (minimal here)
aws iam create-role --role-name rd-task-role --assume-role-policy-document $TRUST
```

### 3.6 CloudWatch log groups

```bash
aws logs create-log-group --log-group-name /rd/backend  --region $REGION
aws logs create-log-group --log-group-name /rd/frontend --region $REGION
```

### 3.7 ECS cluster

```bash
aws ecs create-cluster --cluster-name rd-cluster --region $REGION
```

### 3.8 Register task definitions

Backend task definition (`rd-backend-taskdef.json`):

```json
{
  "family": "rd-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::466742534146:role/rd-exec-role",
  "taskRoleArn": "arn:aws:iam::466742534146:role/rd-task-role",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "466742534146.dkr.ecr.us-east-1.amazonaws.com/rd-app:backend",
      "portMappings": [{ "containerPort": 8000 }],
      "environment": [
        { "name": "DATABASE_URL", "value": "sqlite+aiosqlite:////app/release_doctor.db" },
        { "name": "USE_INLINE_TASKS", "value": "true" },
        { "name": "LOG_LEVEL", "value": "INFO" },
        { "name": "JWT_ALGORITHM", "value": "HS256" },
        { "name": "JWT_EXPIRE_MINUTES", "value": "60" },
        { "name": "CORS_ORIGINS_RAW", "value": "*" }
      ],
      "secrets": [
        { "name": "JWT_SECRET", "valueFrom": "arn:aws:secretsmanager:us-east-1:466742534146:secret:rd/jwt-secret" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/rd/backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "backend"
        }
      }
    }
  ]
}
```

Frontend task definition (`rd-frontend-taskdef.json`): same shape, `family` `rd-frontend`, image `:frontend`, `cpu` `256`, `memory` `512`, container port `3000`, log group `/rd/frontend`, no secrets, env `NODE_ENV=production`.

Register both:

```bash
aws ecs register-task-definition --cli-input-json file://rd-backend-taskdef.json --region $REGION
aws ecs register-task-definition --cli-input-json file://rd-frontend-taskdef.json --region $REGION
```

### 3.9 Application Load Balancer, target groups, listener

```bash
# ALB across both public subnets
$ALB_ARN = (aws elbv2 create-load-balancer --name rd-alb --type application --subnets $SUBNET1 $SUBNET2 --security-groups $ALB_SG --region $REGION --query "LoadBalancers[0].LoadBalancerArn" --output text)
$ALB_DNS = (aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --region $REGION --query "LoadBalancers[0].DNSName" --output text)

# Target groups (ip type, because Fargate awsvpc uses IP targets)
$TG_FE = (aws elbv2 create-target-group --name rd-frontend-tg --protocol HTTP --port 3000 --vpc-id $VPC --target-type ip --health-check-path / --matcher HttpCode=200-399 --region $REGION --query "TargetGroups[0].TargetGroupArn" --output text)
$TG_BE = (aws elbv2 create-target-group --name rd-backend-tg --protocol HTTP --port 8000 --vpc-id $VPC --target-type ip --health-check-path /health --matcher HttpCode=200 --region $REGION --query "TargetGroups[0].TargetGroupArn" --output text)

# Listener: default action → frontend
$LISTENER = (aws elbv2 create-listener --load-balancer-arn $ALB_ARN --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$TG_FE --region $REGION --query "Listeners[0].ListenerArn" --output text)

# Rule: /api/* and docs/health → backend (higher priority than default)
aws elbv2 create-rule --listener-arn $LISTENER --priority 10 `
  --conditions Field=path-pattern,Values='/api/*','/docs','/redoc','/openapi.json','/health' `
  --actions Type=forward,TargetGroupArn=$TG_BE --region $REGION
```

### 3.10 Create the ECS services (wires tasks to target groups)

```bash
# network config shared by both services (public subnets + public IP + task SG)
$NETCFG = "awsvpcConfiguration={subnets=[$SUBNET1,$SUBNET2],securityGroups=[$TASK_SG],assignPublicIp=ENABLED}"

# Backend service (1 task — SQLite is per-container, don't scale)
aws ecs create-service --cluster rd-cluster --service-name rd-backend `
  --task-definition rd-backend --desired-count 1 --launch-type FARGATE `
  --network-configuration $NETCFG `
  --load-balancers "targetGroupArn=$TG_BE,containerName=backend,containerPort=8000" `
  --region $REGION

# Frontend service
aws ecs create-service --cluster rd-cluster --service-name rd-frontend `
  --task-definition rd-frontend --desired-count 1 --launch-type FARGATE `
  --network-configuration $NETCFG `
  --load-balancers "targetGroupArn=$TG_FE,containerName=frontend,containerPort=3000" `
  --region $REGION
```

Give the tasks 1–2 minutes to start and pass health checks, then open `http://$ALB_DNS`.

---

## 4. Verifying the deployment

```bash
# Health (should return 200 {"status":"ok",...})
curl http://$ALB_DNS/health

# Frontend (should return HTML, 200)
curl -I http://$ALB_DNS/

# Demo login (should return a JWT)
curl -X POST http://$ALB_DNS/api/auth/token -H "Content-Type: application/json" -d '{"username":"demo","password":"demo"}'
```

Check the target group is healthy:

```bash
aws elbv2 describe-target-health --target-group-arn $TG_BE --region $REGION --query "TargetHealthDescriptions[].TargetHealth.State"
# expect: "healthy"
```

Read container logs:

```bash
aws logs tail /rd/backend  --region $REGION --since 10m
aws logs tail /rd/frontend --region $REGION --since 10m
```

### Running the demo (once the app is up)

In the UI: **+ Analyze a Release** →
- Repository: `/demo-repository`
- Default branch: `master`
- Base ref: `clean`
- Target ref: `risky`

(The backend image bundles `demo-repository/` and its `init-git.sh` builds the two-commit `clean`→`risky` history on startup.)

---

## 5. Auditing what is running (cost check)

Handy commands to see what is actually costing money in a region:

```bash
# All CloudFormation stacks
aws cloudformation list-stacks --region us-east-1 --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query "StackSummaries[].StackName" --output text

# Load balancers (each ~ $16/mo)
aws elbv2 describe-load-balancers --region us-east-1 --query "LoadBalancers[].LoadBalancerName" --output text

# NAT gateways (each ~ $32/mo) — we intentionally have none
aws ec2 describe-nat-gateways --region us-east-1 --filter Name=state,Values=available --query "NatGateways[].NatGatewayId" --output text

# Running EC2 instances
aws ec2 describe-instances --region us-east-1 --filters Name=instance-state-name,Values=running --query "Reservations[].Instances[].InstanceId" --output text

# RDS databases
aws rds describe-db-instances --region us-east-1 --query "DBInstances[].DBInstanceIdentifier" --output text

# App Runner services
aws apprunner list-services --region us-east-1 --query "ServiceSummaryList[].{Name:ServiceName,Status:Status}" --output text

# ECS clusters + running task count
aws ecs list-clusters --region us-east-1 --query clusterArns --output text
aws ecs list-tasks --cluster rd-cluster --desired-status RUNNING --region us-east-1 --query taskArns --output text
```

---

## 6. Tearing everything down

### CDK path (deletes the whole stack in one shot)

```bash
cd infra/aws-cdk
npx cdk destroy ReleaseDoctorStack --force
```

### Manual path (reverse order of creation)

```bash
# Services first (must be gone before target groups / cluster)
aws ecs update-service --cluster rd-cluster --service rd-backend  --desired-count 0 --region $REGION
aws ecs update-service --cluster rd-cluster --service rd-frontend --desired-count 0 --region $REGION
aws ecs delete-service --cluster rd-cluster --service rd-backend  --force --region $REGION
aws ecs delete-service --cluster rd-cluster --service rd-frontend --force --region $REGION

# Listener, rules, target groups, ALB
aws elbv2 delete-listener --listener-arn $LISTENER --region $REGION
aws elbv2 delete-target-group --target-group-arn $TG_BE --region $REGION
aws elbv2 delete-target-group --target-group-arn $TG_FE --region $REGION
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN --region $REGION

# Cluster, logs, secret
aws ecs delete-cluster --cluster rd-cluster --region $REGION
aws logs delete-log-group --log-group-name /rd/backend  --region $REGION
aws logs delete-log-group --log-group-name /rd/frontend --region $REGION
aws secretsmanager delete-secret --secret-id rd/jwt-secret --force-delete-without-recovery --region $REGION

# IAM roles (detach policies first)
aws iam delete-role-policy --role-name rd-exec-role --policy-name read-jwt
aws iam detach-role-policy --role-name rd-exec-role --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws iam delete-role --role-name rd-exec-role
aws iam delete-role --role-name rd-task-role

# Network (routes, IGW, subnets, SGs, VPC) — delete dependants before the VPC
aws ec2 delete-security-group --group-id $TASK_SG --region $REGION
aws ec2 delete-security-group --group-id $ALB_SG  --region $REGION
aws ec2 detach-internet-gateway --internet-gateway-id $IGW --vpc-id $VPC --region $REGION
aws ec2 delete-internet-gateway --internet-gateway-id $IGW --region $REGION
aws ec2 delete-subnet --subnet-id $SUBNET1 --region $REGION
aws ec2 delete-subnet --subnet-id $SUBNET2 --region $REGION
aws ec2 delete-route-table --route-table-id $RT --region $REGION
aws ec2 delete-vpc --vpc-id $VPC --region $REGION

# ECR (optional — deletes the images)
aws ecr delete-repository --repository-name rd-app --force --region $REGION
```

Verify nothing is left:

```bash
aws elbv2 describe-load-balancers --region $REGION --query "LoadBalancers[].LoadBalancerName" --output text
aws ecs list-clusters --region $REGION --query clusterArns --output text
```

---

## 7. Troubleshooting log — real errors we hit

These are the actual failures encountered during this project and their fixes — useful for learning what commonly goes wrong.

| Error | Cause | Fix |
|-------|-------|-----|
| `No ECR repository named 'cdk-hnb659fds-container-assets-...'` | The CDK bootstrap ECR repo had been deleted out-of-band; the toolkit stack still referenced it (drift) | Recreate it: `aws ecr create-repository --repository-name cdk-hnb659fds-container-assets-<acct>-<region> --region <region>` |
| `Cannot find version 16.4 for postgres` | AWS deprecates RDS minor versions over time | Use a current minor (e.g. `16.15`), or major-only. (We later dropped RDS entirely for SQLite.) |
| `ECS Deployment Circuit Breaker was triggered` (backend) | Container crashed on startup | Read logs; root causes below |
| `ModuleNotFoundError: No module named 'aiosqlite'` | SQLite async driver missing from `requirements.txt` | Add `aiosqlite` to `backend/requirements.txt` |
| `AssertionError: Status code 204 must not have a response body` | FastAPI 0.111 rejects a `DELETE` route declaring 204 but returning a body | Return an explicit `Response(status_code=204)` and set `response_class=Response` |
| Frontend build fails: `Property 'onClick' does not exist` | `Card` component lacked an `onClick` prop | Add `onClick` to the component props |
| Frontend build fails on dynamic `href` | Next.js experimental `typedRoutes` rejects string hrefs | Disable `experimental.typedRoutes` in `next.config.js` |
| Frontend build fails type-checking `vitest.config.ts` | Test config pulled into the Next.js production typecheck | Exclude test configs in `tsconfig.json` |
| `failed to read dockerfile: open Dockerfile: no such file` (frontend asset) | Root `.dockerignore` excluded whole app dirs, breaking CDK asset staging | Don't exclude top-level app dirs in the root `.dockerignore`; add a `frontend/.dockerignore` |
| App Runner frontend `NotStabilized`, no app logs | Next.js standalone server not binding to `0.0.0.0` on App Runner | Set `HOSTNAME=0.0.0.0` and `PORT` in the frontend Dockerfile (App Runner path was ultimately dropped) |
| `Stack ... does not exist` / stuck in `ROLLBACK_COMPLETE` | A rolled-back stack cannot be updated | Delete it first: `aws cloudformation delete-stack --stack-name <name>` |

---

## 8. Command cheat sheet

```bash
# Identity / region
aws sts get-caller-identity

# CDK lifecycle (from infra/aws-cdk)
npm install
npx cdk bootstrap aws://<ACCOUNT>/<REGION>
npx cdk synth
npx cdk diff
npx cdk deploy --require-approval never
npx cdk destroy ReleaseDoctorStack --force

# ECR
aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ACCT>.dkr.ecr.<REGION>.amazonaws.com
docker build -f Dockerfile.backend -t <repo>:backend .
docker push <repo>:backend

# ECS
aws ecs list-clusters --region <REGION>
aws ecs list-services --cluster <cluster> --region <REGION>
aws ecs list-tasks --cluster <cluster> --desired-status RUNNING --region <REGION>
aws ecs update-service --cluster <cluster> --service <svc> --force-new-deployment --region <REGION>

# Load balancer
aws elbv2 describe-load-balancers --region <REGION>
aws elbv2 describe-target-health --target-group-arn <tg-arn> --region <REGION>

# Logs
aws logs tail /rd/backend --region <REGION> --since 15m --follow

# CloudFormation
aws cloudformation list-stacks --region <REGION>
aws cloudformation describe-stack-events --stack-name <name> --region <REGION>
aws cloudformation delete-stack --stack-name <name> --region <REGION>

# Local container testing (reproduce ECS locally before deploying)
docker run --rm -p 8099:8000 \
  -e DATABASE_URL='sqlite+aiosqlite:////app/release_doctor.db' \
  -e USE_INLINE_TASKS=true -e JWT_SECRET=testsecret \
  -e CORS_ORIGINS_RAW=http://localhost <repo>:backend
curl http://localhost:8099/health
```

---

*This document reflects the lean ECS Fargate + SQLite deployment. For the full CDK reference (architecture, config options, scaling to RDS/Redis), see [`README.md`](./README.md) in this folder.*
