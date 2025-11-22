# 🤖 PROMPT PARA KIRO.DEV

Copia y pega este prompt directamente a Kiro.dev:

---

## CONTEXTO
Se realizó un code review de seguridad del proyecto Siesa/Parchita y se encontraron 7 vulnerabilidades críticas que deben corregirse antes de producción.

## TAREA
Implementa las correcciones de seguridad siguiendo las instrucciones detalladas en INSTRUCCIONES-PARA-KIRO.md

## ARCHIVOS PROPORCIONADOS
Tienes 5 archivos:
1. **INSTRUCCIONES-PARA-KIRO.md** - Instrucciones paso a paso (LÉELO PRIMERO)
2. **safe_eval_fixed.py** - Reemplaza src/lambdas/common/safe_eval.py
3. **input_validation_fixed.py** - Reemplaza src/lambdas/common/input_validation.py  
4. **test_security_comprehensive.py** - Agregar a tests/security/
5. **CORRECCIONES-APLICADAS.md** - Documentación técnica de referencia

## PASOS PRINCIPALES

### 1. CREAR BACKUPS (CRÍTICO)
```bash
mkdir -p backups/pre-security-fixes
cp src/lambdas/common/safe_eval.py backups/pre-security-fixes/
cp src/lambdas/common/input_validation.py backups/pre-security-fixes/
```

### 2. REEMPLAZAR ARCHIVOS
```bash
cp safe_eval_fixed.py src/lambdas/common/safe_eval.py
cp input_validation_fixed.py src/lambdas/common/input_validation.py
cp test_security_comprehensive.py tests/security/
```

### 3. BUSCAR FUNCIONES REMOVIDAS (IMPORTANTE)
Estas funciones fueron REMOVIDAS de safe_eval por seguridad:
- `str()` 
- `int()` 
- `float()` 
- `min()` 
- `max()`

**Busca en el código si se usan:**
```bash
grep -r "safe_eval\|apply_transformation_logic\|evaluate_condition" src/lambdas/ --include="*.py"
```

**Si las encuentras, corrígelas según las instrucciones del Paso 3 en INSTRUCCIONES-PARA-KIRO.md**

### 4. EJECUTAR TESTS
```bash
# Tests nuevos (deben pasar 56/56)
pytest tests/security/test_security_comprehensive.py -v

# Tests existentes (deben seguir pasando)
pytest tests/ -v

# Verificación automática (debe pasar 25/25)
python verify-phase1.py
```

### 5. CORREGIR EXTRACTOR (OPCIONAL PERO RECOMENDADO)
En `src/lambdas/extractor/handler.py` líneas ~124-131, hay un uso incorrecto de sanitización.

**Buscar:**
```python
sanitized_filter = sanitize_filter_expression(filter_expr)
params['fechaModificacion'] = modified_since  # ❌ Usa el original
```

**Reemplazar con:**
```python
from common.input_validation import sanitize_iso_datetime
sanitized_date = sanitize_iso_datetime(modified_since)
params['fechaModificacion'] = sanitized_date  # ✅ Usa el sanitizado
```

## CRITERIOS DE ÉXITO
✅ Backups creados
✅ Archivos reemplazados  
✅ Funciones removidas corregidas (si las había)
✅ 56/56 tests de seguridad pasan
✅ Tests existentes pasan
✅ Verificación automática: 25/25 checks
✅ Sin errores de import

## BREAKING CHANGES (IMPORTANTE)
Las siguientes funciones YA NO ESTÁN disponibles en safe_eval:
- `str()` → Corrige según INSTRUCCIONES-PARA-KIRO.md Paso 3.3
- `int()` → Corrige según INSTRUCCIONES-PARA-KIRO.md Paso 3.3  
- `float()` → Corrige según INSTRUCCIONES-PARA-KIRO.md Paso 3.3
- `min()` → Usa directamente fuera de eval
- `max()` → Usa directamente fuera de eval
- Acceso a atributos (ej: `value.upper()`) → Usa `upper(value)`
- Subscript (ej: `value[0]`) → Hazlo fuera de eval

## SI ALGO FALLA
**ROLLBACK inmediato:**
```bash
cp backups/pre-security-fixes/safe_eval.py src/lambdas/common/
cp backups/pre-security-fixes/input_validation.py src/lambdas/common/
```

Luego consulta la sección "🆘 QUÉ HACER SI HAY PROBLEMAS" en INSTRUCCIONES-PARA-KIRO.md

## TIEMPO ESTIMADO
1.5 - 2 horas

## RESULTADO ESPERADO
- 7 vulnerabilidades críticas corregidas
- Coverage de seguridad: 36% → 90%+
- 56 tests nuevos de seguridad
- Código listo para producción

## DOCUMENTACIÓN COMPLETA
Lee INSTRUCCIONES-PARA-KIRO.md para detalles paso a paso de cada acción.
Lee CORRECCIONES-APLICADAS.md para entender cada vulnerabilidad corregida.

---

**COMIENZA POR LEER INSTRUCCIONES-PARA-KIRO.md COMPLETAMENTE ANTES DE HACER CAMBIOS**

**¡Éxito!** 🚀
