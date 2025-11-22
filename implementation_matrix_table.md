# Matriz de Implementación Tecnológica

## Tabla de Decisiones: ¿Qué Tecnología Usar?

| **CLIENTE TIPO** | **NIVEL CRITICIDAD** | **RECEPCIÓN** | **ENVÍO** | **TIEMPO ESPERADO** | **COSTO/MES** |
|------------------|---------------------|---------------|-----------|-------------------|---------------|
| **MODERNO (Shopify)** | Nivel 1 - Crítico | **Webhook** → Recibimos notif. inmediata | **Webhook** → Enviamos notif. inmediata | 1-5 minutos | $5-10 |
| **MODERNO (Shopify)** | Nivel 2 - Alto | **REST API** → Consultamos c/30 min | **REST API** → Enviamos c/hora | 30 min - 2 horas | $3-5 |
| **MODERNO (Shopify)** | Nivel 3-4 - Medio/Bajo | **Airflow** → Consulta batch diaria | **Airflow** → Envío batch diario | 6-24 horas | $2-3 |
| **INTERMEDIO (ERP Tradicional)** | Nivel 1 - Crítico | **REST API** → Consultamos c/10 min | **REST API** → Enviamos c/15 min | 10-15 minutos | $15-25 |
| **INTERMEDIO (ERP Tradicional)** | Nivel 2 - Alto | **REST API** → Consultamos c/hora | **REST API** → Enviamos c/2 horas | 1-2 horas | $8-12 |
| **INTERMEDIO (ERP Tradicional)** | Nivel 3-4 - Medio/Bajo | **Airflow** → Batch programado | **Airflow** → Batch programado | 6-24 horas | $5-8 |
| **LEGACY (SIESA)** | Nivel 1 - Crítico | **Airflow** → Monitor archivos c/15 min | **Archivo + Email** → Generamos + alertamos | 15 minutos | $25-35 |
| **LEGACY (SIESA)** | Nivel 2 - Alto | **Airflow** → Batch c/hora | **Archivo** → Generamos c/2 horas | 1-2 horas | $15-20 |
| **LEGACY (SIESA)** | Nivel 3-4 - Medio/Bajo | **Airflow** → Batch diario/nocturno | **Archivo** → Batch nocturno | 6-24 horas | $8-12 |

## Explicación de Métodos por Tecnología

### WEBHOOK (Solo Clientes Modernos)
**¿Cómo funciona?**
- **Recepción:** Su sistema nos "llama" automáticamente cuando algo pasa
- **Envío:** Nosotros "llamamos" a su sistema cuando detectamos algo crítico
- **Analogía:** Como recibir/hacer llamada telefónica - inmediato

**Ventajas:** Instantáneo, automático, costo muy bajo
**Limitaciones:** Solo funciona si su sistema es moderno

### REST API (Clientes Modernos e Intermedios)
**¿Cómo funciona?**
- **Recepción:** Preguntamos a su sistema cada X minutos "¿hay algo nuevo?"
- **Envío:** Le decimos a su sistema "esto es lo que pasó"
- **Analogía:** Como revisar el buzón cada X minutos

**Ventajas:** Funciona con mayoría de sistemas, confiable
**Limitaciones:** Frecuencia limitada por restricciones del cliente

### AIRFLOW (Todos los Tipos, Especialmente Legacy)
**¿Cómo funciona?**
- **Recepción:** Robot revisa archivos/bases de datos cada X tiempo
- **Envío:** Robot genera archivos/actualiza bases cada X tiempo
- **Analogía:** Como empleado que revisa bandejas de entrada/salida programadamente

**Ventajas:** Funciona con cualquier sistema, muy confiable
**Limitaciones:** No es inmediato, requiere mayor configuración

## Casos Prácticos de Implementación

### CASO A: E-commerce Crítico (Shopify + Productos Alta Rotación)

| Proceso | Método | Implementación Real |
|---------|--------|-------------------|
| **Nueva orden llega** | Webhook Recepción | Shopify nos avisa en 30 segundos → Actualizamos RFID |
| **Stock se agota** | Webhook Envío | RFID detecta → Avisamos a Shopify en 1 minuto |
| **Reportes diarios** | Airflow | Reporte nocturno a las 2 AM |

**Resultado:** Cero overselling, stock siempre actualizado

### CASO B: Manufactura Tradicional (ERP Intermedio + Operación Estándar)

| Proceso | Método | Implementación Real |
|---------|--------|-------------------|
| **Nueva orden producción** | REST API Recepción | Consultamos ERP cada hora |
| **Material consumido** | REST API Envío | Reportamos consumo cada 2 horas |
| **Inventario físico** | Airflow | Conciliación nocturna |

**Resultado:** Planificación eficiente sin sobrecarga

### CASO C: Cliente Legacy Crítico (SIESA + Productos Críticos)

| Proceso | Método | Implementación Real |
|---------|--------|-------------------|
| **Orden urgente** | Airflow + Monitor | Robot revisa carpeta cada 15 min |
| **Stock crítico** | Archivo + Email | Generamos CSV + email de alerta inmediata |
| **Inventarios** | Airflow | Batch nocturno con archivo |

**Resultado:** Mantiene operación crítica a pesar de limitaciones

## Decisiones Prácticas: ¿Cuál Elegir?

### ¿Su cliente puede recibir webhooks?
- **SÍ + Proceso Crítico** → Use Webhook
- **SÍ + Proceso No Crítico** → Use REST API o Airflow
- **NO** → Use REST API o Airflow

### ¿Su cliente tiene APIs funcionales?
- **SÍ + Sin restricciones** → Use REST API frecuente
- **SÍ + Con restricciones** → Use REST API espaciado
- **NO** → Use Airflow obligatorio

### ¿Qué tan crítico es el proceso?
- **Crítico (Nivel 1)** → Método más rápido disponible
- **Alto (Nivel 2)** → Balance velocidad/costo
- **Medio/Bajo (Nivel 3-4)** → Método más económico

## Alertas y Monitoreo por Método

| **Método** | **Monitoreo** | **Alerta si falla** |
|-----------|---------------|-------------------|
| **Webhook** | Respuesta inmediata esperada | Alerta en 5 minutos |
| **REST API** | Consulta exitosa cada X min | Alerta si 3 consultas fallan |
| **Airflow** | Ejecución programada exitosa | Alerta si batch falla |

## Escalamiento por Fallas

### Si Webhook falla:
1. Reintentar 3 veces en 5 minutos
2. Si persiste → Cambiar temporalmente a REST API
3. Notificar al cliente del problema

### Si REST API falla:
1. Reintentar con backoff (1, 2, 5, 10 minutos)
2. Si persiste → Cambiar temporalmente a Airflow
3. Procesar backlog cuando se recupere

### Si Airflow falla:
1. Reintentar en siguiente slot programado
2. Si persiste → Alerta manual inmediata
3. Procesamiento manual si es crítico

Esta matriz permite tomar decisiones claras basadas en dos factores: **capacidad del cliente** y **criticidad del proceso**, resultando en la combinación óptima de velocidad, confiabilidad y costo.