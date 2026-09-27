import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as iam from 'aws-cdk-lib/aws-iam';

/**
 * Release Doctor on AWS — single-stack ECS Fargate deployment.
 *
 * Topology:
 *
 *   Internet
 *      |
 *   [ Application Load Balancer ]  (public subnets, :80)
 *      |                 |
 *   /api/*, /docs,    everything
 *   /health, /openapi   else (/)
 *   (backend TG)       (frontend TG)
 *      |                 |
 *   [ Backend Fargate ] [ Frontend Fargate ]  (private subnets)
 *      |
 *   [ RDS PostgreSQL ]  (isolated subnets)
 *
 * WebSocket note: the backend streams analysis events over /api/ws/*.
 * ALB natively supports WebSocket upgrade on HTTP listeners, so routing
 * the /api/* path prefix to the backend target group covers it — no
 * special configuration required.
 *
 * Task/analysis execution runs INLINE inside the FastAPI process
 * (USE_INLINE_TASKS=true), so no Redis/Celery/ElastiCache is provisioned.
 * This keeps the footprint (and cost) minimal. Redis can be added later
 * by introducing an ElastiCache construct and flipping the env var.
 */
export class ReleaseDoctorStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const repoRoot = path.join(__dirname, '..', '..', '..');

    // Tunables (override at deploy time with -c key=value)
    const desiredCount = Number(this.node.tryGetContext('desiredCount') ?? 1);
    const dbAllocatedStorage = Number(
      this.node.tryGetContext('dbAllocatedStorage') ?? 20
    );
    const backendCpu = Number(this.node.tryGetContext('backendCpu') ?? 512);
    const backendMemory = Number(
      this.node.tryGetContext('backendMemory') ?? 1024
    );

    // ── Networking ──────────────────────────────────────────────────────
    // 2 AZs, NAT gateway so Fargate tasks in private subnets can pull images
    // and reach the internet (git clone of target repos, CVE lookups, etc.).
    const vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        {
          name: 'public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: 'private',
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 24,
        },
        {
          name: 'isolated',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          cidrMask: 28,
        },
      ],
    });

    // ── Secrets ─────────────────────────────────────────────────────────
    // JWT signing secret — generated once, never in source or context.
    const jwtSecret = new secretsmanager.Secret(this, 'JwtSecret', {
      description: 'Release Doctor JWT signing secret',
      generateSecretString: {
        // Store as a raw string secret (no JSON) so the container reads it directly.
        passwordLength: 64,
        excludePunctuation: true,
      },
    });

    // ── Database ────────────────────────────────────────────────────────
    const dbCredentials = rds.Credentials.fromGeneratedSecret('releasedoctor', {
      secretName: `${id}/rds-credentials`,
    });

    const db = new rds.DatabaseInstance(this, 'Postgres', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_16_4,
      }),
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.BURSTABLE4_GRAVITON,
        ec2.InstanceSize.MICRO
      ),
      credentials: dbCredentials,
      databaseName: 'releasedoctor',
      allocatedStorage: dbAllocatedStorage,
      maxAllocatedStorage: 100,
      storageEncrypted: true,
      multiAz: false,
      backupRetention: cdk.Duration.days(7),
      deletionProtection: false,
      // Demo/hackathon default: destroy DB with the stack. For production,
      // switch to RETAIN and enable deletionProtection.
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ── ECS cluster ─────────────────────────────────────────────────────
    const cluster = new ecs.Cluster(this, 'Cluster', {
      vpc,
      containerInsightsV2: ecs.ContainerInsights.ENABLED,
    });

    // ── Load balancer ───────────────────────────────────────────────────
    const alb = new elbv2.ApplicationLoadBalancer(this, 'Alb', {
      vpc,
      internetFacing: true,
    });

    const listener = alb.addListener('HttpListener', {
      port: 80,
      open: true,
    });

    // The public base URL of the whole app (frontend + API share the ALB).
    // Used for CORS and CFN outputs. The frontend derives its API/WS URLs
    // from same-origin at runtime, so no ws:// variant is needed here.
    const appUrl = `http://${alb.loadBalancerDnsName}`;

    // ── Container images ────────────────────────────────────────────────
    // Backend is built from the REPO ROOT context (not backend/) so the image
    // can bundle the demo-repository alongside the app. See Dockerfile.backend.
    // A root .dockerignore keeps the build context lean (excludes node_modules,
    // .git, cdk.out, etc.).
    const backendImage = new ecr_assets.DockerImageAsset(this, 'BackendImage', {
      directory: repoRoot,
      file: 'Dockerfile.backend',
      platform: ecr_assets.Platform.LINUX_AMD64,
    });

    // The frontend and API share this single ALB origin. The ALB DNS name is
    // only known at deploy time (a CloudFormation token), and Docker build
    // args must be concrete before deployment — so we do NOT bake the URL in.
    // Instead the frontend's API client (frontend/lib/api.ts) falls back to
    // same-origin (window.location) at runtime when NEXT_PUBLIC_* is unset,
    // which resolves to this ALB automatically.
    const frontendImage = new ecr_assets.DockerImageAsset(
      this,
      'FrontendImage',
      {
        directory: path.join(repoRoot, 'frontend'),
        platform: ecr_assets.Platform.LINUX_AMD64,
      }
    );

    // ── Backend Fargate service ─────────────────────────────────────────
    const backendLogGroup = new logs.LogGroup(this, 'BackendLogs', {
      retention: logs.RetentionDays.TWO_WEEKS,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const backendTaskDef = new ecs.FargateTaskDefinition(
      this,
      'BackendTaskDef',
      {
        cpu: backendCpu,
        memoryLimitMiB: backendMemory,
      }
    );

    // The RDS-generated secret is JSON with discrete fields
    // {username, password, host, port, dbname, ...}. The backend consumes a
    // single async DATABASE_URL, so we inject the fields as DB_* env vars and
    // compose the URL in the container entrypoint (command below).
    backendTaskDef.addContainer('backend', {
      image: ecs.ContainerImage.fromDockerImageAsset(backendImage),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'backend',
        logGroup: backendLogGroup,
      }),
      environment: {
        USE_INLINE_TASKS: 'true',
        LOG_LEVEL: 'INFO',
        JWT_ALGORITHM: 'HS256',
        JWT_EXPIRE_MINUTES: '60',
        // Frontend served from the same ALB origin.
        CORS_ORIGINS_RAW: appUrl,
      },
      secrets: {
        JWT_SECRET: ecs.Secret.fromSecretsManager(jwtSecret),
        DB_USER: ecs.Secret.fromSecretsManager(db.secret!, 'username'),
        DB_PASSWORD: ecs.Secret.fromSecretsManager(db.secret!, 'password'),
        DB_HOST: ecs.Secret.fromSecretsManager(db.secret!, 'host'),
        DB_PORT: ecs.Secret.fromSecretsManager(db.secret!, 'port'),
        DB_NAME: ecs.Secret.fromSecretsManager(db.secret!, 'dbname'),
      },
      portMappings: [{ containerPort: 8000 }],
      // No command override: the image's entrypoint (backend/entrypoint.sh)
      // composes DATABASE_URL from the DB_* secrets, runs migrations, and
      // starts uvicorn.
    });

    const backendService = new ecs.FargateService(this, 'BackendService', {
      cluster,
      taskDefinition: backendTaskDef,
      desiredCount,
      assignPublicIp: false,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      circuitBreaker: { rollback: true },
      minHealthyPercent: 100,
      maxHealthyPercent: 200,
    });

    // Backend must reach RDS.
    db.connections.allowDefaultPortFrom(
      backendService,
      'Backend Fargate to Postgres'
    );

    // ── Frontend Fargate service ────────────────────────────────────────
    const frontendLogGroup = new logs.LogGroup(this, 'FrontendLogs', {
      retention: logs.RetentionDays.TWO_WEEKS,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    const frontendTaskDef = new ecs.FargateTaskDefinition(
      this,
      'FrontendTaskDef',
      {
        cpu: 256,
        memoryLimitMiB: 512,
      }
    );

    frontendTaskDef.addContainer('frontend', {
      image: ecs.ContainerImage.fromDockerImageAsset(frontendImage),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'frontend',
        logGroup: frontendLogGroup,
      }),
      environment: {
        NODE_ENV: 'production',
        // No NEXT_PUBLIC_* here: those are build-time-only in Next.js and are
        // intentionally left unset so the client falls back to same-origin
        // (this ALB) at runtime. See frontend/lib/api.ts.
      },
      portMappings: [{ containerPort: 3000 }],
    });

    const frontendService = new ecs.FargateService(this, 'FrontendService', {
      cluster,
      taskDefinition: frontendTaskDef,
      desiredCount,
      assignPublicIp: false,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      circuitBreaker: { rollback: true },
      minHealthyPercent: 100,
      maxHealthyPercent: 200,
    });

    // ── ALB routing ─────────────────────────────────────────────────────
    // Default: everything goes to the frontend.
    const frontendTg = listener.addTargets('FrontendTarget', {
      port: 3000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [frontendService],
      healthCheck: {
        path: '/',
        healthyHttpCodes: '200-399',
        interval: cdk.Duration.seconds(30),
      },
      deregistrationDelay: cdk.Duration.seconds(15),
    });

    // API + docs + health + websocket + openapi → backend.
    const backendTg = new elbv2.ApplicationTargetGroup(this, 'BackendTarget', {
      vpc,
      port: 8000,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [backendService],
      healthCheck: {
        path: '/health',
        healthyHttpCodes: '200',
        interval: cdk.Duration.seconds(30),
      },
      deregistrationDelay: cdk.Duration.seconds(15),
    });

    listener.addAction('BackendRoutes', {
      priority: 10,
      conditions: [
        elbv2.ListenerCondition.pathPatterns([
          '/api/*',
          '/docs',
          '/redoc',
          '/openapi.json',
          '/health',
        ]),
      ],
      action: elbv2.ListenerAction.forward([backendTg]),
    });

    // Suppress unused-var lints; frontendTg is wired as the default action.
    void frontendTg;

    // ── Outputs ─────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'AppURL', {
      value: appUrl,
      description: 'Public URL for the Release Doctor frontend + API',
    });
    new cdk.CfnOutput(this, 'ApiDocsURL', {
      value: `${appUrl}/docs`,
      description: 'Interactive API documentation',
    });
    new cdk.CfnOutput(this, 'HealthURL', {
      value: `${appUrl}/health`,
      description: 'Backend health check',
    });
    new cdk.CfnOutput(this, 'DbSecretArn', {
      value: db.secret?.secretArn ?? 'n/a',
      description: 'RDS credentials secret ARN',
    });
  }
}
