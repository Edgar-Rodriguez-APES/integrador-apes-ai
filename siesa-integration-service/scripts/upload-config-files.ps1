# ============================================
# Upload Configuration Files to S3
# ============================================
# This script uploads field mapping configuration files to the S3 bucket
# Run this after deploying the CDK stack

param(
    [Parameter(Mandatory=$true)]
    [string]$Environment,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1",
    
    [Parameter(Mandatory=$false)]
    [string]$Profile = "default"
)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Uploading Configuration Files to S3" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Get AWS Account ID
Write-Host "Getting AWS Account ID..." -ForegroundColor Yellow
$accountId = aws sts get-caller-identity --profile $Profile --query Account --output text

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to get AWS Account ID" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Account ID: $accountId" -ForegroundColor Green
Write-Host ""

# Construct bucket name
$bucketName = "siesa-integration-config-$Environment-$accountId"
Write-Host "Target S3 Bucket: $bucketName" -ForegroundColor Cyan
Write-Host ""

# Check if bucket exists
Write-Host "Checking if bucket exists..." -ForegroundColor Yellow
aws s3 ls "s3://$bucketName" --profile $Profile --region $Region 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Bucket does not exist. Please deploy the CDK stack first." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Bucket exists" -ForegroundColor Green
Write-Host ""

# Upload Kong field mappings
Write-Host "Uploading Kong field mappings..." -ForegroundColor Yellow
aws s3 cp config/field-mappings-kong.json "s3://$bucketName/field-mappings-kong.json" `
    --profile $Profile `
    --region $Region `
    --content-type "application/json"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Kong field mappings uploaded successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to upload Kong field mappings" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Upload WMS field mappings
Write-Host "Uploading WMS field mappings..." -ForegroundColor Yellow
aws s3 cp config/field-mappings-wms.json "s3://$bucketName/field-mappings-wms.json" `
    --profile $Profile `
    --region $Region `
    --content-type "application/json"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ WMS field mappings uploaded successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to upload WMS field mappings" -ForegroundColor Red
    exit 1
}

Write-Host ""

# List uploaded files
Write-Host "Listing uploaded files..." -ForegroundColor Yellow
aws s3 ls "s3://$bucketName/" --profile $Profile --region $Region

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "✅ Configuration files uploaded successfully!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Verify files in S3 console" -ForegroundColor White
Write-Host "2. Configure client entries in DynamoDB" -ForegroundColor White
Write-Host "3. Create Secrets Manager entries for clients" -ForegroundColor White
Write-Host ""
