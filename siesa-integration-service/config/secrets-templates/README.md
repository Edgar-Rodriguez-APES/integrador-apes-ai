# Secrets Templates

This directory contains JSON templates for creating AWS Secrets Manager secrets.

## Files

### siesa-credentials-template.json
Template for Siesa ERP API credentials.

**Usage:**
1. Copy the template
2. Replace all `REPLACE_WITH_*` placeholders with actual values
3. Create secret in AWS Secrets Manager with name: `siesa-integration/{client_id}/siesa`

### kong-credentials-template.json
Template for Kong (RFID Backend) API credentials.

**Usage:**
1. Copy the template
2. Replace all `REPLACE_WITH_*` placeholders with actual values
3. Create secret in AWS Secrets Manager with name: `siesa-integration/{client_id}/kong`

### wms-credentials-template.json
Template for WMS (Warehouse Management System) API credentials.

**Usage:**
1. Copy the template
2. Replace all `REPLACE_WITH_*` placeholders with actual values
3. Create secret in AWS Secrets Manager with name: `siesa-integration/{client_id}/wms`

## Quick Start

### Using AWS Console

1. Go to AWS Secrets Manager console
2. Click "Store a new secret"
3. Select "Other type of secret"
4. Choose "Plaintext" tab
5. Copy content from appropriate template file
6. Replace all placeholder values
7. Name the secret: `siesa-integration/{client_id}/{system}`
8. Create the secret

### Using AWS CLI

```bash
# Create Siesa secret
aws secretsmanager create-secret \
  --name siesa-integration/cliente-a/siesa \
  --description "Siesa ERP credentials for Cliente A" \
  --secret-string file://siesa-credentials-template.json \
  --region us-east-1

# Create Kong secret
aws secretsmanager create-secret \
  --name siesa-integration/cliente-a/kong \
  --description "Kong RFID credentials for Cliente A" \
  --secret-string file://kong-credentials-template.json \
  --region us-east-1

# Create WMS secret
aws secretsmanager create-secret \
  --name siesa-integration/cliente-b/wms \
  --description "WMS credentials for Cliente B" \
  --secret-string file://wms-credentials-template.json \
  --region us-east-1
```

### Using PowerShell Script

```powershell
# Create secrets for Kong client
cd siesa-integration-service
.\scripts\create-client-secrets.ps1 -ClientId "cliente-a" -ProductType "kong"

# Create secrets for WMS client
.\scripts\create-client-secrets.ps1 -ClientId "cliente-b" -ProductType "wms"

# Dry run (preview without creating)
.\scripts\create-client-secrets.ps1 -ClientId "cliente-a" -ProductType "kong" -DryRun
```

## Field Descriptions

### Siesa Credentials

- `baseUrl`: Siesa API base URL (varies per client environment)
- `username`: Siesa API username for integration
- `password`: Siesa API password
- `conniKey`: Siesa Connector Key (from Siesa Connector Module)
- `conniToken`: Siesa Connector Token (from Siesa Connector Module)
- `tenantId`: Siesa tenant identifier
- `environment`: Environment identifier (production/staging/qa)

### Kong Credentials

- `productType`: Always "kong"
- `baseUrl`: Kong API base URL
- `username`: Kong API username
- `password`: Kong API password
- `apiKey`: Optional API key (if Kong uses key-based auth)
- `tenantId`: Kong tenant identifier
- `databaseType`: Database type (typically "rds")
- `additionalConfig.rfidEnabled`: Whether RFID functionality is enabled
- `additionalConfig.batchSize`: Batch size for bulk operations
- `additionalConfig.timeout`: API timeout in milliseconds

### WMS Credentials

- `productType`: Always "wms"
- `baseUrl`: WMS API base URL
- `apiKey`: WMS API key for authentication
- `tenantId`: WMS tenant identifier
- `serviceEndpoints`: WMS microservices endpoints
  - `inventory`: Inventory service endpoint
  - `warehouse`: Warehouse service endpoint
  - `orders`: Orders service endpoint
  - `locations`: Locations service endpoint
- `additionalConfig.warehouseId`: Default warehouse identifier
- `additionalConfig.defaultZone`: Default warehouse zone
- `additionalConfig.batchSize`: Batch size for bulk operations
- `additionalConfig.timeout`: API timeout in milliseconds
- `additionalConfig.lotTrackingEnabled`: Whether lot tracking is enabled
- `additionalConfig.expirationTrackingEnabled`: Whether expiration tracking is enabled

## Security Notes

1. **Never commit actual credentials** to Git
2. These templates contain only placeholder values
3. Always replace placeholders before creating secrets
4. Use strong, unique passwords for each client
5. Enable secret rotation for production environments

## Validation

Before creating a secret, validate the JSON:

```bash
# Validate JSON syntax
cat siesa-credentials-template.json | jq .

# Or use Python
python -m json.tool siesa-credentials-template.json
```

## References

- [Secrets Manager Guide](../../docs/SECRETS-MANAGER-GUIDE.md)
- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
