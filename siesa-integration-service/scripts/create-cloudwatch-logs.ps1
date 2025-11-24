# Script para crear CloudWatch Log Groups para Siesa Integration
# Este script crea los log groups necesarios para las Lambda functions y Step Functions

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('dev', 'test', 'prod')]
    [string]$Environment,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = 'us-east-1',
    
    [Parameter(Mandatory=$false)]
    [string]$Profile = 'default',
    
    [Parameter(Mandatory=$false)]
    [string]$KmsKeyId = ''
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CloudWatch Log Groups Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host "Profile: $Profile" -ForegroundColor Yellow
Write-Host ""

# Configurar retention period basado en environment
$retentionDays = if ($Environment -eq 'prod') { 30 } else { 7 }
Write-Host "Retention Period: $retentionDays days" -ForegroundColor Yellow
Write-Host ""

# Definir log groups a crear
$logGroups = @(
    @{
        Name = "/aws/lambda/siesa-integration-extractor-$Environment"
        Description = "Extractor Lambda function logs"
    },
    @{
        Name = "/aws/lambda/siesa-integration-transformer-$Environment"
        Description = "Transformer Lambda function logs"
    },
    @{
        Name = "/aws/lambda/siesa-integration-loader-$Environment"
        Description = "Loader Lambda function logs"
    },
    @{
        Name = "/aws/stepfunctions/siesa-integration-workflow-$Environment"
        Description = "Step Functions workflow logs"
    },
    @{
        Name = "/aws/apigateway/siesa-integration-$Environment"
        Description = "API Gateway logs (future use)"
    }
)

# Función para crear log group
function Create-LogGroup {
    param(
        [string]$LogGroupName,
        [string]$Description,
        [int]$RetentionDays,
        [string]$KmsKeyId
    )
    
    Write-Host "Creating log group: $LogGroupName" -ForegroundColor Green
    
    try {
        # Verificar si el log group ya existe
        $existingLogGroup = aws logs describe-log-groups `
            --log-group-name-prefix $LogGroupName `
            --region $Region `
            --profile $Profile `
            --query "logGroups[?logGroupName=='$LogGroupName']" `
            --output json | ConvertFrom-Json
        
        if ($existingLogGroup.Count -gt 0) {
            Write-Host "  ✓ Log group already exists" -ForegroundColor Yellow
            
            # Actualizar retention period
            Write-Host "  → Updating retention period to $RetentionDays days..." -ForegroundColor Cyan
            aws logs put-retention-policy `
                --log-group-name $LogGroupName `
                --retention-in-days $RetentionDays `
                --region $Region `
                --profile $Profile
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ Retention period updated" -ForegroundColor Green
            } else {
                Write-Host "  ✗ Failed to update retention period" -ForegroundColor Red
            }
        } else {
            # Crear log group
            if ($KmsKeyId) {
                aws logs create-log-group `
                    --log-group-name $LogGroupName `
                    --kms-key-id $KmsKeyId `
                    --region $Region `
                    --profile $Profile
            } else {
                aws logs create-log-group `
                    --log-group-name $LogGroupName `
                    --region $Region `
                    --profile $Profile
            }
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  ✓ Log group created" -ForegroundColor Green
                
                # Configurar retention period
                Write-Host "  → Setting retention period to $RetentionDays days..." -ForegroundColor Cyan
                aws logs put-retention-policy `
                    --log-group-name $LogGroupName `
                    --retention-in-days $RetentionDays `
                    --region $Region `
                    --profile $Profile
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  ✓ Retention period configured" -ForegroundColor Green
                } else {
                    Write-Host "  ✗ Failed to configure retention period" -ForegroundColor Red
                }
                
                # Agregar tags
                Write-Host "  → Adding tags..." -ForegroundColor Cyan
                aws logs tag-log-group `
                    --log-group-name $LogGroupName `
                    --tags "Project=SiesaIntegration,Environment=$Environment,ManagedBy=Script,Purpose=$Description" `
                    --region $Region `
                    --profile $Profile
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  ✓ Tags added" -ForegroundColor Green
                } else {
                    Write-Host "  ✗ Failed to add tags" -ForegroundColor Red
                }
            } else {
                Write-Host "  ✗ Failed to create log group" -ForegroundColor Red
                return $false
            }
        }
        
        Write-Host ""
        return $true
    }
    catch {
        Write-Host "  ✗ Error: $_" -ForegroundColor Red
        Write-Host ""
        return $false
    }
}

# Crear KMS key si no se proporcionó
if (-not $KmsKeyId) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Creating KMS Key for Log Encryption" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $kmsKeyAlias = "alias/siesa-integration-logs-$Environment"
    
    # Verificar si el alias ya existe
    $existingAlias = aws kms list-aliases `
        --region $Region `
        --profile $Profile `
        --query "Aliases[?AliasName=='$kmsKeyAlias'].TargetKeyId" `
        --output text
    
    if ($existingAlias) {
        Write-Host "KMS key alias already exists: $kmsKeyAlias" -ForegroundColor Yellow
        $KmsKeyId = $existingAlias
        Write-Host "Using existing KMS key: $KmsKeyId" -ForegroundColor Green
    } else {
        Write-Host "Creating new KMS key..." -ForegroundColor Cyan
        
        # Crear KMS key
        $kmsKeyJson = aws kms create-key `
            --description "KMS key for Siesa Integration CloudWatch Logs encryption" `
            --key-policy "{
                `"Version`": `"2012-10-17`",
                `"Statement`": [
                    {
                        `"Sid`": `"Enable IAM User Permissions`",
                        `"Effect`": `"Allow`",
                        `"Principal`": {
                            `"AWS`": `"arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):root`"
                        },
                        `"Action`": `"kms:*`",
                        `"Resource`": `"*`"
                    },
                    {
                        `"Sid`": `"Allow CloudWatch Logs`",
                        `"Effect`": `"Allow`",
                        `"Principal`": {
                            `"Service`": `"logs.$Region.amazonaws.com`"
                        },
                        `"Action`": [
                            `"kms:Encrypt`",
                            `"kms:Decrypt`",
                            `"kms:ReEncrypt*`",
                            `"kms:GenerateDataKey*`",
                            `"kms:CreateGrant`",
                            `"kms:DescribeKey`"
                        ],
                        `"Resource`": `"*`"
                    }
                ]
            }" `
            --region $Region `
            --profile $Profile `
            --output json | ConvertFrom-Json
        
        if ($LASTEXITCODE -eq 0) {
            $KmsKeyId = $kmsKeyJson.KeyMetadata.KeyId
            Write-Host "✓ KMS key created: $KmsKeyId" -ForegroundColor Green
            
            # Crear alias
            aws kms create-alias `
                --alias-name $kmsKeyAlias `
                --target-key-id $KmsKeyId `
                --region $Region `
                --profile $Profile
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ KMS key alias created: $kmsKeyAlias" -ForegroundColor Green
            } else {
                Write-Host "✗ Failed to create KMS key alias" -ForegroundColor Red
            }
            
            # Habilitar key rotation
            aws kms enable-key-rotation `
                --key-id $KmsKeyId `
                --region $Region `
                --profile $Profile
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Key rotation enabled" -ForegroundColor Green
            } else {
                Write-Host "✗ Failed to enable key rotation" -ForegroundColor Red
            }
        } else {
            Write-Host "✗ Failed to create KMS key" -ForegroundColor Red
            Write-Host "Continuing without encryption..." -ForegroundColor Yellow
            $KmsKeyId = ''
        }
    }
    
    Write-Host ""
}

# Crear log groups
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Creating Log Groups" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$successCount = 0
$failCount = 0

foreach ($logGroup in $logGroups) {
    $result = Create-LogGroup `
        -LogGroupName $logGroup.Name `
        -Description $logGroup.Description `
        -RetentionDays $retentionDays `
        -KmsKeyId $KmsKeyId
    
    if ($result) {
        $successCount++
    } else {
        $failCount++
    }
}

# Resumen
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Total log groups: $($logGroups.Count)" -ForegroundColor White
Write-Host "Successfully created/updated: $successCount" -ForegroundColor Green
Write-Host "Failed: $failCount" -ForegroundColor Red
Write-Host ""

if ($KmsKeyId) {
    Write-Host "KMS Key ID: $KmsKeyId" -ForegroundColor Yellow
    Write-Host "KMS Key Alias: alias/siesa-integration-logs-$Environment" -ForegroundColor Yellow
    Write-Host ""
}

# Listar log groups creados
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Created Log Groups" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

aws logs describe-log-groups `
    --log-group-name-prefix "/aws/lambda/siesa-integration" `
    --region $Region `
    --profile $Profile `
    --query "logGroups[*].[logGroupName,retentionInDays,kmsKeyId]" `
    --output table

Write-Host ""
Write-Host "✓ CloudWatch Log Groups setup completed!" -ForegroundColor Green
Write-Host ""

# Instrucciones adicionales
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Verify log groups in AWS Console:" -ForegroundColor White
Write-Host "   https://console.aws.amazon.com/cloudwatch/home?region=$Region#logsV2:log-groups" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Lambda functions will automatically write to these log groups" -ForegroundColor White
Write-Host ""
Write-Host "3. To view logs for a specific Lambda:" -ForegroundColor White
Write-Host "   aws logs tail /aws/lambda/siesa-integration-extractor-$Environment --follow --region $Region --profile $Profile" -ForegroundColor Cyan
Write-Host ""
