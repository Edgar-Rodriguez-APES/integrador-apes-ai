# Arquitectura de Cuentas AWS - Integración Siesa

**Fecha**: 2025-01-21  
**Versión**: 1.0

---

## 📊 Resumen Ejecutivo

La integración Siesa utiliza una arquitectura **centralizada** donde:
- **Un servicio de integración** reside en la cuenta principal de APES
- **Múltiples clientes** con sus productos (Kong/WMS) residen en sus propias cuentas AWS
- El servicio de integración se conecta a las APIs de los productos mediante HTTPS

---

## 🏗️ Arquitectura de Cuentas

### Cuenta Principal (APES - Integración)

**Account ID**: `224874703567`  
**Región**: `us-east-1`  
**Propósito**: Servicio de integración centralizado multi-tenant

#### Componentes Desplegados

```
224874703567 (Cuenta Principal APES)
│
├── Lambda Functions
│   ├── Extractor (Siesa → Canonical)
│   ├── Transformer (Canonical → Product)
│   └── Loader (Product API Writer)
│
├── Step Functions
│   └── Orchestration Workflow (Extract → Transform → Load)
│
├── DynamoDB Tables
│   ├── Config Table (tenant configs, product types, mappings)
│   ├── Sync State Table (sync status, progress)
│   └── Audit Table (operation logs)
│
├── S3 Buckets
│   └── Config Bucket (field-mappings-kong.json, field-mappings-wms.json)
│
├── Secrets Manager
│   ├── Siesa Credentials (per tenant)
│   ├── Kong Credentials (per tenant)
│   └── WMS Credentials (per tenant)
│
├── CloudWatch
│   ├── Log Groups (Lambda, Step Functions, API Gateway)
│   ├── Metrics (custom metrics)
│   └── Alarms (failures, latency, errors)
│
├── API Gateway
│   └── Management API (tenant CRUD, sync triggers, status)
│
└── EventBridge
    └── Scheduled Rules (cron jobs per tenant)
```

#### Responsabilidades
- ✅ Extraer datos de Siesa ERP
- ✅ Transformar datos según field mappings
- ✅ Cargar datos a productos (Kong/WMS)
- ✅ Gestionar configuraciones multi-tenant
- ✅ Monitorear y auditar operaciones
- ✅ Manejar errores y reintentos

---

### Cuentas Cliente (Parchita)

#### Cuenta Staging

**Account ID**: `555569220783`  
**Región**: `us-east-1` (a confirmar)  
**Propósito**: Ambiente de pruebas del cliente Parchita

**Componentes**:
```
555569220783 (Cliente Parchita - Staging)
│
├── Kong RFID (Staging)
│   ├── API Base URL: https://api-staging.technoapes.io/
│   ├── Backend: Monolito Django
│   ├── Database: RDS PostgreSQL
│   └── Endpoints: /inventory/skus/
│
└── WMS (Staging) - Si aplica
    ├── API Base URL: (a confirmar)
    ├── Backend: Microservicios
    └── Endpoints: /products, /items, etc.
```

**Uso**:
- Testing de integración
- Validación de datos
- Pruebas de carga
- Desarrollo de nuevas features

---

#### Cuenta Producción

**Account ID**: `901792597114`  
**Región**: `us-east-1` (a confirmar)  
**Propósito**: Ambiente productivo del cliente Parchita

**Componentes**:
```
901792597114 (Cliente Parchita - Producción)
│
├── Kong RFID (Producción)
│   ├── API Base URL: (a confirmar)
│   ├── Backend: Monolito Django
│   ├── Database: RDS PostgreSQL
│   └── Endpoints: /inventory/skus/
│
└── WMS (Producción) - Si aplica
    ├── API Base URL: (a confirmar)
    ├── Backend: Microservicios
    └── Endpoints: /products, /items, etc.
```

**Uso**:
- Operaciones reales
- Datos de producción
- SLA crítico
- Monitoreo 24/7

---

## 🔄 Flujo de Datos

### Flujo Completo de Sincronización

```
┌─────────────────────────────────────────────────────────────────┐
│                    Siesa ERP (Externo)                          │
│         https://serviciosqa.siesacloud.com/api/siesa/v3/       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS (Bearer Token)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│           Cuenta Principal APES (224874703567)                  │
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │  Extractor   │  →   │ Transformer  │  →   │   Loader     │ │
│  │   Lambda     │      │    Lambda    │      │   Lambda     │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│         │                     │                      │         │
│         ↓                     ↓                      ↓         │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Step Functions Workflow                     │ │
│  └──────────────────────────────────────────────────────────┘ │
│         │                                                      │
│         ↓                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  DynamoDB    │  │  S3 Bucket   │  │   Secrets    │       │
│  │   Tables     │  │   Mappings   │  │   Manager    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS (Token/JWT)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Cuentas Cliente Parchita                     │
│                                                                 │
│  ┌──────────────────────────┐  ┌──────────────────────────┐   │
│  │  Staging (555569220783)  │  │  Prod (901792597114)     │   │
│  │                          │  │                          │   │
│  │  Kong API (Staging)      │  │  Kong API (Producción)   │   │
│  │  api-staging.techno...   │  │  (URL a confirmar)       │   │
│  └──────────────────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔐 Seguridad y Conectividad

### Conectividad Entre Cuentas

**Modelo**: HTTPS público (no VPC peering)

**Razón**:
- Las APIs de Kong/WMS son públicas (con autenticación)
- No requiere configuración de red compleja
- Más simple de mantener
- Funciona para múltiples clientes

**Seguridad**:
- ✅ TLS 1.2+ en todas las conexiones
- ✅ Autenticación por tokens/JWT
- ✅ Credenciales en Secrets Manager
- ✅ IAM roles con least privilege
- ✅ Logs de auditoría en CloudWatch
- ✅ Encriptación en reposo (DynamoDB, S3)

### Credenciales por Ambiente

**Staging (555569220783)**:
```json
{
  "siesa": {
    "baseUrl": "https://serviciosqa.siesacloud.com/api/siesa/v3/",
    "username": "test_user",
    "password": "***",
    "conniKey": "***",
    "conniToken": "***"
  },
  "kong": {
    "baseUrl": "https://api-staging.technoapes.io/",
    "username": "***",
    "password": "***"
  }
}
```

**Producción (901792597114)**:
```json
{
  "siesa": {
    "baseUrl": "https://servicios.siesacloud.com/api/siesa/v3/",
    "username": "prod_user",
    "password": "***",
    "conniKey": "***",
    "conniToken": "***"
  },
  "kong": {
    "baseUrl": "https://api.technoapes.io/",
    "username": "***",
    "password": "***"
  }
}
```

---

## 📋 Configuración Multi-Tenant

### Ejemplo: Cliente Parchita Staging

**DynamoDB Config Table**:
```json
{
  "tenantId": "parchita-staging",
  "configType": "PRODUCT_CONFIG",
  "productType": "KONG_RFID",
  "clientAccount": "555569220783",
  "environment": "staging",
  "siesaConfig": {
    "secretArn": "arn:aws:secretsmanager:us-east-1:224874703567:secret:siesa-integration/parchita-staging/siesa"
  },
  "productConfig": {
    "secretArn": "arn:aws:secretsmanager:us-east-1:224874703567:secret:siesa-integration/parchita-staging/kong",
    "baseUrl": "https://api-staging.technoapes.io/",
    "endpoints": {
      "skus": "/inventory/skus/"
    }
  },
  "syncConfig": {
    "schedule": "rate(1 hour)",
    "batchSize": 100,
    "retryAttempts": 3
  },
  "fieldMappingsKey": "field-mappings-kong.json"
}
```

### Ejemplo: Cliente Parchita Producción

**DynamoDB Config Table**:
```json
{
  "tenantId": "parchita-prod",
  "configType": "PRODUCT_CONFIG",
  "productType": "KONG_RFID",
  "clientAccount": "901792597114",
  "environment": "production",
  "siesaConfig": {
    "secretArn": "arn:aws:secretsmanager:us-east-1:224874703567:secret:siesa-integration/parchita-prod/siesa"
  },
  "productConfig": {
    "secretArn": "arn:aws:secretsmanager:us-east-1:224874703567:secret:siesa-integration/parchita-prod/kong",
    "baseUrl": "https://api.technoapes.io/",
    "endpoints": {
      "skus": "/inventory/skus/"
    }
  },
  "syncConfig": {
    "schedule": "rate(30 minutes)",
    "batchSize": 100,
    "retryAttempts": 3
  },
  "fieldMappingsKey": "field-mappings-kong.json"
}
```

---

## 🚀 Deployment Strategy

### Fase 1: Infraestructura Base (Cuenta Principal)

**Cuenta**: `224874703567`

```bash
# Deploy infrastructure
cd siesa-integration-service
export AWS_PROFILE=apes-principal
export AWS_ACCOUNT_ID=224874703567
export ENVIRONMENT=dev

npm run deploy
```

**Recursos Creados**:
- DynamoDB tables
- Lambda functions
- Step Functions
- S3 bucket
- Secrets Manager structure
- CloudWatch logs/alarms
- API Gateway

---

### Fase 2: Configuración Cliente Staging

**Cuenta Principal**: `224874703567`  
**Cliente Target**: `555569220783` (Parchita Staging)

```bash
# Add tenant configuration
python scripts/add-tenant.py \
  --tenant-id parchita-staging \
  --product-type kong \
  --client-account 555569220783 \
  --environment staging \
  --kong-url https://api-staging.technoapes.io/

# Store credentials
python scripts/store-credentials.py \
  --tenant-id parchita-staging \
  --siesa-username test_user \
  --siesa-password *** \
  --kong-username *** \
  --kong-password ***

# Create EventBridge rule
python scripts/create-schedule.py \
  --tenant-id parchita-staging \
  --schedule "rate(1 hour)"
```

---

### Fase 3: Testing con Staging

**Trigger manual sync**:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:224874703567:stateMachine:SiesaIntegration-dev \
  --input '{"tenantId": "parchita-staging"}' \
  --profile apes-principal
```

**Verificar en Kong Staging**:
```bash
# Check SKUs in staging
curl -X GET https://api-staging.technoapes.io/inventory/skus/ \
  -H "Authorization: Token ***"
```

---

### Fase 4: Configuración Cliente Producción

**Cuenta Principal**: `224874703567`  
**Cliente Target**: `901792597114` (Parchita Producción)

```bash
# Add production tenant
python scripts/add-tenant.py \
  --tenant-id parchita-prod \
  --product-type kong \
  --client-account 901792597114 \
  --environment production \
  --kong-url https://api.technoapes.io/

# Store production credentials
python scripts/store-credentials.py \
  --tenant-id parchita-prod \
  --siesa-username prod_user \
  --siesa-password *** \
  --kong-username *** \
  --kong-password ***

# Create production schedule (more frequent)
python scripts/create-schedule.py \
  --tenant-id parchita-prod \
  --schedule "rate(30 minutes)"
```

---

## 📊 Monitoreo Multi-Cuenta

### CloudWatch Dashboard (Cuenta Principal)

**Dashboard**: `SiesaIntegration-Overview`

**Widgets**:
- Sync success rate (por tenant)
- Execution duration (por tenant)
- Records processed (por tenant)
- API errors (por tenant y producto)
- Lambda errors (por función)

**Filtros**:
```
{tenantId = "parchita-staging"}
{tenantId = "parchita-prod"}
{clientAccount = "555569220783"}
{clientAccount = "901792597114"}
```

---

### Alarmas por Ambiente

**Staging Alarms** (menos críticas):
- Failure rate > 20%
- Duration > 60 minutes
- Errors > 10 in 15 minutes

**Production Alarms** (más críticas):
- Failure rate > 10%
- Duration > 30 minutes
- Errors > 5 in 5 minutes
- SNS → PagerDuty

---

## ✅ Checklist de Verificación

### Cuenta Principal (224874703567)

- [ ] Acceso AWS configurado
- [ ] Permisos IAM verificados
- [ ] CloudFormation stack desplegado
- [ ] DynamoDB tables creadas
- [ ] Lambda functions desplegadas
- [ ] Step Functions creado
- [ ] S3 bucket creado
- [ ] Secrets Manager configurado
- [ ] CloudWatch logs funcionando
- [ ] API Gateway desplegado

### Cliente Staging (555569220783)

- [ ] Kong API accesible desde cuenta principal
- [ ] Credenciales Kong staging obtenidas
- [ ] Tenant configuration creada
- [ ] Secrets almacenados
- [ ] EventBridge rule creado
- [ ] Sync manual exitoso
- [ ] Datos verificados en Kong staging

### Cliente Producción (901792597114)

- [ ] Kong API URL confirmada
- [ ] Credenciales Kong producción obtenidas
- [ ] Tenant configuration creada
- [ ] Secrets almacenados
- [ ] EventBridge rule creado
- [ ] Sync manual exitoso
- [ ] Datos verificados en Kong producción
- [ ] Alarmas configuradas
- [ ] Monitoreo 24/7 activo

---

## 🔧 Troubleshooting

### Error: No se puede conectar a Kong API

**Síntoma**: Lambda Loader falla con timeout o connection refused

**Causas posibles**:
1. URL incorrecta
2. Security group bloqueando tráfico
3. API Gateway no accesible públicamente
4. Credenciales incorrectas

**Solución**:
```bash
# Test connectivity from Lambda
aws lambda invoke \
  --function-name SiesaIntegration-Loader-dev \
  --payload '{"test": "connectivity", "url": "https://api-staging.technoapes.io/"}' \
  response.json \
  --profile apes-principal
```

---

### Error: Credenciales no encontradas

**Síntoma**: Lambda falla con "Secret not found"

**Causa**: Secret no existe o nombre incorrecto

**Solución**:
```bash
# List secrets
aws secretsmanager list-secrets \
  --profile apes-principal

# Verify secret name
aws secretsmanager describe-secret \
  --secret-id siesa-integration/parchita-staging/kong \
  --profile apes-principal
```

---

## 📞 Contactos

### Cuenta Principal APES
- **Account ID**: 224874703567
- **Contacto**: [PENDIENTE]
- **Email**: [PENDIENTE]

### Cliente Parchita
- **Staging Account**: 555569220783
- **Production Account**: 901792597114
- **Contacto**: [PENDIENTE]
- **Email**: [PENDIENTE]

---

**Última actualización**: 2025-01-21  
**Próxima revisión**: Después del primer deployment

