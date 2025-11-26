# Checklist de Validacion STAGING - Siesa-Kong RFID

**Fecha**: 2025-11-25  
**Ambiente**: Staging  
**Objetivo**: Validar 100% la integracion antes de deploy a produccion

---

## RESUMEN EJECUTIVO

**Estado Actual**: Staging deployed  
**Proximo Paso**: Validacion exhaustiva de todos los puntos de integracion  
**Criterio de Exito**: Todos los checkboxes marcados antes de produccion

---

## FASE 1: Validacion de Infraestructura AWS

### 1.1 Lambdas Deployadas

- [ ] siesa-extractor-staging existe
- [ ] siesa-transformer-staging existe
- [ ] siesa-loader-staging existe
- [ ] Todas tienen runtime Python 3.11+
- [ ] Todas tienen timeout > 5 minutos
- [ ] Todas tienen memory > 512 MB

### 1.2 DynamoDB

- [ ] Tabla clients-config-staging existe
- [ ] Tiene GSI en enabled
- [ ] Tiene GSI en product_type
- [ ] Encryption habilitada
- [ ] Contiene configuracion de cliente Parchita

### 1.3 S3 Bucket

- [ ] Bucket existe
- [ ] Versioning habilitado
- [ ] Encryption habilitada
- [ ] Contiene field-mappings-kong.json
- [ ] Field mappings es valido JSON

### 1.4 Secrets Manager

- [ ] Secret staging/parchita/siesa-credentials existe
- [ ] Secret staging/parchita/kong-credentials existe
- [ ] Secrets tienen valores validos (no vacios)
- [ ] Secrets tienen permisos correctos

### 1.5 CloudWatch Logs

- [ ] Log group /aws/lambda/siesa-extractor-staging existe
- [ ] Log group /aws/lambda/siesa-transformer-staging existe
- [ ] Log group /aws/lambda/siesa-loader-staging existe
- [ ] Retention configurado (7 dias staging)
- [ ] KMS encryption habilitada

### 1.6 IAM Roles

- [ ] Role de Lambda execution existe
- [ ] Tiene permisos DynamoDB
- [ ] Tiene permisos Secrets Manager
- [ ] Tiene permisos S3
- [ ] Tiene permisos CloudWatch Logs

---

## FASE 2: Validacion de Conectividad

### 2.1 Siesa API - Extraccion

**Campos Siesa a Verificar**:
- [ ] f120_codigo_externo (ID producto)
- [ ] f120_descripcion (nombre)
- [ ] f120_referencia (SKU)
- [ ] f120_codigo_barras (EAN)
- [ ] f120_precio_venta (precio)

**Checklist**:
- [ ] Lambda se ejecuta sin errores
- [ ] Respuesta contiene statusCode: 200
- [ ] Respuesta contiene productos extraidos
- [ ] Productos tienen estructura correcta de Siesa
- [ ] Paginacion funciona (si hay mas de 10 productos)
- [ ] Autenticacion con Siesa exitosa
- [ ] Logs en CloudWatch son claros

### 2.2 Transformacion de Datos

**Campos Canonicos a Verificar**:
- [ ] product_id mapeado desde Siesa
- [ ] name mapeado correctamente
- [ ] ean validado (13 digitos)
- [ ] external_id presente
- [ ] Tipos de datos correctos (string, number, etc.)

**Checklist**:
- [ ] Lambda se ejecuta sin errores
- [ ] Respuesta contiene statusCode: 200
- [ ] Productos transformados a modelo canonico
- [ ] Field mappings aplicados correctamente
- [ ] Validaciones de campos requeridos funcionan
- [ ] Custom fields con prefijo custom: funcionan
- [ ] Logs muestran warnings de validacion

### 2.3 Kong API - Carga

**Campos Kong a Verificar**:
- [ ] external_id en Kong
- [ ] name en Kong
- [ ] ean en Kong
- [ ] rfid_tag_id en Kong (si aplica)
- [ ] properties en Kong

**Checklist**:
- [ ] Lambda se ejecuta sin errores
- [ ] Respuesta contiene statusCode: 200
- [ ] KongAdapter se crea correctamente
- [ ] Autenticacion con Kong exitosa
- [ ] Productos se cargan a Kong
- [ ] Batching funciona (100 productos por batch)
- [ ] Retry logic funciona en errores
- [ ] DynamoDB actualizado con sync status

---

## FASE 3: Validacion End-to-End

### 3.1 Flujo Completo ETL

- [ ] Extractor → Transformer → Loader ejecutan en secuencia
- [ ] Datos fluyen correctamente entre lambdas
- [ ] No hay perdida de datos
- [ ] Errores se manejan correctamente
- [ ] Logs muestran flujo completo
- [ ] Metricas en CloudWatch se registran

### 3.2 Validacion de Datos en Kong

- [ ] Productos de Siesa aparecen en Kong
- [ ] Datos coinciden con Siesa
- [ ] No hay duplicados
- [ ] Campos mapeados correctamente
- [ ] Timestamps actualizados
- [ ] RFID tags asignados (si aplica)

### 3.3 Validacion Bidireccional

- [ ] Siesa → Kong: Productos nuevos en Siesa aparecen en Kong
- [ ] Siesa → Kong: Actualizaciones en Siesa se reflejan en Kong
- [ ] Siesa → Kong: Productos eliminados en Siesa se marcan en Kong
- [ ] Kong → Siesa: (Si aplica) Cambios en Kong no rompen sync
- [ ] Conteo: Numero de productos coincide entre sistemas

---

## FASE 4: Validacion de Casos de Error

### 4.1 Manejo de Errores Siesa

- [ ] Error de autenticacion se maneja correctamente
- [ ] Logs muestran error claro
- [ ] No se crashea la Lambda
- [ ] Retry logic se activa
- [ ] Circuit breaker funciona (si implementado)

### 4.2 Manejo de Errores Kong

- [ ] Error de conexion se maneja correctamente
- [ ] Logs muestran error claro
- [ ] Retry con exponential backoff funciona
- [ ] Datos no se pierden
- [ ] DynamoDB registra fallo

### 4.3 Datos Invalidos

- [ ] Validacion detecta EAN invalido
- [ ] Producto se marca como error
- [ ] Logs muestran warning
- [ ] Otros productos continuan procesandose
- [ ] Reporte de errores generado

---

## FASE 5: Validacion de Performance

### 5.1 Volumen de Datos

- [ ] 10 productos: < 10 segundos
- [ ] 100 productos: < 30 segundos
- [ ] 1000 productos: < 5 minutos
- [ ] No hay timeouts
- [ ] Memoria suficiente
- [ ] Batching funciona correctamente

### 5.2 Metricas CloudWatch

- [ ] Duration promedio aceptable
- [ ] No hay errores frecuentes
- [ ] Throttles = 0
- [ ] Invocations registradas
- [ ] Custom metrics funcionan

---

## FASE 6: Validacion de Monitoreo

### 6.1 CloudWatch Logs

- [ ] Logs estructurados y legibles
- [ ] Nivel de log apropiado (INFO, WARNING, ERROR)
- [ ] Context de client_id presente
- [ ] Timestamps correctos
- [ ] No hay informacion sensible (passwords, tokens)
- [ ] Stack traces en errores

### 6.2 Alarmas (Si configuradas)

- [ ] Alarma de errores configurada
- [ ] Alarma de duration configurada
- [ ] SNS topic configurado
- [ ] Email de notificacion funciona
- [ ] Alarmas se disparan correctamente

---

## FASE 7: Validacion de Seguridad

### 7.1 Secrets Management

- [ ] Secrets no estan en codigo
- [ ] Secrets no estan en logs
- [ ] Secrets tienen rotation policy
- [ ] Acceso a secrets auditado
- [ ] Encryption at rest habilitada

### 7.2 Input Validation

- [ ] Sanitizacion de inputs funciona
- [ ] SQL injection prevenido
- [ ] XSS prevenido
- [ ] Path traversal prevenido
- [ ] SafeExpressionEvaluator funciona

### 7.3 IAM Permissions

- [ ] Least privilege aplicado
- [ ] No hay permisos * innecesarios
- [ ] Roles especificos por Lambda
- [ ] No hay credenciales hardcoded

---

## CRITERIOS DE APROBACION PARA PRODUCCION

**Todos estos deben estar marcados**:
- [ ] 100% de tests de infraestructura pasando
- [ ] 100% de tests de conectividad pasando
- [ ] 95%+ de tests end-to-end pasando
- [ ] Manejo de errores validado
- [ ] Performance aceptable (< 5 min para 1000 productos)
- [ ] Seguridad validada
- [ ] Documentacion completa
- [ ] Aprobacion del Tech Lead
- [ ] Aprobacion del Product Owner

---

## DASHBOARD DE PROGRESO

FASE 1: Infraestructura    [ ] 0/6  (0%)
FASE 2: Conectividad       [ ] 0/3  (0%)
FASE 3: End-to-End         [ ] 0/3  (0%)
FASE 4: Manejo de Errores  [ ] 0/3  (0%)
FASE 5: Performance        [ ] 0/2  (0%)
FASE 6: Monitoreo          [ ] 0/2  (0%)
FASE 7: Seguridad          [ ] 0/3  (0%)

TOTAL: 0/22 (0%)

---

**Ultima actualizacion**: 2025-11-25  
**Responsable**: Edgar  
**Estado**: Pendiente de ejecucion
