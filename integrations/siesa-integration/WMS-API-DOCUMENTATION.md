# WMS (Warehouse Management System) API - Documentación para Integración

## Información General

**Producto**: WMS (Warehouse Management System)  
**Arquitectura**: Microservicios en AWS  
**Colección Postman**: `SIESA_APIs_WMS_Completo.json` (contiene APIs de Siesa, no de WMS)  
**Base URL**: ⚠️ PENDIENTE - Solicitar al equipo WMS

---

## ✅ ESTADO DE DOCUMENTACIÓN

**COMPLETO**: Colección Postman `WMS-Proxy-API.postman_collection.json` analizada exitosamente.

**Información Disponible**:
1. ✅ Colección Postman de WMS APIs
2. ✅ Base URL del ambiente de staging
3. ✅ Método de autenticación
4. ✅ Endpoints para gestión de productos/items
5. ✅ Estructura de datos y campos requeridos
6. ⚠️ Credenciales de prueba (pendiente)

---

## Información General

**Producto**: WMS (Warehouse Management System)  
**Arquitectura**: Microservicios en AWS (API Gateway + Lambda)  
**Colección Postman**: `WMS-Proxy-API.postman_collection.json`  
**Base URL (Staging)**: `https://lbh1n2whxl.execute-api.us-east-1.amazonaws.com/staging`

---

## Autenticación

**✅ CONFIRMADO**

**Método**: JWT Token-based Authentication

**Endpoint de Login**:
```
POST /auth
Content-Type: application/json
```

**Request Body**:
```json
{
  "username": "user.test",
  "password": "mypassword123"
}
```

**Response** (200 OK):
```json
{
  "token": "eyJhbGciOiJIUzI1...",
  "attributes_user": [
    {
      "Name": "sub",
      "Value": null
    },
    {
      "Name": "email_verified",
      "Value": null
    },
    {
      "Name": "email",
      "Value": null
    }
  ]
}
```

**Uso del Token**:
```
Authorization: Bearer {token}
```

**Nota**: El token debe incluirse en todas las peticiones subsecuentes

---

## Módulos Esperados en WMS

Basado en sistemas WMS típicos, se esperan estos módulos:

### 1. Gestión de Bodegas/Almacenes
- Crear/actualizar bodegas
- Consultar bodegas
- Gestión de zonas

### 2. Gestión de Ubicaciones
- Crear/actualizar ubicaciones
- Consultar ubicaciones por bodega
- Asignación de productos a ubicaciones

### 3. Gestión de Productos/Items
- Crear/actualizar items
- Consultar items
- Gestión de lotes
- Gestión de seriales

### 4. Gestión de Inventario
- Consultar inventario disponible
- Movimientos de inventario
- Ajustes de inventario
- Trazabilidad

### 5. Órdenes de Entrada (Inbound)
- Crear órdenes de compra
- Recepciones
- Confirmaciones de entrada
- Putaway

### 6. Órdenes de Salida (Outbound)
- Crear órdenes de venta
- Picking
- Packing
- Despachos

### 7. Transferencias
- Transferencias entre bodegas
- Transferencias entre ubicaciones
- Movimientos internos

### 8. Reportes y Consultas
- Reportes de inventario
- Reportes de movimientos
- Trazabilidad de productos

---

## Endpoints Relevantes para Integración Siesa

### Productos (Products)

**NOTA IMPORTANTE**: En WMS, los productos se denominan "Products" o "Variants".

#### Crear Producto
```
POST /products
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body**:
```json
{
  "name": "Laptop Lenovo Thinkpad",
  "display_name": "Thinkpad X1 Carbon Gen 10",
  "external_id": "PROD-12345",
  "reference_id": "SKU-45678",
  "reception_type": "GENERAL",
  "barcode_type": "EAN",
  "barcode": "1234567890123",
  "status": "ACTIVE",
  "sale_price": 1200,
  "sale_coin": "USD",
  "purchase_price": 900,
  "purchase_coin": "USD",
  "product_image": "https://example.com/img/thinkpad.png",
  "inventory_unit": "UNIT",
  "presentation": "Caja",
  "properties": {
    "volume": 0.5,
    "length": 30,
    "width": 20,
    "large": 3,
    "tall": 2,
    "hight": 2,
    "size": 15,
    "sale_limit_days": 365,
    "weigth": 1.2,
    "is_on_demand": "false"
  },
  "groups": [
    {
      "group_external_id": "ELECTRONICA",
      "group_name": "ELECTRONICA",
      "group_parent_id": null,
      "group_type": "category"
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "id": "817de9763f494b09821c28cf5c931fec",
  "external_id": "PROD-12345",
  "name": "Laptop Lenovo Thinkpad",
  "display_name": "Thinkpad X1 Carbon Gen 10",
  "reference_id": "SKU-45678",
  "barcode": "1234567890123",
  "barcode_type": "EAN",
  "status": "ACTIVE",
  "reception_type": "GENERAL",
  "inventory_unit": "UNIT",
  "measure_unit": "UND",
  "presentation": "Caja",
  "sale_price": 1200,
  "sale_coin": "USD",
  "purchase_price": 900,
  "purchase_coin": "USD",
  "product_image": "https://example.com/img/thinkpad.png",
  "properties": {...},
  "groups": [...],
  "substitute_ids": [],
  "created": "2025-08-27T16:18:36.423564-05:00",
  "created_unix_epoch": 1756329516,
  "created_by_username": "system@technoapes.co",
  "modified": "2025-08-30T15:18:35.784202-05:00",
  "modified_unix_epoch": 1756585115,
  "modified_by_username": "system@technoapes.co"
}
```

#### Actualizar Producto
```
PATCH /products/{id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body**: Solo los campos a actualizar (mismo formato que CREATE)

**Nota**: Es obligatorio enviar el `external_id` del producto

#### Listar Productos
```
GET /products?external_id__eq={id}&barcode__eq={barcode}&status__eq=ACTIVE&search={term}
Authorization: Bearer {token}
```

**Query Parameters**:
- `external_id__eq`: Filtrar por ID externo exacto
- `barcode__eq`: Filtrar por código de barras exacto
- `status__eq`: Filtrar por estado (ACTIVE, INACTIVE)
- `status__in`: Filtrar por múltiples estados (ACTIVE,INACTIVE)
- `search`: Búsqueda textual en nombre, código de barras, ID externo
- `last_evaluated_key_id`: Cursor de paginación

**Response** (200 OK):
```json
{
  "results": [
    {
      "variant_id": "VAR001",
      "name": "Smartphone X",
      "barcode": "1234567890123",
      "status": "ACTIVE",
      "external_id": "EXT001"
    }
  ],
  "count": 1,
  "warnings": [],
  "limit": 20,
  "last_evaluated_key_id": "Tenant#123-1"
}
```

### Ubicaciones

#### Asignar Ubicación a Item
```
POST /warehouse/locations
Authorization: Bearer {token}
Content-Type: application/json

{
  "item_id": "ITEM001",
  "location_code": "A0105",
  "zone_id": "ZONE-A",
  "quantity": 100
}
```

#### Consultar Zonas
```
GET /warehouse/zones
Authorization: Bearer {token}
```

### Inventario

#### Consultar Inventario
```
GET /inventory/items/{item_id}/stock
Authorization: Bearer {token}
```

#### Ajustar Inventario
```
POST /inventory/adjustments
Authorization: Bearer {token}
Content-Type: application/json

{
  "item_id": "ITEM001",
  "quantity_change": 10,
  "reason": "Siesa sync",
  "location_code": "A0105"
}
```

---

## Campos de Item en WMS

### Campos Estimados (REQUIERE CONFIRMACIÓN)

| Campo WMS | Tipo | Requerido | Descripción | Ejemplo |
|-----------|------|-----------|-------------|---------|
| `item_id` | string | Sí | ID único del item | "ITEM001" |
| `external_item_code` | string | Sí | Código externo (Siesa ID) | "SIESA-ITEM001" |
| `item_name` | string | Sí | Nombre del item | "Laptop Dell XPS 15" |
| `ean_code` | string | No | Código EAN/Barras | "1234567890123" |
| `available_quantity` | integer | Sí | Cantidad disponible | 100 |
| `location_code` | string | Sí | Código de ubicación | "A0105" |
| `zone_id` | string | No | ID de zona en bodega | "ZONE-A" |
| `warehouse_id` | string | No | ID de bodega | "WH001" |
| `unit_of_measure` | string | No | Unidad de medida | "UN" |
| `lot_number` | string | No | Número de lote | "LOT-2025-001" |
| `serial_number` | string | No | Número de serial | "SN123456" |
| `status` | string | No | Estado del item | "active" |

**Diferencias clave con Kong**:
- WMS requiere `location_code` (obligatorio)
- WMS incluye `zone_id` para organización de bodega
- WMS no maneja `rfid_tag_id` (eso es específico de Kong)
- WMS puede requerir `warehouse_id` si hay múltiples bodegas

---

## Rate Limiting

**⚠️ INFORMACIÓN PENDIENTE**

Necesita confirmación del equipo WMS:
- Límite de requests por minuto/hora
- Headers de rate limit en respuestas
- Código de respuesta cuando se excede (probablemente 429)
- Estrategia de retry recomendada

**Estimado conservador**: 100 requests/minuto

---

## Paginación

**⚠️ INFORMACIÓN PENDIENTE**

Necesita confirmación del equipo WMS:
- Método de paginación (page-based, cursor-based, offset-based)
- Parámetros de query: `?page=1&page_size=100`
- Máximo registros por página
- Headers de paginación en respuesta

---

## Códigos de Respuesta

### Exitosos
- `200 OK`: Operación exitosa
- `201 Created`: Recurso creado exitosamente
- `204 No Content`: Operación exitosa sin contenido

### Errores del Cliente
- `400 Bad Request`: Datos inválidos en el request
- `401 Unauthorized`: Token inválido o expirado
- `403 Forbidden`: Sin permisos para la operación
- `404 Not Found`: Recurso no encontrado
- `422 Unprocessable Entity`: Validación de negocio falló
- `429 Too Many Requests`: Rate limit excedido

### Errores del Servidor
- `500 Internal Server Error`: Error interno del servidor
- `503 Service Unavailable`: Servicio temporalmente no disponible

---

## Formato de Errores

**Estructura estimada** (requiere confirmación):

```json
{
  "error": "ValidationError",
  "message": "Location code is required for WMS items",
  "details": {
    "field": "location_code",
    "constraint": "required"
  }
}
```

---

## Credenciales de Prueba

### Ambiente de Staging/Test

**Base URL**: ⚠️ PENDIENTE

**Credenciales**: ⚠️ PENDIENTE - Solicitar al equipo WMS:
- API Key / Token de prueba
- Tenant ID de prueba
- Warehouse ID de prueba
- Permisos necesarios para la integración

---

## Mapeo Siesa → WMS

### Items/Productos

| Campo Siesa | Campo WMS | Transformación |
|-------------|-----------|----------------|
| `f120_id` | `external_item_code` | Ninguna |
| `f120_codigo` | `item_id` | Ninguna |
| `f120_descripcion` | `item_name` | Ninguna |
| `f120_codigo_barras` | `ean_code` | Validar 13 dígitos |
| `f120_cantidad` | `available_quantity` | String → Integer |
| `f120_ubicacion` | `location_code` | Formato: "A-01-05" → "A0105" |
| `f120_zona` | `zone_id` | Ninguna |
| `f120_bodega` | `warehouse_id` | Ninguna |
| `f120_unidad_medida` | `unit_of_measure` | Ninguna |

**Campos específicos de WMS**:
- `location_code`: **OBLIGATORIO** en WMS (no opcional como en Kong)
- `zone_id`: Organización de bodega (no existe en Kong)
- `warehouse_id`: Si hay múltiples bodegas

**Transformaciones específicas**:
- **Location format**: Siesa usa "A-01-05", WMS puede usar "A0105" (sin guiones)
- **Status**: Siempre "active" para items sincronizados

---

## Arquitectura de Microservicios

**Nota importante**: WMS está construido con microservicios, lo que significa:

1. **Múltiples endpoints**: Puede requerir llamadas a diferentes servicios:
   - Servicio de Items: `/inventory/items`
   - Servicio de Ubicaciones: `/warehouse/locations`
   - Servicio de Inventario: `/inventory/stock`

2. **Transacciones distribuidas**: Crear un item puede requerir:
   - Crear el item en el servicio de inventario
   - Asignar ubicación en el servicio de warehouse
   - Actualizar stock en el servicio de stock

3. **Eventual consistency**: Los datos pueden no estar inmediatamente consistentes entre servicios

4. **Service endpoints**: Puede haber URLs diferentes por servicio:
```json
{
  "service_endpoints": {
    "inventory": "https://cliente.wms.com/inventory",
    "warehouse": "https://cliente.wms.com/warehouse",
    "orders": "https://cliente.wms.com/orders"
  }
}
```

---

## Ejemplos de Uso

### 1. Autenticación (ESTIMADO)

```bash
curl -X POST "https://api.wms.com/auth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "api_key": "your_api_key_here"
  }'
```

### 2. Crear Item (ESTIMADO)

```bash
curl -X POST "https://api.wms.com/inventory/items" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "ITEM001",
    "external_item_code": "SIESA-ITEM001",
    "item_name": "Laptop Dell XPS 15",
    "ean_code": "1234567890123",
    "available_quantity": 100,
    "location_code": "A0105",
    "zone_id": "ZONE-A"
  }'
```

### 3. Bulk Create (ESTIMADO)

```bash
curl -X POST "https://api.wms.com/inventory/items/bulk" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "item_id": "ITEM001",
        "external_item_code": "SIESA-ITEM001",
        "item_name": "Laptop Dell XPS 15",
        "ean_code": "1234567890123",
        "available_quantity": 100,
        "location_code": "A0105"
      },
      {
        "item_id": "ITEM002",
        "external_item_code": "SIESA-ITEM002",
        "item_name": "Mouse Logitech",
        "ean_code": "9876543210987",
        "available_quantity": 250,
        "location_code": "B0210"
      }
    ]
  }'
```

### 4. Asignar Ubicación (ESTIMADO)

```bash
curl -X POST "https://api.wms.com/warehouse/locations" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "ITEM001",
    "location_code": "A0105",
    "zone_id": "ZONE-A",
    "quantity": 100
  }'
```

---

## Próximos Pasos - Información Requerida

### Alta Prioridad

1. **Colección Postman de WMS**:
   - [ ] Colección completa de WMS APIs
   - [ ] Ejemplos de requests/responses

2. **Endpoints de Items**:
   - [ ] URL exacta para crear items
   - [ ] URL exacta para actualizar items
   - [ ] URL exacta para bulk operations
   - [ ] Estructura completa del request body
   - [ ] Lista de campos requeridos vs opcionales

3. **Credenciales de Prueba**:
   - [ ] API Key / Token para ambiente staging
   - [ ] Tenant ID de prueba
   - [ ] Warehouse ID de prueba
   - [ ] Permisos necesarios

4. **Arquitectura de Microservicios**:
   - [ ] Lista de servicios y sus URLs
   - [ ] Flujo de creación de item (qué servicios se llaman)
   - [ ] Manejo de transacciones distribuidas

5. **Rate Limiting**:
   - [ ] Límite de requests por servicio
   - [ ] Estrategia de retry recomendada

6. **Paginación**:
   - [ ] Método de paginación
   - [ ] Máximo registros por página

### Media Prioridad

7. **Validaciones**:
   - [ ] Reglas de validación para cada campo
   - [ ] Formato de errores de validación
   - [ ] Validaciones específicas de WMS (ubicaciones, zonas)

8. **Manejo de Duplicados**:
   - [ ] Comportamiento cuando item_id ya existe
   - [ ] Comportamiento cuando external_item_code ya existe

9. **Ubicaciones y Zonas**:
   - [ ] Endpoint para consultar ubicaciones disponibles
   - [ ] Endpoint para consultar zonas
   - [ ] Reglas de asignación de ubicaciones

10. **Inventario**:
    - [ ] Endpoint para consultar stock actual
    - [ ] Endpoint para ajustes de inventario
    - [ ] Manejo de lotes y seriales

---

## Contactos

**Equipo WMS**:
- Contacto: ___________________________
- Email: ___________________________
- Slack: ___________________________

**Solicitar**:
- Colección Postman de WMS APIs
- Documentación completa de API
- Credenciales de staging
- Ejemplos de requests/responses
- Diagrama de arquitectura de microservicios
- Flujos de integración recomendados

---

## Notas Adicionales

```
[Agregar aquí cualquier información adicional que se obtenga del equipo WMS]
```

---

**Última actualización**: 2025-01-21  
**Estado**: ⚠️ DOCUMENTACIÓN PENDIENTE - Requiere colección Postman y documentación del equipo WMS
