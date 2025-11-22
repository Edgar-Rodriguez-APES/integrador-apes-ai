#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SiesaIntegrationStack } from './stacks/siesa-integration-stack';

const app = new cdk.App();

// Get environment configuration
const account = process.env.CDK_DEFAULT_ACCOUNT || '224874703567';
const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';
const environment = process.env.ENVIRONMENT || 'dev';

// Create the main integration stack
new SiesaIntegrationStack(app, `SiesaIntegrationStack-${environment}`, {
  env: {
    account,
    region,
  },
  environment,
  description: 'Siesa ERP Integration Service - Multi-tenant, Multi-product (Kong RFID & WMS)',
  tags: {
    Project: 'SiesaIntegration',
    Environment: environment,
    Owner: 'APES-Team',
    CostCenter: 'Integration',
    Purpose: 'ERP-Integration'
  }
});

app.synth();
