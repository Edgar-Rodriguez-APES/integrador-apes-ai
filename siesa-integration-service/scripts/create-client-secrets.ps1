# ============================================
# Create Client Secrets in AWS Secrets Manager
# ============================================
# This script creates secrets for a new client in AWS Secrets Manager

param(
    [Parameter(Mandatory=$true)]
    [string]$ClientId,
    
    [Parameter(Mandatory=$true)]
    [ValidateSet('kong', 'wms')]
    [string]$ProductType,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1",
    
    [Parameter(Mandatory=$false)]
    [string]$Profile = "default",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Create Client Secrets in AWS Secrets Manager" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Client ID: $ClientId" -ForegroundColor Yellow
Write-Host "Product Type: $ProductType" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host ""

if ($DryRun) {
    Write-Host "⚠️  DRY RUN MODE - No secrets will be created" -ForegroundColor Yellow
    Write-Host ""
}

# ============================================
# 1. Create Siesa Secret
# ============================================

$siesaSecretName = "siesa-integration/$ClientId/siesa"
Write-Host "Creating Siesa secret: $siesaSecretName" -ForegroundColor Cyan

$siesaSecretValue = @{
    baseUrl = "https://serviciosqa.siesacloud.com/api/siesa/v3/"
    username = "REPLACE_WITH_ACTUAL_USERNAME"
    password = "REPLACE_WITH_ACTUAL_PASSWORD"
    conniKey = "REPLACE_WITH_ACTUAL_CONNI_KEY"
    conniToken = "REPLACE_WITH_ACTUAL_CONNI_TOKEN"
    tenantId = "$ClientId-tenant"
    environment = "production"
} | ConvertTo-Json -Compress

if ($DryRun) {
    Write-Host "Would create secret: $siesaSecretName" -ForegroundColor Gray
    Write-Host "Value: $siesaSecretValue" -ForegroundColor Gray
} else {
    try {
        aws secretsmanager create-secret `
            --name $siesaSecretName `
            --description "Siesa ERP credentials for $ClientId" `
            --secret-string $siesaSecretValue `
            --region $Region `
            --profile $Profile 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Siesa secret created successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to create Siesa secret" -ForegroundColor Red
            Write-Host "   Secret may already exist. Use update-secret instead." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ Error creating Siesa secret: $_" -ForegroundColor Red
    }
}

Write-Host ""

# ============================================
# 2. Create Product Secret (Kong or WMS)
# ============================================

$productSecretName = "siesa-integration/$ClientId/$ProductType"
Write-Host "Creating $ProductType secret: $productSecretName" -ForegroundColor Cyan

if ($ProductType -eq "kong") {
    # Kong secret structure
    $productSecretValue = @{
        productType = "kong"
        baseUrl = "https://api-staging.technoapes.io/"
        username = "REPLACE_WITH_KONG_USERNAME"
        password = "REPLACE_WITH_KONG_PASSWORD"
        apiKey = "REPLACE_WITH_API_KEY_IF_USED"
        tenantId = $ClientId
        databaseType = "rds"
        additionalConfig = @{
            rfidEnabled = $true
            batchSize = 100
            timeout = 30000
        }
    } | ConvertTo-Json -Compress
} else {
    # WMS secret structure
    $productSecretValue = @{
        productType = "wms"
        baseUrl = "https://wms-api.$ClientId.com/api/v1"
        apiKey = "REPLACE_WITH_WMS_API_KEY"
        tenantId = $ClientId
        serviceEndpoints = @{
            inventory = "https://wms-api.$ClientId.com/inventory"
            warehouse = "https://wms-api.$ClientId.com/warehouse"
            orders = "https://wms-api.$ClientId.com/orders"
            locations = "https://wms-api.$ClientId.com/locations"
        }
        additionalConfig = @{
            warehouseId = "WH-001"
            defaultZone = "ZONE-A"
            batchSize = 100
            timeout = 30000
            lotTrackingEnabled = $true
            expirationTrackingEnabled = $true
        }
    } | ConvertTo-Json -Compress
}

if ($DryRun) {
    Write-Host "Would create secret: $productSecretName" -ForegroundColor Gray
    Write-Host "Value: $productSecretValue" -ForegroundColor Gray
} else {
    try {
        aws secretsmanager create-secret `
            --name $productSecretName `
            --description "$ProductType credentials for $ClientId" `
            --secret-string $productSecretValue `
            --region $Region `
            --profile $Profile 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $ProductType secret created successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to create $ProductType secret" -ForegroundColor Red
            Write-Host "   Secret may already exist. Use update-secret instead." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ Error creating $ProductType secret: $_" -ForegroundColor Red
    }
}

Write-Host ""

# ============================================
# 3. Verify Secrets
# ============================================

if (-not $DryRun) {
    Write-Host "Verifying secrets..." -ForegroundColor Cyan
    
    # List secrets for this client
    $secrets = aws secretsmanager list-secrets `
        --filters Key=name,Values=siesa-integration/$ClientId/ `
        --region $Region `
        --profile $Profile `
        --query 'SecretList[].Name' `
        --output text
    
    if ($secrets) {
        Write-Host "✅ Found secrets for client $ClientId:" -ForegroundColor Green
        $secrets -split "`t" | ForEach-Object {
            Write-Host "   - $_" -ForegroundColor White
        }
    } else {
        Write-Host "⚠️  No secrets found for client $ClientId" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "✅ Secret creation process completed!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if (-not $DryRun) {
    Write-Host "⚠️  IMPORTANT: Update the placeholder values!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Go to AWS Secrets Manager console" -ForegroundColor White
    Write-Host "2. Find secrets for client: $ClientId" -ForegroundColor White
    Write-Host "3. Edit each secret and replace REPLACE_WITH_* values" -ForegroundColor White
    Write-Host "4. Test secret retrieval with Lambda functions" -ForegroundColor White
    Write-Host "5. Update DynamoDB client configuration" -ForegroundColor White
    Write-Host ""
    Write-Host "To update secrets via CLI:" -ForegroundColor Cyan
    Write-Host "aws secretsmanager update-secret --secret-id $siesaSecretName --secret-string '{...}'" -ForegroundColor Gray
    Write-Host "aws secretsmanager update-secret --secret-id $productSecretName --secret-string '{...}'" -ForegroundColor Gray
} else {
    Write-Host "This was a dry run. Run without -DryRun to create secrets." -ForegroundColor Yellow
}

Write-Host ""
