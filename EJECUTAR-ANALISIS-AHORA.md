# 🚀 Ejecutar Análisis Pre-Deploy AHORA

**Fecha**: 23 de Noviembre, 2025  
**Acción**: Ejecutar primer análisis del código

---

## ⚡ Comandos a Ejecutar (Copia y Pega)

### Paso 1: Ir al Directorio del Proyecto

```powershell
cd siesa-integration-service
```

---

### Paso 2: Instalar Herramientas (Primera vez solamente)

```powershell
.\INSTALL-ANALYSIS-TOOLS.ps1
```

**Tiempo estimado**: 2-3 minutos

**Qué hace**:
- Verifica Python y pip
- Instala Bandit (seguridad)
- Instala pip-audit y Safety (vulnerabilidades)
- Instala Pylint y Flake8 (calidad)
- Instala pytest (testing)
- Guarda versiones instaladas

**Resultado esperado**:
```
✅ INSTALACIÓN COMPLETA
Todas las herramientas están instaladas correctamente.
```

---

### Paso 3: Ejecutar Análisis Completo

```powershell
.\scripts\run-pre-deploy-checks.ps1
```

**Tiempo estimado**: 3-5 minutos

**Qué hace**:
- Analiza seguridad del código Python
- Escanea vulnerabilidades en dependencias
- Verifica calidad del código
- Valida estilo de código
- Ejecuta tests
- Valida infraestructura CDK
- Genera reportes detallados

**Resultado esperado**:
```
✅ LISTO PARA DEPLOY
   El código ha pasado todas las verificaciones
```

O

```
⚠️ DEPLOY CON PRECAUCIÓN
   Se encontraron X advertencias
```

O

```
❌ NO RECOMENDADO PARA DEPLOY
   Se encontraron X errores críticos
```

---

### Paso 4: Revisar Resultados

```powershell
# Ver resumen ejecutivo
cat pre-deploy-reports/SUMMARY.md

# O abrirlo en VS Code (se abre automáticamente)
code pre-deploy-reports/SUMMARY.md
```

---

## 📊 Interpretación de Resultados

### Si ves ✅ Verde

**Significado**: Todo está bien, código listo para deploy

**Acción**: 
```powershell
# Puedes proceder con deploy
.\deploy.ps1
```

---

### Si ves ⚠️ Amarillo

**Significado**: Hay advertencias pero no críticas

**Acción**:
1. Revisar advertencias en reportes
2. Decidir si corregir ahora o después
3. Documentar decisión
4. Proceder con deploy si es aceptable

**Revisar reportes**:
```powershell
cat pre-deploy-reports/pylint-report.txt
cat pre-deploy-reports/flake8-report.txt
```

---

### Si ves ❌ Rojo

**Significado**: Hay errores críticos que deben corregirse

**Acción**:
1. **NO HACER DEPLOY**
2. Revisar reportes de errores
3. Corregir issues críticos
4. Re-ejecutar análisis
5. Repetir hasta verde

**Revisar errores críticos**:
```powershell
# Ver vulnerabilidades de seguridad
cat pre-deploy-reports/bandit-report.txt

# Ver vulnerabilidades en dependencias
cat pre-deploy-reports/pip-audit-report.json

# Ver errores de tests
cat pre-deploy-reports/pytest-report.txt

# Ver errores de CDK
cat pre-deploy-reports/cdk-synth-output.txt
```

---

## 🔧 Correcciones Rápidas

### Si encuentras: "Hardcoded password"

```python
# ❌ Cambiar esto:
password = "mi_password"

# ✅ Por esto:
import os
password = os.environ.get('PASSWORD')
```

### Si encuentras: "SQL injection"

```python
# ❌ Cambiar esto:
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ Por esto:
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

### Si encuentras: "Vulnerable dependency"

```powershell
# Actualizar dependencia específica
pip install --upgrade nombre-del-package

# O actualizar todas
pip install --upgrade -r requirements.txt
```

### Si encuentras: "Line too long"

```python
# ❌ Cambiar esto:
result = some_function(param1, param2, param3, param4, param5)

# ✅ Por esto:
result = some_function(
    param1, param2, param3,
    param4, param5
)
```

---

## 🔄 Workflow Después de Correcciones

```powershell
# 1. Hacer correcciones en el código
# ... editar archivos ...

# 2. Re-ejecutar análisis
.\scripts\run-pre-deploy-checks.ps1

# 3. Revisar resultados
cat pre-deploy-reports/SUMMARY.md

# 4. Repetir hasta verde

# 5. Cuando esté verde, commit
git add .
git commit -m "fix: corregir issues de seguridad y calidad"
git push
```

---

## 📁 Ubicación de Reportes

Todos los reportes se guardan en: `pre-deploy-reports/`

```
pre-deploy-reports/
├── SUMMARY.md                 ⭐ EMPIEZA AQUÍ
├── bandit-report.json         🔒 Seguridad Python
├── bandit-report.txt          🔒 Seguridad Python (legible)
├── pip-audit-report.json      🔒 Vulnerabilidades deps
├── pylint-report.json         📊 Calidad código
├── pylint-report.txt          📊 Calidad código (legible)
├── flake8-report.txt          🎨 Estilo código
├── npm-audit-report.json      📦 Vulnerabilidades npm
├── cdk-synth-output.txt       ☁️ Validación CDK
└── pytest-report.txt          🧪 Resultados tests
```

---

## 🎯 Checklist de Ejecución

- [ ] Navegué a `siesa-integration-service/`
- [ ] Ejecuté `.\INSTALL-ANALYSIS-TOOLS.ps1`
- [ ] Todas las herramientas se instalaron correctamente
- [ ] Ejecuté `.\scripts\run-pre-deploy-checks.ps1`
- [ ] Revisé `pre-deploy-reports/SUMMARY.md`
- [ ] Entendí los resultados (verde/amarillo/rojo)
- [ ] Si hay errores, los identifiqué
- [ ] Si hay errores, tengo plan de corrección
- [ ] Si está verde, estoy listo para deploy

---

## 🆘 Si Algo Sale Mal

### Error: "Python no encontrado"

```powershell
# Instalar Python 3.11+
# Descargar de: https://www.python.org/downloads/
```

### Error: "pip no encontrado"

```powershell
# Instalar pip
python -m ensurepip --upgrade
```

### Error: "Herramienta no instalada"

```powershell
# Instalar manualmente
pip install bandit safety pip-audit pylint flake8 black pytest
```

### Error: "Script no se ejecuta"

```powershell
# Habilitar ejecución de scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Error: "npm no encontrado"

```powershell
# Instalar Node.js
# Descargar de: https://nodejs.org/
```

---

## 📞 Ayuda Adicional

Si necesitas más información:

1. **Quick Start**: `QUICK-START-ANALYSIS.md`
2. **Guía Completa**: `PRE-DEPLOY-ANALYSIS-GUIDE.md`
3. **Configuración**: `PRE-DEPLOY-SETUP-COMPLETE.md`
4. **Resumen General**: `ANALISIS-PRE-DEPLOY-CONFIGURADO.md`

---

## 🚀 ¡Ejecuta Ahora!

**Copia y pega estos comandos en PowerShell**:

```powershell
# Ir al proyecto
cd siesa-integration-service

# Instalar herramientas (primera vez)
.\INSTALL-ANALYSIS-TOOLS.ps1

# Ejecutar análisis
.\scripts\run-pre-deploy-checks.ps1

# Ver resultados
cat pre-deploy-reports/SUMMARY.md
```

---

## ⏱️ Tiempo Total Estimado

- **Primera vez**: 5-8 minutos (incluye instalación)
- **Siguientes veces**: 3-5 minutos (solo análisis)

---

## 🎉 Después del Análisis

### Si está verde ✅

```powershell
# Commit de la configuración
git add .github/ scripts/ .bandit .pylintrc .flake8 *.md
git commit -m "feat: add pre-deploy analysis automation"
git push

# Luego puedes hacer deploy
.\deploy.ps1
```

### Si hay issues ❌

```powershell
# Corregir issues
# ... editar código ...

# Re-ejecutar análisis
.\scripts\run-pre-deploy-checks.ps1

# Repetir hasta verde
```

---

**¡Éxito!** 🎯

Una vez que ejecutes el análisis, tendrás un reporte completo de la calidad y seguridad de tu código antes de hacer deploy a AWS.
