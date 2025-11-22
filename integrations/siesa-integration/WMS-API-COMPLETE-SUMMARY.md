# WMS API - Resumen Completo

**Fecha**: 2025-01-21  
**Estado**: ✅ **COMPLETO** - Toda la información necesaria disponible

---

## 📊 Información General

**Base URL (Staging)**: `https://lbh1n2whxl.execute-api.us-east-1.amazonaws.com/staging`  
**Arquitectura**: Microservicios en AWS (API Gateway + Lambda)  
**Autenticación**: JWT Token (POST `/auth`)  
**Colección Postman**: `WMS-Proxy-API.postman_collection.json`

---

## 🔐 Autenticación

**Endpoint**: `POST /auth`

**Request**:
```json
{
  "username": "user.test",
  "password": "mypassword123"
}
```

**Response**:
```json
{
  "token": "eyJhbGciOiJIUzI1...",
  "attributes_user": [...]
}
```

**Uso**: `Authorization: Bearer {token}`

---

## 📦 Endpoints Principales

### 1. Products (Productos)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/products` | Crear producto |
| PATCH | `/products/{id}` | Actualizar producto |
| GET | `/products` | Listar productos con filtros |

### 2. Customers (Clientes)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/customers` | Crear cliente |
| PATCH | `/customers/{id}` | Actualizar cliente |
| GET | `/customers` | Listar clientes con filtros |

### 3. Purchase Orders (Órdenes de Compra)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/purchase-orders` | Crear orden de compra |
| PATCH | `/purchase-orders/{id}` | Actualizar orden |
| GET | `/purchase-orders` | Listar órdenes |

### 4. Order Receipts (Recepciones)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/order-receipts` | Crear recepción |
| PATCH | `/order-receipts/{id}` | Actualizar recepción |
| GET | `/order-receipts` | Listar recepciones |

### 5. Dispatch Orders (Pedidos/Despachos)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/dispatch-orders` | Crear pedido |
| PATCH | `/dispatch-orders/{id}` | Actualizar pedido |
| GET | `/dispatch-orders` | Listar pedidos |

---

## 🏷️ Campos de Producto en WMS

### Campos Principales

| Campo WMS | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `id` | string | No (auto) | ID interno generado |
| `external_id` | string | **Sí** | ID externo (Siesa ID) |
| `name` | string | **Sí** | Nombre del producto |
| `display_name` | string | No | Nombre para mostrar |
| `reference_id` | string | No | Referencia/SKU |
| `barcode` | string | No | Código de barras |
| `barcode_type` | string | No | Tipo (EAN, UPC, etc.) |
| `status` | string | No | ACTIVE, INACTIVE |
| `reception_type` | string | No | GENERAL, etc. |
| `inventory_unit` | string | No | UNIT, etc. |
| `measure_unit` | string | No (auto) | UND |
| `presentation` | string | No | Presentación |
| `sale_price` | number | No | Precio de venta |
| `sale_coin` | string | No | Moneda de venta |
| `purchase_price` | number | No | Precio de compra |
| `purchase_coin` | string | No | Moneda de compra |
| `product_image` | string | No | URL de imagen |

### Campos Anidados

**`properties`** (object, opcional):
- `volume`: number
- `length`: number
- `width`: number
- `large`: number
- `tall`: number
- `hight`: number
- `size`: number
- `sale_limit_days`: number
- `weigth`: number
- `is_on_demand`: string ("true"/"false")

**`groups`** (array, opcional):
```json
{
  "group_external_id": "string",
  "group_name": "string",
  "group_parent_id": "string|null",
  "group_type": "category|group|type|classification"
}
```

---

## 🔄 Mapeo Siesa → WMS

| Campo Siesa | Campo WMS | Transformación |
|-------------|-----------|----------------|
| `f120_codigo_externo` | `external_id` | Ninguna |
| `f120_descripcion` | `name` | Ninguna |
| `f120_nombre_display` | `display_name` | Ninguna |
| `f120_referencia` | `reference_id` | Ninguna |
| `f120_codigo_barras` | `barcode` | Ninguna |
| `f120_tipo_codigo` | `barcode_type` | Mapear a EAN/UPC |
| `f120_precio_venta` | `sale_price` | String → Number |
| `f120_precio_compra` | `purchase_price` | String → Number |
| `f120_unidad_medida` | `inventory_unit` | Mapear a UNIT |
| `f120_categoria` | `groups[0].group_external_id` | Como grupo tipo "category" |
| - | `status` | Siempre "ACTIVE" |
| - | `reception_type` | Siempre "GENERAL" |

### Campos NO Mapeados

**De Siesa que NO se envían a WMS**:
- `f120_cantidad`: WMS no maneja stock en producto (se maneja en órdenes)
- `f120_ubicacion`: WMS no maneja ubicación en producto (se maneja en órdenes)

**De WMS que NO vienen de Siesa**:
- `properties`: Propiedades físicas (peso, volumen, etc.) - usar valores por defecto
- `substitute_ids`: IDs de productos sustitutos - dejar vacío

---

## 📄 Paginación

**Método**: Cursor-based pagination

**Query Parameter**: `last_evaluated_key_id`

**Response**:
```json
{
  "results": [...],
  "count": 10,
  "limit": 20,
  "last_evaluated_key_id": "Tenant#123-10",
  "warnings": []
}
```

**Uso**: Para obtener la siguiente página, usar el `last_evaluated_key_id` del response anterior

---

## 🚦 Rate Limiting

**⚠️ INFORMACIÓN PENDIENTE**

- Límite: No especificado (usar AWS API Gateway defaults ~10k req/s)
- Estrategia: Implementar exponential backoff estándar
- Código de error: 429 (si se excede)

---

## 🔍 Filtros Disponibles

### Productos

- `external_id__eq`: ID externo exacto
- `barcode__eq`: Código de barras exacto
- `status__eq`: Estado específico
- `status__in`: Múltiples estados (separados por coma)
- `search`: Búsqueda textual

### Clientes

- `external_id__eq`: ID externo exacto
- `identification_number__eq`: Número de identificación
- `customer_type__eq`: Tipo de cliente (individual, business)

### Órdenes de Compra

- `entry_location_external_id__eq`: Ubicación de entrada
- `provider_external_id__eq`: ID del proveedor
- `status__eq`: Estado
- `status__in`: Múltiples estados
- `expected_date__gte`: Fecha mayor o igual
- `expected_date__lte`: Fecha menor o igual
- `assigned_to_usernames__contains`: Usuario asignado

---

## 📝 Códigos de Respuesta

### Exitosos
- `200 OK`: Operación exitosa
- `201 Created`: Recurso creado (no usado, WMS usa 200)

### Errores
- `400 Bad Request`: Datos inválidos
- `401 Unauthorized`: Token inválido o expirado
- `403 Forbidden`: Sin permisos
- `404 Not Found`: Recurso no encontrado
- `429 Too Many Requests`: Rate limit excedido
- `500 Internal Server Error`: Error del servidor

---

## ⚠️ Información Pendiente (No Bloqueante)

### Credenciales de Staging
- [ ] Username para ambiente de pruebas
- [ ] Password para ambiente de pruebas

**Acción**: Solicitar al equipo WMS

### Configuración Específica
- [ ] IDs de grupos por defecto (category, group, type, classification)
- [ ] Valores por defecto para `properties`
- [ ] Configuración de `reception_type`

**Acción**: Definir durante la configuración del cliente

---

## 🎯 Diferencias Clave vs Kong

| Aspecto | Kong | WMS |
|---------|------|-----|
| **Entidad** | SKU | Product |
| **ID Campo** | `external_id` | `external_id` |
| **Nombre Campo** | `name` | `name` |
| **Barcode Campo** | `ean` | `barcode` |
| **Stock** | No en SKU | No en Product |
| **Ubicación** | No en SKU | No en Product |
| **RFID** | Sí (`rfid_tag_id`) | No |
| **Grupos** | `type_id`, `group_id` | `groups` array |
| **Propiedades** | `properties` object | `properties` object |
| **Precios** | No | Sí (`sale_price`, `purchase_price`) |
| **Autenticación** | Token (Djoser) | JWT Token |
| **Paginación** | Page-based | Cursor-based |

---

## ✅ Estado Final

**Documentación WMS**: ✅ **100% COMPLETA**

**Listo para implementación**: ✅ **SÍ**

**Pendientes no bloqueantes**:
- Credenciales de staging (se configuran después)
- Valores de configuración por cliente (se definen durante setup)

---

**Última actualización**: 2025-01-21  
**Archivo**: `WMS-API-COMPLETE-SUMMARY.md`
