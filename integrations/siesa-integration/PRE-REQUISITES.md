# Pre-requisitos para Implementación - Siesa Integration

Este documento lista toda la información que necesitas recopilar ANTES de empezar la implementación.

## ✅ Checklist de Información Requerida

### 1. Información de Siesa API ✅

#### 1.1 Configuración General
- [x] **Base URL**: `https://serviciosqa.siesacloud.com/api/siesa/v3/`
- [x] **Versión de API**: `v3`
- [x] **Método de Autenticación**: 
  - [x] Bearer Token + Custom Headers
  - **Headers requeridos**:
    - `Authorization: Bearer {token}`
    - `ConniKey: {key}`
    - `ConniToken: {token}`

#### 1.2 Credenciales de Prueba
- [x] **URL Ambiente Test/Sandbox**: `https://serviciosqa.siesacloud.com`
- [x] **Bearer Token**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (ver Postman collection)
- [x] **ConniKey**: `925ee450b69d8744c4c5a0272ccba195`
- [x] **ConniToken**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (ver Postman collection)
- [x] **Company ID (idCompania)**: `8585`

#### 1.3 Endpoints Disponibles ✅
**Endpoint Base**: `GET /ejecutarconsultaestandar`

**Consultas WMS Disponibles** (cambiar parámetro `descripcion`):
- [x] `API_v2_Items` - Productos/Items
- [x] `API_v2_ItemsExtensiones` - Extensiones de Items
- [x] `API_v2_ItemsUnidadesMedida` - Unidades de Medida
- [x] `API_v2_ItemsCriterios` - Criterios de Items
- [x] `API_v2_ItemsBarras` - Códigos de Barras
- [x] `API_v2_Bodegas` - Bodegas/Almacenes
- [x] `API_v2_Ubicaciones` - Ubicaciones en Bodega
- [x] `API_v2_Inventarios_Entradas_Directas` - Entradas de Inventario
- [x] `API_v2_Inventarios_Salidas_Directas` - Salidas de Inventario
- [x] `API_v2_Inventarios_Ajustes` - Ajustes de Inventario
- [x] `API_v2_Compras_Ordenes` - Órdenes de Compra
- [x] `API_v2_Ventas_Pedidos` - Pedidos de Venta
- [x] `API_v2_Ventas_Pedidos_Compromisos` - Compromisos de Pedidos
- [x] `API_v2_Terceros` - Terceros/Clientes/Proveedores
- [x] `API_v2_Centros_Operacion` - Centros de Operación

**Ejemplo de URL Completa**:
```
GET https://serviciosqa.siesacloud.com/api/siesa/v3/ejecutarconsultaestandar?idCompania=8585&descripcion=API_v2_Items&paginacion=numPag=1|tamPag=100
```

#### 1.4 Estructura de Respuesta
**Formato**: JSON con estructura estándar de Siesa

**Nota**: Para obtener la estructura exacta de cada consulta, ejecutar el request en Postman (archivo `SIESA_APIs_WMS_Completo.json`). Los campos varían por consulta pero siguen el patrón `f{numero}_{nombre_campo}`.

#### 1.5 Campos Disponibles en Siesa
**Acción Requerida**: Ejecutar consulta `API_v2_Items` en Postman para obtener lista completa de campos.

**Campos típicos esperados** (verificar con respuesta real):
- `f120_id` - ID del producto
- `f120_descripcion` - Descripción/Nombre
- `f120_codigo` - Código del producto
- `f120_referencia` - Referencia
- `f120_codigo_barras` - Código de barras/EAN
- `f120_unidad_medida` - Unidad de medida
- `f120_cantidad` - Cantidad en stock

#### 1.6 Paginación ✅
- [x] **Método de paginación**: Custom (Siesa format)
  - Formato: `paginacion=numPag=1|tamPag=100`
  - `numPag`: Número de página (inicia en 1)
  - `tamPag`: Tamaño de página (registros por página)
- [x] **Máximo registros por página**: 100 (recomendado)

#### 1.7 Rate Limiting
- [ ] **Límite de requests**: ⚠️ PENDIENTE - Consultar con equipo Siesa
- [ ] **Header de rate limit**: ⚠️ PENDIENTE
- [ ] **Código de respuesta cuando excede**: Probablemente 429

---

### 2. Información de Kong/APES API

#### 2.1 Configuración General
- [ ] **Base URL**: _______________________________________
- [ ] **Versión de API**: _______________________________________
- [ ] **Método de Autenticación**:
  - [ ] API Key (Header)
  - [ ] Bearer Token
  - [ ] OAuth 2.0
  - [ ] Otro: _______________________________________

#### 2.2 Credenciales de Prueba
- [ ] **URL Ambiente Test**: _______________________________________
- [ ] **API Key / Token**: _______________________________________
- [ ] **Tenant ID**: _______________________________________

#### 2.3 Endpoints de Productos
- [ ] **Crear Producto**:
  - Método: POST
  - URL: _______________________________________
  - Content-Type: _______________________________________

- [ ] **Actualizar Producto**:
  - Método: PUT
  - URL: _______________________________________

- [ ] **Crear/Actualizar en Bulk**:
  - Método: POST
  - URL: _______________________________________
  - Máximo registros por request: _______________________________________

#### 2.4 Estructura de Request
```json
// Pega aquí un ejemplo de request body para Kong API
{
  "ejemplo": "completar con estructura real"
}
```

#### 2.5 Campos Requeridos en Kong
Lista todos los campos que Kong necesita para crear un producto:

| Campo Kong | Tipo | Requerido | Descripción | Ejemplo |
|------------|------|-----------|-------------|---------|
| | | Sí/No | | |
| | | Sí/No | | |
| | | Sí/No | | |

#### 2.6 Rate Limiting
- [ ] **Límite de requests**: _______ requests por _______
- [ ] **Código de respuesta cuando excede**: _______________________________________

---

### 3. Mapeo de Campos Siesa ↔ Kong

Completa esta tabla mapeando campos entre ambos sistemas:

| Campo Siesa | Campo Kong | Tipo | Transformación Necesaria | Requerido |
|-------------|------------|------|--------------------------|-----------|
| | | string | Ninguna | Sí |
| | | string | Ninguna | Sí |
| | | string | Ninguna | No |
| | | integer | Ninguna | Sí |
| | | string | Ninguna | No |

**Transformaciones Comunes:**
- Formato de fecha: Siesa usa `YYYY-MM-DD`, Kong usa `ISO8601`
- Moneda: Siesa usa `COP`, Kong usa `USD`
- Booleanos: Siesa usa `"S"/"N"`, Kong usa `true/false`

---

### 4. Cliente de Prueba

#### 4.1 Información del Cliente Test
- [ ] **Client ID**: _______________________________________
- [ ] **Nombre del Cliente**: _______________________________________
- [ ] **Cuenta AWS** (si tiene): _______________________________________

#### 4.2 Datos de Prueba
- [ ] **¿Tiene productos en Siesa test?**: Sí / No
- [ ] **Cantidad aproximada de productos**: _______________________________________
- [ ] **¿Tiene instancia de Kong test?**: Sí / No

---

### 5. Documentos de Referencia

Marca los documentos que ya revisaste:

- [ ] `ERP Siesa/APIs SIESA.pdf`
- [ ] `ERP Siesa/Detalle de APIs SIESA 100125.xlsx`
- [ ] `ERP Siesa/4. MAPEO_CAMPOS_INTEGRACION - SIESA ↔ Kong.pdf`
- [ ] `ERP Siesa/SIESA_Documentación Módulo de Conectividad V2.pdf`
- [ ] Documentación de Kong/APES API (conseguir)

---

## 🧪 Pruebas de Conectividad

Una vez tengas las credenciales, prueba que puedes acceder a las APIs:

### Test Siesa API
```powershell
# Reemplaza con tus valores reales
curl -X GET "https://test.siesa.com/api/products?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Resultado esperado**: Lista de productos en JSON

### Test Kong API
```powershell
# Reemplaza con tus valores reales
curl -X POST "https://test.kong.com/api/products" \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "TEST001",
    "name": "Producto de Prueba"
  }'
```

**Resultado esperado**: Producto creado exitosamente

---

## 📞 Contactos para Conseguir Información

### Siesa
- **Contacto**: _______________________________________
- **Email**: _______________________________________
- **Teléfono**: _______________________________________
- **Solicitar**: Credenciales de sandbox, documentación API

### Kong/APES
- **Contacto**: _______________________________________
- **Email**: _______________________________________
- **Teléfono**: _______________________________________
- **Solicitar**: Credenciales de test, documentación API

---

## ✅ Cuando Tengas Todo

Una vez completes este documento:

1. Guárdalo en `integrations/siesa-integration/PRE-REQUISITES.md`
2. Avísame que tienes la información completa
3. Empezaremos con Task 1.1 del plan de implementación

---

## 📝 Notas Adicionales

Usa este espacio para notas importantes:

```
[Escribe aquí cualquier nota relevante]
```
