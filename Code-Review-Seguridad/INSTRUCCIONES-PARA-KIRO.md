# 📋 Instrucciones para Kiro.dev: Implementación de Correcciones de Seguridad

**Fecha:** 2025-01-21  
**Prioridad:** 🔴 CRÍTICA  
**Tiempo Estimado:** 2-3 horas

---

## 🎯 Objetivo

Implementar correcciones de seguridad críticas identificadas en el code review. Se encontraron **7 vulnerabilidades críticas** que deben ser corregidas antes de proceder a producción.

---

## 📦 Archivos a Procesar

Tienes 4 archivos con las correcciones:

1. **safe_eval_fixed.py** - Versión hardened de safe_eval.py
2. **input_validation_fixed.py** - Versión mejorada con regex robustos
3. **test_security_comprehensive.py** - Suite de 56 tests de seguridad
4. **CORRECCIONES-APLICADAS.md** - Documentación completa (para tu referencia)

---

## 🚨 PASO 1: BACKUP (CRÍTICO - NO OMITIR)

Antes de hacer cualquier cambio, crea backups de los archivos originales:

```bash
# Crear directorio de backup
mkdir -p backups/pre-security-fixes

# Backup de archivos originales
cp src/lambdas/common/safe_eval.py backups/pre-security-fixes/
cp src/lambdas/common/input_validation.py backups/pre-security-fixes/

# Verificar que los backups existen
ls -l backups/pre-security-fixes/
```

**✅ CHECKPOINT:** Confirma que los backups se crearon correctamente antes de continuar.

---

## 📝 PASO 2: REEMPLAZAR ARCHIVOS DE SEGURIDAD

### 2.1. Reemplazar safe_eval.py

**Acción:** Reemplazar completamente `src/lambdas/common/safe_eval.py` con el contenido de `safe_eval_fixed.py`

**Comando:**
```bash
cp safe_eval_fixed.py src/lambdas/common/safe_eval.py
```

**Cambios Importantes en este archivo:**
- ✅ Removidas funciones peligrosas: `str()`, `int()`, `float()`, `min()`, `max()`
- ✅ Agregado límite de profundidad (MAX_DEPTH = 50)
- ✅ Bloqueado acceso a atributos (`__class__`, `__globals__`, etc.)
- ✅ Agregado timeout de 1 segundo
- ✅ Validación de complejidad AST
- ✅ Short-circuit evaluation correcto

**⚠️ BREAKING CHANGE:** Las funciones removidas causarán errores si se usan en el código. Continúa al Paso 3 para manejar esto.

---

### 2.2. Reemplazar input_validation.py

**Acción:** Reemplazar completamente `src/lambdas/common/input_validation.py` con el contenido de `input_validation_fixed.py`

**Comando:**
```bash
cp input_validation_fixed.py src/lambdas/common/input_validation.py
```

**Cambios Importantes en este archivo:**
- ✅ Regex SQL mejorados (cubre comentarios, encoding, union, etc.)
- ✅ Regex XSS comprehensivos (100+ event handlers)
- ✅ Agregado límite de recursión en `sanitize_dict`
- ✅ Nueva función: `sanitize_iso_datetime()`
- ✅ Nueva función: `validate_email()`
- ✅ DynamoDB keys más restrictivos
- ✅ Opción de HTML escaping en `sanitize_string`

**✅ COMPATIBLE:** Este archivo es mayormente compatible con código existente.

---

## 🔍 PASO 3: IDENTIFICAR Y CORREGIR USOS DE FUNCIONES REMOVIDAS

**Problema:** Las siguientes funciones fueron removidas de `SAFE_FUNCTIONS` en safe_eval.py:
- `str()`
- `int()`
- `float()`
- `min()`
- `max()`

### 3.1. Buscar Usos en el Código

**Acción:** Busca en TODO el código donde se usan estas funciones dentro de expresiones eval:

```bash
# Buscar archivos que usen safe_eval
grep -r "safe_eval\|apply_transformation_logic\|evaluate_condition" src/lambdas/ --include="*.py"

# Buscar uso de funciones problemáticas
grep -r "int(\|float(\|str(\|min(\|max(" src/lambdas/ --include="*.py"
```

### 3.2. Patrones a Buscar y Corregir

**Busca patrones como estos:**

```python
# ❌ PATRÓN PROBLEMÁTICO 1: int() en expresión
result = safe_eval("int(value) + 10", {"value": "123"})

# ❌ PATRÓN PROBLEMÁTICO 2: str() en expresión  
result = safe_eval("str(value)", {"value": 123})

# ❌ PATRÓN PROBLEMÁTICO 3: Acceso a atributos
result = safe_eval("value.upper()", {"value": "hello"})

# ❌ PATRÓN PROBLEMÁTICO 4: Subscript
result = safe_eval("value[0]", {"value": [1, 2, 3]})
```

### 3.3. Aplicar Correcciones

**Para cada caso encontrado, aplica estas correcciones:**

#### Caso 1: Conversión de tipos (int, float, str)
```python
# ❌ ANTES:
result = safe_eval("int(value) + 10", {"value": "123"})

# ✅ DESPUÉS - Opción A (conversión previa):
from common.input_validation import sanitize_string
try:
    int_value = int(sanitize_string(value))
    result = safe_eval("value + 10", {"value": int_value})
except ValueError:
    logger.error("Invalid integer conversion")
    result = value  # o valor por defecto

# ✅ DESPUÉS - Opción B (sin eval):
from common.input_validation import sanitize_string
try:
    int_value = int(sanitize_string(value))
    result = int_value + 10
except ValueError:
    logger.error("Invalid integer conversion")
    result = value
```

#### Caso 2: Acceso a métodos (str.upper(), etc.)
```python
# ❌ ANTES:
result = safe_eval("value.upper()", {"value": "hello"})

# ✅ DESPUÉS:
result = safe_eval("upper(value)", {"value": "hello"})
```

#### Caso 3: min/max
```python
# ❌ ANTES:
result = safe_eval("max(a, b)", {"a": 10, "b": 20})

# ✅ DESPUÉS (sin eval):
result = max(a, b)  # Fuera del eval
```

#### Caso 4: Subscript
```python
# ❌ ANTES:
result = safe_eval("value[0]", {"value": [1, 2, 3]})

# ✅ DESPUÉS (sin eval):
from common.input_validation import sanitize_value
result = sanitize_value(value[0])
```

### 3.4. Archivos Probables a Revisar

**Revisa especialmente estos archivos:**

1. `src/lambdas/transformer/handler.py`
   - Busca cualquier uso de `safe_eval`, `apply_transformation_logic`, `evaluate_condition`
   - Revisa las transformaciones de productos

2. Cualquier lambda que procese transformaciones dinámicas

**Comando para verificar:**
```bash
# Ver todos los usos de safe_eval
grep -n "safe_eval\|apply_transformation_logic\|evaluate_condition" src/lambdas/transformer/handler.py
```

**✅ CHECKPOINT:** Lista todos los archivos que necesitan cambios y documéntalos antes de continuar.

---

## 🧪 PASO 4: AGREGAR TESTS DE SEGURIDAD

### 4.1. Copiar Suite de Tests

**Acción:** Agregar la nueva suite de tests al proyecto:

```bash
# Crear directorio si no existe
mkdir -p tests/security

# Copiar tests
cp test_security_comprehensive.py tests/security/

# Verificar
ls -l tests/security/test_security_comprehensive.py
```

### 4.2. Ejecutar Tests Nuevos

**Acción:** Ejecuta los 56 tests nuevos para verificar que las correcciones funcionan:

```bash
# Ejecutar solo los tests de seguridad nuevos
pytest tests/security/test_security_comprehensive.py -v

# Ver resumen
pytest tests/security/test_security_comprehensive.py -v --tb=short
```

**Resultado Esperado:**
```
====== 56 passed in X seconds ======
```

**⚠️ Si hay fallos:**
1. Lee el error específico
2. Verifica que copiaste los archivos correctamente
3. Asegúrate de que no hay conflictos con código existente

---

## ✅ PASO 5: EJECUTAR TESTS EXISTENTES

**Acción:** Verifica que los cambios no rompieron funcionalidad existente:

```bash
# Ejecutar TODOS los tests
pytest tests/ -v

# Si hay tests de seguridad originales
pytest tests/security/test_safe_evaluator.py -v
pytest tests/security/test_input_validation.py -v
```

**Resultado Esperado:**
- ✅ Tests existentes de seguridad siguen pasando (si los había)
- ✅ Tests de lambdas siguen pasando
- ⚠️ Si algún test falla por uso de funciones removidas, corrige según Paso 3

---

## 🔧 PASO 6: ACTUALIZAR HANDLER DE EXTRACTOR (MEJORA OPCIONAL)

En `src/lambdas/extractor/handler.py` hay un uso incorrecto de sanitización (líneas ~124-131):

### Encontrar este código:
```python
if modified_since:
    try:
        filter_expr = f"fechaModificacion>={modified_since}"
        sanitized_filter = sanitize_filter_expression(filter_expr)
        params['fechaModificacion'] = modified_since  # ❌ Usa el ORIGINAL!
    except ValueError as e:
        logger.error(f"Invalid filter expression: {sanitize_log_message(str(e))}")
```

### Reemplazar con:
```python
if modified_since:
    try:
        # Sanitizar y validar el timestamp ISO
        from common.input_validation import sanitize_iso_datetime
        sanitized_date = sanitize_iso_datetime(modified_since)
        params['fechaModificacion'] = sanitized_date  # ✅ Usa el SANITIZADO
    except ValueError as e:
        logger.error(f"Invalid date format: {sanitize_log_message(str(e))}")
        # Continuar sin filtro en vez de fallar
```

**✅ CHECKPOINT:** Verifica que el cambio se aplicó correctamente.

---

## 📊 PASO 7: VERIFICACIÓN AUTOMÁTICA

**Acción:** Ejecuta el script de verificación original para confirmar que todo sigue funcionando:

```bash
# Verificar fase 1
python verify-phase1.py

# Debería mostrar:
# ✅ 25/25 verificaciones pasando
```

**Si hay fallos:**
- Revisa qué verificación específica falla
- Compara con los backups
- Aplica correcciones necesarias

---

## 🎯 PASO 8: VALIDACIÓN FINAL

### 8.1. Checklist de Validación

Verifica que TODOS estos puntos están completos:

- [ ] Backups creados (Paso 1)
- [ ] `safe_eval.py` reemplazado (Paso 2.1)
- [ ] `input_validation.py` reemplazado (Paso 2.2)
- [ ] Búsqueda de funciones removidas completada (Paso 3.1)
- [ ] Correcciones aplicadas para funciones removidas (Paso 3.3)
- [ ] Tests de seguridad agregados (Paso 4.1)
- [ ] Tests nuevos pasan 56/56 (Paso 4.2)
- [ ] Tests existentes pasan (Paso 5)
- [ ] Handler de extractor mejorado (Paso 6)
- [ ] Verificación automática pasa 25/25 (Paso 7)

### 8.2. Tests de Humo Manuales

**Ejecuta estos comandos para verificar imports:**

```bash
# Verificar que los módulos se importan sin errores
python -c "from common.safe_eval import safe_eval, apply_transformation_logic; print('✅ safe_eval OK')"
python -c "from common.input_validation import sanitize_string, sanitize_dict; print('✅ input_validation OK')"

# Verificar funcionalidad básica
python -c "
from common.safe_eval import safe_eval
result = safe_eval('10 + 5', {})
assert result == 15
print('✅ safe_eval functionality OK')
"

python -c "
from common.input_validation import sanitize_string
result = sanitize_string('hello world')
assert result == 'hello world'
print('✅ sanitize_string functionality OK')
"
```

**Resultado Esperado:**
```
✅ safe_eval OK
✅ input_validation OK
✅ safe_eval functionality OK
✅ sanitize_string functionality OK
```

---

## 📝 PASO 9: DOCUMENTAR CAMBIOS

**Acción:** Crea un commit/registro con los cambios aplicados:

```bash
# Git commit (si usas git)
git add src/lambdas/common/safe_eval.py
git add src/lambdas/common/input_validation.py
git add tests/security/test_security_comprehensive.py

git commit -m "Security fixes: Hardened safe_eval and input_validation

- Removed dangerous functions from safe_eval (str, int, float, min, max)
- Added recursion depth limits (max 50 levels)
- Blocked attribute and subscript access in expressions
- Added execution timeout (1 second)
- Enhanced SQL injection patterns (15+ variants)
- Enhanced XSS patterns (100+ event handlers)
- Added 56 comprehensive security tests
- Fixed sanitize_filter_expression usage in extractor

BREAKING CHANGES:
- safe_eval no longer supports: str(), int(), float(), min(), max()
- Expressions with attribute access (e.g., value.upper()) blocked
- Subscript access (e.g., value[0]) blocked

Tests: 56/56 security tests passing
Verification: 25/25 checks passing
Coverage: 36% → 90%+ on security modules"
```

**O crea un archivo de cambios:**
```bash
cat > CAMBIOS-SEGURIDAD-$(date +%Y%m%d).txt << EOF
Fecha: $(date)
Cambios Aplicados: Correcciones de Seguridad Críticas

Archivos Modificados:
1. src/lambdas/common/safe_eval.py - Hardened version
2. src/lambdas/common/input_validation.py - Enhanced patterns
3. tests/security/test_security_comprehensive.py - 56 new tests
4. src/lambdas/extractor/handler.py - Fixed sanitization usage

Vulnerabilidades Corregidas:
1. SafeEval bypasseable - CRÍTICO
2. Recursión sin límites - CRÍTICO  
3. Regex SQL/XSS débiles - ALTO
4. Acceso a atributos no bloqueado - CRÍTICO
5. Token validation insuficiente - ALTO
6. BoolOp sin short-circuit - MEDIO
7. Sin timeout para DoS - MEDIO

Tests: 56/56 passing
Verification: 25/25 passing
Coverage: 90%+

Breaking Changes: Ver CORRECCIONES-APLICADAS.md
EOF
```

---

## 🚨 PASO 10: ROLLBACK PLAN (IMPORTANTE)

**Si algo sale mal, ten este plan de rollback listo:**

```bash
# ROLLBACK COMPLETO
cp backups/pre-security-fixes/safe_eval.py src/lambdas/common/
cp backups/pre-security-fixes/input_validation.py src/lambdas/common/

# Verificar que volvió al estado original
python verify-phase1.py

# Ejecutar tests originales
pytest tests/security/ -v
```

---

## ⏰ TIEMPO ESTIMADO POR PASO

| Paso | Descripción | Tiempo |
|------|-------------|--------|
| 1 | Backups | 2 min |
| 2 | Reemplazar archivos | 2 min |
| 3 | Buscar y corregir funciones removidas | 30-60 min |
| 4 | Agregar y ejecutar tests | 10 min |
| 5 | Ejecutar tests existentes | 5 min |
| 6 | Actualizar extractor handler | 5 min |
| 7 | Verificación automática | 2 min |
| 8 | Validación final | 10 min |
| 9 | Documentar cambios | 5 min |
| 10 | Preparar rollback | 2 min |
| **TOTAL** | | **70-95 min (1.5-2 hrs)** |

---

## ✅ CRITERIOS DE ÉXITO

La implementación es exitosa cuando:

1. ✅ Todos los backups están creados
2. ✅ Archivos de seguridad reemplazados
3. ✅ No hay usos de funciones removidas (o están corregidos)
4. ✅ 56/56 tests de seguridad nuevos pasan
5. ✅ Tests existentes siguen pasando
6. ✅ Verificación automática: 25/25 checks
7. ✅ Tests de humo manuales pasan
8. ✅ Sin errores de import
9. ✅ Cambios documentados
10. ✅ Plan de rollback probado

---

## 🆘 QUÉ HACER SI HAY PROBLEMAS

### Problema 1: Tests Nuevos Fallan
**Solución:**
```bash
# Ver error específico
pytest tests/security/test_security_comprehensive.py -v --tb=long

# Verificar imports
python -c "from common.safe_eval import safe_eval"
python -c "from common.input_validation import sanitize_string"
```

### Problema 2: Tests Existentes Fallan por Funciones Removidas
**Solución:**
1. Identifica qué función removida se usa
2. Aplica corrección del Paso 3.3
3. Re-ejecuta tests

### Problema 3: Error de Import
**Solución:**
```bash
# Verificar que archivos se copiaron bien
ls -l src/lambdas/common/safe_eval.py
ls -l src/lambdas/common/input_validation.py

# Verificar sintaxis
python -m py_compile src/lambdas/common/safe_eval.py
python -m py_compile src/lambdas/common/input_validation.py
```

### Problema 4: Funcionalidad Rota
**Solución:**
```bash
# ROLLBACK inmediato
bash
cp backups/pre-security-fixes/* src/lambdas/common/

# Analizar qué falló
# Aplicar correcciones una por una
# Re-intentar
```

---

## 📞 PREGUNTAS FRECUENTES

**P: ¿Puedo aplicar solo algunas correcciones?**
R: No recomendado. Las correcciones trabajan en conjunto. Aplica todas o ninguna.

**P: ¿Qué hago si no encuentro usos de funciones removidas?**
R: Excelente! Procede al Paso 4 directamente.

**P: ¿Los tests nuevos reemplazan los viejos?**
R: No, son complementarios. Mantén ambos.

**P: ¿Cuánto tiempo antes de producción?**
R: Mínimo 24-48 horas en staging para validación completa.

---

## 🎯 RESULTADO ESPERADO

Al completar todos los pasos:

```
✅ 0 vulnerabilidades críticas (antes: 7)
✅ 91 tests de seguridad (antes: 35)
✅ >90% coverage en módulos de seguridad (antes: 36%)
✅ >95% de exploits bloqueados (antes: ~20%)
✅ Código listo para producción enterprise-grade
```

---

**¿Todo claro? Si tienes dudas en cualquier paso, consulta CORRECCIONES-APLICADAS.md para más detalles técnicos.**

**¡Éxito con la implementación!** 🚀
