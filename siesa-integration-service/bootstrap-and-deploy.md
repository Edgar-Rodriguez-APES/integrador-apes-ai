# Guía de Despliegue Manual - Siesa Integration Service

## Problema Identificado

CDK tiene problemas para leer credenciales de AWS SSO directamente. Necesitamos usar una solución alternativa.

## Solución: Usar AWS CLI para Bootstrap Manual

### Opción 1: Bootstrap usando AWS CloudFormation directamente

Ya que CDK no puede leer las credenciales SSO, vamos a hacer el bootstrap manualmente usando AWS CLI:

```powershell
# 1. Verificar que estás autenticado
aws sts get-caller-identity --profile principal

# 2. Crear el stack de bootstrap manualmente
aws cloudformation create-stack `
  --stack-name CDKToolkit `
  --template-url https://s3.amazonaws.com/aws-cdk-prod-assets-224874703567-us-east-1/bootstrap-template.yaml `
  --capabilities CAPABILITY_NAMED_IAM `
  --profile principal `
  --region us-east-1
```

### Opción 2: Usar credenciales temporales

Exporta las credenciales temporales de AWS SSO:

```powershell
# 1. Obtener credenciales temporales
$creds = aws configure export-credentials --profile principal | ConvertFrom-Json

# 2. Configurar variables de entorno
$env:AWS_ACCESS_KEY_ID = $creds.AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $creds.SecretAccessKey
$env:AWS_SESSION_TOKEN = $creds.SessionToken
$env:AWS_DEFAULT_REGION = "us-east-1"
$env:CDK_DEFAULT_ACCOUNT = "224874703567"
$env:CDK_DEFAULT_REGION = "us-east-1"
$env:ENVIRONMENT = "dev"

# 3. Ahora ejecutar CDK
cd siesa-integration-service
npx cdk bootstrap
npx cdk deploy
```

### Opción 3: Instalar CDK globalmente y usar --profile

```powershell
# 1. Instalar CDK globalmente
npm install -g aws-cdk

# 2. Ejecutar con --profile
cd siesa-integration-service
cdk bootstrap --profile principal
cdk deploy --profile principal
```

## Recomendación

**Usa la Opción 2** (credenciales temporales) ya que es la más confiable con AWS SSO.

## Pasos Detallados - Opción 2

### Paso 1: Abrir PowerShell en el directorio del proyecto

```powershell
cd "C:\Disco local\MisProyectos\Integrador APES AI\siesa-integration-service"
```

### Paso 2: Exportar credenciales temporales

```powershell
# Obtener credenciales
$creds = aws configure export-credentials --profile principal | ConvertFrom-Json

# Configurar variables de entorno
$env:AWS_ACCESS_KEY_ID = $creds.AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $creds.SecretAccessKey
$env:AWS_SESSION_TOKEN = $creds.SessionToken
$env:AWS_DEFAULT_REGION = "us-east-1"
$env:CDK_DEFAULT_ACCOUNT = "224874703567"
$env:CDK_DEFAULT_REGION = "us-east-1"
$env:ENVIRONMENT = "dev"

# Verificar
aws sts get-caller-identity
```

Deberías ver:
```json
{
    "UserId": "...",
    "Account": "224874703567",
    "Arn": "..."
}
```

### Paso 3: Bootstrap CDK (solo primera vez)

```powershell
npx cdk bootstrap
```

Esto tomará 2-3 minutos y creará el stack `CDKToolkit` en CloudFormation.

### Paso 4: Desplegar la infraestructura

```powershell
npx cdk deploy --require-approval never
```

Esto tomará 5-10 minutos y creará todos los recursos.

## Verificación Post-Despliegue

```powershell
# Ver stacks desplegados
aws cloudformation list-stacks --profile principal --region us-east-1 --stack-status-filter CREATE_COMPLETE

# Ver tablas DynamoDB
aws dynamodb list-tables --profile principal --region us-east-1

# Ver buckets S3
aws s3 ls --profile principal --region us-east-1
```

## Troubleshooting

### Error: "Token has expired"

```powershell
# Renovar sesión SSO
aws sso login --profile principal

# Volver a exportar credenciales
$creds = aws configure export-credentials --profile principal | ConvertFrom-Json
$env:AWS_ACCESS_KEY_ID = $creds.AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $creds.SecretAccessKey
$env:AWS_SESSION_TOKEN = $creds.SessionToken
```

### Error: "Stack already exists"

Si el stack ya existe, usa `deploy` en lugar de `bootstrap`:

```powershell
npx cdk deploy --require-approval never
```

## Script Completo (Copiar y Pegar)

```powershell
# Navegar al directorio
cd "C:\Disco local\MisProyectos\Integrador APES AI\siesa-integration-service"

# Exportar credenciales
$creds = aws configure export-credentials --profile principal | ConvertFrom-Json
$env:AWS_ACCESS_KEY_ID = $creds.AccessKeyId
$env:AWS_SECRET_ACCESS_KEY = $creds.SecretAccessKey
$env:AWS_SESSION_TOKEN = $creds.SessionToken
$env:AWS_DEFAULT_REGION = "us-east-1"
$env:CDK_DEFAULT_ACCOUNT = "224874703567"
$env:CDK_DEFAULT_REGION = "us-east-1"
$env:ENVIRONMENT = "dev"

# Verificar autenticación
Write-Host "Verificando autenticacion..." -ForegroundColor Cyan
aws sts get-caller-identity

# Bootstrap (solo primera vez)
Write-Host "Ejecutando bootstrap..." -ForegroundColor Cyan
npx cdk bootstrap

# Desplegar
Write-Host "Desplegando infraestructura..." -ForegroundColor Cyan
npx cdk deploy --require-approval never

Write-Host "Despliegue completado!" -ForegroundColor Green
```

## Próximos Pasos

Después del despliegue exitoso:

1. Verificar recursos en AWS Console
2. Subir field mappings a S3
3. Crear configuración de tenant de prueba
4. Continuar con Task 2 (Lambda functions)
