# Step Functions State Machine Guide

## Overview

This document describes the Step Functions state machine that orchestrates the Siesa ERP integration workflow. The state machine coordinates the Extract → Transform → Load (ETL) process for synchronizing data from Siesa ERP to product platforms (Kong/WMS).

## State Machine Architecture

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  Siesa Integration Workflow                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │ ExtractFromSiesa │
                  │  (Lambda Task)   │
                  └──────────────────┘
                            │
                    ┌───────┴───────┐
                    │   Success     │
                    └───────┬───────┘
                            ▼
                  ┌──────────────────┐
                  │  TransformData   │
                  │  (Lambda Task)   │
                  └──────────────────┘
                            │
                    ┌───────┴───────┐
                    │   Success     │
                    └───────┬───────┘
                            ▼
                  ┌──────────────────┐
                  │  LoadToProduct   │
                  │  (Lambda Task)   │
                  └──────────────────┘
                            │
                    ┌───────┴───────┐
                    │   Success     │
                    └───────┬───────┘
                            ▼
                  ┌──────────────────┐
                  │   LogSuccess     │
                  │ (DynamoDB Task)  │
                  └──────────────────┘
                            │
                            ▼
                        [END]

         ┌──────────────────────────────────┐
         │  Error Handler (Any Step Fails)  │
         └──────────────────────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  NotifyFailure   │
                  │   (SNS Task)     │
                  └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │   LogFailure     │
                  │ (DynamoDB Task)  │
                  └──────────────────┘
                            │
                            ▼
                        [END]
```

## State Definitions

### 1. ExtractFromSiesa

**Type**: Lambda Task  
**Function**: `siesa-integration-extractor-{environment}`  
**Purpose**: Extracts product data from Siesa ERP API

**Input**:
```json
{
  "client_id": "cliente-a",
  "sync_type": "incremental"
}
```

**Output**:
```json
{
  "client_id": "cliente-a",
  "product_type": "kong",
  "products": [...],
  "count": 1250,
  "extraction_timestamp": "2025-01-15T10:00:00Z"
}
```

**Retry Configuration**:
- Errors: `States.TaskFailed`, `States.Timeout`
- Max Attempts: 3
- Interval: 2 seconds
- Backoff Rate: 2.0

**Error Handling**: On failure, transitions to `NotifyFailure`

### 2. TransformData

**Type**: Lambda Task  
**Function**: `siesa-integration-transformer-{environment}`  
**Purpose**: Transforms Siesa data to canonical model

**Input**: Output from ExtractFromSiesa

**Output**:
```json
{
  "client_id": "cliente-a",
  "product_type": "kong",
  "canonical_products": [...],
  "count": 1250,
  "transformation_timestamp": "2025-01-15T10:01:00Z",
  "validation_errors": []
}
```

**Retry Configuration**: Same as ExtractFromSiesa

**Error Handling**: On failure, transitions to `NotifyFailure`

### 3. LoadToProduct

**Type**: Lambda Task  
**Function**: `siesa-integration-loader-{environment}`  
**Purpose**: Loads transformed data to product API (Kong or WMS)

**Input**: Output from TransformData

**Output**:
```json
{
  "client_id": "cliente-a",
  "product_type": "kong",
  "status": "success",
  "records_processed": 1250,
  "records_success": 1248,
  "records_failed": 2,
  "failed_records": [...],
  "load_timestamp": "2025-01-15T10:05:00Z",
  "duration_seconds": 240,
  "sync_id": "sync-20250115-100000"
}
```

**Retry Configuration**: Same as ExtractFromSiesa

**Error Handling**: On failure, transitions to `NotifyFailure`

### 4. LogSuccess

**Type**: DynamoDB PutItem Task  
**Table**: `siesa-integration-sync-state-{environment}`  
**Purpose**: Records successful sync execution

**Item Structure**:
```json
{
  "tenantId": "cliente-a",
  "syncId": "sync-20250115-100000",
  "status": "success",
  "timestamp": "2025-01-15T10:05:00Z",
  "recordsProcessed": 1248,
  "productType": "kong"
}
```

### 5. NotifyFailure

**Type**: SNS Publish Task  
**Topic**: `siesa-integration-alerts-{environment}`  
**Purpose**: Sends failure notification to operations team

**Message**:
```json
{
  "client_id": "cliente-a",
  "product_type": "kong",
  "error": {
    "Error": "States.TaskFailed",
    "Cause": "..."
  },
  "timestamp": "2025-01-15T10:05:00Z"
}
```

### 6. LogFailure

**Type**: DynamoDB PutItem Task  
**Table**: `siesa-integration-sync-state-{environment}`  
**Purpose**: Records failed sync execution

**Item Structure**:
```json
{
  "tenantId": "cliente-a",
  "syncId": "sync-20250115-100000",
  "status": "failed",
  "timestamp": "2025-01-15T10:05:00Z",
  "error": "States.TaskFailed"
}
```

## Execution Patterns

### Manual Execution

Execute the state machine manually for testing or one-time syncs:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:224874703567:stateMachine:siesa-integration-workflow-prod \
  --input '{"client_id": "cliente-a", "sync_type": "initial"}' \
  --name "manual-sync-$(date +%s)" \
  --profile principal
```

### Scheduled Execution (EventBridge)

Create an EventBridge rule for automatic scheduled syncs:

```bash
# Create the rule
aws events put-rule \
  --name siesa-integration-cliente-a-schedule \
  --schedule-expression "rate(6 hours)" \
  --state ENABLED \
  --profile principal

# Add the state machine as target
aws events put-targets \
  --rule siesa-integration-cliente-a-schedule \
  --targets '[
    {
      "Id": "1",
      "Arn": "arn:aws:states:us-east-1:224874703567:stateMachine:siesa-integration-workflow-prod",
      "RoleArn": "arn:aws:iam::224874703567:role/siesa-integration-eventbridge-role-prod",
      "Input": "{\"client_id\": \"cliente-a\", \"sync_type\": \"incremental\"}"
    }
  ]' \
  --profile principal
```

### Sync Types

**Initial Sync** (`sync_type: "initial"`):
- Extracts all products from Siesa
- Used for first-time data migration
- May take longer (up to 2 hours for 10,000 products)

**Incremental Sync** (`sync_type: "incremental"`):
- Extracts only products modified since last sync
- Used for regular scheduled syncs
- Faster execution (typically < 15 minutes)

## Monitoring and Observability

### CloudWatch Logs

All state machine executions are logged to:
```
/aws/stepfunctions/siesa-integration-workflow-{environment}
```

Log level: `ALL` (includes execution data)

### Execution History

View execution history in AWS Console:
```
https://us-east-1.console.aws.amazon.com/states/home?region=us-east-1#/statemachines/view/arn:aws:states:us-east-1:224874703567:stateMachine:siesa-integration-workflow-prod
```

### Metrics

Key CloudWatch metrics:
- `ExecutionsFailed`: Number of failed executions
- `ExecutionsSucceeded`: Number of successful executions
- `ExecutionTime`: Duration of executions
- `ExecutionsStarted`: Total executions started

### Alarms

Recommended CloudWatch alarms:
1. **High Failure Rate**: `ExecutionsFailed > 0` in 5 minutes
2. **Long Execution Time**: `ExecutionTime > 7200 seconds` (2 hours)
3. **No Executions**: `ExecutionsStarted == 0` in 24 hours (for scheduled syncs)

## Error Handling

### Retry Strategy

All Lambda tasks implement automatic retry with exponential backoff:
- **Max Attempts**: 3
- **Initial Interval**: 2 seconds
- **Backoff Rate**: 2.0 (doubles each retry)
- **Total Max Time**: ~14 seconds (2 + 4 + 8)

### Error Types

**Transient Errors** (Retried):
- `States.TaskFailed`: Lambda execution failed
- `States.Timeout`: Lambda timeout exceeded
- Network errors
- API rate limiting (429)

**Permanent Errors** (Not Retried):
- Invalid input data
- Authentication failures (401)
- Authorization failures (403)
- Resource not found (404)

### Failure Notifications

When an execution fails after all retries:
1. SNS notification sent to `siesa-integration-alerts-{environment}`
2. Failure logged to DynamoDB `sync-state` table
3. CloudWatch alarm triggered (if configured)

## Troubleshooting

### Common Issues

#### 1. Execution Fails at ExtractFromSiesa

**Symptoms**: State machine fails immediately at first step

**Possible Causes**:
- Invalid Siesa credentials
- Siesa API unavailable
- Network connectivity issues
- Client not enabled in config table

**Resolution**:
1. Check CloudWatch logs for extractor Lambda
2. Verify Secrets Manager credentials
3. Test Siesa API connectivity manually
4. Verify client config in DynamoDB

#### 2. Execution Fails at TransformData

**Symptoms**: Extraction succeeds but transformation fails

**Possible Causes**:
- Invalid field mappings in S3
- Missing required fields in Siesa data
- Data type conversion errors

**Resolution**:
1. Check CloudWatch logs for transformer Lambda
2. Verify field mappings file in S3
3. Review validation errors in logs
4. Update field mappings if needed

#### 3. Execution Fails at LoadToProduct

**Symptoms**: Transformation succeeds but loading fails

**Possible Causes**:
- Invalid product API credentials
- Product API unavailable
- Rate limiting
- Data validation errors in product API

**Resolution**:
1. Check CloudWatch logs for loader Lambda
2. Verify product credentials in Secrets Manager
3. Test product API connectivity manually
4. Review failed records in output

#### 4. Execution Times Out

**Symptoms**: Execution exceeds 2-hour timeout

**Possible Causes**:
- Too many products to process
- Slow API responses
- Network latency

**Resolution**:
1. Check execution duration in Step Functions console
2. Review Lambda duration metrics
3. Consider splitting into smaller batches
4. Optimize API calls (increase batch size)

### Manual Retry

To retry a failed execution:

```bash
# Get the failed execution ARN
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:us-east-1:224874703567:stateMachine:siesa-integration-workflow-prod \
  --status-filter FAILED \
  --max-results 1 \
  --profile principal

# Start a new execution with the same input
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:224874703567:stateMachine:siesa-integration-workflow-prod \
  --input '{"client_id": "cliente-a", "sync_type": "incremental"}' \
  --name "retry-$(date +%s)" \
  --profile principal
```

## Performance Optimization

### Batch Size Tuning

The loader Lambda processes products in batches. Adjust `BATCH_SIZE` environment variable:
- **Smaller batches** (50-100): Better for rate-limited APIs
- **Larger batches** (200-500): Faster for high-throughput APIs

### Concurrent Executions

Multiple clients can sync simultaneously:
- Each execution is isolated by `client_id`
- Lambda concurrency limits apply (default: 1000)
- Monitor Lambda throttling metrics

### Cost Optimization

Reduce costs by:
- Using incremental syncs instead of full syncs
- Adjusting sync frequency based on data change rate
- Optimizing Lambda memory allocation
- Enabling S3 Intelligent-Tiering for config files

## Security Considerations

### IAM Permissions

The state machine role has least-privilege permissions:
- Lambda: `InvokeFunction` only
- DynamoDB: `PutItem`, `UpdateItem`, `GetItem` only
- SNS: `Publish` only

### Data Encryption

All data is encrypted:
- **In Transit**: TLS 1.3 for all API calls
- **At Rest**: 
  - DynamoDB: AWS managed encryption
  - CloudWatch Logs: KMS encryption
  - Secrets Manager: AWS managed encryption

### Credential Management

- No credentials in state machine definition
- All credentials retrieved at runtime from Secrets Manager
- Credentials never logged to CloudWatch

## Multi-Tenant Support

### Client Isolation

Each execution is isolated by `client_id`:
- Separate credentials per client
- Separate field mappings per client
- Separate sync state tracking

### Adding New Clients

To add a new client:
1. Create DynamoDB config entry
2. Store credentials in Secrets Manager
3. Create EventBridge rule for scheduled syncs
4. Test with manual execution

See [OPERATIONAL-PROCEDURES.md](./OPERATIONAL-PROCEDURES.md) for detailed steps.

## Multi-Product Support

### Product Type Routing

The state machine supports multiple products:
- `product_type: "kong"`: Routes to Kong adapter
- `product_type: "wms"`: Routes to WMS adapter

Product type is determined from client config and passed through all states.

### Adding New Products

To add a new product (e.g., TMS):
1. Create new adapter class in loader Lambda
2. Update adapter factory
3. Create field mappings file
4. No changes needed to state machine!

## References

- [AWS Step Functions Developer Guide](https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html)
- [Step Functions Best Practices](https://docs.aws.amazon.com/step-functions/latest/dg/bp-express.html)
- [Lambda Integration Patterns](https://docs.aws.amazon.com/step-functions/latest/dg/connect-lambda.html)
- [DynamoDB Integration](https://docs.aws.amazon.com/step-functions/latest/dg/connect-ddb.html)
- [SNS Integration](https://docs.aws.amazon.com/step-functions/latest/dg/connect-sns.html)

## Next Steps

1. Deploy the state machine using CDK
2. Create test client configuration
3. Execute manual test sync
4. Set up EventBridge rules for scheduled syncs
5. Configure CloudWatch alarms
6. Monitor first production sync

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-23  
**Owner**: APES Integration Team
