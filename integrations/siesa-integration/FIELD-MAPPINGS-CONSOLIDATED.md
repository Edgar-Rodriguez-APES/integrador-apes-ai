# Mapeo de Campos Consolidado: Siesa ↔ Kong ↔ WMS

## Introducción

Este documento consolida los mapeos de campos entre Siesa ERP y nuestros dos productos (Kong RFID y WMS). Cada cliente usa SOLO uno de los dos productos.

---

## Modelo Canónico (Intermedio)

El modelo canónico es la estructura intermedia que usamos para transformar datos entre Siesa y los productos.

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
  "warehouse_zone": "string (optional)",
  "rfid_tag_id": "string (optional)",
  "unit_of_measure": "string (optional)",
  "custom:*": "any (optional custom fields)"
}
```

---

## Mapeo Completo: Siesa → Canónico → Kong

### Tabla de Mapeo

| Campo Siesa | Campo Canónico | Campo Kong | Tipo | Transformación | Requerido |
|-------------|----------------|------------|------|----------------|-----------|
| `f120_id` | `id` | `product_id` | string | Ninguna | Sí |
| `f120_codigo_externo` | `external_id` | `external_reference` | string | Ninguna | Sí |
| `f120_descripcion` | `name` | `name` | string | Ninguna | Sí |
| `f120_nombre_display` | `display_name` | - | string | No se envía a Kong | No |
| `f120_codigo_barras` | `ean` | `barcode` | string | Validar 13 dígitos | No |
| `f120_referencia` | `sku` | - | string | No se envía a Kong | Sí |
| `f120_categoria` | `category` | `category` | string | Ninguna | No |
| `f120_cantidad` | `stock_quantity` | `quantity` | integer | String → Integer | Sí |
| `f120_ubicacion` | `warehouse_location` | `location` | string | Ninguna | No |
| `f120_zona` | `warehouse_zone` | - | string | No se envía a Kong | No |
| - | `rfid_tag_id` | `rfid_tag_id` | string | Se asigna en Kong | No |
| `f120_unidad_medida` | `unit_of_measure` | - | string | No se envía a Kong | No |

### Campos Específicos de Kong

- **`rfid_tag_id`**: No viene de Siesa. Se asigna cuando se asocia un tag RFID al producto en Kong.
- **`status`**: Siempre "active" para productos sincronizados desde Siesa.

### Ejemplo de Transformación

**Datos de Siesa**:
```json
{
  "f120_id": "PROD001",
  "f120_codigo_externo": "SIESA-PROD001",
  "f120_descripcion": "Laptop Dell XPS 15",
  "f120_codigo_barras": "1234567890123",
  "f120_cantidad": "100",
  "f120_ubicacion": "A-01-05",
  "f120_categoria": "Electronics"
}
```

**Modelo Canónico**:
```json
{
  "id": "PROD001",
  "external_id": "SIESA-PROD001",
  "name": "Laptop Dell XPS 15",
  "ean": "1234567890123",
  "sku": "PROD001",
  "category": "Electronics",
  "stock_quantity": 100,
  "warehouse_location": "A-01-05"
}
```

**Datos para Kong**:
```json
{
  "product_id": "PROD001",
  "external_reference": "SIESA-PROD001",
  "name": "Laptop Dell XPS 15",
  "barcode": "1234567890123",
  "quantity": 100,
  "location": "A-01-05",
  "category": "Electronics",
  "status": "active"
}
```

---

## Mapeo Completo: Siesa → Canónico → WMS

### Tabla de Mapeo

| Campo Siesa | Campo Canónico | Campo WMS | Tipo | Transformación | Requerido |
|-------------|----------------|-----------|------|----------------|-----------|
| `f120_id` | `id` | `item_id` | string | Ninguna | Sí |
| `f120_codigo_externo` | `external_id` | `external_item_code` | string | Ninguna | Sí |
| `f120_descripcion` | `name` | `item_name` | string | Ninguna | Sí |
| `f120_nombre_display` | `display_name` | - | string | No se envía a WMS | No |
| `f120_codigo_barras` | `ean` | `ean_code` | string | Validar 13 dígitos | No |
| `f120_referencia` | `sku` | - | string | No se envía a WMS | Sí |
| `f120_categoria` | `category` | - | string | No se envía a WMS | No |
| `f120_cantidad` | `stock_quantity` | `available_quantity` | integer | String → Integer | Sí |
| `f120_ubicacion` | `warehouse_location` | `location_code` | string | "A-01-05" → "A0105" | **Sí** |
| `f120_zona` | `warehouse_zone` | `zone_id` | string | Ninguna | No |
| `f120_bodega` | - | `warehouse_id` | string | Ninguna | No |
| `f120_unidad_medida` | `unit_of_measure` | `unit_of_measure` | string | Ninguna | No |

### Campos Específicos de WMS

- **`location_code`**: **OBLIGATORIO** en WMS (a diferencia de Kong donde es opcional)
- **`zone_id`**: Organización de bodega (no existe en Kong)
- **`warehouse_id`**: Si el cliente tiene múltiples bodegas
- **`status`**: Siempre "active" para items sincronizados desde Siesa

### Transformaciones Específicas de WMS

1. **Location Format**:
   - Siesa: `"A-01-05"` (con guiones)
   - WMS: `"A0105"` (sin guiones)
   - Transformación: Remover guiones

2. **Zone Mapping**:
   - Si Siesa no proporciona zona, usar zona por defecto del warehouse

### Ejemplo de Transformación

**Datos de Siesa**:
```json
{
  "f120_id": "ITEM001",
  "f120_codigo_externo": "SIESA-ITEM001",
  "f120_descripcion": "Laptop Dell XPS 15",
  "f120_codigo_barras": "1234567890123",
  "f120_cantidad": "100",
  "f120_ubicacion": "A-01-05",
  "f120_zona": "ZONE-A",
  "f120_unidad_medida": "UN"
}
```

**Modelo Canónico**:
```json
{
  "id": "ITEM001",
  "external_id": "SIESA-ITEM001",
  "name": "Laptop Dell XPS 15",
  "ean": "1234567890123",
  "sku": "ITEM001",
  "stock_quantity": 100,
  "warehouse_location": "A-01-05",
  "warehouse_zone": "ZONE-A",
  "unit_of_measure": "UN"
}
```

**Datos para WMS**:
```json
{
  "item_id": "ITEM001",
  "external_item_code": "SIESA-ITEM001",
  "item_name": "Laptop Dell XPS 15",
  "ean_code": "1234567890123",
  "available_quantity": 100,
  "location_code": "A0105",
  "zone_id": "ZONE-A",
  "unit_of_measure": "UN",
  "status": "active"
}
```

---

## Comparación de Campos por Producto

### Campos Comunes (Ambos Productos)

| Concepto | Kong | WMS |
|----------|------|-----|
| ID del producto | `product_id` | `item_id` |
| Referencia externa | `external_reference` | `external_item_code` |
| Nombre | `name` | `item_name` |
| Código de barras | `barcode` | `ean_code` |
| Cantidad | `quantity` | `available_quantity` |
| Ubicación | `location` | `location_code` |
| Estado | `status` | `status` |

### Campos Únicos de Kong

| Campo | Descripción | Requerido |
|-------|-------------|-----------|
| `rfid_tag_id` | ID del tag RFID asociado | No |

### Campos Únicos de WMS

| Campo | Descripción | Requerido |
|-------|-------------|-----------|
| `zone_id` | Zona dentro de la bodega | No |
| `warehouse_id` | ID de la bodega | No |
| `unit_of_measure` | Unidad de medida | No |
| `lot_number` | Número de lote | No |
| `serial_number` | Número de serial | No |

### Diferencias Clave

1. **Location (Ubicación)**:
   - Kong: Opcional
   - WMS: **Obligatorio**

2. **RFID**:
   - Kong: Soporta `rfid_tag_id`
   - WMS: No soporta RFID

3. **Warehouse Organization**:
   - Kong: Solo `location`
   - WMS: `location_code` + `zone_id` + `warehouse_id`

4. **Naming Convention**:
   - Kong: `product_*`, `barcode`
   - WMS: `item_*`, `ean_code`

---

## Reglas de Validación

### Validaciones Comunes (Ambos Productos)

1. **EAN/Barcode**:
   - Formato: 13 dígitos numéricos
   - Regex: `^[0-9]{13}$`
   - Ejemplo válido: `"1234567890123"`

2. **Quantity**:
   - Tipo: Integer
   - Mínimo: 0
   - Ejemplo válido: `100`

3. **ID Fields**:
   - No vacío
   - Sin espacios
   - Alfanumérico con guiones permitidos

### Validaciones Específicas de Kong

1. **RFID Tag ID**:
   - Formato: Hexadecimal
   - Longitud: Variable (típicamente 24 caracteres)
   - Ejemplo: `"E2801170000002012345678"`

### Validaciones Específicas de WMS

1. **Location Code**:
   - **Obligatorio** (a diferencia de Kong)
   - Formato: Alfanumérico sin guiones
   - Ejemplo: `"A0105"`

2. **Zone ID**:
   - Formato: Alfanumérico con guiones permitidos
   - Ejemplo: `"ZONE-A"`

---

## Transformaciones de Datos

### Transformaciones Comunes

1. **String → Integer**:
   - Campo: `stock_quantity`
   - Siesa: `"100"` (string)
   - Canónico/Productos: `100` (integer)

2. **Date Format** (si aplica):
   - Siesa: `"YYYY-MM-DD"`
   - Productos: `"YYYY-MM-DDTHH:mm:ssZ"` (ISO8601)

### Transformaciones Específicas de WMS

1. **Location Format**:
   - Siesa: `"A-01-05"`
   - WMS: `"A0105"`
   - Transformación: `location.replace(/-/g, '')`

---

## Campos Personalizados (Custom Fields)

Ambos productos soportan campos personalizados usando el prefijo `custom:`.

**Ejemplo en Siesa**:
```json
{
  "f120_id": "PROD001",
  "f120_color": "Blue",
  "f120_talla": "M"
}
```

**Modelo Canónico**:
```json
{
  "id": "PROD001",
  "custom:color": "Blue",
  "custom:talla": "M"
}
```

**Nota**: Los campos custom se pasan tal cual a Kong/WMS si los soportan.

---

## Archivos de Configuración

### field-mappings-kong.json

```json
{
  "version": "1.0",
  "product_type": "kong",
  "mappings": {
    "product": {
      "id": {
        "siesa_field": "f120_id",
        "product_field": "product_id",
        "type": "string",
        "required": true
      },
      "external_id": {
        "siesa_field": "f120_codigo_externo",
        "product_field": "external_reference",
        "type": "string",
        "required": true
      },
      "name": {
        "siesa_field": "f120_descripcion",
        "product_field": "name",
        "type": "string",
        "required": true
      },
      "ean": {
        "siesa_field": "f120_codigo_barras",
        "product_field": "barcode",
        "type": "string",
        "required": false,
        "validation": "^[0-9]{13}$"
      },
      "stock_quantity": {
        "siesa_field": "f120_cantidad",
        "product_field": "quantity",
        "type": "integer",
        "required": true,
        "transformation": "string_to_int"
      },
      "warehouse_location": {
        "siesa_field": "f120_ubicacion",
        "product_field": "location",
        "type": "string",
        "required": false
      },
      "category": {
        "siesa_field": "f120_categoria",
        "product_field": "category",
        "type": "string",
        "required": false
      }
    }
  },
  "transformations": {
    "string_to_int": {
      "type": "cast",
      "from": "string",
      "to": "integer"
    }
  },
  "defaults": {
    "status": "active"
  }
}
```

### field-mappings-wms.json

```json
{
  "version": "1.0",
  "product_type": "wms",
  "mappings": {
    "product": {
      "id": {
        "siesa_field": "f120_id",
        "product_field": "item_id",
        "type": "string",
        "required": true
      },
      "external_id": {
        "siesa_field": "f120_codigo_externo",
        "product_field": "external_item_code",
        "type": "string",
        "required": true
      },
      "name": {
        "siesa_field": "f120_descripcion",
        "product_field": "item_name",
        "type": "string",
        "required": true
      },
      "ean": {
        "siesa_field": "f120_codigo_barras",
        "product_field": "ean_code",
        "type": "string",
        "required": false,
        "validation": "^[0-9]{13}$"
      },
      "stock_quantity": {
        "siesa_field": "f120_cantidad",
        "product_field": "available_quantity",
        "type": "integer",
        "required": true,
        "transformation": "string_to_int"
      },
      "warehouse_location": {
        "siesa_field": "f120_ubicacion",
        "product_field": "location_code",
        "type": "string",
        "required": true,
        "transformation": "remove_hyphens"
      },
      "warehouse_zone": {
        "siesa_field": "f120_zona",
        "product_field": "zone_id",
        "type": "string",
        "required": false
      },
      "unit_of_measure": {
        "siesa_field": "f120_unidad_medida",
        "product_field": "unit_of_measure",
        "type": "string",
        "required": false
      }
    }
  },
  "transformations": {
    "string_to_int": {
      "type": "cast",
      "from": "string",
      "to": "integer"
    },
    "remove_hyphens": {
      "type": "string_replace",
      "pattern": "-",
      "replacement": ""
    }
  },
  "defaults": {
    "status": "active"
  }
}
```

---

## Casos Especiales

### 1. Producto sin Ubicación (Location)

**Kong**: Permitido - el campo es opcional
```json
{
  "product_id": "PROD001",
  "name": "Product without location",
  "quantity": 100
}
```

**WMS**: **NO permitido** - el campo es obligatorio
- Solución: Usar ubicación por defecto o rechazar el producto

### 2. Producto con RFID Tag

**Kong**: Soportado
```json
{
  "product_id": "PROD001",
  "rfid_tag_id": "E2801170000002012345678"
}
```

**WMS**: Campo ignorado (WMS no maneja RFID)

### 3. Producto con Zona de Bodega

**Kong**: Campo ignorado (Kong no maneja zonas)

**WMS**: Soportado
```json
{
  "item_id": "ITEM001",
  "location_code": "A0105",
  "zone_id": "ZONE-A"
}
```

---

## Resumen de Diferencias Críticas

| Aspecto | Kong | WMS |
|---------|------|-----|
| **Location requerido** | No | **Sí** |
| **Soporta RFID** | Sí | No |
| **Soporta Zonas** | No | Sí |
| **Formato Location** | Con guiones | Sin guiones |
| **Naming** | product_*, barcode | item_*, ean_code |
| **Unit of Measure** | No usado | Soportado |

---

**Última actualización**: 2025-01-21  
**Versión**: 1.0
