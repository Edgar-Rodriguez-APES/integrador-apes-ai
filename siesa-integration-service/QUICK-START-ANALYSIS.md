# 🚀 Quick Start: Análisis Pre-Deploy

## ⚡ Ejecución Rápida

### 1. Instalar Herramientas (Una sola vez)

```powershell
# Python tools
pip install bandit safety pip-audit pylint flake8 black pytest

# Verificar
bandit --version
```

### 2. Ejecutar Análisis

```powershell
cd siesa-integration-service
.\scripts\run-pre-deploy-checks.ps1
```

### 3. Revisar Resultados

Los reportes se guardan en `pre-deploy-reports/`:

- **SUMMARY.md** - Resumen ejecutivo (¡empieza aquí!)
- Reportes detallados por herramienta

### 4. Interpretar Resultados

#### ✅ Verde - Listo para Deploy
```
✅ LISTO PARA DEPLOY
   El código ha pasado todas las verificaciones
```

#### ⚠️ Amarillo - Revisar
```
⚠️ DEPLOY CON PRECAUCIÓN
   Se encontraron 3 advertencias
```

#### ❌ Rojo - Corregir Primero
```
❌ NO RECOMENDADO PARA DEPLOY
   Se encontraron 2 errores críticos
```

---

## 🔧 Correcciones Rápidas

### Issue: Hardcoded Secrets

```python
# ❌ Mal
api_key = "abc123"

# ✅ Bien
import os
api_key = os.environ.get('API_KEY')
```

### Issue: SQL Injection

```python
# ❌ Mal
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ Bien
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

### Issue: Line Too Long

```python
# ❌ Mal
result = function(param1, param2, param3, param4, param5)

# ✅ Bien
result = function(
    param1, param2, param3,
    param4, param5
)
```

---

## 📊 GitHub Actions (Automático)

El análisis también se ejecuta automáticamente en GitHub:

1. Haz push a `main` o `develop`
2. Ve a **GitHub > Actions**
3. Revisa el workflow **Pre-Deploy Code Analysis**
4. Descarga los artifacts si necesitas reportes detallados

---

## 🎯 Workflow Recomendado

```powershell
# 1. Hacer cambios en el código
# ...

# 2. Ejecutar análisis
.\scripts\run-pre-deploy-checks.ps1

# 3. Si hay errores, corregir y repetir paso 2

# 4. Cuando esté verde, commit y push
git add .
git commit -m "feat: nueva funcionalidad"
git push

# 5. Verificar GitHub Actions pasó

# 6. Deploy a AWS
.\deploy.ps1
```

---

## 📚 Documentación Completa

Para más detalles, ver: **PRE-DEPLOY-ANALYSIS-GUIDE.md**

---

## 🆘 Ayuda Rápida

### Error: "command not found"

```powershell
pip install bandit pylint flake8
```

### Análisis Toma Mucho Tiempo

Ejecuta verificaciones individuales:

```powershell
# Solo seguridad
bandit -r src/lambdas/

# Solo tests
python -m pytest tests/
```

### Ver Solo Errores Críticos

```powershell
# Bandit solo HIGH
bandit -r src/lambdas/ -ll

# Pylint solo errores
pylint src/lambdas/ --errors-only
```

---

**¿Preguntas?** Revisa la guía completa en `PRE-DEPLOY-ANALYSIS-GUIDE.md`
