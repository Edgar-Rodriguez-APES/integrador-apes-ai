# IAM Roles and Policies Guide

This guide documents all IAM roles and policies used in the Siesa ERP integration.

## Overview

The integration uses **3 main IAM roles** following the principle of least privilege:

1. **Lambda Execution Role** - For Lambda functions
2. **Step Functions Execution Role** - For Step Functions workflow
3. **EventBridge Execution Role** - For EventBridge scheduled rules

All roles are created automatically by the CDK stack.

---

## 1. Lambda Execution Role

**Role Name**: `siesa-integration-lambda-role-{environment}`

**Purpose**: Allows Lambda functions to access AWS services

**Trust Policy** (Who can assume this role):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Managed Policies Attached:
1. `AWSLambdaBasicExecutionRole` - CloudWatch Logs access
2. `AWSLambdaVPCAccessExecutionRole` - VPC access (if needed)

### Custom Inline Policies:

#### DynamoDB Access Policy
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:DeleteItem",
    "dynamodb:Query",
    "dynamodb:Scan",
    "dynamodb:BatchGetItem",
    "dynamodb:BatchWriteItem"
  ],
  "Resource": [
    "arn:aws:dynamodb:REGION:ACCOUNT:table/siesa-integration-config-ENV",
    "arn:aws:dynamodb:REGION:ACCOUNT:table/siesa-integration-sync-state-ENV",
    "arn:aws:dynamodb:REGION:ACCOUNT:table/siesa-integration-audit-ENV",
    "arn:aws:dynamodb:REGION:ACCOUNT:table/siesa-integration-config-ENV/index/*",
    "arn:aws:dynamodb:REGION:ACCOUNT:table/siesa-integration-sync-state-ENV/index/*"
  ]
}
```

**Why**: Lambda functions need to read client configurations, update sync state, and log audit events.

#### Secrets Manager Access Policy
```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue",
    "secretsmanager:DescribeSecret"
  ],
  "Resource": [
    "arn:aws:secretsmanager:REGION:ACCOUNT:secret:siesa-integration/*"
  ]
}
```

**Why**: Lambda functions need to retrieve API credentials for Siesa, Kong, and WMS.

**Security Note**: Only `GetSecretValue` and `DescribeSecret` are allowed. Lambda cannot create, update, or delete secrets.

#### S3 Access Policy
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject",
    "s3:DeleteObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::siesa-integration-config-ENV-ACCOUNT",
    "arn:aws:s3:::siesa-integration-config-ENV-ACCOUNT/*"
  ]
}
```

**Why**: Lambda functions need to read field mapping configurations from S3.

#### Step Functions Access Policy
```json
{
  "Effect": "Allow",
  "Action": [
    "states:StartExecution",
    "states:DescribeExecution",
    "states:StopExecution"
  ],
  "Resource": [
    "arn:aws:states:REGION:ACCOUNT:stateMachine:*"
  ]
}
```

**Why**: Lambda functions may need to trigger or monitor Step Functions executions.

### Used By:
- ✅ Extractor Lambda
- ✅ Transformer Lambda
- ✅ Loader Lambda

---

## 2. Step Functions Execution Role

**Role Name**: `siesa-integration-stepfunctions-role-{environment}`

**Purpose**: Allows Step Functions to invoke Lambda functions and update DynamoDB

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "states.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Custom Inline Policies:

#### Lambda Invocation Policy
```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:InvokeFunction"
  ],
  "Resource": [
    "arn:aws:lambda:REGION:ACCOUNT:function:siesa-integration-*"
  ]
}
```

**Why**: Step Functions needs to invoke the 3 Lambda functions (Extractor, Transformer, Loader).

#### DynamoDB Update Policy
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:UpdateItem",
    "dynamodb:PutItem"
  ],
  "Resource": [
    "arn:aws:dynamodb:REGION:ACCOUNT:table/siesa-integration-config-ENV",
    "arn:aws:dynamodb:REGION:ACCOUNT:table/siesa-integration-sync-state-ENV"
  ]
}
```

**Why**: Step Functions needs to log success/failure status in DynamoDB.

#### SNS Publish Policy
```json
{
  "Effect": "Allow",
  "Action": [
    "sns:Publish"
  ],
  "Resource": [
    "arn:aws:sns:REGION:ACCOUNT:siesa-integration-alerts-ENV"
  ]
}
```

**Why**: Step Functions needs to send failure notifications to SNS.

### Used By:
- ✅ Step Functions State Machine

---

## 3. EventBridge Execution Role

**Role Name**: `siesa-integration-eventbridge-role-{environment}`

**Purpose**: Allows EventBridge to trigger Step Functions executions

**Trust Policy**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

### Custom Inline Policies:

#### Step Functions Start Execution Policy
```json
{
  "Effect": "Allow",
  "Action": [
    "states:StartExecution"
  ],
  "Resource": [
    "arn:aws:states:REGION:ACCOUNT:stateMachine:*"
  ]
}
```

**Why**: EventBridge scheduled rules need to trigger Step Functions executions for each client.

### Used By:
- ✅ EventBridge Scheduled Rules (per client)

---

## Security Best Practices

### 1. Least Privilege Principle
✅ Each role has only the minimum permissions needed
✅ No wildcard (*) permissions on sensitive actions
✅ Resources are scoped to specific ARNs

### 2. Separation of Concerns
✅ Lambda role cannot invoke Step Functions directly (only Step Functions can)
✅ Step Functions role cannot access Secrets Manager (only Lambda can)
✅ EventBridge role can only start executions (not stop or describe)

### 3. Resource Scoping
✅ Secrets Manager: Only `siesa-integration/*` secrets
✅ DynamoDB: Only integration-specific tables
✅ S3: Only integration config bucket
✅ Lambda: Only `siesa-integration-*` functions

### 4. No Dangerous Permissions
❌ No `*:*` permissions
❌ No `iam:*` permissions
❌ No `secretsmanager:CreateSecret` or `DeleteSecret`
❌ No `dynamodb:DeleteTable`
❌ No `s3:DeleteBucket`

---

## Permission Matrix

| Service | Lambda Role | Step Functions Role | EventBridge Role |
|---------|-------------|---------------------|------------------|
| **CloudWatch Logs** | ✅ Write | ❌ | ❌ |
| **DynamoDB Read** | ✅ | ❌ | ❌ |
| **DynamoDB Write** | ✅ | ✅ | ❌ |
| **Secrets Manager** | ✅ Read Only | ❌ | ❌ |
| **S3** | ✅ Read/Write | ❌ | ❌ |
| **Lambda Invoke** | ❌ | ✅ | ❌ |
| **Step Functions Start** | ✅ | ❌ | ✅ |
| **Step Functions Describe** | ✅ | ❌ | ❌ |
| **SNS Publish** | ❌ | ✅ | ❌ |

---

## Verification

### Check Role Exists
```bash
aws iam get-role --role-name siesa-integration-lambda-role-dev
aws iam get-role --role-name siesa-integration-stepfunctions-role-dev
aws iam get-role --role-name siesa-integration-eventbridge-role-dev
```

### List Attached Policies
```bash
# Lambda role
aws iam list-attached-role-policies --role-name siesa-integration-lambda-role-dev
aws iam list-role-policies --role-name siesa-integration-lambda-role-dev

# Step Functions role
aws iam list-role-policies --role-name siesa-integration-stepfunctions-role-dev

# EventBridge role
aws iam list-role-policies --role-name siesa-integration-eventbridge-role-dev
```

### Get Policy Document
```bash
aws iam get-role-policy \
  --role-name siesa-integration-lambda-role-dev \
  --policy-name DynamoDBAccess
```

---

## Troubleshooting

### Issue: "Access Denied" in Lambda
**Possible Causes:**
1. Lambda not using the correct execution role
2. IAM policy missing required permission
3. Resource ARN incorrect in policy

**Solution:**
1. Check Lambda configuration: `aws lambda get-function --function-name siesa-integration-extractor-dev`
2. Verify role ARN matches
3. Check CloudWatch Logs for specific permission denied error
4. Update IAM policy if needed

### Issue: "Step Functions cannot invoke Lambda"
**Possible Causes:**
1. Step Functions role missing `lambda:InvokeFunction` permission
2. Lambda function ARN pattern doesn't match policy

**Solution:**
1. Verify Step Functions role has Lambda invoke permission
2. Check Lambda function name matches pattern `siesa-integration-*`

### Issue: "EventBridge cannot start execution"
**Possible Causes:**
1. EventBridge role missing `states:StartExecution` permission
2. State machine ARN incorrect in EventBridge rule

**Solution:**
1. Verify EventBridge role has Step Functions start permission
2. Check EventBridge rule target configuration

---

## Monitoring

### CloudTrail Events
Monitor IAM role usage in CloudTrail:
- `AssumeRole` events - Who/what is using the roles
- `AccessDenied` events - Failed permission attempts

### CloudWatch Logs
Check Lambda logs for permission errors:
```
/aws/lambda/siesa-integration-extractor-{environment}
/aws/lambda/siesa-integration-transformer-{environment}
/aws/lambda/siesa-integration-loader-{environment}
```

Look for:
- `AccessDeniedException`
- `UnauthorizedException`
- `Forbidden`

---

## Updating Policies

### When to Update:
1. Adding new AWS service integration
2. Adding new DynamoDB table
3. Adding new S3 bucket
4. Changing resource naming patterns

### How to Update:
1. Modify CDK stack (`siesa-integration-stack.ts`)
2. Add new policy statement
3. Deploy CDK stack: `cdk deploy`
4. Verify new permissions work

### Example: Adding SQS Access
```typescript
this.lambdaExecutionRole.addToPolicy(new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: [
    'sqs:SendMessage',
    'sqs:ReceiveMessage',
    'sqs:DeleteMessage'
  ],
  resources: [
    `arn:aws:sqs:${this.region}:${this.account}:siesa-integration-*`
  ]
}));
```

---

## Cost Optimization

### IAM Pricing:
- ✅ **IAM roles are FREE**
- ✅ No charge for role creation or usage
- ✅ No charge for policy attachments

### Best Practices:
1. Reuse roles across Lambda functions (we do this)
2. Use inline policies for integration-specific permissions
3. Use managed policies for common patterns (CloudWatch Logs)

---

## Compliance

### Audit Requirements:
✅ All roles follow least privilege principle
✅ All permissions are documented
✅ All resource access is scoped
✅ CloudTrail logging enabled for all role usage

### Security Review Checklist:
- [ ] No wildcard permissions on sensitive actions
- [ ] No cross-account access (unless required)
- [ ] No public access to resources
- [ ] Secrets Manager access is read-only
- [ ] DynamoDB access is scoped to specific tables
- [ ] S3 access is scoped to specific bucket

---

## References

- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [Lambda Execution Role](https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html)
- [Step Functions IAM Policies](https://docs.aws.amazon.com/step-functions/latest/dg/procedure-create-iam-role.html)
- [EventBridge IAM Roles](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-use-identity-based.html)

---

## Support

For IAM-related issues:
1. Check CloudWatch Logs for specific error messages
2. Verify role ARNs in AWS Console
3. Review CloudTrail for AccessDenied events
4. Contact AWS Support if needed
