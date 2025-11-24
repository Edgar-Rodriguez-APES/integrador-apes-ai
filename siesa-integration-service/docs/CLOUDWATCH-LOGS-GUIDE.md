# CloudWatch Logs Configuration Guide

## Overview

This guide explains the CloudWatch Logs configuration for the Siesa Integration service, including log groups, retention policies, encryption, and monitoring.

## Log Groups Structure

### Lambda Functions

| Log Group | Function | Retention |
|-----------|----------|-----------|
| `/aws/lambda/siesa-integration-extractor-{env}` | Extractor Lambda | 30 days (prod), 7 days (test/dev) |
| `/aws/lambda/siesa-integration-transformer-{env}` | Transformer Lambda | 30 days (prod), 7 days (test/dev) |
| `/aws/lambda/siesa-integration-loader-{env}` | Loader Lambda | 30 days (prod), 7 days (test/dev) |

### Step Functions

| Log Group | Purpose | Retention |
|-----------|---------|-----------|
| `/aws/stepfunctions/siesa-integration-workflow-{env}` | Workflow orchestration logs | 30 days (prod), 7 days (test/dev) |

### API Gateway (Future)

| Log Group | Purpose | Retention |
|-----------|---------|-----------|
| `/aws/apigateway/siesa-integration-{env}` | API Gateway access logs | 30 days (prod), 7 days (test/dev) |

## Encryption

### KMS Key

All log groups are encrypted using a dedicated KMS key:

- **Key Alias**: `alias/siesa-integration-logs-{environment}`
- **Key Rotation**: Enabled (automatic annual rotation)
- **Key Policy**: Allows CloudWatch Logs service to encrypt/decrypt logs

### Benefits

- **Data at Rest Encryption**: All logs are encrypted when stored
- **Compliance**: Meets security and compliance requirements
- **Access Control**: Fine-grained access control via KMS key policies

## Retention Policies

### Production Environment

- **Retention Period**: 30 days
- **Rationale**: Balance between compliance requirements and cost optimization
- **Cost**: ~$0.03 per GB per month

### Test/Dev Environments

- **Retention Period**: 7 days
- **Rationale**: Sufficient for debugging and troubleshooting
- **Cost**: Minimal (~$0.007 per GB per month)

## Log Format

### Structured Logging

All Lambda functions use structured JSON logging:

```json
{
  "timestamp": "2025-11-23T10:00:00.000Z",
  "level": "INFO",
  "client_id": "cliente-a",
  "product_type": "kong",
  "component": "extractor",
  "message": "Starting data extraction",
  "metadata": {
    "sync_type": "incremental",
    "last_sync": "2025-11-23T04:00:00.000Z"
  }
}
```

### Log Levels

- **ERROR**: Failures requiring immediate attention
- **WARN**: Validation errors, retries, non-critical issues
- **INFO**: Sync start/end, record counts, status updates
- **DEBUG**: Detailed API calls, data transformations (test only)

## Deployment

### Option 1: Using CDK

```bash
cd siesa-integration-service
npm install
cdk deploy --profile principal --context environment=dev
```

The CDK stack automatically creates:
- KMS key for encryption
- All log groups with proper retention
- IAM permissions for CloudWatch Logs

### Option 2: Using PowerShell Script

```powershell
cd siesa-integration-service/scripts
./create-cloudwatch-logs.ps1 -Environment dev -Region us-east-1 -Profile principal
```

The script will:
1. Create KMS key (if not exists)
2. Create all log groups
3. Configure retention policies
4. Add tags
5. Enable encryption

### Option 3: Manual Creation (AWS CLI)

```bash
# Create KMS key
aws kms create-key \
  --description "Siesa Integration CloudWatch Logs encryption" \
  --region us-east-1 \
  --profile principal

# Create log group
aws logs create-log-group \
  --log-group-name /aws/lambda/siesa-integration-extractor-dev \
  --kms-key-id <key-id> \
  --region us-east-1 \
  --profile principal

# Set retention
aws logs put-retention-policy \
  --log-group-name /aws/lambda/siesa-integration-extractor-dev \
  --retention-in-days 7 \
  --region us-east-1 \
  --profile principal
```

## Monitoring and Querying

### CloudWatch Logs Insights

#### Query 1: Error Rate by Client

```sql
fields @timestamp, client_id, @message
| filter level = "ERROR"
| stats count() by client_id
| sort count desc
```

#### Query 2: Sync Duration by Client

```sql
fields @timestamp, client_id, duration_seconds
| filter component = "loader" and message like /Load completed/
| stats avg(duration_seconds), max(duration_seconds) by client_id
```

#### Query 3: Failed Records

```sql
fields @timestamp, client_id, product_type, records_failed
| filter records_failed > 0
| sort @timestamp desc
```

#### Query 4: API Errors

```sql
fields @timestamp, client_id, @message
| filter @message like /API error/ or @message like /HTTP error/
| stats count() by client_id, product_type
```

### CloudWatch Metrics

Custom metrics published to CloudWatch:

- `SyncDuration`: Time taken for sync (seconds)
- `RecordsProcessed`: Number of records processed
- `RecordsFailed`: Number of failed records
- `APILatency`: API call latency (milliseconds)

Dimensions:
- `ClientId`: Tenant identifier
- `ProductType`: kong or wms
- `Environment`: dev, test, prod

### CloudWatch Alarms

Recommended alarms:

1. **High Error Rate**
   - Metric: Errors
   - Threshold: > 5 errors in 5 minutes
   - Action: SNS notification

2. **Long Sync Duration**
   - Metric: SyncDuration
   - Threshold: > 1800 seconds (30 minutes)
   - Action: SNS notification

3. **High Failed Records**
   - Metric: RecordsFailed
   - Threshold: > 5% of total records
   - Action: SNS notification

## Viewing Logs

### AWS Console

1. Navigate to CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
2. Select log group (e.g., `/aws/lambda/siesa-integration-extractor-dev`)
3. View log streams (one per Lambda invocation)
4. Use filter patterns to search logs

### AWS CLI

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/siesa-integration-extractor-dev \
  --follow \
  --region us-east-1 \
  --profile principal

# Get recent logs
aws logs tail /aws/lambda/siesa-integration-extractor-dev \
  --since 1h \
  --region us-east-1 \
  --profile principal

# Filter logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/siesa-integration-extractor-dev \
  --filter-pattern "ERROR" \
  --region us-east-1 \
  --profile principal
```

### CloudWatch Logs Insights

```bash
# Run query
aws logs start-query \
  --log-group-name /aws/lambda/siesa-integration-extractor-dev \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter level = "ERROR"' \
  --region us-east-1 \
  --profile principal
```

## Cost Optimization

### Current Costs (Estimated)

**Production (30-day retention)**:
- Ingestion: $0.50 per GB
- Storage: $0.03 per GB per month
- Insights queries: $0.005 per GB scanned

**Example**: 10 GB/month
- Ingestion: $5.00
- Storage: $0.30
- Total: ~$5.30/month

**Test/Dev (7-day retention)**:
- Ingestion: $0.50 per GB
- Storage: $0.007 per GB per month
- Total: ~$0.50/month per GB

### Optimization Tips

1. **Use appropriate log levels**
   - Production: INFO and above
   - Test: DEBUG for troubleshooting only

2. **Filter logs before ingestion**
   - Use Lambda environment variables to control verbosity
   - Avoid logging sensitive data

3. **Archive old logs to S3**
   - Export logs older than retention period to S3
   - Use S3 Glacier for long-term archival

4. **Use log sampling**
   - Sample DEBUG logs (e.g., 10% of requests)
   - Always log ERROR and WARN

## Security Best Practices

### 1. Encryption

- ✅ All logs encrypted with KMS
- ✅ Key rotation enabled
- ✅ Separate keys per environment

### 2. Access Control

- ✅ IAM policies restrict log access
- ✅ KMS key policies control encryption access
- ✅ CloudTrail logs all access attempts

### 3. Data Sanitization

- ✅ No credentials in logs
- ✅ PII data sanitized
- ✅ Sensitive fields masked

### 4. Audit Trail

- ✅ CloudTrail logs all log group changes
- ✅ Log group modifications require approval
- ✅ Regular access reviews

## Troubleshooting

### Issue: Logs not appearing

**Possible causes**:
1. Lambda execution role lacks CloudWatch Logs permissions
2. Log group doesn't exist
3. KMS key policy doesn't allow CloudWatch Logs

**Solution**:
```bash
# Check IAM permissions
aws iam get-role-policy \
  --role-name siesa-integration-lambda-role-dev \
  --policy-name CloudWatchLogsPolicy

# Verify log group exists
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/siesa-integration

# Check KMS key policy
aws kms get-key-policy \
  --key-id alias/siesa-integration-logs-dev \
  --policy-name default
```

### Issue: High costs

**Possible causes**:
1. Too much DEBUG logging in production
2. Long retention periods
3. Frequent Insights queries

**Solution**:
1. Reduce log level to INFO in production
2. Adjust retention periods
3. Use log sampling
4. Archive old logs to S3

### Issue: Cannot decrypt logs

**Possible causes**:
1. KMS key policy doesn't grant access
2. IAM role lacks kms:Decrypt permission

**Solution**:
```bash
# Grant IAM role access to KMS key
aws kms create-grant \
  --key-id alias/siesa-integration-logs-dev \
  --grantee-principal arn:aws:iam::ACCOUNT:role/siesa-integration-lambda-role-dev \
  --operations Decrypt DescribeKey
```

## References

- [CloudWatch Logs Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)
- [CloudWatch Logs Insights Query Syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [KMS Key Policies](https://docs.aws.amazon.com/kms/latest/developerguide/key-policies.html)
- [Lambda Logging Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/python-logging.html)

## Support

For issues or questions:
- Create an issue in the repository
- Contact the APES DevOps team
- Check CloudWatch Logs console for error details
