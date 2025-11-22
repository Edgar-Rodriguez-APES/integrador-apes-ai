# Design Document: Siesa ERP Integration - Week 1

## Overview

This document defines the technical design for a multi-tenant, autonomous integration between Siesa ERP and our two product platforms: **Kong (RFID Backend)** and **WMS (Microservices)**. The integration is deployed centrally in the Principal AWS Account (224874703567) and serves multiple clients through a REST API architecture.

### Product Architecture Context

We have two distinct products with different architectures:

1. **Kong (RFID Backend)**
   - Monolithic architecture
   - Relational database (RDS)
   - Independent REST API (Postman collection: Kong APIs)
   - Used by clients who need RFID functionality

2. **WMS (Warehouse Management System)**
   - Microservices architecture
   - AWS-based services
   - Independent REST API (Postman collection: WMS APIs)
   - Used by clients who need warehouse management

**Critical Constraint**: Each Siesa client uses ONLY ONE product (either Kong/RFID OR WMS, never both).

### Key Design Principles

1. **Multi-Tenant Architecture**: Single deployment serves multiple clients with isolated configurations
2. **Multi-Product Support**: Flexible adapter pattern to support both Kong and WMS products
3. **REST API Integration**: Both products expose REST APIs; no cross-account AWS access required
4. **Build Once, Run Forever**: Autonomous code with no AI agent runtime dependencies
5. **Microservice Pattern**: Independent service that doesn't modify Kong, WMS, or Siesa code
6. **Configuration-Driven**: Add new clients without code changes; product selection per tenant

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Principal AWS Account (224874703567)                               │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │  Siesa Integration Service (Multi-Tenant, Multi-Product)  │     │
│  │                                                           │     │
│  │  EventBridge Rules (per client)                           │     │
│  │         ↓                                                 │     │
│  │  Step Functions Workflow                                  │     │
│  │         ↓                                                 │     │
│  │  ┌─────────────────────────────────────────────┐         │     │
│  │  │ Lambda: Extractor                           │         │     │
│  │  │ - Reads client config from DynamoDB         │         │     │
│  │  │ - Identifies product type (Kong or WMS)     │         │     │
│  │  │ - Gets Siesa credentials from Secrets       │         │     │
│  │  │ - Calls Siesa REST API                      │         │     │
│  │  └─────────────────────────────────────────────┘         │     │
│  │         ↓                                                 │     │
│  │  ┌─────────────────────────────────────────────┐         │     │
│  │  │ Lambda: Transformer                         │         │     │
│  │  │ - Loads product-specific field mappings     │         │     │
│  │  │ - Applies transformations per product       │         │     │
│  │  │ - Validates data                            │         │     │
│  │  │ - Converts to canonical model               │         │     │
│  │  └─────────────────────────────────────────────┘         │     │
│  │         ↓                                                 │     │
│  │  ┌─────────────────────────────────────────────┐         │     │
│  │  │ Lambda: Loader (Product Adapter Pattern)    │         │     │
│  │  │                                             │         │     │
│  │  │ ┌─────────────────┐  ┌─────────────────┐   │         │     │
│  │  │ │ Kong Adapter    │  │ WMS Adapter     │   │         │     │
│  │  │ │ - Kong API      │  │ - WMS API       │   │         │     │
│  │  │ │ - RDS format    │  │ - Microservices │   │         │     │
│  │  │ │ - RFID logic    │  │ - WMS logic     │   │         │     │
│  │  │ └─────────────────┘  └─────────────────┘   │         │     │
│  │  │                                             │         │     │
│  │  │ - Selects adapter based on client config    │         │     │
│  │  │ - Gets product credentials from Secrets     │         │     │
│  │  │ - Calls product-specific REST API           │         │     │
│  │  │ - Logs results                              │         │     │
│  │  └─────────────────────────────────────────────┘         │     │
│  │                                                           │     │
│  │  Supporting Services:                                     │     │
│  │  - DynamoDB: Client configs, product type, sync state    │     │
│  │  - Secrets Manager: Per-client credentials (Siesa+Product)│     │
│  │  - S3: Product-specific field mappings                    │     │
│  │  - CloudWatch: Logs & metrics                            │     │
│  │  - SNS: Failure alerts                                   │     │
│  └───────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
          │
          │ HTTPS REST API Calls
          │
          ├──────────────────┬──────────────────┬──────────────────┐
          ▼                  ▼                  ▼                  ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │ Client A    │    │ Client B    │    │ Client C    │    │ Client D    │
    │ Account     │    │ Account     │    │ Account     │    │ Account     │
    │             │    │             │    │             │    │             │
    │ Siesa ERP   │    │ Siesa ERP   │    │ Siesa ERP   │    │ Siesa ERP   │
    │ Kong (RFID) │    │ WMS         │    │ Kong (RFID) │    │ WMS         │
    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## Component Design

### 1. DynamoDB Table: Client Configuration

**Table Name**: `siesa-integration-clients`

**Primary Key**: `client_id` (String)

**Attributes**:

```json
{
  "client_id": "cliente-a",
  "client_name": "Empresa A S.A.",
  "enabled": true,
  "product_type": "kong",
  "siesa_api_url": "https://cliente-a.siesa.com/api",
  "siesa_credentials_secret": "siesa-integration/cliente-a/siesa",
  "product_api_url": "https://cliente-a.kong.com/api",
  "product_credentials_secret": "siesa-integration/cliente-a/kong",
  "aws_account_id": "111111111111",
  "sync_schedule": "rate(6 hours)",
  "field_mappings_key": "field-mappings-kong.json",
  "last_sync_timestamp": "2025-01-15T10:00:00Z",
  "last_sync_status": "success",
  "last_sync_records": 1250,
  "created_at": "2025-01-10T00:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

**Example for WMS Client**:

```json
{
  "client_id": "cliente-b",
  "client_name": "Empresa B S.A.",
  "enabled": true,
  "product_type": "wms",
  "siesa_api_url": "https://cliente-b.siesa.com/api",
  "siesa_credentials_secret": "siesa-integration/cliente-b/siesa",
  "product_api_url": "https://cliente-b.wms.com/api",
  "product_credentials_secret": "siesa-integration/cliente-b/wms",
  "aws_account_id": "222222222222",
  "sync_schedule": "rate(4 hours)",
  "field_mappings_key": "field-mappings-wms.json",
  "last_sync_timestamp": "2025-01-15T09:00:00Z",
  "last_sync_status": "success",
  "last_sync_records": 3400,
  "created_at": "2025-01-12T00:00:00Z",
  "updated_at": "2025-01-15T09:00:00Z"
}
```

**Key Attributes**:
- `product_type`: **REQUIRED** - Either "kong" or "wms" - determines which adapter to use
- `product_api_url`: Generic field name (replaces kong_api_url) - URL for the client's product
- `product_credentials_secret`: Generic field name - secret containing product credentials
- `field_mappings_key`: Product-specific field mapping file in S3

**Indexes**:
- GSI: `enabled-index` on `enabled` attribute for querying active clients
- GSI: `product-type-index` on `product_type` attribute for querying by product

### 2. AWS Secrets Manager: Credentials

**Naming Pattern**: `siesa-integration/{client_id}/{system}`

**Siesa Credentials** (`siesa-integration/cliente-a/siesa`):
```json
{
  "api_url": "https://cliente-a.siesa.com/api",
  "api_key": "siesa_api_key_here",
  "username": "integration_user",
  "password": "encrypted_password",
  "tenant_id": "cliente-a-tenant"
}
```

**Kong Product Credentials** (`siesa-integration/cliente-a/kong`):
```json
{
  "product_type": "kong",
  "api_url": "https://cliente-a.kong.com/api",
  "api_key": "kong_api_key_here",
  "tenant_id": "cliente-a",
  "database_type": "rds",
  "additional_config": {
    "rfid_enabled": true
  }
}
```

**WMS Product Credentials** (`siesa-integration/cliente-b/wms`):
```json
{
  "product_type": "wms",
  "api_url": "https://cliente-b.wms.com/api",
  "api_key": "wms_api_key_here",
  "tenant_id": "cliente-b",
  "service_endpoints": {
    "inventory": "https://cliente-b.wms.com/inventory",
    "warehouse": "https://cliente-b.wms.com/warehouse",
    "orders": "https://cliente-b.wms.com/orders"
  }
}
```

### 3. Lambda Function: Extractor

**Function Name**: `siesa-integration-extractor`
**Runtime**: Python 3.11
**Memory**: 512 MB
**Timeout**: 5 minutes

**Environment Variables**:
- `CLIENTS_TABLE`: `siesa-integration-clients`
- `LOG_LEVEL`: `INFO`

**IAM Permissions**:
- `dynamodb:GetItem` on clients table
- `secretsmanager:GetSecretValue` on `siesa-integration/*`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**Input Event**:
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
  "products": [
    {
      "id": "PROD001",
      "name": "Product Name",
      "ean": "1234567890123",
      ...
    }
  ],
  "count": 1250,
  "extraction_timestamp": "2025-01-15T10:00:00Z"
}
```

**Key Logic**:
1. Retrieve client config from DynamoDB
2. Check if client is enabled
3. Get Siesa credentials from Secrets Manager
4. Call Siesa API with pagination
5. Handle rate limiting and retries
6. Return extracted data



### 4. Lambda Function: Transformer

**Function Name**: `siesa-integration-transformer`
**Runtime**: Python 3.11
**Memory**: 256 MB
**Timeout**: 3 minutes

**Environment Variables**:
- `FIELD_MAPPINGS_S3_BUCKET`: `siesa-integration-config`
- `FIELD_MAPPINGS_S3_KEY`: `field-mappings.json`

**IAM Permissions**:
- `s3:GetObject` on config bucket
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**Input Event**:
```json
{
  "client_id": "cliente-a",
  "products": [...],
  "count": 1250,
  "extraction_timestamp": "2025-01-15T10:00:00Z"
}
```

**Output**:
```json
{
  "client_id": "cliente-a",
  "canonical_products": [
    {
      "id": "PROD001",
      "external_id": "SIESA-PROD001",
      "name": "Product Name",
      "display_name": "Product Display Name",
      "ean": "1234567890123",
      "sku": "SKU001",
      "category": "Electronics",
      "stock_quantity": 100,
      "warehouse_location": "A-01-05",
      "rfid_tag_id": null,
      "custom:color": "Blue",
      "custom:size": "M"
    }
  ],
  "count": 1250,
  "transformation_timestamp": "2025-01-15T10:01:00Z",
  "validation_errors": []
}
```

**Key Logic**:
1. Load field mappings from S3
2. Apply transformations for each product
3. Validate required fields
4. Convert data types
5. Handle custom fields with "custom:" prefix
6. Log validation warnings
7. Return canonical model data

### 5. Lambda Function: Loader (Multi-Product Adapter)

**Function Name**: `siesa-integration-loader`
**Runtime**: Python 3.11
**Memory**: 512 MB
**Timeout**: 10 minutes

**Environment Variables**:
- `CLIENTS_TABLE`: `siesa-integration-clients`
- `BATCH_SIZE`: `100`

**IAM Permissions**:
- `dynamodb:GetItem`, `dynamodb:UpdateItem` on clients table
- `secretsmanager:GetSecretValue` on `siesa-integration/*`
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**Input Event**:
```json
{
  "client_id": "cliente-a",
  "product_type": "kong",
  "canonical_products": [...],
  "count": 1250,
  "transformation_timestamp": "2025-01-15T10:01:00Z"
}
```

**Output**:
```json
{
  "client_id": "cliente-a",
  "product_type": "kong",
  "status": "success",
  "records_processed": 1250,
  "records_success": 1248,
  "records_failed": 2,
  "failed_records": [
    {
      "id": "PROD999",
      "error": "Kong API returned 400: Invalid EAN format"
    }
  ],
  "load_timestamp": "2025-01-15T10:05:00Z",
  "duration_seconds": 240
}
```

**Key Logic (Adapter Pattern)**:
1. Read client config from DynamoDB to get `product_type`
2. Get product credentials from Secrets Manager
3. **Select appropriate adapter** based on `product_type`:
   - If `product_type == "kong"`: Use `KongAdapter`
   - If `product_type == "wms"`: Use `WMSAdapter`
4. Batch products into groups of 100
5. For each batch:
   - Adapter transforms to product-specific format
   - Adapter calls product-specific API
   - Handle errors with retry (3 attempts)
6. Update DynamoDB with sync status
7. Return summary report

**Adapter Interface**:
```python
class ProductAdapter(ABC):
    @abstractmethod
    def transform_products(self, canonical_products: List[Dict]) -> List[Dict]:
        """Transform canonical model to product-specific format"""
        pass
    
    @abstractmethod
    def load_batch(self, products: List[Dict]) -> Dict:
        """Load batch to product API"""
        pass
    
    @abstractmethod
    def get_api_client(self, credentials: Dict):
        """Initialize product-specific API client"""
        pass
```

**Kong Adapter** (`adapters/kong_adapter.py`):
- Transforms to Kong/RFID format
- Calls Kong monolithic API
- Handles RDS-specific data structures
- Supports RFID tag operations

**WMS Adapter** (`adapters/wms_adapter.py`):
- Transforms to WMS microservices format
- Calls multiple WMS service endpoints
- Handles distributed data structures
- Supports warehouse-specific operations



### 6. Step Functions State Machine

**State Machine Name**: `siesa-integration-workflow`

**Definition**:
```json
{
  "Comment": "Siesa to Kong Integration Workflow - Multi-Tenant",
  "StartAt": "ExtractFromSiesa",
  "States": {
    "ExtractFromSiesa": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:224874703567:function:siesa-integration-extractor",
      "Parameters": {
        "client_id.$": "$.client_id",
        "sync_type.$": "$.sync_type"
      },
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "NotifyFailure",
          "ResultPath": "$.error"
        }
      ],
      "Next": "TransformData"
    },
    "TransformData": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:224874703567:function:siesa-integration-transformer",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "NotifyFailure",
          "ResultPath": "$.error"
        }
      ],
      "Next": "LoadToKong"
    },
    "LoadToKong": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:us-east-1:224874703567:function:siesa-integration-loader",
      "Retry": [
        {
          "ErrorEquals": ["States.TaskFailed"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "Next": "NotifyFailure",
          "ResultPath": "$.error"
        }
      ],
      "Next": "LogSuccess"
    },
    "LogSuccess": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:updateItem",
      "Parameters": {
        "TableName": "siesa-integration-clients",
        "Key": {
          "client_id": {
            "S.$": "$.client_id"
          }
        },
        "UpdateExpression": "SET last_sync_status = :status, last_sync_timestamp = :timestamp, last_sync_records = :records",
        "ExpressionAttributeValues": {
          ":status": {"S": "success"},
          ":timestamp": {"S.$": "$.load_timestamp"},
          ":records": {"N.$": "States.Format('{}', $.records_success)"}
        }
      },
      "End": true
    },
    "NotifyFailure": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sns:publish",
      "Parameters": {
        "TopicArn": "arn:aws:sns:us-east-1:224874703567:siesa-integration-alerts",
        "Subject": "Siesa Integration Failed",
        "Message.$": "States.Format('Integration failed for client {}. Error: {}', $.client_id, $.error)"
      },
      "Next": "LogFailure"
    },
    "LogFailure": {
      "Type": "Task",
      "Resource": "arn:aws:states:::dynamodb:updateItem",
      "Parameters": {
        "TableName": "siesa-integration-clients",
        "Key": {
          "client_id": {
            "S.$": "$.client_id"
          }
        },
        "UpdateExpression": "SET last_sync_status = :status, last_sync_timestamp = :timestamp",
        "ExpressionAttributeValues": {
          ":status": {"S": "failed"},
          ":timestamp": {"S.$": "$$.State.EnteredTime"}
        }
      },
      "End": true
    }
  }
}
```



### 7. EventBridge Rules (Per Client)

**Rule Name Pattern**: `siesa-integration-{client_id}-schedule`

**Example for Client A**:
```json
{
  "Name": "siesa-integration-cliente-a-schedule",
  "ScheduleExpression": "rate(6 hours)",
  "State": "ENABLED",
  "Targets": [
    {
      "Arn": "arn:aws:states:us-east-1:224874703567:stateMachine:siesa-integration-workflow",
      "RoleArn": "arn:aws:iam::224874703567:role/siesa-integration-eventbridge-role",
      "Input": "{\"client_id\": \"cliente-a\", \"sync_type\": \"incremental\"}"
    }
  ]
}
```

### 8. CloudWatch Dashboards

**Dashboard Name**: `siesa-integration-monitoring`

**Widgets**:
1. **Execution Success Rate** (per client)
2. **Average Execution Duration**
3. **Records Processed** (time series)
4. **Lambda Errors** (by function)
5. **API Call Latency** (Siesa vs Kong)
6. **Failed Records Count**

### 9. SNS Topic for Alerts

**Topic Name**: `siesa-integration-alerts`

**Subscriptions**:
- Email: `ops-team@empresa.com`
- SMS: `+57-XXX-XXX-XXXX` (optional)

**Alert Triggers**:
- Step Function execution fails
- Lambda function errors exceed threshold
- Sync duration exceeds 30 minutes
- Failed records exceed 5% of total

## Data Models

### Canonical Product Model

```json
{
  "id": "string (required)",
  "external_id": "string (required)",
  "name": "string (required)",
  "display_name": "string (optional)",
  "ean": "string (13 digits, optional)",
  "sku": "string (required)",
  "category": "string (optional)",
  "stock_quantity": "integer (required)",
  "warehouse_location": "string (optional)",
  "rfid_tag_id": "string (optional)",
  "custom:*": "any (optional custom fields)"
}
```

### Field Mappings Configuration (Product-Specific)

**S3 Location**: `s3://siesa-integration-config/`

**Kong Field Mappings** (`field-mappings-kong.json`):
```json
{
  "version": "1.0",
  "product_type": "kong",
  "mappings": {
    "product": {
      "id": {
        "siesa_field": "f_codigo",
        "product_field": "product_id",
        "type": "string",
        "required": true
      },
      "external_id": {
        "siesa_field": "f_codigo_externo",
        "product_field": "external_reference",
        "type": "string",
        "required": true
      },
      "name": {
        "siesa_field": "f_nombre",
        "product_field": "name",
        "type": "string",
        "required": true
      },
      "ean": {
        "siesa_field": "f_ean",
        "product_field": "barcode",
        "type": "string",
        "required": false,
        "validation": "^[0-9]{13}$"
      },
      "stock_quantity": {
        "siesa_field": "f_cantidad",
        "product_field": "quantity",
        "type": "integer",
        "required": true
      },
      "rfid_tag": {
        "siesa_field": "f_tag_rfid",
        "product_field": "rfid_tag_id",
        "type": "string",
        "required": false
      }
    }
  },
  "transformations": {
    "date_format": {
      "from": "YYYY-MM-DD",
      "to": "ISO8601"
    }
  }
}
```

**WMS Field Mappings** (`field-mappings-wms.json`):
```json
{
  "version": "1.0",
  "product_type": "wms",
  "mappings": {
    "product": {
      "id": {
        "siesa_field": "f_codigo",
        "product_field": "item_id",
        "type": "string",
        "required": true
      },
      "external_id": {
        "siesa_field": "f_codigo_externo",
        "product_field": "external_item_code",
        "type": "string",
        "required": true
      },
      "name": {
        "siesa_field": "f_nombre",
        "product_field": "item_name",
        "type": "string",
        "required": true
      },
      "ean": {
        "siesa_field": "f_ean",
        "product_field": "ean_code",
        "type": "string",
        "required": false,
        "validation": "^[0-9]{13}$"
      },
      "stock_quantity": {
        "siesa_field": "f_cantidad",
        "product_field": "available_quantity",
        "type": "integer",
        "required": true
      },
      "warehouse_location": {
        "siesa_field": "f_ubicacion",
        "product_field": "location_code",
        "type": "string",
        "required": true
      },
      "warehouse_zone": {
        "siesa_field": "f_zona",
        "product_field": "zone_id",
        "type": "string",
        "required": false
      }
    }
  },
  "transformations": {
    "date_format": {
      "from": "YYYY-MM-DD",
      "to": "ISO8601"
    },
    "location_format": {
      "from": "A-01-05",
      "to": "A0105"
    }
  }
}
```

**Key Differences**:
- **Kong**: Uses `product_id`, `barcode`, `quantity`, includes `rfid_tag_id`
- **WMS**: Uses `item_id`, `ean_code`, `available_quantity`, includes `location_code` and `zone_id`
- Each product has its own transformation rules
- Field mappings are loaded dynamically based on `field_mappings_key` in client config



## API Integration Specifications

### Siesa API Integration

**Base URL Pattern**: `https://{client-subdomain}.siesa.com/api/v1`

**Authentication**: 
- Method: Bearer Token or API Key
- Header: `Authorization: Bearer {token}`

**Key Endpoints**:
```
GET /inventory/products
  - Query params: page, limit, modified_since
  - Response: Paginated product list

GET /inventory/products/{id}
  - Response: Single product details

GET /inventory/stock
  - Query params: warehouse_id, product_id
  - Response: Stock levels by location
```

**Rate Limiting**:
- 100 requests per minute per client
- Implement exponential backoff on 429 responses

**Pagination**:
- Page-based: `?page=1&limit=100`
- Max 1000 records per request

### Kong (RFID) API Integration

**Base URL Pattern**: `https://{client-subdomain}.kong.com/api/v1`

**Authentication**:
- Method: API Key
- Header: `X-API-Key: {api_key}`

**Architecture**: Monolithic backend with RDS database

**Key Endpoints**:
```
POST /products
  - Body: Array of products (max 100)
  - Response: Created product IDs

PUT /products/{id}
  - Body: Product update
  - Response: Updated product

POST /products/bulk
  - Body: Array of products (max 100)
  - Response: Bulk operation result

POST /rfid/tags
  - Body: RFID tag associations
  - Response: Tag assignment confirmation
```

**Data Format**:
```json
{
  "product_id": "PROD001",
  "external_reference": "SIESA-PROD001",
  "name": "Product Name",
  "barcode": "1234567890123",
  "quantity": 100,
  "rfid_tag_id": "E2801170000002012345678"
}
```

**Error Handling**:
- 400: Validation error - log and skip record
- 401: Authentication error - alert and stop
- 429: Rate limit - retry with backoff
- 500: Server error - retry up to 3 times

### WMS (Microservices) API Integration

**Base URL Pattern**: `https://{client-subdomain}.wms.com/api/v1`

**Authentication**:
- Method: API Key
- Header: `Authorization: Bearer {api_key}`

**Architecture**: Microservices with distributed AWS services

**Key Endpoints**:
```
POST /inventory/items
  - Body: Array of inventory items (max 100)
  - Response: Created item IDs

PUT /inventory/items/{id}
  - Body: Item update
  - Response: Updated item

POST /inventory/items/bulk
  - Body: Array of items (max 100)
  - Response: Bulk operation result

POST /warehouse/locations
  - Body: Location assignments
  - Response: Location confirmation

GET /warehouse/zones
  - Response: Available warehouse zones
```

**Data Format**:
```json
{
  "item_id": "ITEM001",
  "external_item_code": "SIESA-ITEM001",
  "item_name": "Item Name",
  "ean_code": "1234567890123",
  "available_quantity": 100,
  "location_code": "A0105",
  "zone_id": "ZONE-A"
}
```

**Error Handling**:
- 400: Validation error - log and skip record
- 401: Authentication error - alert and stop
- 429: Rate limit - retry with backoff
- 500: Server error - retry up to 3 times
- 503: Service unavailable - retry with exponential backoff

## Product Adapter Architecture

### Adapter Pattern Implementation

The Loader Lambda uses the **Adapter Pattern** to support multiple products without code duplication. Each product has its own adapter that implements a common interface.

### Directory Structure

```
src/
├── adapters/
│   ├── __init__.py
│   ├── base_adapter.py          # Abstract base class
│   ├── kong_adapter.py          # Kong/RFID implementation
│   └── wms_adapter.py           # WMS implementation
├── loader.py                    # Main loader Lambda
└── utils/
    ├── api_client.py
    └── retry_handler.py
```

### Base Adapter Interface

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ProductAdapter(ABC):
    """Base adapter interface for all products"""
    
    def __init__(self, credentials: Dict[str, Any], config: Dict[str, Any]):
        self.credentials = credentials
        self.config = config
        self.api_client = self.get_api_client()
    
    @abstractmethod
    def get_api_client(self):
        """Initialize product-specific API client"""
        pass
    
    @abstractmethod
    def transform_products(self, canonical_products: List[Dict]) -> List[Dict]:
        """Transform canonical model to product-specific format"""
        pass
    
    @abstractmethod
    def load_batch(self, products: List[Dict]) -> Dict:
        """Load batch to product API and return results"""
        pass
    
    @abstractmethod
    def validate_product(self, product: Dict) -> tuple[bool, str]:
        """Validate product for product-specific requirements"""
        pass
```

### Kong Adapter Implementation

```python
class KongAdapter(ProductAdapter):
    """Adapter for Kong (RFID) product"""
    
    def get_api_client(self):
        return KongAPIClient(
            base_url=self.credentials['api_url'],
            api_key=self.credentials['api_key']
        )
    
    def transform_products(self, canonical_products: List[Dict]) -> List[Dict]:
        """Transform to Kong format"""
        kong_products = []
        for product in canonical_products:
            kong_products.append({
                'product_id': product['id'],
                'external_reference': product['external_id'],
                'name': product['name'],
                'barcode': product.get('ean'),
                'quantity': product['stock_quantity'],
                'rfid_tag_id': product.get('rfid_tag_id')
            })
        return kong_products
    
    def load_batch(self, products: List[Dict]) -> Dict:
        """Load batch to Kong API"""
        response = self.api_client.post('/products/bulk', json=products)
        return {
            'success': response.status_code == 200,
            'records_processed': len(products),
            'response': response.json()
        }
    
    def validate_product(self, product: Dict) -> tuple[bool, str]:
        """Kong-specific validation"""
        if not product.get('product_id'):
            return False, "Missing product_id"
        if not product.get('name'):
            return False, "Missing name"
        return True, ""
```

### WMS Adapter Implementation

```python
class WMSAdapter(ProductAdapter):
    """Adapter for WMS (Microservices) product"""
    
    def get_api_client(self):
        return WMSAPIClient(
            base_url=self.credentials['api_url'],
            api_key=self.credentials['api_key'],
            service_endpoints=self.credentials.get('service_endpoints', {})
        )
    
    def transform_products(self, canonical_products: List[Dict]) -> List[Dict]:
        """Transform to WMS format"""
        wms_items = []
        for product in canonical_products:
            wms_items.append({
                'item_id': product['id'],
                'external_item_code': product['external_id'],
                'item_name': product['name'],
                'ean_code': product.get('ean'),
                'available_quantity': product['stock_quantity'],
                'location_code': product.get('warehouse_location'),
                'zone_id': product.get('warehouse_zone')
            })
        return wms_items
    
    def load_batch(self, products: List[Dict]) -> Dict:
        """Load batch to WMS API (may call multiple microservices)"""
        # First, create/update items
        items_response = self.api_client.post('/inventory/items/bulk', json=products)
        
        # Then, update locations if needed
        locations = [p for p in products if p.get('location_code')]
        if locations:
            location_response = self.api_client.post('/warehouse/locations', json=locations)
        
        return {
            'success': items_response.status_code == 200,
            'records_processed': len(products),
            'response': items_response.json()
        }
    
    def validate_product(self, product: Dict) -> tuple[bool, str]:
        """WMS-specific validation"""
        if not product.get('item_id'):
            return False, "Missing item_id"
        if not product.get('item_name'):
            return False, "Missing item_name"
        if not product.get('location_code'):
            return False, "Missing location_code (required for WMS)"
        return True, ""
```

### Adapter Factory

```python
class AdapterFactory:
    """Factory to create appropriate adapter based on product type"""
    
    @staticmethod
    def create_adapter(product_type: str, credentials: Dict, config: Dict) -> ProductAdapter:
        if product_type == 'kong':
            return KongAdapter(credentials, config)
        elif product_type == 'wms':
            return WMSAdapter(credentials, config)
        else:
            raise ValueError(f"Unknown product type: {product_type}")
```

### Loader Lambda Integration

```python
def lambda_handler(event, context):
    client_id = event['client_id']
    product_type = event['product_type']
    canonical_products = event['canonical_products']
    
    # Get client config and credentials
    client_config = get_client_config(client_id)
    credentials = get_product_credentials(client_config['product_credentials_secret'])
    
    # Create appropriate adapter
    adapter = AdapterFactory.create_adapter(
        product_type=product_type,
        credentials=credentials,
        config=client_config
    )
    
    # Transform and load
    product_data = adapter.transform_products(canonical_products)
    
    # Process in batches
    batch_size = int(os.environ.get('BATCH_SIZE', 100))
    results = []
    
    for i in range(0, len(product_data), batch_size):
        batch = product_data[i:i+batch_size]
        result = adapter.load_batch(batch)
        results.append(result)
    
    return aggregate_results(results)
```

### Benefits of Adapter Pattern

1. **Single Responsibility**: Each adapter handles only its product's logic
2. **Open/Closed Principle**: Easy to add new products without modifying existing code
3. **Testability**: Each adapter can be tested independently
4. **Maintainability**: Product-specific changes are isolated
5. **Scalability**: New products (e.g., future "TMS" product) can be added easily

## Security Design

### IAM Roles and Policies

**Lambda Execution Role**: `siesa-integration-lambda-role`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:224874703567:table/siesa-integration-clients"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:224874703567:secret:siesa-integration/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::siesa-integration-config/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:224874703567:log-group:/aws/lambda/siesa-integration-*"
    }
  ]
}
```

**Step Functions Execution Role**: `siesa-integration-stepfunctions-role`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:us-east-1:224874703567:function:siesa-integration-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:224874703567:table/siesa-integration-clients"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sns:Publish"
      ],
      "Resource": "arn:aws:sns:us-east-1:224874703567:siesa-integration-alerts"
    }
  ]
}
```

### Encryption

**Data at Rest**:
- DynamoDB: Encrypted with AWS managed KMS key
- Secrets Manager: Encrypted with AWS managed KMS key
- CloudWatch Logs: Encrypted with KMS key `alias/siesa-integration-logs`

**Data in Transit**:
- All API calls use TLS 1.3
- No credentials in logs or error messages

## Deployment Strategy

### Multi-Environment Setup

**Test Environment**:
- Deploy to test client account first
- Use test Siesa and Kong instances
- Validate with sample data
- Run integration tests

**Production Environment**:
- Deploy to principal account (224874703567)
- Configure production client credentials
- Enable CloudWatch alarms
- Monitor first sync closely

### Deployment Steps

1. **Infrastructure Deployment** (CloudFormation)
   - DynamoDB table
   - Lambda functions
   - Step Functions state machine
   - IAM roles
   - CloudWatch log groups
   - SNS topic

2. **Configuration Setup**
   - Upload field mappings to S3
   - Create client entries in DynamoDB
   - Store credentials in Secrets Manager

3. **EventBridge Rules**
   - Create schedule rules per client
   - Configure input payloads

4. **Validation**
   - Manual test execution
   - Verify logs
   - Check data in Kong

### Rollback Plan

If deployment fails:
1. CloudFormation automatic rollback
2. Restore previous stack version
3. Verify no data corruption
4. Review logs for root cause



## Monitoring and Observability

### CloudWatch Metrics

**Custom Metrics**:
- `SyncDuration` (per client)
- `RecordsProcessed` (per client)
- `RecordsFailed` (per client)
- `APILatency` (Siesa vs Kong)
- `SyncSuccessRate` (per client)

**Metric Dimensions**:
- `ClientId`
- `SyncType` (initial, incremental)
- `Environment` (test, prod)

### CloudWatch Alarms

**Critical Alarms**:
1. **Sync Failure Rate > 10%**
   - Metric: `SyncSuccessRate`
   - Threshold: < 90%
   - Action: SNS notification

2. **Lambda Errors > 5 in 5 minutes**
   - Metric: `Errors`
   - Threshold: > 5
   - Action: SNS notification

3. **Step Function Execution Failed**
   - Metric: `ExecutionsFailed`
   - Threshold: > 0
   - Action: SNS notification

4. **Sync Duration > 30 minutes**
   - Metric: `SyncDuration`
   - Threshold: > 1800 seconds
   - Action: SNS notification

### Logging Strategy

**Log Levels**:
- `ERROR`: Failures requiring immediate attention
- `WARN`: Validation errors, retries
- `INFO`: Sync start/end, record counts
- `DEBUG`: Detailed API calls (test only)

**Log Format** (JSON):
```json
{
  "timestamp": "2025-01-15T10:00:00Z",
  "level": "INFO",
  "client_id": "cliente-a",
  "component": "extractor",
  "message": "Starting data extraction",
  "metadata": {
    "sync_type": "incremental",
    "last_sync": "2025-01-15T04:00:00Z"
  }
}
```

**Log Retention**:
- Production: 30 days
- Test: 7 days

## Testing Strategy

### Unit Tests

**Coverage Target**: 80%

**Test Files**:
- `test_extractor.py`: Siesa API calls, pagination, error handling
- `test_transformer.py`: Field mappings, validation, data types
- `test_loader.py`: Kong API calls, batching, retries

**Mocking**:
- Mock Siesa API responses
- Mock Kong API responses
- Mock DynamoDB and Secrets Manager

### Integration Tests

**Test Scenarios**:
1. **Happy Path**: Full sync with 100 products
2. **Pagination**: Sync with 2500 products (multiple pages)
3. **Partial Failure**: Some products fail validation
4. **API Errors**: Siesa returns 500, verify retry
5. **Rate Limiting**: Kong returns 429, verify backoff
6. **Incremental Sync**: Only modified records

**Test Environment**:
- Use Siesa sandbox API
- Use Kong test instance
- Separate DynamoDB table for tests

### Performance Tests

**Load Test**:
- 10,000 products
- Target: < 2 hours
- Monitor Lambda memory and duration

**Concurrency Test**:
- 3 clients syncing simultaneously
- Verify no resource contention
- Check Lambda throttling

## Operational Procedures

### Adding a New Client

**Steps**:

#### For Kong (RFID) Client

1. Create DynamoDB entry:
```bash
aws dynamodb put-item \
  --table-name siesa-integration-clients \
  --item file://cliente-kong-config.json \
  --profile principal
```

**cliente-kong-config.json**:
```json
{
  "client_id": {"S": "cliente-c"},
  "client_name": {"S": "Empresa C S.A."},
  "enabled": {"BOOL": true},
  "product_type": {"S": "kong"},
  "siesa_api_url": {"S": "https://cliente-c.siesa.com/api"},
  "siesa_credentials_secret": {"S": "siesa-integration/cliente-c/siesa"},
  "product_api_url": {"S": "https://cliente-c.kong.com/api"},
  "product_credentials_secret": {"S": "siesa-integration/cliente-c/kong"},
  "field_mappings_key": {"S": "field-mappings-kong.json"},
  "sync_schedule": {"S": "rate(6 hours)"}
}
```

2. Store Siesa credentials:
```bash
aws secretsmanager create-secret \
  --name siesa-integration/cliente-c/siesa \
  --secret-string file://cliente-c-siesa-creds.json \
  --profile principal
```

3. Store Kong credentials:
```bash
aws secretsmanager create-secret \
  --name siesa-integration/cliente-c/kong \
  --secret-string file://cliente-c-kong-creds.json \
  --profile principal
```

**cliente-c-kong-creds.json**:
```json
{
  "product_type": "kong",
  "api_url": "https://cliente-c.kong.com/api",
  "api_key": "kong_api_key_here",
  "tenant_id": "cliente-c"
}
```

#### For WMS Client

1. Create DynamoDB entry:
```bash
aws dynamodb put-item \
  --table-name siesa-integration-clients \
  --item file://cliente-wms-config.json \
  --profile principal
```

**cliente-wms-config.json**:
```json
{
  "client_id": {"S": "cliente-d"},
  "client_name": {"S": "Empresa D S.A."},
  "enabled": {"BOOL": true},
  "product_type": {"S": "wms"},
  "siesa_api_url": {"S": "https://cliente-d.siesa.com/api"},
  "siesa_credentials_secret": {"S": "siesa-integration/cliente-d/siesa"},
  "product_api_url": {"S": "https://cliente-d.wms.com/api"},
  "product_credentials_secret": {"S": "siesa-integration/cliente-d/wms"},
  "field_mappings_key": {"S": "field-mappings-wms.json"},
  "sync_schedule": {"S": "rate(4 hours)"}
}
```

2. Store Siesa credentials:
```bash
aws secretsmanager create-secret \
  --name siesa-integration/cliente-d/siesa \
  --secret-string file://cliente-d-siesa-creds.json \
  --profile principal
```

3. Store WMS credentials:
```bash
aws secretsmanager create-secret \
  --name siesa-integration/cliente-d/wms \
  --secret-string file://cliente-d-wms-creds.json \
  --profile principal
```

**cliente-d-wms-creds.json**:
```json
{
  "product_type": "wms",
  "api_url": "https://cliente-d.wms.com/api",
  "api_key": "wms_api_key_here",
  "tenant_id": "cliente-d",
  "service_endpoints": {
    "inventory": "https://cliente-d.wms.com/inventory",
    "warehouse": "https://cliente-d.wms.com/warehouse"
  }
}
```

#### Common Steps (Both Products)

4. Create EventBridge rule:
```bash
aws events put-rule \
  --name siesa-integration-{client-id}-schedule \
  --schedule-expression "rate(6 hours)" \
  --profile principal

aws events put-targets \
  --rule siesa-integration-{client-id}-schedule \
  --targets file://{client-id}-target.json \
  --profile principal
```

5. Test manually:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:...:stateMachine:siesa-integration-workflow \
  --input '{"client_id": "{client-id}", "sync_type": "initial"}' \
  --profile principal
```

### Troubleshooting Guide

**Issue**: Sync fails with "Authentication Error"
- **Check**: Verify credentials in Secrets Manager
- **Fix**: Update secret with correct API key

**Issue**: Sync takes > 30 minutes
- **Check**: Number of records, API latency
- **Fix**: Increase Lambda timeout, optimize batch size

**Issue**: High failure rate for specific products
- **Check**: Validation errors in logs
- **Fix**: Update field mappings, fix data quality in Siesa

**Issue**: Kong API returns 429 (rate limit)
- **Check**: Batch size, request frequency
- **Fix**: Reduce batch size, increase delay between batches

## Cost Estimation

### Monthly Cost (per client)

**Assumptions**:
- 10,000 products
- Sync every 6 hours (4 times/day)
- 120 syncs per month

**AWS Services**:
- Lambda: ~$5/month (3 functions × 120 executions)
- Step Functions: ~$2/month (120 executions)
- DynamoDB: ~$1/month (minimal reads/writes)
- Secrets Manager: ~$1/month (2 secrets)
- CloudWatch: ~$3/month (logs + metrics)
- S3: ~$0.50/month (config files)

**Total per client**: ~$12.50/month
**Total for 10 clients**: ~$125/month

**Note**: Costs scale linearly with number of clients and sync frequency.

## Success Criteria

### Technical Metrics

- ✅ Sync success rate > 95% (for both Kong and WMS)
- ✅ Average sync duration < 15 minutes (for 10,000 products)
- ✅ Lambda cold start < 3 seconds
- ✅ API error rate < 1%
- ✅ Code coverage > 80%
- ✅ Adapter pattern supports both products without code duplication

### Business Metrics

- ✅ Support 10+ clients simultaneously (mixed Kong and WMS)
- ✅ Add new client in < 30 minutes (regardless of product type)
- ✅ Zero data loss
- ✅ Sync latency < 6 hours
- ✅ 99.9% uptime
- ✅ Easy addition of future products (e.g., TMS) through new adapters

### Product-Specific Metrics

**Kong (RFID)**:
- ✅ RFID tag association success rate > 98%
- ✅ RDS connection pool efficiency > 90%

**WMS (Microservices)**:
- ✅ Warehouse location assignment success rate > 98%
- ✅ Microservice call distribution balanced across services

