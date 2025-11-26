# Plan de Implementacion WMS - Siesa-WMS Integration

**Fecha**: 2025-11-25  
**Estado**: Pendiente (Week 2)  
**Prerequisito**: Kong integration 100% validada y en produccion

---

## RESUMEN EJECUTIVO

**Objetivo**: Implementar integracion Siesa → WMS siguiendo el mismo patron de Kong  
**Tiempo Estimado**: 2-3 dias  
**Complejidad**: Media (arquitectura ya existe, solo agregar adapter)

---

## QUE YA ESTA LISTO (Reutilizable)

### Infraestructura Completa
- [x] 3 Lambdas ETL (Extractor, Transformer, Loader)
- [x] DynamoDB para configuracion
- [x] S3 para field mappings
- [x] Secrets Manager para credenciales
- [x] CloudWatch Logs y Metrics
- [x] IAM Roles y Policies
- [x] Pattern de Adapters (Base + Factory)

### Documentacion Completa
- [x] WMS API documentada (WMS-API-COMPLETE-SUMMARY.md)
- [x] Field mappings WMS (field-mappings-wms.json)
- [x] Diferencias Kong vs WMS identificadas
- [x] Endpoints WMS documentados

---

## QUE FALTA IMPLEMENTAR

### 1. WMS Adapter (2-3 horas)

**Archivo**: `src/lambdas/loader/adapters/wms_adapter.py`

**Funcionalidad Requerida**:
- Autenticacion JWT con WMS
- Transformacion de modelo canonico a WMS
- Llamadas a WMS API (POST /products)
- Manejo de paginacion cursor-based
- Manejo de errores especificos WMS
- Retry logic con exponential backoff

**Diferencias vs Kong**:
- Autenticacion: JWT (POST /auth) vs Token (Djoser)
- Paginacion: Cursor-based vs Page-based
- Campos: groups array vs type_id/group_id
- Precios: sale_price/purchase_price (WMS tiene, Kong no)

**Codigo Base** (estructura):
```python
class WMSAdapter(ProductAdapter):
    def __init__(self, credentials, config):
        super().__init__(credentials, config)
        self.base_url = credentials.get('base_url')
        self.token = None
    
    def authenticate(self):
        # POST /auth con username/password
        # Guardar JWT token
        pass
    
    def transform_product(self, canonical_product):
        # Transformar de canonico a WMS
        # Mapear groups array
        # Agregar sale_price/purchase_price
        pass
    
    def load_products(self, products):
        # POST /products
        # Manejar cursor pagination
        # Retry en errores
        pass
```

### 2. Actualizar Adapter Factory (15 min)

**Archivo**: `src/lambdas/loader/adapters/adapter_factory.py`

**Cambio Requerido**:
```python
elif product_type_lower in ['wms']:
    logger.info(f"Creating WMSAdapter for product type: {product_type}")
    return WMSAdapter(credentials, config)
```

### 3. Tests Unitarios WMS (2 horas)

**Archivo**: `tests/unit/test_wms_adapter.py`

**Tests Requeridos**:
- Test autenticacion JWT
- Test transformacion de productos
- Test load_products
- Test manejo de errores
- Test paginacion cursor-based
- Test retry logic

### 4. Configuracion Cliente WMS (1 hora)

**DynamoDB Entry**:
```json
{
  "client_id": "parchita-wms-staging",
  "product_type": "wms",
  "enabled": true,
  "field_mappings_key": "field-mappings-wms.json"
}
```

**Secrets Manager**:
```json
{
  "base_url": "https://staging.wms.parchita.com/api",
  "username": "parchita-test",
  "password": "wms-test-123"
}
```

### 5. Validacion WMS (2 horas)

**Tests End-to-End**:
- Extractor → Transformer → Loader (WMS)
- Validar datos en WMS
- Validar campos especificos WMS
- Validar groups array
- Validar precios

---

## DIFERENCIAS CLAVE KONG VS WMS

### Autenticacion

**Kong**:
```python
# Token directo (Djoser)
headers = {"Authorization": f"Token {token}"}
```

**WMS**:
```python
# JWT via POST /auth
response = requests.post(f"{base_url}/auth", json={
    "username": username,
    "password": password
})
token = response.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
```

### Paginacion

**Kong**:
```python
# Page-based
params = {"page": page_number, "page_size": 100}
```

**WMS**:
```python
# Cursor-based
params = {"last_evaluated_key_id": cursor}
cursor = response.json().get("last_evaluated_key_id")
```

### Estructura de Producto

**Kong**:
```json
{
  "external_id": "PROD-001",
  "name": "Producto 1",
  "ean": "1234567890123",
  "rfid_tag_id": "RFID-001",
  "type_id": 1,
  "group_id": 2
}
```

**WMS**:
```json
{
  "external_id": "PROD-001",
  "name": "Producto 1",
  "barcode": "1234567890123",
  "sale_price": 100.50,
  "purchase_price": 80.00,
  "groups": [
    {
      "group_external_id": "CAT-001",
      "group_name": "Categoria 1",
      "group_type": "category"
    }
  ]
}
```

---

## PLAN DE EJECUCION (Week 2)

### Dia 1: Implementacion

**Manana (3 horas)**:
1. Implementar WMSAdapter (2 horas)
2. Actualizar AdapterFactory (15 min)
3. Escribir tests unitarios (45 min)

**Tarde (2 horas)**:
4. Configurar cliente WMS en staging (30 min)
5. Crear secrets WMS (15 min)
6. Ejecutar tests unitarios (30 min)
7. Fix bugs encontrados (45 min)

### Dia 2: Validacion

**Manana (2 horas)**:
1. Deploy WMS adapter a staging (30 min)
2. Test end-to-end con datos reales (1 hora)
3. Validar datos en WMS (30 min)

**Tarde (2 horas)**:
4. Validacion exhaustiva (1 hora)
5. Ajustes finales (30 min)
6. Documentacion (30 min)

### Dia 3: Produccion

**Manana (2 horas)**:
1. Deploy WMS a produccion (30 min)
2. Configurar cliente WMS prod (30 min)
3. Primera ejecucion supervisada (1 hora)

**Tarde (1 hora)**:
4. Monitoreo post-deploy (1 hora)
5. Validacion final (30 min)

---

## CHECKLIST DE IMPLEMENTACION WMS

### Codigo
- [ ] WMSAdapter implementado
- [ ] AdapterFactory actualizado
- [ ] Tests unitarios escritos
- [ ] Tests unitarios pasando
- [ ] Code review completado

### Configuracion
- [ ] field-mappings-wms.json validado
- [ ] Cliente WMS en DynamoDB (staging)
- [ ] Secrets WMS creados (staging)
- [ ] Cliente WMS en DynamoDB (prod)
- [ ] Secrets WMS creados (prod)

### Testing
- [ ] Test autenticacion WMS
- [ ] Test transformacion datos
- [ ] Test load productos
- [ ] Test end-to-end
- [ ] Test con datos reales
- [ ] Validacion en WMS

### Deployment
- [ ] Deploy a staging
- [ ] Validacion staging
- [ ] Deploy a produccion
- [ ] Validacion produccion
- [ ] Monitoreo 24 horas

### Documentacion
- [ ] README actualizado
- [ ] WMS adapter documentado
- [ ] Troubleshooting guide
- [ ] Runbook operativo

---

## RIESGOS Y MITIGACIONES

### Riesgo 1: Autenticacion JWT diferente
**Mitigacion**: Ya documentado, implementar segun WMS-API-COMPLETE-SUMMARY.md

### Riesgo 2: Paginacion cursor-based nueva
**Mitigacion**: Implementar segun documentacion, testear con datasets grandes

### Riesgo 3: Estructura groups array compleja
**Mitigacion**: Field mappings ya definidos, validar con datos reales

### Riesgo 4: Credenciales WMS no disponibles
**Mitigacion**: Solicitar con anticipacion, usar staging primero

---

## COMANDOS UTILES

### Deploy WMS Adapter
```powershell
# Staging
$env:ENVIRONMENT = "staging"
cdk deploy SiesaIntegrationStack-staging

# Produccion
$env:ENVIRONMENT = "production"
cdk deploy SiesaIntegrationStack-production
```

### Test WMS Adapter
```powershell
# Test unitario
pytest tests/unit/test_wms_adapter.py -v

# Test end-to-end
aws lambda invoke `
  --function-name siesa-loader-staging `
  --payload '{"client_id":"parchita-wms-staging","product_type":"wms"}' `
  response-wms.json
```

### Validar en WMS
```powershell
# Consultar productos en WMS
curl -X GET "https://staging.wms.parchita.com/api/products?external_id__eq=PROD-001" `
  -H "Authorization: Bearer YOUR-WMS-TOKEN"
```

---

## ESTIMACION DE ESFUERZO

| Tarea | Tiempo | Complejidad |
|-------|--------|-------------|
| WMSAdapter | 2-3 horas | Media |
| Tests | 2 horas | Baja |
| Configuracion | 1 hora | Baja |
| Validacion | 2 horas | Media |
| Deploy | 1 hora | Baja |
| Documentacion | 1 hora | Baja |
| **TOTAL** | **9-10 horas** | **Media** |

**Distribucion**: 2-3 dias de trabajo

---

## CRITERIOS DE EXITO

- [ ] WMSAdapter funciona igual que KongAdapter
- [ ] Autenticacion JWT exitosa
- [ ] Productos se cargan a WMS correctamente
- [ ] Paginacion cursor-based funciona
- [ ] Grupos (groups array) se mapean correctamente
- [ ] Precios (sale_price/purchase_price) se envian
- [ ] Tests unitarios pasando
- [ ] Validacion end-to-end exitosa
- [ ] Documentacion completa
- [ ] Produccion operacional

---

## PROXIMOS PASOS DESPUES DE WMS

### Week 3+: Optimizaciones
- Implementar Circuit Breaker
- Implementar Rate Limiting avanzado
- Optimizar performance
- Agregar mas metricas custom

### Futuro: Mas Integraciones
- TMS (Transport Management System)
- Otros ERPs (SAP, NetSuite, etc.)
- Otros WMS
- Otros sistemas RFID

---

**Ultima actualizacion**: 2025-11-25  
**Responsable**: Edgar  
**Estado**: Planificado para Week 2
