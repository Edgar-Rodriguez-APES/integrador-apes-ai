# Script de Instalación de Herramientas de Análisis
# Instala todas las herramientas necesarias para el análisis pre-deploy

Write-Host "🔧 Instalando herramientas de análisis..." -ForegroundColor Cyan
Write-Host ""

$ErrorCount = 0

# ============================================
# 1. Verificar Python
# ============================================
Write-Host "1️⃣ Verificando Python..." -ForegroundColor Green

try {
    $pythonVersion = python --version 2>&1
    Write-Host "   ✓ Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Python no encontrado" -ForegroundColor Red
    Write-Host "   Por favor instala Python 3.11+ desde https://www.python.org/" -ForegroundColor Yellow
    $ErrorCount++
}

Write-Host ""

# ============================================
# 2. Verificar pip
# ============================================
Write-Host "2️⃣ Verificando pip..." -ForegroundColor Green

try {
    $pipVersion = pip --version 2>&1
    Write-Host "   ✓ pip encontrado: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ pip no encontrado" -ForegroundColor Red
    Write-Host "   Instalando pip..." -ForegroundColor Yellow
    python -m ensurepip --upgrade
}

Write-Host ""

# ============================================
# 3. Actualizar pip
# ============================================
Write-Host "3️⃣ Actualizando pip..." -ForegroundColor Green

try {
    python -m pip install --upgrade pip
    Write-Host "   ✓ pip actualizado" -ForegroundColor Green
} catch {
    Write-Host "   ⚠ No se pudo actualizar pip" -ForegroundColor Yellow
}

Write-Host ""

# ============================================
# 4. Instalar herramientas de seguridad
# ============================================
Write-Host "4️⃣ Instalando herramientas de seguridad..." -ForegroundColor Green

$securityTools = @("bandit", "safety", "pip-audit")

foreach ($tool in $securityTools) {
    try {
        Write-Host "   Instalando $tool..." -ForegroundColor Cyan
        pip install $tool --quiet
        Write-Host "   ✓ $tool instalado" -ForegroundColor Green
    } catch {
        Write-Host "   ✗ Error instalando $tool" -ForegroundColor Red
        $ErrorCount++
    }
}

Write-Host ""

# ============================================
# 5. Instalar herramientas de calidad
# ============================================
Write-Host "5️⃣ Instalando herramientas de calidad..." -ForegroundColor Green

$qualityTools = @("pylint", "flake8", "black")

foreach ($tool in $qualityTools) {
    try {
        Write-Host "   Instalando $tool..." -ForegroundColor Cyan
        pip install $tool --quiet
        Write-Host "   ✓ $tool instalado" -ForegroundColor Green
    } catch {
        Write-Host "   ✗ Error instalando $tool" -ForegroundColor Red
        $ErrorCount++
    }
}

Write-Host ""

# ============================================
# 6. Instalar herramientas de testing
# ============================================
Write-Host "6️⃣ Instalando herramientas de testing..." -ForegroundColor Green

$testTools = @("pytest", "pytest-cov", "pytest-mock")

foreach ($tool in $testTools) {
    try {
        Write-Host "   Instalando $tool..." -ForegroundColor Cyan
        pip install $tool --quiet
        Write-Host "   ✓ $tool instalado" -ForegroundColor Green
    } catch {
        Write-Host "   ✗ Error instalando $tool" -ForegroundColor Red
        $ErrorCount++
    }
}

Write-Host ""

# ============================================
# 7. Verificar instalaciones
# ============================================
Write-Host "7️⃣ Verificando instalaciones..." -ForegroundColor Green
Write-Host ""

$tools = @{
    "bandit" = "bandit --version"
    "safety" = "safety --version"
    "pip-audit" = "pip-audit --version"
    "pylint" = "pylint --version"
    "flake8" = "flake8 --version"
    "black" = "black --version"
    "pytest" = "pytest --version"
}

$installedCount = 0
$totalTools = $tools.Count

foreach ($tool in $tools.Keys) {
    try {
        $version = Invoke-Expression $tools[$tool] 2>&1 | Select-Object -First 1
        Write-Host "   ✓ $tool - OK" -ForegroundColor Green
        $installedCount++
    } catch {
        Write-Host "   ✗ $tool - NO INSTALADO" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# ============================================
# Resumen
# ============================================
Write-Host "📊 RESUMEN DE INSTALACIÓN" -ForegroundColor Cyan
Write-Host ""
Write-Host "   Herramientas instaladas: $installedCount / $totalTools" -ForegroundColor $(if ($installedCount -eq $totalTools) { "Green" } else { "Yellow" })
Write-Host ""

if ($installedCount -eq $totalTools) {
    Write-Host "✅ INSTALACIÓN COMPLETA" -ForegroundColor Green
    Write-Host ""
    Write-Host "Todas las herramientas están instaladas correctamente." -ForegroundColor Green
    Write-Host ""
    Write-Host "🚀 Próximo paso: Ejecutar análisis" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   .\scripts\run-pre-deploy-checks.ps1" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "⚠️ INSTALACIÓN INCOMPLETA" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Algunas herramientas no se instalaron correctamente." -ForegroundColor Yellow
    Write-Host "Revisa los errores arriba e intenta instalar manualmente:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   pip install bandit safety pip-audit pylint flake8 black pytest" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

# ============================================
# Crear archivo de versiones
# ============================================
Write-Host "📝 Guardando versiones instaladas..." -ForegroundColor Cyan

$versionsFile = "analysis-tools-versions.txt"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

$versionsContent = @"
# Versiones de Herramientas de Análisis
# Instaladas el: $timestamp

"@

foreach ($tool in $tools.Keys) {
    try {
        $version = Invoke-Expression $tools[$tool] 2>&1 | Select-Object -First 1
        $versionsContent += "$tool`: $version`n"
    } catch {
        $versionsContent += "$tool`: NO INSTALADO`n"
    }
}

$versionsContent | Out-File $versionsFile -Encoding UTF8
Write-Host "   ✓ Versiones guardadas en: $versionsFile" -ForegroundColor Green
Write-Host ""

# Exit code
if ($ErrorCount -gt 0) {
    exit 1
} else {
    exit 0
}
