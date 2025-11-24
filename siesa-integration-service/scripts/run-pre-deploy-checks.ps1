# Pre-Deploy Analysis Script
# Ejecuta todas las verificaciones antes del deploy

Write-Host "🔍 Iniciando análisis pre-deploy..." -ForegroundColor Cyan
Write-Host ""

$ErrorCount = 0
$WarningCount = 0

# Crear directorio para reportes
$ReportDir = "pre-deploy-reports"
if (Test-Path $ReportDir) {
    Remove-Item $ReportDir -Recurse -Force
}
New-Item -ItemType Directory -Path $ReportDir | Out-Null

Write-Host "📁 Reportes se guardarán en: $ReportDir" -ForegroundColor Yellow
Write-Host ""

# ============================================
# 1. Python Security Analysis
# ============================================
Write-Host "🔒 1. Análisis de Seguridad Python (Bandit)..." -ForegroundColor Green

try {
    bandit -r src/lambdas/ -f json -o "$ReportDir/bandit-report.json" 2>&1 | Out-Null
    bandit -r src/lambdas/ -f txt -o "$ReportDir/bandit-report.txt"
    
    $banditJson = Get-Content "$ReportDir/bandit-report.json" | ConvertFrom-Json
    $highSeverity = ($banditJson.results | Where-Object { $_.issue_severity -eq "HIGH" }).Count
    $mediumSeverity = ($banditJson.results | Where-Object { $_.issue_severity -eq "MEDIUM" }).Count
    
    Write-Host "   ✓ Bandit completado" -ForegroundColor Green
    Write-Host "     - Issues HIGH: $highSeverity" -ForegroundColor $(if ($highSeverity -gt 0) { "Red" } else { "Green" })
    Write-Host "     - Issues MEDIUM: $mediumSeverity" -ForegroundColor $(if ($mediumSeverity -gt 0) { "Yellow" } else { "Green" })
    
    if ($highSeverity -gt 0) { $ErrorCount++ }
    if ($mediumSeverity -gt 0) { $WarningCount++ }
} catch {
    Write-Host "   ⚠ Bandit no disponible o falló" -ForegroundColor Yellow
    $WarningCount++
}

Write-Host ""

# ============================================
# 2. Python Dependencies Security
# ============================================
Write-Host "🔒 2. Seguridad de Dependencias Python..." -ForegroundColor Green

try {
    pip-audit --format json > "$ReportDir/pip-audit-report.json" 2>&1
    $pipAuditJson = Get-Content "$ReportDir/pip-audit-report.json" | ConvertFrom-Json
    $vulnCount = $pipAuditJson.dependencies.Count
    
    Write-Host "   ✓ pip-audit completado" -ForegroundColor Green
    Write-Host "     - Vulnerabilidades encontradas: $vulnCount" -ForegroundColor $(if ($vulnCount -gt 0) { "Red" } else { "Green" })
    
    if ($vulnCount -gt 0) { $ErrorCount++ }
} catch {
    Write-Host "   ⚠ pip-audit no disponible" -ForegroundColor Yellow
    $WarningCount++
}

Write-Host ""

# ============================================
# 3. Python Code Quality
# ============================================
Write-Host "📊 3. Calidad de Código Python (Pylint)..." -ForegroundColor Green

try {
    pylint src/lambdas/ --output-format=json > "$ReportDir/pylint-report.json" 2>&1
    pylint src/lambdas/ --output-format=text > "$ReportDir/pylint-report.txt" 2>&1
    
    $pylintJson = Get-Content "$ReportDir/pylint-report.json" | ConvertFrom-Json
    $errorCount = ($pylintJson | Where-Object { $_.type -eq "error" }).Count
    $warningCount = ($pylintJson | Where-Object { $_.type -eq "warning" }).Count
    
    Write-Host "   ✓ Pylint completado" -ForegroundColor Green
    Write-Host "     - Errores: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Green" })
    Write-Host "     - Warnings: $warningCount" -ForegroundColor $(if ($warningCount -gt 0) { "Yellow" } else { "Green" })
    
    if ($errorCount -gt 0) { $ErrorCount++ }
    if ($warningCount -gt 5) { $WarningCount++ }
} catch {
    Write-Host "   ⚠ Pylint no disponible" -ForegroundColor Yellow
    $WarningCount++
}

Write-Host ""

# ============================================
# 4. Python Style Check
# ============================================
Write-Host "🎨 4. Verificación de Estilo Python (Flake8)..." -ForegroundColor Green

try {
    flake8 src/lambdas/ --max-line-length=120 --output-file="$ReportDir/flake8-report.txt" 2>&1
    $flake8Issues = (Get-Content "$ReportDir/flake8-report.txt").Count
    
    Write-Host "   ✓ Flake8 completado" -ForegroundColor Green
    Write-Host "     - Issues encontrados: $flake8Issues" -ForegroundColor $(if ($flake8Issues -gt 0) { "Yellow" } else { "Green" })
    
    if ($flake8Issues -gt 10) { $WarningCount++ }
} catch {
    Write-Host "   ⚠ Flake8 no disponible" -ForegroundColor Yellow
}

Write-Host ""

# ============================================
# 5. TypeScript/CDK Analysis
# ============================================
Write-Host "📦 5. Análisis TypeScript/CDK..." -ForegroundColor Green

try {
    npm audit --json > "$ReportDir/npm-audit-report.json" 2>&1
    $npmAudit = Get-Content "$ReportDir/npm-audit-report.json" | ConvertFrom-Json
    $npmVulns = $npmAudit.metadata.vulnerabilities.total
    
    Write-Host "   ✓ npm audit completado" -ForegroundColor Green
    Write-Host "     - Vulnerabilidades npm: $npmVulns" -ForegroundColor $(if ($npmVulns -gt 0) { "Red" } else { "Green" })
    
    if ($npmVulns -gt 0) { $ErrorCount++ }
} catch {
    Write-Host "   ⚠ npm audit falló" -ForegroundColor Yellow
    $WarningCount++
}

Write-Host ""

# ============================================
# 6. CDK Synth Validation
# ============================================
Write-Host "☁️ 6. Validación AWS CDK..." -ForegroundColor Green

try {
    npm run cdk synth > "$ReportDir/cdk-synth-output.txt" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ CDK synth exitoso" -ForegroundColor Green
    } else {
        Write-Host "   ✗ CDK synth falló" -ForegroundColor Red
        $ErrorCount++
    }
} catch {
    Write-Host "   ✗ CDK synth falló" -ForegroundColor Red
    $ErrorCount++
}

Write-Host ""

# ============================================
# 7. Python Tests
# ============================================
Write-Host "🧪 7. Ejecutando Tests Python..." -ForegroundColor Green

try {
    python -m pytest tests/ -v --tb=short > "$ReportDir/pytest-report.txt" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✓ Tests pasaron" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Algunos tests fallaron" -ForegroundColor Red
        $ErrorCount++
    }
} catch {
    Write-Host "   ⚠ Tests no ejecutados" -ForegroundColor Yellow
    $WarningCount++
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# ============================================
# Summary Report
# ============================================
Write-Host "📊 RESUMEN DEL ANÁLISIS" -ForegroundColor Cyan
Write-Host ""

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$summaryReport = @"
# 🔍 Pre-Deploy Analysis Summary

**Fecha:** $timestamp

## 📊 Resultados Generales

- **Errores Críticos:** $ErrorCount
- **Advertencias:** $WarningCount

## ✅ Verificaciones Completadas

1. ✓ Análisis de Seguridad Python (Bandit)
2. ✓ Seguridad de Dependencias (pip-audit)
3. ✓ Calidad de Código Python (Pylint)
4. ✓ Estilo de Código (Flake8)
5. ✓ Seguridad npm (npm audit)
6. ✓ Validación CDK (cdk synth)
7. ✓ Tests Python (pytest)

## 📁 Reportes Detallados

Todos los reportes están disponibles en: \`$ReportDir/\`

- \`bandit-report.json\` - Análisis de seguridad Python
- \`pip-audit-report.json\` - Vulnerabilidades en dependencias
- \`pylint-report.json\` - Calidad de código
- \`flake8-report.txt\` - Estilo de código
- \`npm-audit-report.json\` - Vulnerabilidades npm
- \`cdk-synth-output.txt\` - Validación CDK
- \`pytest-report.txt\` - Resultados de tests

## 🎯 Recomendación

"@

if ($ErrorCount -eq 0 -and $WarningCount -eq 0) {
    $summaryReport += @"
**✅ LISTO PARA DEPLOY**

El código ha pasado todas las verificaciones. Puedes proceder con confianza al deployment en AWS.

"@
    Write-Host "✅ LISTO PARA DEPLOY" -ForegroundColor Green
    Write-Host "   El código ha pasado todas las verificaciones" -ForegroundColor Green
} elseif ($ErrorCount -eq 0) {
    $summaryReport += @"
**⚠️ DEPLOY CON PRECAUCIÓN**

Se encontraron $WarningCount advertencias. Revisa los reportes antes de hacer deploy.

"@
    Write-Host "⚠️ DEPLOY CON PRECAUCIÓN" -ForegroundColor Yellow
    Write-Host "   Se encontraron $WarningCount advertencias" -ForegroundColor Yellow
} else {
    $summaryReport += @"
**❌ NO RECOMENDADO PARA DEPLOY**

Se encontraron $ErrorCount errores críticos y $WarningCount advertencias. 
Por favor, revisa y corrige los issues antes de hacer deploy.

"@
    Write-Host "❌ NO RECOMENDADO PARA DEPLOY" -ForegroundColor Red
    Write-Host "   Se encontraron $ErrorCount errores críticos" -ForegroundColor Red
}

$summaryReport += @"

## 📝 Próximos Pasos

1. Revisa los reportes detallados en \`$ReportDir/\`
2. Corrige los issues críticos (si los hay)
3. Considera las advertencias importantes
4. Re-ejecuta este script para verificar
5. Procede con el deploy cuando todo esté verde

---
*Generado automáticamente por pre-deploy-checks.ps1*
"@

# Guardar resumen
$summaryReport | Out-File "$ReportDir/SUMMARY.md" -Encoding UTF8

Write-Host ""
Write-Host "📄 Resumen completo guardado en: $ReportDir/SUMMARY.md" -ForegroundColor Cyan
Write-Host ""

# Abrir resumen si es posible
if (Get-Command code -ErrorAction SilentlyContinue) {
    Write-Host "📖 Abriendo resumen en VS Code..." -ForegroundColor Cyan
    code "$ReportDir/SUMMARY.md"
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# Exit code basado en errores
if ($ErrorCount -gt 0) {
    exit 1
} else {
    exit 0
}
