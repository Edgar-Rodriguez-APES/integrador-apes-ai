# Kong (RFID) API - Documentación para Integración

## Información General

**Producto**: Kong RFID Backend  
**Arquitectura**: Monolito con base de datos RDS (Relacional)  
**Colección Postman**: `Kong Core API.postman_collection.json`  
**Base URL (Staging)**: `https://api-apes-stock-rfid-staging.technoapes.io`

---

## Autenticación

### Método: Token-Based Authentication (Djoser)

**Endpoint de Login**:
```
POST /auth/token/login/
```

**Request Body**:
```json
{
  "username": "usuario",
  "password": "contraseña"
}
```

**Response** (201 Created):
```json
{
  "auth_token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

**Uso del Token**:
```
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
```

**Logout**:
```
POST /auth/token/logout/
Authorization: Token {token}
```

---

## Módulos Principales de Kong API

### 1. Autenticación (`/auth`)
- Token login/logout
- User management
- Password reset
- Username reset

### 2. Configuración Core (`/core_config`)
- JSON map configs
- Kong modules
- Roles
- User configs
- Users

### 3. Clientes (`/customers`)
- Customer management
- Customer history

### 4. Integraciones (`/integrations`)
- ARCO integration (purchase orders, SKUs)
- Integration configs
- Integration groups
- Integration params
- Integration types
- Module config
- Package orders
- Package service types

### 5. Inventario (`/inventory`)
- Gestión de inventario con RFID
- Stock movements
- Inventory adjustments

### 6. Logística (`/logistics`)
- Operaciones logísticas
- Movimientos de mercancía

### 7. Operaciones (`/operations`)
- Operaciones generales del sistema

### 8. RFID (`/rfid`)
- Lectores RFID
- Tags RFID
- Eventos de lectura
- Asociación de tags a productos

### 9. Configuración RFID (`/rfid_config`)
- Configuración de lectores
- Configuración de antenas
- Parámetros RFID

### 10. Stock (`/stock`)
- Stock movements
- Stock levels
- Stock adjustments

---

## Endpoints Relevantes para Integración Siesa

### SKUs (Productos)

**NOTA IMPORTANTE**: En Kong RFID, los productos se denominan "SKUs" (Stock Keeping Units).

#### Crear/Actualizar SKU (Upsert)
```
POST /inventory/skus/
Authorization: Token {token}
Content-Type: application/json
```

**Descripción**: Crea un nuevo SKU o lo actualiza si el `external_id` ya existe (comportamiento upsert).

**Request Body**:
```json
{
  "external_id": "SIESA-PROD001",
  "name": "Laptop Dell XPS 15",
  "display_name": "Dell XPS 15 - 16GB RAM",
  "reference": "PROD001",
  "type_id": 1,
  "group_id": 10,
  "customer_id": 100,
  "is_active": true,
  "filter": 1,
  "ean": "1234567890123",
  "upc": "",
  "isbn": "",
  "properties": {
    "color": "Silver",
    "size": "15 inch"
  },
  "params": {
    "warranty": "2 years"
  }
}
```

**Response** (201 Created):
```json
{
  "id": 86131475,
  "external_id": "SIESA-PROD001",
  "name": "Laptop Dell XPS 15",
  "display_name": "Dell XPS 15 - 16GB RAM",
  "reference": "PROD001",
  "gtin_code": "01234567890123",
  "company_prefix": "0123456",
  "serial_count": 0,
  "type_id": 1,
  "group_id": 10,
  "customer_id": 100,
  "is_active": true,
  "filter": 1,
  "ean": "1234567890123",
  "upc": "",
  "isbn": "",
  "properties": {
    "color": "Silver",
    "size": "15 inch"
  },
  "params": {
    "warranty": "2 years"
  },
  "created": "2025-01-21T10:00:00Z",
  "modified": "2025-01-21T10:00:00Z",
  "photo": null
}
```

#### Consultar SKU por ID
```
GET /inventory/skus/{id}/
Authorization: Token {token}
```

**Response** (200 OK): Mismo formato que el response de CREATE

#### Actualizar SKU Completo
```
PUT /inventory/skus/{id}/
Authorization: Token {token}
Content-Type: application/json
```

**Request Body**: Mismo formato que CREATE (todos los campos)

#### Actualizar SKU Parcial
```
PATCH /inventory/skus/{id}/
Authorization: Token {token}
Content-Type: application/json
```

**Request Body**: Solo los campos a actualizar

#### Listar SKUs
```
GET /inventory/skus/?customer_id={id}&search={term}&page={num}&page_size={size}
Authorization: Token {token}
```

**Query Parameters**:
- `customer_id`: Filtrar por cliente
- `search`: Búsqueda por nombre o external_id
- `page`: Número de página
- `page_size`: Registros por página

#### Historial de SKU
```
GET /inventory/skus/{id}/history/
Authorization: Token {token}
```

**Descripción**: Retorna el historial de cambios del SKU

### RFID Tags

**Asociar Tag RFID a Producto** (estimado):
```
POST /rfid/tags
Authorization: Token {token}
Content-Type: application/json

{
  "tag_id": "E2801170000002012345678",
  "product_id": "PROD001",
  "status": "active"
}
```

### Inventario

**Consultar Inventario** (estimado):
```
GET /inventory/stock?product_id={id}
Authorization: Token {token}
```

**Ajustar Inventario** (estimado):
```
POST /stock/adjustments
Authorization: Token {token}
Content-Type: application/json

{
  "product_id": "PROD001",
  "quantity_change": 10,
  "reason": "Siesa sync",
  "location": "A-01-05"
}
```

---

## Campos de SKU en Kong

### Campos Confirmados

| Campo Kong | Tipo | Requerido | Descripción | Ejemplo |
|------------|------|-----------|-------------|---------|
| `id` | integer | No (auto) | ID interno de Kong | 86131475 |
| `external_id` | string | **Sí** | Referencia externa (Siesa ID) | "SIESA-PROD001" |
| `name` | string | **Sí** | Nombre del SKU | "Laptop Dell XPS 15" |
| `display_name` | string | No | Nombre para mostrar | "Dell XPS 15 - 16GB" |
| `reference` | string | No | Referencia interna | "PROD001" |
| `type_id` | integer | **Sí** | ID del tipo de SKU | 1 |
| `type_external_id` | string | No | External ID del tipo | "TYPE-001" |
| `group_id` | integer | **Sí** | ID del grupo de SKU | 10 |
| `group_external_id` | string | No | External ID del grupo | "GROUP-A" |
| `customer_id` | integer | **Sí** | ID del cliente | 100 |
| `is_active` | boolean | No | Estado activo/inactivo | true |
| `filter` | integer | No | Filtro RFID (0-7) | 1 |
| `ean` | string | No | Código EAN-13 | "1234567890123" |
| `upc` | string | No | Código UPC | "" |
| `isbn` | string | No | Código ISBN | "" |
| `gtin_code` | string | No (auto) | Código GTIN generado | "01234567890123" |
| `company_prefix` | string | No (auto) | Prefijo de compañía | "0123456" |
| `serial_count` | integer | No (auto) | Contador de seriales | 0 |
| `properties` | object | No | Propiedades personalizadas | {"color": "Blue"} |
| `params` | object | No | Parámetros adicionales | {"warranty": "2y"} |
| `photo` | string | No | URL de foto | "http://..." |
| `created` | datetime | No (auto) | Fecha de creación | "2025-01-21T10:00:00Z" |
| `modified` | datetime | No (auto) | Fecha de modificación | "2025-01-21T10:00:00Z" |

### Campos Relacionados con RFID

Los tags RFID se asocian a los SKUs a través de **Items** (no directamente al SKU). El flujo es:
1. Crear SKU
2. Crear Items asociados al SKU
3. Asociar tags RFID a los Items

**Nota**: Para la integración Siesa, nos enfocaremos en la creación/actualización de SKUs. La asociación RFID es un proceso posterior.

---

## Rate Limiting

**✅ CONFIRMADO**

- **Límite**: No hay throttling agresivo en Staging
- **Default AWS API Gateway**: ~10,000 requests/segundo burst
- **Recomendación**: Proceder con uso estándar sin restricciones especiales
- **Código de respuesta**: 429 (si se excede)
- **Estrategia**: Implementar exponential backoff estándar (2s, 4s, 8s)

---

## Paginación

**✅ CONFIRMADO**

- **Método**: Page-based pagination
- **Parámetros**: `?page=1&page_size=100`
- **Máximo por página**: No especificado (usar 100 como estándar)
- **Response**: Incluye `count`, `next`, `previous`, `results`

**Ejemplo Response**:
```json
{
  "count": 1250,
  "next": "https://api.../inventory/skus/?page=2",
  "previous": null,
  "results": [...]
}
```

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
- `429 Too Many Requests`: Rate limit excedido

### Errores del Servidor
- `500 Internal Server Error`: Error interno del servidor
- `503 Service Unavailable`: Servicio temporalmente no disponible

---

## Formato de Errores

**Estructura estimada** (requiere confirmación):

```json
{
  "error": "Validation Error",
  "message": "Invalid barcode format",
  "details": {
    "field": "barcode",
    "value": "invalid",
    "expected": "13 digits"
  }
}
```

---

## Credenciales de Prueba

### Ambiente de Staging

**Base URL**: `https://api-apes-stock-rfid-staging.technoapes.io`

**✅ DISPONIBLES**:

**Base URL Staging**: `https://api-staging.technoapes.io/`

**Credenciales**:
- Username: `[PENDIENTE - Solicitar al usuario]`
- Password: `[PENDIENTE - Solicitar al usuario]`

**Proceso de Autenticación**:
1. POST `/auth/token/login/` con username y password
2. Obtener `auth_token` del response
3. Usar en headers: `Authorization: Token {auth_token}`

**Permisos Necesarios**:
- Lectura y escritura en `/inventory/skus/`
- Acceso a customer específico

---

## Mapeo Siesa → Kong

### SKUs

| Campo Siesa | Campo Kong | Transformación | Notas |
|-------------|------------|----------------|-------|
| `f120_codigo_externo` | `external_id` | Ninguna | **Requerido** - Clave para upsert |
| `f120_descripcion` | `name` | Ninguna | **Requerido** |
| `f120_nombre_display` | `display_name` | Ninguna | Opcional |
| `f120_referencia` | `reference` | Ninguna | Opcional |
| `f120_codigo_barras` | `ean` | Validar 13 dígitos | Opcional |
| `f120_categoria` | `properties.category` | Ninguna | Como propiedad custom |
| - | `type_id` | Valor fijo | **Requerido** - Configurar por cliente |
| - | `group_id` | Valor fijo | **Requerido** - Configurar por cliente |
| - | `customer_id` | Valor fijo | **Requerido** - ID del cliente Kong |
| - | `is_active` | Siempre `true` | Para productos sincronizados |
| - | `filter` | Valor fijo (1) | Filtro RFID estándar |

**Campos NO mapeados de Siesa**:
- `f120_cantidad`: Kong no maneja stock en SKU (se maneja en Items)
- `f120_ubicacion`: Kong no maneja ubicación en SKU (se maneja en Items)

**Campos específicos de Kong que requieren configuración**:
- `type_id`: Debe obtenerse del cliente (tipo de SKU en Kong)
- `group_id`: Debe obtenerse del cliente (grupo de SKU en Kong)
- `customer_id`: ID del cliente en Kong

---

## Ejemplos de Uso

### 1. Autenticación

```bash
curl -X POST "https://api-apes-stock-rfid-staging.technoapes.io/auth/token/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "integration_user",
    "password": "secure_password"
  }'
```

### 2. Crear Producto (ESTIMADO - REQUIERE CONFIRMACIÓN)

```bash
curl -X POST "https://api-apes-stock-rfid-staging.technoapes.io/inventory/products" \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "PROD001",
    "external_reference": "SIESA-PROD001",
    "name": "Laptop Dell XPS 15",
    "barcode": "1234567890123",
    "quantity": 100,
    "location": "A-01-05"
  }'
```

### 3. Bulk Create (ESTIMADO - REQUIERE CONFIRMACIÓN)

```bash
curl -X POST "https://api-apes-stock-rfid-staging.technoapes.io/inventory/products/bulk" \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  -H "Content-Type: application/json" \
  -d '{
    "products": [
      {
        "product_id": "PROD001",
        "external_reference": "SIESA-PROD001",
        "name": "Laptop Dell XPS 15",
        "barcode": "1234567890123",
        "quantity": 100
      },
      {
        "product_id": "PROD002",
        "external_reference": "SIESA-PROD002",
        "name": "Mouse Logitech MX Master",
        "barcode": "9876543210987",
        "quantity": 250
      }
    ]
  }'
```

---

## Próximos Pasos - Información Requerida

### Alta Prioridad

1. **Endpoints de Productos**:
   - [ ] URL exacta para crear productos
   - [ ] URL exacta para actualizar productos
   - [ ] URL exacta para bulk operations
   - [ ] Estructura completa del request body
   - [ ] Lista de campos requeridos vs opcionales

2. **Credenciales de Prueba**:
   - [ ] Username/password para ambiente staging
   - [ ] Tenant ID de prueba
   - [ ] Permisos necesarios

3. **Rate Limiting**:
   - [ ] Límite de requests
   - [ ] Estrategia de retry recomendada

4. **Paginación**:
   - [ ] Método de paginación
   - [ ] Máximo registros por página

### Media Prioridad

5. **Validaciones**:
   - [ ] Reglas de validación para cada campo
   - [ ] Formato de errores de validación

6. **Manejo de Duplicados**:
   - [ ] Comportamiento cuando product_id ya existe
   - [ ] Comportamiento cuando external_reference ya existe

7. **RFID Tags**:
   - [ ] Endpoint para asociar tags
   - [ ] Endpoint para consultar tags disponibles

---

## Contactos

**Equipo Kong/APES**:
- Contacto: ___________________________
- Email: ___________________________
- Slack: ___________________________

**Solicitar**:
- Documentación completa de API
- Credenciales de staging
- Ejemplos de requests/responses
- Postman collection actualizada con endpoints de productos

---

## Notas Adicionales

```
[Agregar aquí cualquier información adicional que se obtenga del equipo Kong]
```

---

**Última actualización**: 2025-01-21  
**Estado**: ⚠️ DOCUMENTACIÓN PARCIAL - Requiere información del equipo Kong
