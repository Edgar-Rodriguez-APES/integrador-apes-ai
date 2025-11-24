# 🔍 Guía de Análisis Pre-Deploy

Esta guía explica cómo usar las herramientas de análisis automatizado antes de hacer deploy a AWS.

## 📋 Tabla de Contenidos

1. [Análisis Local (Antes de Push)](#análisis-local)
2. [Análisis en GitHub (Automático)](#análisis-en-github)
3. [Interpretación de Resultados](#interpretación-de-resultados)
4. [Corrección de Issues](#corrección-de-issues)

---

## 🖥️ Análisis Local

### Instalación de Herramientas

Primero, instala las herramientas necesarias:

```powershell
# Python tools
pip install bandit safety pip-audit pylint flake8 black pytest

# Verificar instalación
bandit --version
pylint --version
flake8 --version
```

### Ejecutar Análisis Completo

```powershell
cd siesa-integration-service
.\scripts\run-pre-deploy-checks.ps1
```

### ¿Qué Analiza?

El script ejecuta 7 verificaciones:

1. **Bandit** - Seguridad del código Python
2. **pip-audit** - Vulnerabilidades en dependencias Python
3. **Pylint** - Calidad del código Python
4. **Flake8** - Estilo y convenciones Python
5. **npm audit** - Vulnerabilidades en dependencias npm
6. **CDK synth** - Validación de infraestructura AWS
7. **pytest** - Ejecución de tests

### Resultados

Los reportes se guardan en `pre-deploy-reports/`:

```
pre-deploy-reports/
├── SUMMARY.md                 # Resumen ejecutivo
├── bandit-report.json         # Seguridad Python
├── pip-audit-report.json      # Vulnerabilidades deps
├── pylint-report.json         # Calidad código
├── flake8-report.txt          # Estilo código
├── npm-audit-report.json      # Vulnerabilidades npm
├── cdk-synth-output.txt       # Validación CDK
└── pytest-report.txt          # Resultados tests
```

---

## 🐙 Análisis en GitHub

### Configuración Automática

El workflow de GitHub Actions se ejecuta automáticamente en:

- ✅ Push a `main` o `develop`
- ✅ Pull Requests
- ✅ Ejecución manual

### Ver Resultados en GitHub

1. Ve a tu repositorio en GitHub
2. Click en la pestaña **Actions**
3. Selecciona el workflow **Pre-Deploy Code Analysis**
4. Revisa los jobs:
   - Python Security Analysis
   - Python Code Quality
   - TypeScript/CDK Analysis
   - CDK Validation
   - Summary Report

### Descargar Reportes

Los reportes están disponibles como **Artifacts** en cada ejecución:

- `python-security-reports`
- `python-quality-reports`
- `typescript-reports`
- `cdk-reports`
- `analysis-summary`

---

## 📊 Interpretación de Resultados

### Niveles de Severidad

#### 🔴 CRÍTICO (Bloquea Deploy)

- Vulnerabilidades HIGH en Bandit
- Vulnerabilidades en dependencias
- CDK synth falla
- Tests fallan

**Acción:** Debe corregirse antes del deploy

#### 🟡 ADVERTENCIA (Revisar)

- Vulnerabilidades MEDIUM en Bandit
- Muchos warnings de Pylint (>5)
- Issues de estilo en Flake8 (>10)

**Acción:** Revisar y considerar corrección

#### 🟢 OK (Listo para Deploy)

- Sin issues críticos
- Pocas o ninguna advertencia

**Acción:** Proceder con deploy

### Ejemplo de Salida

```
🔍 Iniciando análisis pre-deploy...

🔒 1. Análisis de Seguridad Python (Bandit)...
   ✓ Bandit completado
     - Issues HIGH: 0
     - Issues MEDIUM: 2

📊 3. Calidad de Código Python (Pylint)...
   ✓ Pylint completado
     - Errores: 0
     - Warnings: 3

✅ LISTO PARA DEPLOY
   El código ha pasado todas las verificaciones
```

---

## 🔧 Corrección de Issues

### Issues Comunes y Soluciones

#### 1. Bandit: Hardcoded Password

**Issue:**
```
Issue: [B105:hardcoded_password_string] Possible hardcoded password
```

**Solución:**
```python
# ❌ Mal
password = "mi_password_secreto"

# ✅ Bien
import os
password = os.environ.get('DB_PASSWORD')
```

#### 2. Bandit: SQL Injection

**Issue:**
```
Issue: [B608:hardcoded_sql_expressions] Possible SQL injection
```

**Solución:**
```python
# ❌ Mal
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ Bien
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

#### 3. Pylint: Unused Import

**Issue:**
```
W0611: Unused import json
```

**Solución:**
```python
# Remover imports no usados
# import json  # ← Eliminar si no se usa
```

#### 4. Flake8: Line Too Long

**Issue:**
```
E501 line too long (125 > 120 characters)
```

**Solución:**
```python
# ❌ Mal
result = some_function(param1, param2, param3, param4, param5, param6)

# ✅ Bien
result = some_function(
    param1, param2, param3,
    param4, param5, param6
)
```

#### 5. npm audit: Vulnerabilidad

**Issue:**
```
high severity vulnerability in package-name
```

**Solución:**
```powershell
# Actualizar dependencia
npm update package-name

# O forzar actualización
npm audit fix --force
```

#### 6. CDK Synth Falla

**Issue:**
```
Error: Cannot find module 'aws-cdk-lib'
```

**Solución:**
```powershell
# Reinstalar dependencias
npm ci

# Verificar
npm run build
npm run cdk synth
```

---

## 🚀 Workflow Recomendado

### Antes de Cada Commit

```powershell
# 1. Ejecutar análisis local
.\scripts\run-pre-deploy-checks.ps1

# 2. Si hay errores, corregir

# 3. Re-ejecutar hasta que esté verde
.\scripts\run-pre-deploy-checks.ps1

# 4. Hacer commit
git add .
git commit -m "feat: nueva funcionalidad"
git push
```

### Antes de Deploy a AWS

```powershell
# 1. Verificar que GitHub Actions pasó
# (Ver en GitHub > Actions)

# 2. Ejecutar análisis local final
.\scripts\run-pre-deploy-checks.ps1

# 3. Si todo está verde, proceder
.\deploy.ps1
```

---

## 📈 Métricas de Calidad

### Objetivos

| Métrica | Objetivo | Crítico |
|---------|----------|---------|
| Vulnerabilidades HIGH | 0 | > 0 |
| Vulnerabilidades MEDIUM | < 3 | > 10 |
| Pylint Errors | 0 | > 0 |
| Pylint Warnings | < 5 | > 20 |
| Test Coverage | > 80% | < 50% |
| CDK Synth | ✅ Pass | ❌ Fail |

---

## 🆘 Troubleshooting

### Error: "bandit: command not found"

```powershell
pip install bandit
```

### Error: "npm audit requires package-lock.json"

```powershell
npm install
```

### Error: "CDK synth fails with TypeScript errors"

```powershell
npm run build
# Revisar errores de compilación
```

### Análisis Toma Mucho Tiempo

Puedes ejecutar verificaciones individuales:

```powershell
# Solo seguridad
bandit -r src/lambdas/

# Solo calidad
pylint src/lambdas/

# Solo tests
python -m pytest tests/
```

---

## 📚 Referencias

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Pylint Documentation](https://pylint.pycqa.org/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [npm audit](https://docs.npmjs.com/cli/v8/commands/npm-audit)
- [AWS CDK Best Practices](https://docs.aws.amazon.com/cdk/latest/guide/best-practices.html)

---

## 🎯 Checklist Pre-Deploy

Usa este checklist antes de cada deploy:

- [ ] Análisis local ejecutado sin errores críticos
- [ ] GitHub Actions pasó todas las verificaciones
- [ ] Todos los tests pasan
- [ ] CDK synth exitoso
- [ ] Sin vulnerabilidades HIGH
- [ ] Vulnerabilidades MEDIUM revisadas y documentadas
- [ ] Code review completado
- [ ] Documentación actualizada
- [ ] Variables de entorno configuradas en AWS
- [ ] Secrets configurados en Secrets Manager

---

**¿Listo para Deploy?** 🚀

Si todos los checks están en verde, puedes proceder con confianza:

```powershell
.\deploy.ps1
```
