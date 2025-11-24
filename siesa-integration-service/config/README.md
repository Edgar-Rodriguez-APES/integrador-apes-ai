# Configuration Files

This directory contains field mapping configuration files for the Siesa ERP integration.

## Overview

Field mappings define how data is transformed from Siesa ERP format to product-specific formats (Kong or WMS). These files are uploaded to S3 and loaded dynamically by the Transformer Lambda function based on the client's `field_mappings_key` configuration.

## Files

### field-mappings-kong.json

Field mappings for **Kong (RFID Backend)** product integration.

**Key Features:**
- Maps Siesa fields to Kong monolithic API format
- Includes RFID-specific fields (`rfid_tag_id`)
- Supports product tracking and inventory management
- Uses Kong-specific field names: `product_id`, `barcode`, `quantity`

**Target API:** Kong REST API (Monolithic)

### field-mappings-wms.json

Field mappings for **WMS (Warehouse Management System)** product integration.

**Key Features:**
- Maps Siesa fields to WMS microservices API format
- Includes warehouse-specific fields (`location_code`, `zone_id`, `aisle`, `rack`, `level`)
- Supports advanced inventory tracking (lot numbers, expiration dates)
- Uses WMS-specific field names: `item_id`, `ean_code`, `available_quantity`
- **REQUIRES** `location_code` field (mandatory for WMS)

**Target API:** WMS Microservices API

## File Structure

Each mapping file contains:

```json
{
  "version": "1.0",
  "product_type": "kong|wms",
  "description": "...",
  "mappings": {
    "product": {
      "field_name": {
        "siesa_field": "f_campo_siesa",
        "product_field": "product_field_name",
        "type": "string|integer|decimal|date",
        "required": true|false,
        "validation": "regex_pattern",
        "description": "..."
      }
    }
  },
  "transformations": {
    "date_format": {...},
    "location_format": {...},
    "decimal_separator": {...}
  },
  "validation_rules": {...},
  "default_values": {...},
  "custom_fields": {...}
}
```

## Uploading to S3

After deploying the CDK stack, upload these files to S3:

### Using PowerShell Script (Recommended)

```powershell
cd siesa-integration-service
.\scripts\upload-config-files.ps1 -Environment dev -Profile default
```

### Using AWS CLI Manually

```bash
# Get your AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Set environment
ENVIRONMENT=dev

# Upload Kong mappings
aws s3 cp config/field-mappings-kong.json \
  s3://siesa-integration-config-${ENVIRONMENT}-${ACCOUNT_ID}/field-mappings-kong.json \
  --content-type application/json

# Upload WMS mappings
aws s3 cp config/field-mappings-wms.json \
  s3://siesa-integration-config-${ENVIRONMENT}-${ACCOUNT_ID}/field-mappings-wms.json \
  --content-type application/json
```

## Client Configuration

When adding a new client to DynamoDB, specify which mapping file to use:

### Kong Client Example

```json
{
  "client_id": "cliente-a",
  "product_type": "kong",
  "field_mappings_key": "field-mappings-kong.json",
  ...
}
```

### WMS Client Example

```json
{
  "client_id": "cliente-b",
  "product_type": "wms",
  "field_mappings_key": "field-mappings-wms.json",
  ...
}
```

## Customization

### Adding New Fields

1. Edit the appropriate mapping file (`field-mappings-kong.json` or `field-mappings-wms.json`)
2. Add the new field mapping under `mappings.product`
3. Upload the updated file to S3
4. No code changes required - mappings are loaded dynamically

### Creating Product-Specific Mappings

For clients with unique requirements, create custom mapping files:

```bash
# Copy base template
cp field-mappings-kong.json field-mappings-kong-cliente-especial.json

# Edit custom mappings
# ...

# Upload to S3
aws s3 cp config/field-mappings-kong-cliente-especial.json \
  s3://siesa-integration-config-${ENVIRONMENT}-${ACCOUNT_ID}/

# Update client config in DynamoDB
{
  "client_id": "cliente-especial",
  "field_mappings_key": "field-mappings-kong-cliente-especial.json"
}
```

## Validation Rules

Both mapping files include validation rules:

- **EAN Code**: Must be exactly 13 digits
- **Quantity**: Cannot be negative
- **Location Code** (WMS only): Must match format `A0105` (1 letter + 4 digits)
- **Weight/Volume**: Must be within reasonable ranges

## Transformations

### Date Format
- **From**: `YYYY-MM-DD` (Siesa format)
- **To**: `ISO8601` (Product format)

### Location Format (WMS only)
- **From**: `A-01-05` (Siesa format with hyphens)
- **To**: `A0105` (WMS compact format)

### Decimal Separator
- **From**: `,` (Siesa uses comma)
- **To**: `.` (Products use dot)

### Boolean Conversion
- **True values**: `S`, `SI`, `1`, `true`
- **False values**: `N`, `NO`, `0`, `false`

## Custom Fields

Both products support custom fields using the `custom:` prefix:

```json
{
  "custom:color": "Blue",
  "custom:size": "M",
  "custom:material": "Cotton"
}
```

Custom fields from Siesa that don't map to standard product fields are automatically prefixed and passed through.

## Versioning

The S3 bucket has versioning enabled. When updating mapping files:

1. Upload the new version to S3
2. Previous versions are automatically retained
3. Rollback is possible by restoring a previous version

## Monitoring

Check CloudWatch Logs for transformation errors:

```
/aws/lambda/siesa-integration-transformer-{environment}
```

Look for log entries with:
- `Validation error`: Field validation failed
- `Transformation error`: Data transformation failed
- `Missing required field`: Required field not present

## Troubleshooting

### Issue: Transformation fails with "Field not found"

**Solution**: Check that the `siesa_field` name in the mapping file matches the actual field name from Siesa API.

### Issue: Validation error for location_code (WMS)

**Solution**: WMS requires `location_code` field. Ensure Siesa data includes `f_ubicacion` field and it matches the format `A0105`.

### Issue: Custom fields not appearing in product

**Solution**: Verify that custom fields use the `custom:` prefix in the mapping file.

## Support

For questions or issues with field mappings:
1. Check CloudWatch Logs for detailed error messages
2. Verify mapping file syntax using a JSON validator
3. Test with sample data using the Transformer Lambda directly
4. Contact the integration team

## References

- [Siesa API Documentation](../integrations/siesa-integration/SIESA-API-SUMMARY.md)
- [Kong API Documentation](../integrations/siesa-integration/KONG-API-DOCUMENTATION.md)
- [WMS API Documentation](../integrations/siesa-integration/WMS-API-DOCUMENTATION.md)
- [Field Mappings Comparison](../integrations/siesa-integration/FIELD-MAPPINGS-CONSOLIDATED.md)
