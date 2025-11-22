# Script de despliegue para Siesa Integration Service
# Este script configura las variables de entorno necesarias y ejecuta el despliegue

Write-Host ">> Iniciando despliegue de Siesa Integration Service" -ForegroundColor Green
Write-Host ""

# Configurar variables de entorno
$env:AWS_PROFILE = "principal"
$env:CDK_DEFAULT_ACCOUNT = "224874703567"
$env:CDK_DEFAULT_REGION = "us-east-1"
$env:ENVIRONMENT = "dev"

Write-Host ">> Variables de entorno configuradas:" -ForegroundColor Cyan
Write-Host "   AWS_PROFILE: $env:AWS_PROFILE"
Write-Host "   CDK_DEFAULT_ACCOUNT: $env:CDK_DEFAULT_ACCOUNT"
Write-Host "   CDK_DEFAULT_REGION: $env:CDK_DEFAULT_REGION"
Write-Host "   ENVIRONMENT: $env:ENVIRONMENT"
Write-Host ""

# Verificar credenciales
Write-Host ">> Verificando credenciales AWS..." -ForegroundColor Cyan
$identity = aws sts get-caller-identity --profile principal 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: No se pudo verificar las credenciales AWS" -ForegroundColor Red
    Write-Host "Por favor ejecuta: aws sso login --profile principal" -ForegroundColor Yellow
    exit 1
}

$identityJson = $identity | ConvertFrom-Json
Write-Host ">> Autenticado como: $($identityJson.Arn)" -ForegroundColor Green
Write-Host "   Cuenta: $($identityJson.Account)" -ForegroundColor Green
Write-Host ""

# Preguntar qué acción realizar
Write-Host "Que deseas hacer?" -ForegroundColor Yellow
Write-Host "1. Bootstrap CDK (solo primera vez)"
Write-Host "2. Desplegar infraestructura"
Write-Host "3. Ver diferencias (diff)"
Write-Host "4. Sintetizar template (synth)"
Write-Host "5. Destruir infraestructura"
Write-Host ""

$action = Read-Host "Selecciona una opcion (1-5)"

switch ($action) {
    "1" {
        Write-Host ""
        Write-Host ">> Ejecutando CDK Bootstrap..." -ForegroundColor Cyan
        npx cdk bootstrap
    }
    "2" {
        Write-Host ""
        Write-Host ">> Desplegando infraestructura..." -ForegroundColor Cyan
        npx cdk deploy --require-approval never
    }
    "3" {
        Write-Host ""
        Write-Host ">> Mostrando diferencias..." -ForegroundColor Cyan
        npx cdk diff
    }
    "4" {
        Write-Host ""
        Write-Host ">> Sintetizando template..." -ForegroundColor Cyan
        npx cdk synth
    }
    "5" {
        Write-Host ""
        Write-Host "ADVERTENCIA: Estas seguro de que deseas destruir la infraestructura? (S/N)" -ForegroundColor Red
        $confirm = Read-Host
        if ($confirm -eq "S" -or $confirm -eq "s") {
            Write-Host ">> Destruyendo infraestructura..." -ForegroundColor Red
            npx cdk destroy
        } else {
            Write-Host "Operacion cancelada" -ForegroundColor Yellow
        }
    }
    default {
        Write-Host "Opcion invalida" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host ">> Operacion completada" -ForegroundColor Green
