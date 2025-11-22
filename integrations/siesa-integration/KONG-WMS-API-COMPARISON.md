# Comparación de APIs: Kong RFID vs WMS

## Resumen Ejecutivo

Este documento compara las estructuras de API de los dos productos principales de APES que requieren integración con Siesa ERP:

1. **Kong (RFID Backend)**: Monolito con base de datos relacional (RDS)
2. **WMS**: Arquitectura de microservicios

**Implicación clave**: Cada cliente Siesa usará SOLO uno de estos productos, nunca ambos simultáneamente.

---

## Kong RFID API - Estructura Principal

### Módulos Principales (10 secciones)

1. **auth** - Autenticación y gestión de usuarios
   - Token login/logout
   - User management
   - Password/username reset

2. **core_config** - Configuración del sistema
   - json-map-configs
   - kong-modules
   - roles
   - user-configs
   - users

3. **customers** - Gestión de clientes
   - Customer history
   - Customer data

4. **integrations** - Integraciones externas
   - arco (purchase-order-event, sku-event)
   - integration-configs
   - integration-groups
   - integration-params
   - integration-types
   - module-config
   - package-orders
   - package-service-types

5. **inventory** - Gestión de inventario RFID
   - (Endpoints específicos de inventario con tags RFID)

6. **logistics** - Operaciones logísticas
   - (Gestión de movimientos y logística)

7. **operations** - Operaciones del sistema
   - (Operaciones generales del sistema RFID)

8. **rfid** - Funcionalidad RFID específica
   - Lectores RFID
   - Tags RFID
   - Eventos de lectura

9. **rfid_config** - Configuración RFID
   - Configuración de lectores
   - Configuración de antenas
   - Parámetros RFID

10. **stock** - Gestión de stock
    - Stock movements
    - Stock levels
    - Stock adjustments

### Características Técnicas Kong
- **Arquitectura**: Monolito
- **Base de datos**: RDS (Relacional)
- **Autenticación**: Token-based (Djoser)
- **Base URL**: `https://api-apes-stock-rfid-staging.technoapes.io`
- **Enfoque**: RFID tracking y gestión de inventario con tecnología RFID

---

## WMS API - Estructura Principal

### Módulos Principales (Basado en SIESA_APIs_WMS_Completo.json)

1. **Gestión de Bodegas (Warehouses)**
   - Crear/actualizar bodegas
   - Consultar bodegas

2. **Gestión de Ubicaciones (Locations)**
   - Crear/actualizar ubicaciones
   - Consultar ubicaciones por bodega

3. **Gestión de Productos (Products/SKUs)**
   - Crear/actualizar productos
   - Consultar productos
   - Gestión de lotes

4. **Gestión de Inventario**
   - Consultar inventario disponible
   - Movimientos de inventario
   - Ajustes de inventario

5. **Órdenes de Entrada (Inbound Orders)**
   - Crear órdenes de compra
   - Recepciones
   - Confirmaciones de entrada

6. **Órdenes de Salida (Outbound Orders)**
   - Crear órdenes de venta
   - Picking
   - Packing
   - Despachos

7. **Transferencias**
   - Transferencias entre bodegas
   - Transferencias entre ubicaciones

8. **Reportes y Consultas**
   - Reportes de inventario
   - Reportes de movimientos
   - Trazabilidad

### Características Técnicas WMS
- **Arquitectura**: Microservicios
- **Base de datos**: Distribuida (múltiples servicios)
- **Autenticación**: (Por determinar - revisar colección)
- **Enfoque**: Gestión completa de almacén sin RFID

---

## Diferencias Clave

| Aspecto | Kong RFID | WMS |
|---------|-----------|-----|
| **Arquitectura** | Monolito | Microservicios |
| **Base de Datos** | RDS Relacional | Distribuida |
| **Tecnología Core** | RFID tracking | Warehouse management |
| **Complejidad API** | ~10 módulos principales | ~8 módulos principales |
| **Enfoque** | Tracking automático con RFID | Gestión manual/semi-automática |
| **Integraciones** | Módulo específico de integraciones | (Por determinar) |

---

## Implicaciones para la Integración con Siesa

### 1. Arquitectura Multi-Producto Requerida

La integración debe soportar:
- **Configuración por tenant** que especifique qué producto usa (RFID o WMS)
- **Adaptadores específicos** para cada producto
- **Mapeos de datos diferentes** para cada producto

### 2. Endpoints Comunes a Integrar

Ambos productos necesitan sincronizar con Siesa:

#### Datos Maestros (Master Data)
- **Productos/SKUs**: Ambos necesitan sincronizar catálogo de productos
- **Bodegas/Ubicaciones**: Ambos manejan ubicaciones físicas
- **Clientes**: Ambos necesitan información de clientes

#### Transacciones
- **Entradas de inventario**: 
  - Kong: Lecturas RFID de entrada
  - WMS: Recepciones de órdenes de compra
  
- **Salidas de inventario**:
  - Kong: Lecturas RFID de salida
  - WMS: Despachos de órdenes de venta

- **Ajustes de inventario**:
  - Kong: Reconciliación RFID
  - WMS: Ajustes manuales

### 3. Flujos de Integración Diferentes

#### Kong RFID → Siesa
1. Lectura RFID detecta movimiento
2. Sistema valida contra inventario
3. Genera transacción automática
4. Sincroniza con Siesa en tiempo real

#### WMS → Siesa
1. Usuario ejecuta operación en WMS
2. Sistema valida y confirma
3. Genera documento de movimiento
4. Sincroniza con Siesa (puede ser batch o tiempo real)

---

## Recomendaciones de Diseño

### 1. Patrón Adapter por Producto

```
Siesa Integration Service
├── Common Layer (Siesa API client)
├── Kong Adapter
│   ├── Inventory sync
│   ├── RFID events → Siesa transactions
│   └── Master data sync
└── WMS Adapter
    ├── Warehouse operations → Siesa
    ├── Order fulfillment → Siesa
    └── Master data sync
```

### 2. Configuración por Tenant

```json
{
  "tenantId": "cliente-123",
  "product": "KONG_RFID",  // o "WMS"
  "siesaConfig": {
    "companyId": "...",
    "credentials": "..."
  },
  "productConfig": {
    "apiUrl": "...",
    "credentials": "...",
    "mappings": {...}
  }
}
```

### 3. Eventos Comunes con Implementaciones Específicas

Definir eventos de negocio comunes:
- `InventoryReceived`
- `InventoryShipped`
- `InventoryAdjusted`
- `ProductCreated`
- `ProductUpdated`

Cada adaptador implementa cómo generar estos eventos desde su producto específico.

---

## Próximos Pasos

1. ✅ Analizar colecciones Postman de ambos productos
2. ⏳ Definir mapeos de datos específicos Kong → Siesa
3. ⏳ Definir mapeos de datos específicos WMS → Siesa
4. ⏳ Actualizar requirements.md para incluir arquitectura multi-producto
5. ⏳ Actualizar design.md con patrón de adaptadores
6. ⏳ Actualizar tasks.md con tareas específicas por producto
