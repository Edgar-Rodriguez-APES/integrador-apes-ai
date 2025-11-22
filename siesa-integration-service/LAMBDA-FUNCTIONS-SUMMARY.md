# Lambda Functions - Resumen de Implementación

## 📋 Resumen General

Se implementaron 3 Lambda functions en Python 3.11 siguiendo el patrón de Product Adapter para soportar múltiples productos (Kong prioritario, WMS en Semana 2).

---

## 1️⃣ Extractor Lambda

**Ubicación**: `src/lambdas/extractor/handler.py`

### Propósito
Extrae datos de productos desde Siesa ERP API.

### Características Principales

**Autenticación Siesa**:
- Bearer Token + ConniKey + ConniToken
- Método: POST `/auth/login`
- Headers personalizados para Siesa

**Paginación Automática**:
- Formato Siesa: `paginacion=numPag=1|tamPag=100`
- Itera automáticamente hasta obtener todos los productos
- Límite de seguridad: 1000 páginas

**Sync Incremental**:
- Parámetro `sync_type`: 'initial' o 'incremental'
- Usa `lastSyncTimestamp` para obtener solo cambios
- Filtro: `fechaModificacion` en query params

**Retry Logic**:
- 3 intentos con exponential backoff (factor 2)
- Maneja códigos: 429, 500, 502, 503, 504
- Timeout: 60 segundos por request

**Input Event**:
```json
{
  "client_id": "parchita-staging",
  "sync_type": "incremental"
}
```

**Output**:
```json
{
  "client_id": "parchita-staging",
  "tenantId": "parchita-staging",
  "productType": "KONG_RFID",
  "products": [...],
  "count": 1250,
  "sync_type": "incremental",
  "extraction_timestamp": "2025-01-21T10:00:00Z",
  "status": "success"
}
```

### Flujo de Ejecución

1. Obtener configuración del cliente desde DynamoDB
2. Verificar que el cliente esté habilitado
3. Obtener credenciales de Siesa desde Secrets Manager
4. Autenticar con Siesa API
5. Extraer productos con paginación
6. Retornar datos crudos de Siesa

### Manejo de Errores

- Logs detallados en CloudWatch
- Retorna status 'error' con mensaje descriptivo
- No falla silenciosamente

---

## 2️⃣ Transformer Lambda

**Ubicación**: `src/lambdas/transformer/handler.py`

### Propósito
Transforma datos de Siesa a modelo canónico usando field mappings configurables.

### Características Principales

**Field Mappings Dinámicos**:
- Carga desde S3: `field-mappings-kong.json` o `field-mappings-wms.json`
- Selección automática según `productType`
- Formato JSON con reglas de mapeo

**Conversión de Tipos**:
- `string`: Conversión a texto
- `number/integer`: Maneja separadores decimales (`,` → `.`)
- `float`: Números decimales
- `boolean`: Reconoce 'true', '1', 'yes', 'si', 's'
- `object`: Parse JSON
- `array`: Parse JSON o convierte valor único a array

**Transformaciones**:
- **format**: Conversión de formatos (ej: fecha YYYY-MM-DD → ISO8601)
- **calculation**: Cálculos matemáticos
- **lookup**: Tablas de búsqueda
- **conditional**: Transformaciones condicionales

**Validación**:
- Campos requeridos: `id`, `external_id`, `name`, `sku`
- Patrones regex para validación
- Warnings para datos inválidos (no detiene el proceso)

**Campos Custom**:
- Prefijo `custom:` o `f120_custom_`
- Se preservan en el modelo canónico
- Útil para campos específicos del cliente

**Input Event**:
```json
{
  "client_id": "parchita-staging",
  "productType": "KONG_RFID",
  "products": [...],
  "extraction_timestamp": "2025-01-21T10:00:00Z"
}
```

**Output**:
```json
{
  "client_id": "parchita-staging",
  "tenantId": "parchita-staging",
  "productType": "KONG_RFID",
  "canonical_products": [...],
  "count": 1248,
  "extraction_timestamp": "2025-01-21T10:00:00Z",
  "transformation_timestamp": "2025-01-21T10:01:00Z",
  "validation_errors": ["Product 5: Missing required field: sku"],
  "status": "success"
}
```

### Modelo Canónico

```json
{
  "id": "PROD001",
  "external_id": "SIESA-PROD001",
  "name": "Product Name",
  "display_name": "Display Name",
  "ean": "1234567890123",
  "sku": "SKU001",
  "category": "Electronics",
  "stock_quantity": 100,
  "warehouse_location": "A-01-05",
  "rfid_tag_id": "E280...",
  "custom:color": "Blue"
}
```

### Flujo de Ejecución

1. Determinar archivo de field mappings según `productType`
2. Cargar mappings desde S3
3. Para cada producto:
   - Aplicar field mappings
   - Convertir tipos de datos
   - Validar con regex (si aplica)
   - Aplicar transformaciones
   - Manejar campos custom
4. Validar productos transformados
5. Retornar productos en modelo canónico

---

## 3️⃣ Loader Lambda (Product Adapter Pattern)

**Ubicación**: `src/lambdas/loader/handler.py`

### Propósito
Carga datos transformados a las APIs de productos usando el patrón de adaptador.

### Arquitectura de Adapters

```
loader/
├── handler.py                    # Handler principal
├── adapters/
│   ├── base_adapter.py          # Clase abstracta base
│   ├── kong_adapter.py          # Implementación Kong
│   ├── adapter_factory.py       # Factory pattern
│   └── __init__.py
```

### Base Adapter (Abstracto)

**Métodos Abstractos**:
- `get_api_client()`: Inicializa cliente API
- `transform_products()`: Transforma a formato específico
- `load_batch()`: Carga batch a API
- `validate_product()`: Valida producto

**Método Concreto**:
- `process_batch()`: Orquesta todo el proceso
  - Transforma productos
  - Valida productos
  - Procesa en batches
  - Maneja errores
  - Retorna resumen

### Kong Adapter

**Autenticación**:
- Djoser token-based auth
- Endpoint: POST `/auth/token/login/`
- Header: `Authorization: Token {token}`

**API Endpoint**:
- POST `/inventory/skus/` (bulk upsert)
- Soporta crear y actualizar en una sola operación

**Transformación a Kong**:
```json
{
  "external_id": "SIESA-PROD001",
  "name": "Product Name",
  "display_name": "Display Name",
  "reference": "SKU001",
  "ean": "1234567890123",
  "is_active": true,
  "type_id": 1,
  "group_id": 10,
  "customer_id": 100,
  "rfid_tag_id": "E280...",
  "properties": {
    "color": "Blue"
  }
}
```

**Validación Kong**:
- Campos requeridos: `external_id`, `name`
- EAN: 13 dígitos numéricos (si presente)

**Retry Logic**:
- 3 intentos con exponential backoff
- Maneja: 429, 500, 502, 503, 504

### Adapter Factory

**Selección Automática**:
```python
adapter = AdapterFactory.create_adapter(
    product_type='KONG_RFID',  # o 'kong', 'WMS', 'wms'
    credentials=credentials,
    config=config
)
```

**Productos Soportados**:
- ✅ Kong / KONG_RFID (Implementado)
- ⏳ WMS (Semana 2)

### Input Event

```json
{
  "client_id": "parchita-staging",
  "productType": "KONG_RFID",
  "canonical_products": [...],
  "transformation_timestamp": "2025-01-21T10:01:00Z"
}
```

### Output

```json
{
  "client_id": "parchita-staging",
  "tenantId": "parchita-staging",
  "productType": "KONG_RFID",
  "status": "success",
  "records_processed": 1248,
  "records_success": 1246,
  "records_failed": 2,
  "validation_errors": [],
  "batch_results": [
    {
      "batch_number": 1,
      "processed": 100,
      "success": 100,
      "failed": 0
    }
  ],
  "transformation_timestamp": "2025-01-21T10:01:00Z",
  "load_timestamp": "2025-01-21T10:05:00Z",
  "duration_seconds": 240
}
```

### Flujo de Ejecución

1. Obtener configuración del cliente desde DynamoDB
2. Obtener credenciales del producto desde Secrets Manager
3. Crear adapter apropiado usando Factory
4. Procesar productos en batches (100 por batch):
   - Transformar a formato específico del producto
   - Validar productos
   - Cargar batch a API
   - Manejar errores con retry
5. Actualizar sync status en DynamoDB
6. Retornar resumen detallado

### Actualización de Estado

Actualiza en DynamoDB:
- `lastSyncTimestamp`: Timestamp de la sync
- `lastSyncStatus`: 'success', 'partial', 'failed'
- `lastSyncRecords`: Número de registros exitosos

---

## 4️⃣ Common Utilities

**Ubicación**: `src/lambdas/common/aws_utils.py`

### Utilidades Compartidas

**DynamoDB**:
- `get_dynamodb_item()`: Obtener item
- `put_dynamodb_item()`: Crear item
- `update_dynamodb_item()`: Actualizar item

**Secrets Manager**:
- `get_secret()`: Obtener secret y parsear JSON

**S3**:
- `get_s3_object()`: Obtener objeto
- `put_s3_object()`: Subir objeto

**Características**:
- Singleton pattern para clientes AWS
- Manejo de errores consistente
- Logs detallados

---

## 🔄 Flujo Completo de Datos

```
┌─────────────────────────────────────────────────────────────┐
│ 1. EXTRACTOR LAMBDA                                         │
│                                                             │
│ Input: { client_id, sync_type }                            │
│   ↓                                                         │
│ • Get client config from DynamoDB                          │
│ • Get Siesa credentials from Secrets Manager              │
│ • Authenticate with Siesa API                             │
│ • Extract products with pagination                         │
│   ↓                                                         │
│ Output: { products: [...], count, extraction_timestamp }   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. TRANSFORMER LAMBDA                                       │
│                                                             │
│ Input: { products, productType }                           │
│   ↓                                                         │
│ • Load field mappings from S3                              │
│ • Transform each product:                                  │
│   - Apply field mappings                                   │
│   - Convert data types                                     │
│   - Validate required fields                               │
│   - Apply transformations                                  │
│   ↓                                                         │
│ Output: { canonical_products: [...], validation_errors }   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. LOADER LAMBDA (Product Adapter Pattern)                 │
│                                                             │
│ Input: { canonical_products, productType }                 │
│   ↓                                                         │
│ • Get product credentials from Secrets Manager            │
│ • Create adapter (Kong/WMS) via Factory                   │
│ • Process in batches:                                      │
│   - Transform to product format                            │
│   - Validate product-specific rules                        │
│   - Load batch to product API                              │
│   - Retry on failures                                      │
│ • Update sync status in DynamoDB                           │
│   ↓                                                         │
│ Output: { records_success, records_failed, batch_results } │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Configuración Requerida

### DynamoDB (Config Table)

```json
{
  "tenantId": "parchita-staging",
  "configType": "PRODUCT_CONFIG",
  "productType": "KONG_RFID",
  "enabled": "true",
  "siesaConfig": {
    "baseUrl": "https://serviciosqa.siesacloud.com/api/siesa/v3/",
    "credentialsSecretArn": "arn:aws:secretsmanager:...:secret:siesa-integration/parchita-staging/siesa"
  },
  "productConfig": {
    "baseUrl": "https://api-staging.technoapes.io/",
    "credentialsSecretArn": "arn:aws:secretsmanager:...:secret:siesa-integration/parchita-staging/kong",
    "type_id": 1,
    "group_id": 10,
    "customer_id": 100
  }
}
```

### Secrets Manager

**Siesa Credentials**:
```json
{
  "baseUrl": "https://serviciosqa.siesacloud.com/api/siesa/v3/",
  "username": "siesa_user",
  "password": "siesa_pass",
  "conniKey": "key123",
  "conniToken": "token456"
}
```

**Kong Credentials**:
```json
{
  "productType": "kong",
  "baseUrl": "https://api-staging.technoapes.io/",
  "username": "kong_user",
  "password": "kong_pass"
}
```

### S3 (Field Mappings)

**Bucket**: `siesa-integration-config-dev-224874703567`

**File**: `field-mappings-kong.json`
```json
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
      }
    }
  }
}
```

---

## 🧪 Testing

### Test Extractor

```python
event = {
    "client_id": "parchita-staging",
    "sync_type": "initial"
}
```

### Test Transformer

```python
event = {
    "client_id": "parchita-staging",
    "productType": "KONG_RFID",
    "products": [
        {
            "f120_id": "PROD001",
            "f120_descripcion": "Product Name",
            "f120_referencia": "SKU001"
        }
    ]
}
```

### Test Loader

```python
event = {
    "client_id": "parchita-staging",
    "productType": "KONG_RFID",
    "canonical_products": [
        {
            "id": "PROD001",
            "external_id": "SIESA-PROD001",
            "name": "Product Name",
            "sku": "SKU001"
        }
    ]
}
```

---

## ✅ Checklist de Revisión

### Extractor
- [ ] Autenticación Siesa correcta
- [ ] Paginación funciona
- [ ] Retry logic implementado
- [ ] Sync incremental soportado
- [ ] Manejo de errores robusto

### Transformer
- [ ] Field mappings desde S3
- [ ] Conversión de tipos correcta
- [ ] Validación de campos requeridos
- [ ] Transformaciones funcionan
- [ ] Campos custom preservados

### Loader
- [ ] Product Adapter Pattern implementado
- [ ] Kong Adapter funcional
- [ ] Autenticación Kong correcta
- [ ] Batch processing funciona
- [ ] Retry logic implementado
- [ ] Estado actualizado en DynamoDB
- [ ] Extensible para WMS

### Common
- [ ] Utilidades AWS funcionan
- [ ] Singleton pattern correcto
- [ ] Manejo de errores consistente

---

## 🚀 Próximos Pasos

1. **Revisar código** ✓ (Estás aquí)
2. **Crear field mappings** en S3
3. **Desplegar Lambdas** a AWS
4. **Crear Step Functions** workflow
5. **Testing end-to-end**

---

**Fecha**: 2025-01-21  
**Estado**: Código implementado, pendiente despliegue  
**Prioridad**: Kong-Siesa (WMS en Semana 2)
