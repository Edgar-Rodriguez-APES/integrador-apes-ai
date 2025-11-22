# Siesa API - Resumen Técnico

## ✅ Información Confirmada

### Autenticación
```http
GET https://serviciosqa.siesacloud.com/api/siesa/v3/ejecutarconsultaestandar
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ConniKey: 925ee450b69d8744c4c5a0272ccba195
ConniToken: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Query Parameters
- `idCompania`: `8585` (Company ID)
- `descripcion`: Nombre de la consulta (ej: `API_v2_Items`)
- `paginacion`: `numPag=1|tamPag=100`

### Consultas WMS Disponibles

| Consulta | Descripción | Uso para Integración |
|----------|-------------|---------------------|
| `API_v2_Items` | Productos/Items | ✅ **PRINCIPAL** - Maestro de productos |
| `API_v2_ItemsExtensiones` | Propiedades extendidas | ✅ Campos custom |
| `API_v2_ItemsBarras` | Códigos de barras | ✅ EAN/Barcodes |
| `API_v2_ItemsUnidadesMedida` | Unidades de medida | ✅ UOM |
| `API_v2_Bodegas` | Bodegas/Almacenes | ✅ Warehouses |
| `API_v2_Ubicaciones` | Ubicaciones | ✅ Warehouse locations |
| `API_v2_Inventarios_Entradas_Directas` | Entradas | ⚠️ Movimientos |
| `API_v2_Inventarios_Salidas_Directas` | Salidas | ⚠️ Movimientos |
| `API_v2_Inventarios_Ajustes` | Ajustes | ⚠️ Movimientos |
| `API_v2_Ventas_Pedidos` | Pedidos | 📦 Opcional |
| `API_v2_Compras_Ordenes` | Órdenes de compra | 📦 Opcional |

## ⚠️ Acciones Pendientes

### 1. Ejecutar Consulta de Productos
**Acción**: Ejecutar en Postman el request `co_items` (API_v2_Items)

**Objetivo**: Obtener la estructura real de respuesta JSON con nombres de campos exactos.

**Comando curl equivalente**:
```bash
curl -X GET "https://serviciosqa.siesacloud.com/api/siesa/v3/ejecutarconsultaestandar?idCompania=8585&descripcion=API_v2_Items&paginacion=numPag=1|tamPag=10" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "ConniKey: 925ee450b69d8744c4c5a0272ccba195" \
  -H "ConniToken: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Guardar**: La respuesta JSON completa para análisis de campos.

### 2. Identificar Campos Clave
De la respuesta JSON, identificar los campos que corresponden a:

| Dato Necesario | Campo Siesa (buscar en JSON) | Ejemplo |
|----------------|------------------------------|---------|
| ID del producto | `f120_id` o similar | "PROD001" |
| Código/SKU | `f120_codigo` o similar | "SKU-123" |
| Nombre | `f120_descripcion` o similar | "Producto X" |
| Código de barras/EAN | `f120_codigo_barras` o similar | "1234567890123" |
| Cantidad en stock | `f120_cantidad` o similar | 100 |
| Unidad de medida | `f120_unidad_medida` o similar | "UND" |
| Bodega | `f120_bodega` o similar | "BOD01" |
| Ubicación | `f120_ubicacion` o similar | "A-01-05" |

### 3. Consultar Rate Limits
**Contacto**: Equipo de Siesa o revisar documentación

**Preguntas**:
- ¿Cuántos requests por minuto/hora permite la API?
- ¿Hay headers que indiquen el rate limit restante?
- ¿Qué código HTTP devuelve cuando se excede? (429?)

### 4. Verificar Filtros por Fecha
**Pregunta**: ¿La API permite filtrar productos modificados desde una fecha?

**Probar**:
```
?idCompania=8585&descripcion=API_v2_Items&paginacion=numPag=1|tamPag=100&filtro=fecha_modificacion>2025-01-01
```

**Alternativa**: Si no hay filtro, usar sincronización completa y comparar timestamps.

---

## 🔄 Conectores de Escritura (POST)

### Endpoint Base
```http
POST https://serviciosqa.siesacloud.com/api/siesa/v3/conectoresimportarestandar
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ConniKey: 925ee450b69d8744c4c5a0272ccba195
ConniToken: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json
```

### Query Parameters para Escritura
- `idCompania`: `8585` (Company ID)
- `idDocumento`: ID del conector (ej: `142951`)
- `nombreDocumento`: Nombre del conector (ej: `API_v1_Inventarios_Comercial_DocumentoInv`)

### Conectores Disponibles

#### 1. Movimientos de Inventario
**Conector**: `API_v1_Inventarios_Comercial_DocumentoInv`
- **idDocumento**: `142951`
- **Uso**: Crear movimientos de inventario (entradas/salidas)
- **Estructura JSON**:
  - `Inicial`: Datos de compañía
  - `Documentos`: Encabezado del documento (f350_*, f450_*, f462_*)
  - `Movimientos`: Detalle de movimientos (f470_*)
  - `Final`: Cierre

**Campos Clave del Documento**:
```json
{
  "f350_id_co": "Centro de operación",
  "f350_id_tipo_docto": "Tipo de documento",
  "f350_consec_docto": "Consecutivo",
  "f350_fecha": "Fecha del documento",
  "f350_id_tercero": "ID del tercero",
  "f350_ind_estado": "Estado (0=Activo, 1=Anulado)",
  "f450_id_concepto": "Concepto del movimiento",
  "f450_id_bodega_salida": "Bodega origen",
  "f450_id_bodega_entrada": "Bodega destino"
}
```

**Campos Clave del Movimiento**:
```json
{
  "f470_id_item": "ID del producto",
  "f470_referencia_item": "Referencia del producto",
  "f470_codigo_barras": "Código de barras",
  "f470_id_bodega": "Bodega",
  "f470_id_ubicacion_aux": "Ubicación",
  "f470_id_lote": "Lote",
  "f470_cant_base": "Cantidad base",
  "f470_id_unidad_medida": "Unidad de medida",
  "f470_costo_prom_uni": "Costo promedio unitario"
}
```

#### 2. Recepciones de Compra
**Conector**: `API_v1_Compras_Comercial_EntradaOC`
- **idDocumento**: `142948`
- **Uso**: Registrar entradas de mercancía desde órdenes de compra
- **Estructura JSON**:
  - `Inicial`: Datos de compañía
  - `Documentos`: Encabezado (f350_*, f451_*, f462_*, f420_*)
  - `Movimientos`: Detalle de productos recibidos (f470_*, f421_*)
  - `Final`: Cierre

**Campos Adicionales Específicos**:
```json
{
  "f451_id_sucursal_prov": "Sucursal del proveedor",
  "f451_id_tercero_comprador": "Comprador",
  "f451_num_docto_referencia": "Número de documento de referencia",
  "f451_id_moneda_docto": "Moneda del documento",
  "f451_tasa_conv": "Tasa de conversión",
  "f451_ind_consignacion": "Indicador de consignación",
  "f420_id_co_docto": "CO del documento base (OC)",
  "f420_id_tipo_docto": "Tipo de documento base (OC)",
  "f420_consec_docto": "Consecutivo del documento base (OC)"
}
```

#### 3. Despachos de Pedidos (Remisiones)
**Conector**: `API_v1_Ventas_Comercial_RemisionPedido`
- **idDocumento**: `142945`
- **Uso**: Crear remisiones de despacho desde pedidos de venta
- **Estructura JSON**:
  - `Inicial`: Datos de compañía
  - `Remision`: Encabezado de remisión (F350_*, F430_*, f462_*, f460_*)
  - `Movtoventascomercial`: Detalle de productos despachados (f470_*)
  - `Final`: Cierre

**Campos Específicos de Ventas**:
```json
{
  "F430_ID_TIPO_DOCTO": "Tipo de documento base (pedido)",
  "F430_CONSEC_DOCTO": "Consecutivo del pedido",
  "f470_ind_obsequio": "Indicador de obsequio",
  "f470_id_lista_precio": "Lista de precios",
  "f470_vlr_bruto": "Valor bruto",
  "f470_ind_naturaleza": "Naturaleza del movimiento",
  "f470_ind_impto_asumido": "Impuesto asumido",
  "f470_id_causal_devol": "Causal de devolución"
}
```

#### 4. Transferencias de Inventario
**Conector**: `API_v1_Inventarios_Comercial_TransferenciaDirecta`
- **idDocumento**: `173066`
- **Uso**: Transferencias directas entre bodegas
- **Estructura JSON**:
  - `Inicial`: Datos de compañía
  - `Documentos`: Encabezado (f350_*, f450_*)
  - `Movimiento de Seriales`: Seriales transferidos (f479_*)
  - `Movimientos`: Detalle de productos (f470_*)
  - `Final`: Cierre

**Campos de Transferencia**:
```json
{
  "f450_id_bodega_salida": "Bodega origen",
  "f450_id_bodega_entrada": "Bodega destino",
  "f470_id_ubicacion_aux": "Ubicación origen",
  "f470_id_ubicacion_aux_ent": "Ubicación destino",
  "f470_id_lote": "Lote origen",
  "f470_id_lote_ent": "Lote destino"
}
```

**Campos de Seriales**:
```json
{
  "f479_id_serial": "ID del serial",
  "f479_fecha_garantia": "Fecha de garantía",
  "f479_notas": "Notas del serial"
}
```

### Estructura Común de Transporte (f462_*)
Todos los conectores incluyen información de transporte:
```json
{
  "f462_id_vehiculo": "ID del vehículo",
  "f462_id_tercero_transp": "Transportadora",
  "f462_id_sucursal_transp": "Sucursal transportadora",
  "f462_id_tercero_conductor": "ID del conductor",
  "f462_nombre_conductor": "Nombre del conductor",
  "f462_identif_conductor": "Identificación del conductor",
  "f462_numero_guia": "Número de guía",
  "f462_cajas": "Número de cajas",
  "f462_peso": "Peso total",
  "f462_volumen": "Volumen",
  "f462_valor_seguros": "Valor de seguros",
  "f462_notas": "Notas de transporte"
}
```

### Patrón de Respuesta
Todos los conectores devuelven una respuesta con:
- **Código HTTP**: 200 (éxito), 400 (error de validación), 500 (error del servidor)
- **Estructura JSON**:
```json
{
  "success": true/false,
  "message": "Mensaje descriptivo",
  "data": {
    "consecutivo": "Número del documento creado",
    "errores": []
  }
}
```

## 📋 Próximos Pasos

### Consultas (GET)
1. **Ahora mismo**: Ejecutar request en Postman y guardar respuesta JSON
2. **Analizar**: Identificar nombres exactos de campos
3. **Documentar**: Completar mapeo de campos Siesa → Canónico
4. **Validar**: Probar paginación con más de 100 registros
5. **Confirmar**: Rate limits con equipo Siesa

### Escritura (POST)
1. **Validar**: Campos obligatorios vs opcionales para cada conector
2. **Probar**: Crear un documento de prueba en ambiente QA
3. **Documentar**: Códigos de error y mensajes de validación
4. **Mapear**: Flujos Kong → Siesa para cada tipo de operación
5. **Confirmar**: Manejo de transacciones y rollback

## 🔗 Referencias

- **Postman Collection (Consultas)**: `ERP Siesa/SIESA_APIs_WMS_Completo.json`
- **Postman Collection (Escritura)**: `ERP Siesa/Conectores estandar siesa.postman_collection.json`
- **Documentación**: `ERP Siesa/SIESA_Documentación Módulo de Conectividad V2.pdf`
- **Mapeo de Campos**: `ERP Siesa/4. MAPEO_CAMPOS_INTEGRACION - SIESA ↔ Kong.pdf`
