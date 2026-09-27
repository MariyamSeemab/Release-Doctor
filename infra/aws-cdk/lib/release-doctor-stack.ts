import * as path from 'path';
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr_assets from 'aws-cdk-lib/aws-ecr-assets';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as logs from 'aws-cdk-lib/aws-logs';

/**
 * Release Doctor on AWS — lean single-stack ECS Fargate deployment.
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
 *   [ Backend Fargate ] [ Frontend Fargate ]  (public subnets, public IP)
 *      |
 *   SQLite (in-container)
 *
 * Cost-optimized for a demo/hackathon:
 *   - No RDS: the backend uses SQLite (the app's built-in zero-infra mode).
 *   - No NAT gateway: tasks run in public subnets with a public IP so they can
 *     pull images and reach the internet directly.
 *   - No Redis/Celery: USE_INLINE_TASKS=true runs analyses in-process.
 *
 * This keeps the standing footprint to just an ALB + 2 small Fargate tasks.
 *
 * WebSocket note: the backend streams analysis events over /api/ws/*. ALB
 * natively upgrades WebSocket connections on the HTTP listener, so routing the
 * /api/* path prefix to the backend target group covers it.
 *
 * SQLite note: the backend runs as a single task (desiredCount 1). SQLite is
 * per-container and not shared, so the backend must not be scaled horizontally.
 * To scale out, switch to RDS + a shared DATABASE_URL (see infra README).
 */
export class ReleaseDoctorStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const repoRoot = path.join(__dirname, '..', '..', '..');

    // Tunables (override at deploy time with -c key=value)
    const backendCpu = Number(this.node.tryGetContext('backendCpu') ?? 512);
    const backendMemory = Number(
      this.node.tryGetContext('backendMemory') ?? 1024
    );

    // ── Networking ──────────────────────────────────────────────────────
    // Public subnets only, NO NAT gateway (the biggest hidden cost). Fargate
    // tasks get a public IP so they can pull images and reach the internet.
    const vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 2,
      natGateways: 0,
      subnetConfiguration: [
        {
          name: 'public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
      ],
    });

    // ── Secrets ─────────────────────────────────────────────────────────
    // JWT signing secret — generated once, never in source or context.
    const jwtSecret = new secretsmanager.Secret(this, 'JwtSecret', {
      description: 'Release Doctor JWT signing secret',
      generateSecretString: {
        passwordLength: 64,
        excludePunctuation: true,
      },
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
    const appUrl = `http://${alb.loadBalancerDnsName}`;

    // ── Container images ────────────────────────────────────────────────
    // Backend is built from the REPO ROOT context (not backend/) so the image
    // can bundle the demo-repository alongside the app. See Dockerfile.backend.
    const backendImage = new ecr_assets.DockerImageAsset(this, 'BackendImage', {
      directory: repoRoot,
      file: 'Dockerfile.backend',
      platform: ecr_assets.Platform.LINUX_AMD64,
    });

    // The frontend and API share this single ALB origin. The ALB DNS name is
    // only known at deploy time (a CloudFormation token), and Docker build
    // args must be concrete before deployment — so we do NOT bake the URL in.
    // Instead the frontend's API client (frontend/lib/api.ts) falls back to
    // same-origin (window.location) at runtime when NEXT_PUBLIC_* is unset.
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

    backendTaskDef.addContainer('backend', {
      image: ecs.ContainerImage.fromDockerImageAsset(backendImage),
      logging: ecs.LogDrivers.awsLogs({
        streamPrefix: 'backend',
        logGroup: backendLogGroup,
      }),
      environment: {
        // SQLite in-container — the app's built-in zero-infra database mode.
        DATABASE_URL: 'sqlite+aiosqlite:////app/release_doctor.db',
        USE_INLINE_TASKS: 'true',
        LOG_LEVEL: 'INFO',
        JWT_ALGORITHM: 'HS256',
        JWT_EXPIRE_MINUTES: '60',
        // Frontend served from the same ALB origin.
        CORS_ORIGINS_RAW: appUrl,
      },
      secrets: {
        JWT_SECRET: ecs.Secret.fromSecretsManager(jwtSecret),
      },
      portMappings: [{ containerPort: 8000 }],
      // The image entrypoint (backend/entrypoint.sh) initializes the demo git
      // repo, runs migrations, and starts uvicorn. DATABASE_URL is set above,
      // so no DB_* composition is needed.
    });

    const backendService = new ecs.FargateService(this, 'BackendService', {
      cluster,
      taskDefinition: backendTaskDef,
      // SQLite is per-container: keep the backend to a single task.
      desiredCount: 1,
      assignPublicIp: true,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
      circuitBreaker: { rollback: true },
      minHealthyPercent: 0,
      maxHealthyPercent: 100,
    });

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
        // No NEXT_PUBLIC_* here: build-time-only in Next.js and intentionally
        // left unset so the client uses same-origin (this ALB) at runtime.
      },
      portMappings: [{ containerPort: 3000 }],
    });

    const frontendService = new ecs.FargateService(this, 'FrontendService', {
      cluster,
      taskDefinition: frontendTaskDef,
      desiredCount: 1,
      assignPublicIp: true,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
      circuitBreaker: { rollback: true },
      minHealthyPercent: 0,
      maxHealthyPercent: 100,
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
  }
}
