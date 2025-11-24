# Script para crear SNS Topic para alertas de Siesa Integration
# Este script crea el topic SNS y configura subscripciones de email

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('dev', 'test', 'prod')]
    [string]$Environment,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = 'us-east-1',
    
    [Parameter(Mandatory=$false)]
    [string]$Profile = 'default',
    
    [Parameter(Mandatory=$false)]
    [string[]]$EmailAddresses = @()
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SNS Topic Setup for Alerts" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Environment: $Environment" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host "Profile: $Profile" -ForegroundColor Yellow
Write-Host ""

$topicName = "siesa-integration-alerts-$Environment"
$displayName = "Siesa Integration Alerts ($Environment)"

# Crear SNS Topic
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Creating SNS Topic" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Topic Name: $topicName" -ForegroundColor Yellow
Write-Host ""

# Verificar si el topic ya existe
$existingTopic = aws sns list-topics `
    --region $Region `
    --profile $Profile `
    --query "Topics[?contains(TopicArn, '$topicName')].TopicArn" `
    --output text

if ($existingTopic) {
    Write-Host "✓ SNS topic already exists" -ForegroundColor Yellow
    Write-Host "Topic ARN: $existingTopic" -ForegroundColor Cyan
    $topicArn = $existingTopic
} else {
    Write-Host "Creating SNS topic..." -ForegroundColor Cyan
    
    $createResult = aws sns create-topic `
        --name $topicName `
        --region $Region `
        --profile $Profile `
        --attributes "{
            `"DisplayName`": `"$displayName`",
            `"DeliveryPolicy`": `"{
                \`"http\`": {
                    \`"defaultHealthyRetryPolicy\`": {
                        \`"minDelayTarget\`": 20,
                        \`"maxDelayTarget\`": 20,
                        \`"numRetries\`": 3,
                        \`"numMaxDelayRetries\`": 0,
                        \`"numNoDelayRetries\`": 0,
                        \`"numMinDelayRetries\`": 0,
                        \`"backoffFunction\`": \`"linear\`"
                    },
                    \`"disableSubscriptionOverrides\`": false
                }
            }`"
        }" `
        --output json | ConvertFrom-Json
    
    if ($LASTEXITCODE -eq 0) {
        $topicArn = $createResult.TopicArn
        Write-Host "✓ SNS topic created successfully" -ForegroundColor Green
        Write-Host "Topic ARN: $topicArn" -ForegroundColor Cyan
    } else {
        Write-Host "✗ Failed to create SNS topic" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Configurar topic policy
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuring Topic Policy" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$accountId = aws sts get-caller-identity --query Account --output text

$topicPolicy = @"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowStepFunctionsPublish",
      "Effect": "Allow",
      "Principal": {
        "Service": "states.amazonaws.com"
      },
      "Action": "SNS:Publish",
      "Resource": "$topicArn",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "$accountId"
        }
      }
    },
    {
      "Sid": "AllowLambdaPublish",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "SNS:Publish",
      "Resource": "$topicArn",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "$accountId"
        }
      }
    },
    {
      "Sid": "AllowCloudWatchAlarmsPublish",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudwatch.amazonaws.com"
      },
      "Action": "SNS:Publish",
      "Resource": "$topicArn",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "$accountId"
        }
      }
    },
    {
      "Sid": "AllowAccountAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::$($accountId):root"
      },
      "Action": [
        "SNS:GetTopicAttributes",
        "SNS:SetTopicAttributes",
        "SNS:AddPermission",
        "SNS:RemovePermission",
        "SNS:DeleteTopic",
        "SNS:Subscribe",
        "SNS:ListSubscriptionsByTopic",
        "SNS:Publish"
      ],
      "Resource": "$topicArn"
    }
  ]
}
"@

Write-Host "Setting topic policy..." -ForegroundColor Cyan

# Escapar el JSON para PowerShell
$escapedPolicy = $topicPolicy -replace '"', '\"'

aws sns set-topic-attributes `
    --topic-arn $topicArn `
    --attribute-name Policy `
    --attribute-value $topicPolicy `
    --region $Region `
    --profile $Profile

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Topic policy configured" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to configure topic policy" -ForegroundColor Red
}

Write-Host ""

# Agregar tags
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Adding Tags" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

aws sns tag-resource `
    --resource-arn $topicArn `
    --tags "Key=Project,Value=SiesaIntegration" "Key=Environment,Value=$Environment" "Key=ManagedBy,Value=Script" "Key=Purpose,Value=Alerts" `
    --region $Region `
    --profile $Profile

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Tags added" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to add tags" -ForegroundColor Red
}

Write-Host ""

# Configurar subscripciones de email
if ($EmailAddresses.Count -gt 0) {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Creating Email Subscriptions" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    foreach ($email in $EmailAddresses) {
        Write-Host "Subscribing: $email" -ForegroundColor Cyan
        
        $subscribeResult = aws sns subscribe `
            --topic-arn $topicArn `
            --protocol email `
            --notification-endpoint $email `
            --region $Region `
            --profile $Profile `
            --output json | ConvertFrom-Json
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Subscription created (pending confirmation)" -ForegroundColor Green
            Write-Host "  Subscription ARN: $($subscribeResult.SubscriptionArn)" -ForegroundColor Cyan
            Write-Host "  ⚠️  Check email inbox for confirmation link" -ForegroundColor Yellow
        } else {
            Write-Host "✗ Failed to create subscription" -ForegroundColor Red
        }
        
        Write-Host ""
    }
} else {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Email Subscriptions" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "⚠️  No email addresses provided" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To add email subscriptions later, run:" -ForegroundColor White
    Write-Host "  aws sns subscribe --topic-arn $topicArn --protocol email --notification-endpoint your-email@example.com --region $Region --profile $Profile" -ForegroundColor Cyan
    Write-Host ""
}

# Crear mensaje de prueba
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Message" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$testMessage = @"
{
  "AlarmName": "Test Alarm",
  "AlarmDescription": "This is a test message from Siesa Integration setup",
  "NewStateValue": "OK",
  "NewStateReason": "Testing SNS topic configuration",
  "StateChangeTime": "$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffZ')",
  "Region": "$Region",
  "Environment": "$Environment"
}
"@

$sendTest = Read-Host "Do you want to send a test message? (y/n)"

if ($sendTest -eq 'y' -or $sendTest -eq 'Y') {
    Write-Host ""
    Write-Host "Sending test message..." -ForegroundColor Cyan
    
    aws sns publish `
        --topic-arn $topicArn `
        --subject "Siesa Integration - Test Alert ($Environment)" `
        --message $testMessage `
        --region $Region `
        --profile $Profile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Test message sent successfully" -ForegroundColor Green
        Write-Host "  Check your email inbox (if subscribed)" -ForegroundColor Yellow
    } else {
        Write-Host "✗ Failed to send test message" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Listar subscripciones
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Current Subscriptions" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$subscriptions = aws sns list-subscriptions-by-topic `
    --topic-arn $topicArn `
    --region $Region `
    --profile $Profile `
    --output json | ConvertFrom-Json

if ($subscriptions.Subscriptions.Count -gt 0) {
    foreach ($sub in $subscriptions.Subscriptions) {
        Write-Host "Protocol: $($sub.Protocol)" -ForegroundColor White
        Write-Host "Endpoint: $($sub.Endpoint)" -ForegroundColor Cyan
        Write-Host "Status: $($sub.SubscriptionArn)" -ForegroundColor $(if ($sub.SubscriptionArn -eq 'PendingConfirmation') { 'Yellow' } else { 'Green' })
        Write-Host ""
    }
} else {
    Write-Host "No subscriptions configured yet" -ForegroundColor Yellow
    Write-Host ""
}

# Resumen
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ SNS Topic created/configured successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Topic Name: $topicName" -ForegroundColor White
Write-Host "Topic ARN: $topicArn" -ForegroundColor Cyan
Write-Host "Display Name: $displayName" -ForegroundColor White
Write-Host "Region: $Region" -ForegroundColor White
Write-Host "Environment: $Environment" -ForegroundColor White
Write-Host ""

if ($EmailAddresses.Count -gt 0) {
    Write-Host "Email Subscriptions: $($EmailAddresses.Count)" -ForegroundColor White
    Write-Host "⚠️  Remember to confirm email subscriptions!" -ForegroundColor Yellow
    Write-Host ""
}

# Instrucciones adicionales
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Confirm email subscriptions (check inbox)" -ForegroundColor White
Write-Host ""
Write-Host "2. Configure CloudWatch Alarms to publish to this topic:" -ForegroundColor White
Write-Host "   Topic ARN: $topicArn" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Configure Step Functions to publish failures to this topic" -ForegroundColor White
Write-Host ""
Write-Host "4. Test the integration:" -ForegroundColor White
Write-Host "   aws sns publish --topic-arn $topicArn --subject 'Test' --message 'Test message' --region $Region --profile $Profile" -ForegroundColor Cyan
Write-Host ""
Write-Host "5. View topic in AWS Console:" -ForegroundColor White
Write-Host "   https://console.aws.amazon.com/sns/v3/home?region=$Region#/topic/$topicArn" -ForegroundColor Cyan
Write-Host ""

Write-Host "✓ SNS Topic setup completed!" -ForegroundColor Green
Write-Host ""
