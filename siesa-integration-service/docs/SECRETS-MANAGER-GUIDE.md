# Secrets Manager Configuration Guide

This guide explains how to configure AWS Secrets Manager for the Siesa ERP integration.

## Overview

The integration uses AWS Secrets Manager to securely store API credentials for:
- **Siesa ERP** (per client)
- **Kong (RFID Backend)** (per Kong client)
- **WMS (Warehouse Management System)** (per WMS client)

## Naming Convention

All secrets follow this pattern:

```
siesa-integration/{client_id}/{system}
```

### Examples:
- `siesa-integration/cliente-a/siesa` - Siesa credentials for Cliente A
- `siesa-integration/cliente-a/kong` - Kong credentials for Cliente A
- `siesa-integration/cliente-b/siesa` - Siesa credentials for Cliente B
- `siesa-integration/cliente-b/wms` - WMS credentials for Cliente B

## Secret Templates

### 1. Siesa ERP Credentials

**Secret Name**: `siesa-integration/{client_id}/siesa`

**JSON Structure**:
```json
{
  "baseUrl": "https://serviciosqa.siesacloud.com/api/siesa/v3/",
  "username": "integration_user",
  "password": "secure_password_here",
  "conniKey": "your_conni_key_here",
  "conniToken": "your_conni_token_here",
  "tenantId": "cliente-a-tenant",
  "environment": "production"
}
```

**Field Descriptions**:
- `baseUrl`: Siesa API base URL (varies per client)
- `username`: Siesa API username
- `password`: Siesa API password
- `conniKey`: Siesa Connector Key (from Siesa Connector Module)
- `conniToken`: Siesa Connector Token (from Siesa Connector Module)
- `tenantId`: Siesa tenant identifier
- `environment`: Environment identifier (production/staging/qa)

### 2. Kong (RFID) Product Credentials

**Secret Name**: `siesa-integration/{client_id}/kong`

**JSON Structure**:
```json
{
  "productType": "kong",
  "baseUrl": "https://api-staging.technoapes.io/",
  "username": "kong_api_user",
  "password": "kong_secure_password",
  "apiKey": "optional_api_key_if_used",
  "tenantId": "cliente-a",
  "databaseType": "rds",
  "additionalConfig": {
    "rfidEnabled": true,
    "batchSize": 100,
    "timeout": 30000
  }
}
```

**Field Descriptions**:
- `productType`: Always "kong" for Kong clients
- `baseUrl`: Kong API base URL
- `username`: Kong API username
- `password`: Kong API password
- `apiKey`: Optional API key (if Kong uses key-based auth)
- `tenantId`: Kong tenant identifier
- `databaseType`: Database type (typically "rds")
- `additionalConfig`: Kong-specific configuration
  - `rfidEnabled`: Whether RFID functionality is enabled
  - `batchSize`: Batch size for bulk operations
  - `timeout`: API timeout in milliseconds

### 3. WMS (Warehouse Management) Product Credentials

**Secret Name**: `siesa-integration/{client_id}/wms`

**JSON Structure**:
```json
{
  "productType": "wms",
  "baseUrl": "https://wms-api.cliente-b.com/api/v1",
  "apiKey": "wms_api_key_here",
  "tenantId": "cliente-b",
  "serviceEndpoints": {
    "inventory": "https://wms-api.cliente-b.com/inventory",
    "warehouse": "https://wms-api.cliente-b.com/warehouse",
    "orders": "https://wms-api.cliente-b.com/orders",
    "locations": "https://wms-api.cliente-b.com/locations"
  },
  "additionalConfig": {
    "warehouseId": "WH-001",
    "defaultZone": "ZONE-A",
    "batchSize": 100,
    "timeout": 30000,
    "lotTrackingEnabled": true,
    "expirationTrackingEnabled": true
  }
}
```

**Field Descriptions**:
- `productType`: Always "wms" for WMS clients
- `baseUrl`: WMS API base URL
- `apiKey`: WMS API key for authentication
- `tenantId`: WMS tenant identifier
- `serviceEndpoints`: WMS microservices endpoints
  - `inventory`: Inventory service endpoint
  - `warehouse`: Warehouse service endpoint
  - `orders`: Orders service endpoint
  - `locations`: Locations service endpoint
- `additionalConfig`: WMS-specific configuration
  - `warehouseId`: Default warehouse identifier
  - `defaultZone`: Default warehouse zone
  - `batchSize`: Batch size for bulk operations
  - `timeout`: API timeout in milliseconds
  - `lotTrackingEnabled`: Whether lot tracking is enabled
  - `expirationTrackingEnabled`: Whether expiration tracking is enabled

## Creating Secrets

### Option 1: Using AWS Console

1. Go to AWS Secrets Manager console
2. Click "Store a new secret"
3. Select "Other type of secret"
4. Choose "Plaintext" tab
5. Paste the JSON structure (see templates above)
6. Fill in actual values
7. Name the secret following the convention: `siesa-integration/{client_id}/{system}`
8. Add description: "Credentials for {client_id} - {system}"
9. Configure automatic rotation (optional)
10. Review and create

### Option 2: Using AWS CLI

#### Create Siesa Secret:
```bash
aws secretsmanager create-secret \
  --name siesa-integration/cliente-a/siesa \
  --description "Siesa ERP credentials for Cliente A" \
  --secret-string '{
    "baseUrl": "https://serviciosqa.siesacloud.com/api/siesa/v3/",
    "username": "integration_user",
    "password": "secure_password_here",
    "conniKey": "your_conni_key_here",
    "conniToken": "your_conni_token_here",
    "tenantId": "cliente-a-tenant",
    "environment": "production"
  }' \
  --region us-east-1
```

#### Create Kong Secret:
```bash
aws secretsmanager create-secret \
  --name siesa-integration/cliente-a/kong \
  --description "Kong RFID credentials for Cliente A" \
  --secret-string '{
    "productType": "kong",
    "baseUrl": "https://api-staging.technoapes.io/",
    "username": "kong_api_user",
    "password": "kong_secure_password",
    "tenantId": "cliente-a",
    "databaseType": "rds",
    "additionalConfig": {
      "rfidEnabled": true,
      "batchSize": 100,
      "timeout": 30000
    }
  }' \
  --region us-east-1
```

#### Create WMS Secret:
```bash
aws secretsmanager create-secret \
  --name siesa-integration/cliente-b/wms \
  --description "WMS credentials for Cliente B" \
  --secret-string '{
    "productType": "wms",
    "baseUrl": "https://wms-api.cliente-b.com/api/v1",
    "apiKey": "wms_api_key_here",
    "tenantId": "cliente-b",
    "serviceEndpoints": {
      "inventory": "https://wms-api.cliente-b.com/inventory",
      "warehouse": "https://wms-api.cliente-b.com/warehouse",
      "orders": "https://wms-api.cliente-b.com/orders",
      "locations": "https://wms-api.cliente-b.com/locations"
    },
    "additionalConfig": {
      "warehouseId": "WH-001",
      "defaultZone": "ZONE-A",
      "batchSize": 100,
      "timeout": 30000,
      "lotTrackingEnabled": true,
      "expirationTrackingEnabled": true
    }
  }' \
  --region us-east-1
```

### Option 3: Using PowerShell Script

See `scripts/create-client-secrets.ps1` for automated secret creation.

## Updating Secrets

### Using AWS CLI:
```bash
aws secretsmanager update-secret \
  --secret-id siesa-integration/cliente-a/siesa \
  --secret-string '{...new values...}' \
  --region us-east-1
```

### Using AWS Console:
1. Go to Secrets Manager
2. Find the secret
3. Click "Retrieve secret value"
4. Click "Edit"
5. Update values
6. Save

## Secret Rotation

### Automatic Rotation (Recommended)

Configure automatic rotation for production secrets:

```bash
aws secretsmanager rotate-secret \
  --secret-id siesa-integration/cliente-a/siesa \
  --rotation-lambda-arn arn:aws:lambda:us-east-1:ACCOUNT:function:SecretsManagerRotation \
  --rotation-rules AutomaticallyAfterDays=30 \
  --region us-east-1
```

### Manual Rotation

1. Create new credentials in Siesa/Kong/WMS
2. Update secret in Secrets Manager
3. Test integration with new credentials
4. Deactivate old credentials

## Security Best Practices

### 1. Least Privilege Access
Only grant Lambda execution role access to specific secrets:
```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue",
    "secretsmanager:DescribeSecret"
  ],
  "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:siesa-integration/*"
}
```

### 2. Encryption
All secrets are encrypted at rest using AWS KMS (default AWS managed key).

### 3. Audit Logging
Enable CloudTrail to log all secret access:
- Who accessed the secret
- When it was accessed
- From which Lambda function

### 4. Never Log Credentials
The Lambda functions are configured to NEVER log credentials in CloudWatch.

## Retrieving Secrets in Lambda

The Lambda functions use this pattern to retrieve secrets:

```python
import boto3
import json

def get_secret(secret_name):
    """Retrieve secret from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Error retrieving secret {secret_name}: {str(e)}")
        raise
```

## Client Onboarding Checklist

When adding a new client, create these secrets:

### For Kong Clients:
- [ ] Create Siesa secret: `siesa-integration/{client_id}/siesa`
- [ ] Create Kong secret: `siesa-integration/{client_id}/kong`
- [ ] Test secret retrieval
- [ ] Update DynamoDB client configuration with secret names

### For WMS Clients:
- [ ] Create Siesa secret: `siesa-integration/{client_id}/siesa`
- [ ] Create WMS secret: `siesa-integration/{client_id}/wms`
- [ ] Test secret retrieval
- [ ] Update DynamoDB client configuration with secret names

## Troubleshooting

### Issue: "Secret not found"
**Solution**: Verify secret name matches exactly: `siesa-integration/{client_id}/{system}`

### Issue: "Access denied"
**Solution**: Check Lambda execution role has `secretsmanager:GetSecretValue` permission

### Issue: "Invalid JSON"
**Solution**: Validate JSON structure using a JSON validator before creating secret

### Issue: "Secret value is null"
**Solution**: Ensure all required fields are present in the secret JSON

## Monitoring

### CloudWatch Metrics
Monitor secret access in CloudWatch:
- `SecretRetrievalCount`: Number of times secret was retrieved
- `SecretRetrievalErrors`: Number of failed retrievals

### CloudWatch Logs
Check Lambda logs for secret-related errors:
```
/aws/lambda/siesa-integration-extractor-{environment}
/aws/lambda/siesa-integration-loader-{environment}
```

Look for log entries:
- `Error retrieving secret`: Secret retrieval failed
- `Invalid secret format`: Secret JSON is malformed
- `Missing required field`: Secret is missing required fields

## Cost Optimization

### Secrets Manager Pricing:
- $0.40 per secret per month
- $0.05 per 10,000 API calls

### Recommendations:
1. Cache secrets in Lambda (use environment variables or global scope)
2. Don't retrieve secrets on every invocation
3. Delete unused secrets for deactivated clients

## References

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [Secrets Manager Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/best-practices.html)
- [Secrets Manager Pricing](https://aws.amazon.com/secrets-manager/pricing/)

## Support

For questions about secret configuration:
1. Check this guide
2. Review CloudWatch Logs for errors
3. Verify secret JSON structure
4. Contact the integration team
