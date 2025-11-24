# Test Step Functions State Machine
# This script tests the Siesa integration state machine with sample data

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory=$false)]
    [string]$ClientId = "test-client",
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("initial", "incremental")]
    [string]$SyncType = "incremental",
    
    [Parameter(Mandatory=$false)]
    [string]$Profile = "principal",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Step Functions State Machine Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$StateMachineName = "siesa-integration-workflow-$Environment"
$ExecutionName = "test-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Environment: $Environment"
Write-Host "  Client ID: $ClientId"
Write-Host "  Sync Type: $SyncType"
Write-Host "  State Machine: $StateMachineName"
Write-Host "  Execution Name: $ExecutionName"
Write-Host "  AWS Profile: $Profile"
Write-Host "  AWS Region: $Region"
Write-Host ""

# Get state machine ARN
Write-Host "Getting state machine ARN..." -ForegroundColor Yellow
try {
    $StateMachineArn = aws stepfunctions list-state-machines `
        --query "stateMachines[?name=='$StateMachineName'].stateMachineArn | [0]" `
        --output text `
        --profile $Profile `
        --region $Region
    
    if ([string]::IsNullOrEmpty($StateMachineArn) -or $StateMachineArn -eq "None") {
        Write-Host "ERROR: State machine '$StateMachineName' not found!" -ForegroundColor Red
        Write-Host "Please deploy the CDK stack first." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "State Machine ARN: $StateMachineArn" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "ERROR: Failed to get state machine ARN" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Prepare input
$Input = @{
    client_id = $ClientId
    sync_type = $SyncType
} | ConvertTo-Json -Compress

Write-Host "Input:" -ForegroundColor Yellow
Write-Host $Input
Write-Host ""

# Start execution
Write-Host "Starting state machine execution..." -ForegroundColor Yellow
try {
    $ExecutionArn = aws stepfunctions start-execution `
        --state-machine-arn $StateMachineArn `
        --name $ExecutionName `
        --input $Input `
        --query 'executionArn' `
        --output text `
        --profile $Profile `
        --region $Region
    
    Write-Host "Execution started successfully!" -ForegroundColor Green
    Write-Host "Execution ARN: $ExecutionArn" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "ERROR: Failed to start execution" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# Wait for execution to complete
Write-Host "Waiting for execution to complete..." -ForegroundColor Yellow
Write-Host "(This may take several minutes depending on the data volume)" -ForegroundColor Gray
Write-Host ""

$MaxWaitTime = 300  # 5 minutes
$WaitInterval = 5   # 5 seconds
$ElapsedTime = 0

while ($ElapsedTime -lt $MaxWaitTime) {
    Start-Sleep -Seconds $WaitInterval
    $ElapsedTime += $WaitInterval
    
    # Get execution status
    $Status = aws stepfunctions describe-execution `
        --execution-arn $ExecutionArn `
        --query 'status' `
        --output text `
        --profile $Profile `
        --region $Region
    
    Write-Host "  Status: $Status (elapsed: ${ElapsedTime}s)" -ForegroundColor Gray
    
    if ($Status -eq "SUCCEEDED") {
        Write-Host ""
        Write-Host "Execution completed successfully!" -ForegroundColor Green
        break
    } elseif ($Status -eq "FAILED" -or $Status -eq "TIMED_OUT" -or $Status -eq "ABORTED") {
        Write-Host ""
        Write-Host "Execution failed with status: $Status" -ForegroundColor Red
        break
    }
}

if ($ElapsedTime -ge $MaxWaitTime) {
    Write-Host ""
    Write-Host "Execution is still running after $MaxWaitTime seconds" -ForegroundColor Yellow
    Write-Host "Check the AWS Console for final status" -ForegroundColor Yellow
}

# Get execution details
Write-Host ""
Write-Host "Execution Details:" -ForegroundColor Yellow
Write-Host "==================" -ForegroundColor Yellow

$ExecutionDetails = aws stepfunctions describe-execution `
    --execution-arn $ExecutionArn `
    --profile $Profile `
    --region $Region | ConvertFrom-Json

Write-Host "Status: $($ExecutionDetails.status)" -ForegroundColor $(if ($ExecutionDetails.status -eq "SUCCEEDED") { "Green" } else { "Red" })
Write-Host "Start Time: $($ExecutionDetails.startDate)"
Write-Host "Stop Time: $($ExecutionDetails.stopDate)"

if ($ExecutionDetails.status -eq "SUCCEEDED") {
    Write-Host ""
    Write-Host "Output:" -ForegroundColor Yellow
    $Output = $ExecutionDetails.output | ConvertFrom-Json
    Write-Host ($Output | ConvertTo-Json -Depth 10)
} elseif ($ExecutionDetails.status -eq "FAILED") {
    Write-Host ""
    Write-Host "Error:" -ForegroundColor Red
    Write-Host $ExecutionDetails.error
    Write-Host ""
    Write-Host "Cause:" -ForegroundColor Red
    Write-Host $ExecutionDetails.cause
}

# Get execution history
Write-Host ""
Write-Host "Execution History (Last 5 Events):" -ForegroundColor Yellow
Write-Host "===================================" -ForegroundColor Yellow

$History = aws stepfunctions get-execution-history `
    --execution-arn $ExecutionArn `
    --max-results 5 `
    --reverse-order `
    --profile $Profile `
    --region $Region | ConvertFrom-Json

foreach ($Event in $History.events) {
    Write-Host "[$($Event.timestamp)] $($Event.type)" -ForegroundColor Cyan
}

# Console URLs
Write-Host ""
Write-Host "AWS Console URLs:" -ForegroundColor Yellow
Write-Host "=================" -ForegroundColor Yellow
Write-Host "State Machine: https://$Region.console.aws.amazon.com/states/home?region=$Region#/statemachines/view/$StateMachineArn"
Write-Host "Execution: https://$Region.console.aws.amazon.com/states/home?region=$Region#/executions/details/$ExecutionArn"
Write-Host ""

# CloudWatch Logs
Write-Host "CloudWatch Logs:" -ForegroundColor Yellow
Write-Host "================" -ForegroundColor Yellow
Write-Host "State Machine Logs: /aws/stepfunctions/$StateMachineName"
Write-Host "Extractor Logs: /aws/lambda/siesa-integration-extractor-$Environment"
Write-Host "Transformer Logs: /aws/lambda/siesa-integration-transformer-$Environment"
Write-Host "Loader Logs: /aws/lambda/siesa-integration-loader-$Environment"
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($ExecutionDetails.status -eq "SUCCEEDED") {
    Write-Host "Result: SUCCESS" -ForegroundColor Green
    exit 0
} else {
    Write-Host "Result: FAILED" -ForegroundColor Red
    Write-Host "Check the logs and execution history for details" -ForegroundColor Yellow
    exit 1
}
