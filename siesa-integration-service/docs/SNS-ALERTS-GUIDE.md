# SNS Alerts Configuration Guide

## Overview

This guide explains the SNS (Simple Notification Service) configuration for the Siesa Integration service, including topic setup, subscriptions, message formats, and alert types.

## SNS Topic

### Topic Details

| Property | Value |
|----------|-------|
| **Topic Name** | `siesa-integration-alerts-{environment}` |
| **Display Name** | Siesa Integration Alerts ({environment}) |
| **Protocol** | Email, SMS (optional), Lambda (optional) |
| **Region** | us-east-1 (configurable) |

### Topic ARN Format

```
arn:aws:sns:us-east-1:{account-id}:siesa-integration-alerts-{environment}
```

## Alert Types

### 1. Step Function Failures

**Trigger**: Step Function execution fails

**Message Format**:
```json
{
  "AlarmName": "StepFunctionExecutionFailed",
  "AlarmDescription": "Step Function execution failed for client",
  "NewStateValue": "ALARM",
  "NewStateReason": "Execution failed with error",
  "StateChangeTime": "2025-11-23T10:00:00.000Z",
  "Region": "us-east-1",
  "client_id": "cliente-a",
  "execution_arn": "arn:aws:states:...",
  "error": "Lambda function failed",
  "cause": "Timeout exceeded"
}
```

**Actions**:
1. Check CloudWatch Logs for detailed error
2. Review Step Functions execution history
3. Retry execution if transient error
4. Fix code if persistent error

### 2. Lambda Function Errors

**Trigger**: Lambda function errors exceed threshold (> 5 in 5 minutes)

**Message Format**:
```json
{
  "AlarmName": "LambdaErrorRateHigh",
  "AlarmDescription": "Lambda function error rate exceeded threshold",
  "NewStateValue": "ALARM",
  "NewStateReason": "Threshold Crossed: 5 errors in 5 minutes",
  "StateChangeTime": "2025-11-23T10:00:00.000Z",
  "Region": "us-east-1",
  "function_name": "siesa-integration-extractor-prod",
  "error_count": 7,
  "threshold": 5
}
```

**Actions**:
1. Check Lambda CloudWatch Logs
2. Identify error pattern
3. Check API connectivity
4. Review recent code changes

### 3. Sync Duration Exceeded

**Trigger**: Sync duration > 30 minutes

**Message Format**:
```json
{
  "AlarmName": "SyncDurationExceeded",
  "AlarmDescription": "Sync duration exceeded 30 minutes",
  "NewStateValue": "ALARM",
  "NewStateReason": "Sync took 35 minutes",
  "StateChangeTime": "2025-11-23T10:00:00.000Z",
  "Region": "us-east-1",
  "client_id": "cliente-a",
  "duration_seconds": 2100,
  "threshold_seconds": 1800,
  "records_processed": 15000
}
```

**Actions**:
1. Check if large dataset
2. Review API performance
3. Consider increasing Lambda timeout
4. Optimize batch size

### 4. High Failed Records Rate

**Trigger**: Failed records > 5% of total

**Message Format**:
```json
{
  "AlarmName": "HighFailedRecordsRate",
  "AlarmDescription": "Failed records exceeded 5% threshold",
  "NewStateValue": "ALARM",
  "NewStateReason": "8% of records failed",
  "StateChangeTime": "2025-11-23T10:00:00.000Z",
  "Region": "us-east-1",
  "client_id": "cliente-a",
  "product_type": "kong",
  "total_records": 1000,
  "failed_records": 80,
  "failure_rate": 0.08
}
```

**Actions**:
1. Check validation errors in logs
2. Review data quality in Siesa
3. Check product API status
4. Update field mappings if needed

### 5. API Rate Limiting

**Trigger**: API returns 429 (Too Many Requests)

**Message Format**:
```json
{
  "AlarmName": "APIRateLimitExceeded",
  "AlarmDescription": "API rate limit exceeded",
  "NewStateValue": "ALARM",
  "NewStateReason": "Received 429 response from API",
  "StateChangeTime": "2025-11-23T10:00:00.000Z",
  "Region": "us-east-1",
  "client_id": "cliente-a",
  "api_type": "kong",
  "retry_count": 3,
  "backoff_seconds": 60
}
```

**Actions**:
1. Wait for rate limit reset
2. Reduce batch size
3. Increase delay between batches
4. Contact API provider for limit increase

## Subscription Types

### Email Subscriptions

**Setup**:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod \
  --protocol email \
  --notification-endpoint ops-team@empresa.com
```

**Confirmation**:
1. Check email inbox
2. Click confirmation link
3. Verify subscription in SNS console

**Email Format**:
- **Subject**: Siesa Integration - [Alert Type] ([Environment])
- **Body**: JSON formatted alert details
- **Sender**: AWS Notifications <no-reply@sns.amazonaws.com>

### SMS Subscriptions (Optional)

**Setup**:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod \
  --protocol sms \
  --notification-endpoint +57XXXXXXXXXX
```

**Cost**: ~$0.00645 per SMS (Colombia)

**Recommendation**: Use only for critical alerts in production

### Lambda Subscriptions (Advanced)

**Use Case**: Custom alert processing, ticket creation, Slack notifications

**Setup**:
```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:ACCOUNT:function:alert-processor
```

**Lambda Function Example**:
```python
import json
import requests

def lambda_handler(event, context):
    # Parse SNS message
    message = json.loads(event['Records'][0]['Sns']['Message'])
    
    # Send to Slack
    slack_webhook = 'https://hooks.slack.com/services/...'
    requests.post(slack_webhook, json={
        'text': f"🚨 Alert: {message['AlarmName']}",
        'attachments': [{
            'color': 'danger',
            'fields': [
                {'title': 'Client', 'value': message.get('client_id', 'N/A')},
                {'title': 'Reason', 'value': message['NewStateReason']}
            ]
        }]
    })
    
    return {'statusCode': 200}
```

## Deployment

### Option 1: Using CDK

The SNS topic is automatically created by the CDK stack:

```bash
cd siesa-integration-service
npm install
cdk deploy --profile principal --context environment=prod
```

### Option 2: Using PowerShell Script

```powershell
cd siesa-integration-service/scripts

# Create topic with email subscriptions
./create-sns-topic.ps1 `
  -Environment prod `
  -Region us-east-1 `
  -Profile principal `
  -EmailAddresses @('ops-team@empresa.com', 'devops@empresa.com')
```

### Option 3: Manual Creation (AWS CLI)

```bash
# Create topic
aws sns create-topic \
  --name siesa-integration-alerts-prod \
  --region us-east-1 \
  --profile principal

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod \
  --protocol email \
  --notification-endpoint ops-team@empresa.com \
  --region us-east-1 \
  --profile principal
```

## Topic Policy

The SNS topic policy allows:

1. **Step Functions** to publish failure notifications
2. **Lambda Functions** to publish custom alerts
3. **CloudWatch Alarms** to publish alarm state changes
4. **Account root** to manage topic

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowStepFunctionsPublish",
      "Effect": "Allow",
      "Principal": {
        "Service": "states.amazonaws.com"
      },
      "Action": "SNS:Publish",
      "Resource": "arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod"
    },
    {
      "Sid": "AllowCloudWatchAlarmsPublish",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudwatch.amazonaws.com"
      },
      "Action": "SNS:Publish",
      "Resource": "arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod"
    }
  ]
}
```

## Testing

### Send Test Message

```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod \
  --subject "Test Alert" \
  --message '{"test": "This is a test message"}' \
  --region us-east-1 \
  --profile principal
```

### Verify Delivery

1. Check email inbox (if subscribed)
2. Check SNS delivery logs in CloudWatch
3. Verify subscription status in SNS console

## Monitoring

### SNS Metrics

CloudWatch metrics for SNS topic:

- `NumberOfMessagesPublished`: Total messages published
- `NumberOfNotificationsDelivered`: Successful deliveries
- `NumberOfNotificationsFailed`: Failed deliveries

### CloudWatch Alarms for SNS

```bash
# Alarm for failed deliveries
aws cloudwatch put-metric-alarm \
  --alarm-name SNSDeliveryFailures \
  --alarm-description "SNS message delivery failures" \
  --metric-name NumberOfNotificationsFailed \
  --namespace AWS/SNS \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=TopicName,Value=siesa-integration-alerts-prod
```

## Cost Optimization

### Current Costs

**Email**:
- First 1,000 notifications: Free
- Additional: $2.00 per 100,000 notifications

**SMS** (Colombia):
- $0.00645 per SMS

**Example**: 100 alerts/month
- Email: Free (< 1,000)
- SMS: $0.65

### Optimization Tips

1. **Filter alerts by severity**
   - Send only ERROR and CRITICAL to SMS
   - Send all alerts to email

2. **Batch notifications**
   - Group multiple alerts into single message
   - Send summary every hour instead of real-time

3. **Use Lambda for filtering**
   - Process alerts before sending
   - Deduplicate similar alerts

## Troubleshooting

### Issue: Not receiving emails

**Possible causes**:
1. Email not confirmed
2. Email in spam folder
3. SNS delivery failed

**Solution**:
```bash
# Check subscription status
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod

# Resend confirmation
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod \
  --protocol email \
  --notification-endpoint your-email@example.com
```

### Issue: Too many alerts

**Possible causes**:
1. Threshold too low
2. Recurring issue not fixed
3. No alert deduplication

**Solution**:
1. Adjust CloudWatch alarm thresholds
2. Fix underlying issue
3. Implement Lambda filter for deduplication

### Issue: Delivery failures

**Possible causes**:
1. Invalid email address
2. Email server rejecting messages
3. SNS service issue

**Solution**:
```bash
# Check delivery logs
aws logs tail /aws/sns/us-east-1/ACCOUNT/siesa-integration-alerts-prod/Failure \
  --follow

# Verify email address
aws sns get-subscription-attributes \
  --subscription-arn arn:aws:sns:...
```

## Best Practices

### 1. Alert Fatigue Prevention

- ✅ Set appropriate thresholds
- ✅ Implement alert deduplication
- ✅ Use different channels for different severities
- ✅ Regular review and tuning

### 2. Security

- ✅ Encrypt messages in transit (HTTPS)
- ✅ Restrict topic access with IAM policies
- ✅ Don't include sensitive data in alerts
- ✅ Use separate topics per environment

### 3. Reliability

- ✅ Multiple subscription endpoints
- ✅ Monitor SNS delivery metrics
- ✅ Test alerts regularly
- ✅ Document escalation procedures

### 4. Cost Management

- ✅ Use email for non-critical alerts
- ✅ Reserve SMS for critical alerts only
- ✅ Implement alert batching
- ✅ Regular cost review

## Integration with Other Services

### CloudWatch Alarms

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name HighErrorRate \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

### Step Functions

In state machine definition:
```json
{
  "Catch": [{
    "ErrorEquals": ["States.ALL"],
    "Next": "NotifyFailure"
  }],
  "NotifyFailure": {
    "Type": "Task",
    "Resource": "arn:aws:states:::sns:publish",
    "Parameters": {
      "TopicArn": "arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod",
      "Subject": "Integration Failed",
      "Message.$": "$.error"
    }
  }
}
```

### Lambda Functions

```python
import boto3

sns = boto3.client('sns')

def send_alert(message, subject='Alert'):
    sns.publish(
        TopicArn='arn:aws:sns:us-east-1:ACCOUNT:siesa-integration-alerts-prod',
        Subject=subject,
        Message=json.dumps(message)
    )
```

## References

- [SNS Documentation](https://docs.aws.amazon.com/sns/)
- [SNS Pricing](https://aws.amazon.com/sns/pricing/)
- [SNS Best Practices](https://docs.aws.amazon.com/sns/latest/dg/sns-best-practices.html)
- [Email Notifications](https://docs.aws.amazon.com/sns/latest/dg/sns-email-notifications.html)

## Support

For issues or questions:
- Create an issue in the repository
- Contact the APES DevOps team
- Check SNS console for delivery status
