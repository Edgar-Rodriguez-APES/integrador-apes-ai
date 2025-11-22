# 🎯 PROMPT PARA KIRO.DEV - AJUSTE DE TESTS

**Copia y pega esto:**

---

Perfecto. Ahora necesito que ajustes los tests. La decisión de Edgar es:

**OPCIÓN A MODIFICADA:**
- Eliminar 21 tests de funciones no usadas (5 min)
- Actualizar 16 tests de seguridad para nuevo comportamiento (15 min)
- Total: 20 minutos

## 📋 TU TAREA

### PASO 1: Eliminar 21 tests (funciones removidas)

En `tests/security/test_input_validation.py`, elimina estas clases completas:

1. `TestSanitizeDynamoDBKey` → 7 tests
2. `TestSanitizeFilterExpression` → 6 tests
3. `TestValidateProductData` → 6 tests
4. ~2 tests adicionales de comportamiento removido

**Razón:** Estas funciones NO existen en V2 (no se usan en producción)

---

### PASO 2: Actualizar 16 tests (comportamiento cambió)

El nuevo código **lanza ValidationError** cuando detecta ataques (esto es más seguro).

**Patrón de cambio:**
```python
# ANTES:
result = sanitize_string("'; SELECT * FROM users--")
assert "SELECT" not in result  # Esperaba sanitización

# AHORA:
with pytest.raises(ValidationError, match="SQL injection"):
    sanitize_string("'; SELECT * FROM users--")
```

**Tests a actualizar:**
- 6 tests de SQL Injection → Ahora esperan `ValidationError`
- 6 tests de XSS → Ahora esperan `ValidationError`
- 4 tests de validación general → Ajustar comportamiento

---

### PASO 3: Verificar

```bash
pytest tests/security/test_input_validation.py -v
```

**Resultado esperado:**
✅ **26 tests PASSED** (10 originales + 16 actualizados)

---

## 📄 INSTRUCCIONES DETALLADAS

**Archivo:** `INSTRUCCIONES-AJUSTE-TESTS.md`

Lee ese archivo para ver EXACTAMENTE cómo actualizar cada test individual.

---

## ✅ CUANDO TERMINES

Reporta a Edgar:
- ✅ 21 tests eliminados
- ✅ 16 tests actualizados
- ✅ 26/26 tests PASSING
- ✅ Listo para actualizar documentación

---

**Detalles completos en:** `INSTRUCCIONES-AJUSTE-TESTS.md`
