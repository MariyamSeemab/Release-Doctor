#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { ReleaseDoctorStack } from '../lib/release-doctor-stack';

const app = new cdk.App();

// Account/region resolution order:
//   1. CDK context (-c account=... -c region=...)
//   2. CDK_DEFAULT_ACCOUNT / CDK_DEFAULT_REGION (from your AWS credentials)
const account =
  app.node.tryGetContext('account') || process.env.CDK_DEFAULT_ACCOUNT;
const region =
  app.node.tryGetContext('region') ||
  process.env.CDK_DEFAULT_REGION ||
  'us-east-1';

// ── ECS Fargate deployment (single ALB, SQLite) ───────────────────────────
new ReleaseDoctorStack(app, 'ReleaseDoctorStack', {
  env: { account, region },
  description:
    'Release Doctor - multi-agent release-readiness analysis on ECS Fargate',
});

app.synth();
