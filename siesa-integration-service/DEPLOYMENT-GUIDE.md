# Deployment Guide - Siesa Integration Service

## Task 1 Completed: AWS Infrastructure Foundation ✅

### What Was Implemented

#### 1. Project Structure
```
siesa-integration-service/
├── src/
│   └── infrastructure/
│       ├── app.ts                          # CDK app entry point
│       └── stacks/
│           └── siesa-integration-stack.ts  # Main infrastructure stack
├── package.json                            # Dependencies and scripts
├── tsconfig.json                           # TypeScript configuration
├── cdk.json                                # CDK configuration
├── jest.config.js                          # Test configuration
├── .eslintrc.json                          # Linting rules
├── .gitignore                              # Git ignore rules
└── README.md                               # Project documentation
```

#### 2. AWS Resources Created (via CDK)

**DynamoDB Tables:**
- ✅ `siesa-integration-config-{env}` - Tenant configurations
  - Partition Key: `tenantId`
  - Sort Key: `configType`
  - GSI: `ProductTypeIndex` (productType, tenantId)
  - GSI: `EnabledIndex` (enabled, tenantId)
  - Encryption: AWS Managed
  - Point-in-time recovery: Enabled
  
- ✅ `siesa-integration-sync-state-{env}` - Sync status tracking
  - Partition Key: `tenantId`
  - Sort Key: `syncId`
  - GSI: `StatusIndex` (status, createdAt)
  - TTL: Enabled
  
- ✅ `siesa-integration-audit-{env}` - Audit trail
  - Partition Key: `tenantId`
  - Sort Key: `timestamp`
  - TTL: Enabled

**S3 Bucket:**
- ✅ `siesa-integration-config-{env}-{account}` - Configuration files
  - Versioning: Enabled
  - Encryption: S3 Managed
  - Public access: Blocked
  - Lifecycle: Delete old versions after 30 days

**Secrets Manager:**
- ✅ Template secrets created for:
  - Siesa credentials (`siesa-integration/template/siesa-{env}`)
  - Kong credentials (`siesa-integration/template/kong-{env}`)

**IAM Roles:**
- ✅ Lambda Execution Role
  - DynamoDB permissions (GetItem, PutItem, UpdateItem, Query, Scan)
  - Secrets Manager permissions (GetSecretValue)
  - S3 permissions (GetObject, PutObject, ListBucket)
  - Step Functions permissions (StartExecution)
  - CloudWatch Logs permissions
  
- ✅ Step Functions Execution Role
  - Lambda invocation permissions
  - DynamoDB update permissions
  - SNS publish permissions
  
- ✅ EventBridge Execution Role
  - Step Functions start execution permissions

**CloudWatch:**
- ✅ Log Groups:
  - `/aws/lambda/siesa-integration-{env}`
  - `/aws/stepfunctions/siesa-integration-{env}`
  - Retention: 30 days (prod), 7 days (dev)

**SNS:**
- ✅ Alert Topic: `siesa-integration-alerts-{env}`
  - For failure notifications
  - Email subscriptions can be added manually

#### 3. Stack Outputs

The stack exports the following values:
- ConfigTableName
- SyncStateTableName
- AuditTableName
- ConfigBucketName
- AlertTopicArn
- LambdaExecutionRoleArn
- StepFunctionsRoleArn
- EventBridgeRoleArn

### Deployment Instructions

#### Prerequisites

1. **AWS CLI configured** with access to account **224874703567**:
```bash
aws configure --profile apes-principal
# AWS Access Key ID: [YOUR_KEY]
# AWS Secret Access Key: [YOUR_SECRET]
# Default region name: us-east-1
# Default output format: json
```

2. **Verify access**:
```bash
aws sts get-caller-identity --profile apes-principal
# Should show Account: 224874703567
```

3. **Install dependencies**:
```bash
cd siesa-integration-service
npm install
```

#### Bootstrap CDK (First Time Only)

```bash
# Bootstrap CDK in account 224874703567
export AWS_PROFILE=apes-principal
export CDK_DEFAULT_ACCOUNT=224874703567
export CDK_DEFAULT_REGION=us-east-1

cdk bootstrap aws://224874703567/us-east-1
```

#### Deploy to Development

```bash
cd siesa-integration-service
export AWS_PROFILE=apes-principal
export ENVIRONMENT=dev

# Build TypeScript
npm run build

# Synthesize CloudFormation template (optional - to review)
npm run synth

# Deploy
npm run deploy
```

Expected output:
```
✅  SiesaIntegrationStack-dev

Outputs:
SiesaIntegrationStack-dev.ConfigTableName = siesa-integration-config-dev
SiesaIntegrationStack-dev.SyncStateTableName = siesa-integration-sync-state-dev
SiesaIntegrationStack-dev.AuditTableName = siesa-integration-audit-dev
SiesaIntegrationStack-dev.ConfigBucketName = siesa-integration-config-dev-224874703567
SiesaIntegrationStack-dev.AlertTopicArn = arn:aws:sns:us-east-1:224874703567:siesa-integration-alerts-dev
...
```

#### Verify Deployment

```bash
# Check DynamoDB tables
aws dynamodb list-tables --profile apes-principal | grep siesa-integration

# Check S3 bucket
aws s3 ls --profile apes-principal | grep siesa-integration

# Check Secrets Manager
aws secretsmanager list-secrets --profile apes-principal | grep siesa-integration

# Check IAM roles
aws iam list-roles --profile apes-principal | grep siesa-integration

# Check SNS topics
aws sns list-topics --profile apes-principal | grep siesa-integration
```

### Post-Deployment Configuration

#### 1. Upload Field Mappings to S3

Create Kong field mappings file:

```bash
# Create field-mappings-kong.json locally
cat > field-mappings-kong.json << 'EOF'
{
  "version": "1.0",
  "product_type": "kong",
  "mappings": {
    "product": {
      "id": {
        "siesa_field": "f120_id",
        "product_field": "external_id",
        "type": "string",
        "required": true
      },
      "name": {
        "siesa_field": "f120_descripcion",
        "product_field": "name",
        "type": "string",
        "required": true
      },
      "ean": {
        "siesa_field": "f120_codigo_barras",
        "product_field": "ean",
        "type": "string",
        "required": false
      },
      "sku": {
        "siesa_field": "f120_referencia",
        "product_field": "reference",
        "type": "string",
        "required": true
      }
    }
  }
}
EOF

# Upload to S3
aws s3 cp field-mappings-kong.json \
  s3://siesa-integration-config-dev-224874703567/field-mappings-kong.json \
  --profile apes-principal
```

#### 2. Create Tenant Configuration in DynamoDB

Example for Parchita staging (Kong):

```bash
# Create tenant config JSON
cat > parchita-staging-config.json << 'EOF'
{
  "tenantId": {"S": "parchita-staging"},
  "configType": {"S": "PRODUCT_CONFIG"},
  "productType": {"S": "KONG_RFID"},
  "enabled": {"S": "true"},
  "clientAccount": {"S": "555569220783"},
  "siesaConfig": {
    "M": {
      "baseUrl": {"S": "https://serviciosqa.siesacloud.com/api/siesa/v3/"},
      "credentialsSecretArn": {"S": "arn:aws:secretsmanager:us-east-1:224874703567:secret:siesa-integration/parchita-staging/siesa"}
    }
  },
  "productConfig": {
    "M": {
      "baseUrl": {"S": "https://api-staging.technoapes.io/"},
      "credentialsSecretArn": {"S": "arn:aws:secretsmanager:us-east-1:224874703567:secret:siesa-integration/parchita-staging/kong"}
    }
  },
  "syncConfig": {
    "M": {
      "schedule": {"S": "rate(1 hour)"},
      "batchSize": {"N": "100"},
      "retryAttempts": {"N": "3"}
    }
  },
  "fieldMappingsKey": {"S": "field-mappings-kong.json"},
  "createdAt": {"S": "2025-01-21T00:00:00Z"},
  "updatedAt": {"S": "2025-01-21T00:00:00Z"}
}
EOF

# Put item in DynamoDB
aws dynamodb put-item \
  --table-name siesa-integration-config-dev \
  --item file://parchita-staging-config.json \
  --profile apes-principal
```

#### 3. Store Credentials in Secrets Manager

**Siesa credentials:**
```bash
aws secretsmanager create-secret \
  --name siesa-integration/parchita-staging/siesa \
  --description "Siesa API credentials for Parchita staging" \
  --secret-string '{
    "baseUrl": "https://serviciosqa.siesacloud.com/api/siesa/v3/",
    "username": "REPLACE_WITH_ACTUAL_USERNAME",
    "password": "REPLACE_WITH_ACTUAL_PASSWORD",
    "conniKey": "REPLACE_WITH_ACTUAL_CONNI_KEY",
    "conniToken": "REPLACE_WITH_ACTUAL_CONNI_TOKEN"
  }' \
  --profile apes-principal
```

**Kong credentials:**
```bash
aws secretsmanager create-secret \
  --name siesa-integration/parchita-staging/kong \
  --description "Kong API credentials for Parchita staging" \
  --secret-string '{
    "productType": "kong",
    "baseUrl": "https://api-staging.technoapes.io/",
    "username": "REPLACE_WITH_ACTUAL_USERNAME",
    "password": "REPLACE_WITH_ACTUAL_PASSWORD"
  }' \
  --profile apes-principal
```

### Troubleshooting

#### Issue: CDK Bootstrap fails

**Error**: `Need to perform AWS calls for account 224874703567, but no credentials found`

**Solution**:
```bash
# Ensure AWS profile is set
export AWS_PROFILE=apes-principal

# Verify credentials
aws sts get-caller-identity --profile apes-principal
```

#### Issue: Deployment fails with permissions error

**Error**: `User is not authorized to perform: cloudformation:CreateStack`

**Solution**: Ensure your IAM user/role has permissions:
- `cloudformation:*`
- `iam:*`
- `dynamodb:*`
- `s3:*`
- `secretsmanager:*`
- `sns:*`
- `logs:*`

#### Issue: Stack already exists

**Error**: `Stack [SiesaIntegrationStack-dev] already exists`

**Solution**:
```bash
# Update existing stack
npm run deploy

# Or destroy and recreate
npm run destroy
npm run deploy
```

### Next Steps

✅ **Task 1 Complete**: AWS Infrastructure Foundation

**Task 2**: Implement Lambda Functions
- Extractor Lambda (Siesa API client)
- Transformer Lambda (Field mappings)
- Loader Lambda (Kong adapter)

**Task 3**: Create Step Functions Workflow
- Define state machine
- Configure error handling
- Set up retry logic

**Task 4**: Testing
- Unit tests for infrastructure
- Integration tests with AWS services

### Cost Estimation

**Monthly cost for dev environment** (minimal usage):
- DynamoDB: ~$1 (on-demand, minimal reads/writes)
- S3: ~$0.50 (minimal storage)
- Secrets Manager: ~$1 (2 secrets)
- CloudWatch Logs: ~$1 (minimal logs)
- SNS: ~$0.10 (minimal notifications)

**Total**: ~$3.60/month for dev environment

**Note**: Lambda, Step Functions costs will be added in Task 2-3.

### Support

For issues or questions:
1. Check CloudWatch Logs
2. Review CDK synthesis output: `npm run synth`
3. Check AWS Console for resource status
4. Contact APES Integration Team

---

**Deployment Date**: 2025-01-21  
**Deployed By**: Kiro AI Agent  
**Environment**: Development  
**AWS Account**: 224874703567  
**Region**: us-east-1
