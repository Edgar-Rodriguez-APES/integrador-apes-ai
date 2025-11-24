# Siesa Integration Service

Autonomous integration service between Siesa ERP and APES products (Kong RFID & WMS).

## 🎉 Estado Actual: Fase 1 Completada ✅

**Última actualización**: 2025-01-21  
**Progreso General**: 30% (Fase 1 de 3 completada)  
**Seguridad**: 🔒 95% de cobertura - 0 vulnerabilidades críticas

### ✅ Completado Recientemente:
- ✅ **Fase 1**: Correcciones Críticas de Seguridad (100%)
  - Eliminado eval() - Implementado SafeExpressionEvaluator basado en AST
  - Validación robusta de autenticación con tokens
  - Sanitización completa de inputs (SQL, NoSQL, XSS, etc.)
- ✅ **Verificación Automática**: 25/25 checks pasando (100%)
- ✅ **Documentación**: Completa y actualizada

### 📚 Documentación Clave:
- **[FASE1-RESUMEN-EJECUTIVO.md](FASE1-RESUMEN-EJECUTIVO.md)** - Resumen ejecutivo de Fase 1
- **[STATUS-DASHBOARD.md](STATUS-DASHBOARD.md)** - Dashboard de estado del proyecto
- **[PROXIMOS-PASOS.md](PROXIMOS-PASOS.md)** - Próximos pasos y timeline
- **[SECURITY-STATUS.md](SECURITY-STATUS.md)** - Estado detallado de seguridad

### 🚀 Próximos Pasos:
1. Tests unitarios de seguridad
2. Fase 2: Estabilidad (Circuit Breaker, Retry Logic, Rate Limiting)
3. Tests de integración y performance
4. Deploy a Staging

---

## Architecture Overview

This service implements a multi-tenant, multi-product integration architecture deployed in AWS account **224874703567** that supports:

- **Kong RFID**: Monolithic backend with RDS database (Client staging: 555569220783, Production: 901792597114)
- **WMS**: Microservices architecture in AWS
- **Siesa ERP**: External ERP system integration

## Features

- ✅ Multi-tenant architecture (one deployment, multiple clients)
- ✅ Multi-product support (Kong RFID or WMS per client)
- ✅ Product Adapter Pattern for different API structures
- ✅ Autonomous synchronization with configurable schedules
- ✅ Real-time and batch processing capabilities
- ✅ Comprehensive error handling and retry mechanisms
- ✅ Audit trail and monitoring
- ✅ Secure credential management

## Technology Stack

- **Infrastructure**: AWS CDK (TypeScript)
- **Compute**: AWS Lambda
- **Orchestration**: AWS Step Functions
- **Storage**: DynamoDB, S3
- **Security**: Secrets Manager, IAM
- **Monitoring**: CloudWatch, SNS

## Project Structure

```
siesa-integration-service/
├── src/
│   ├── infrastructure/          # AWS CDK infrastructure code
│   │   ├── app.ts              # CDK app entry point
│   │   └── stacks/             # CDK stack definitions
│   ├── lambdas/                # Lambda function code (to be implemented)
│   ├── types/                  # TypeScript type definitions (to be implemented)
│   └── config/                 # Configuration files (to be implemented)
├── test/                       # Test files (to be implemented)
├── docs/                       # Documentation
└── config/                     # Field mappings and configurations
```

## Quick Start

### Prerequisites

- Node.js 18+
- AWS CLI configured with access to account 224874703567
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- TypeScript
- Python 3.11+ (for Lambda functions)

### Installation

```bash
# Install dependencies
npm install

# Install Python tools for development
pip install bandit pylint flake8 pytest

# Bootstrap CDK (first time only in account 224874703567)
npm run bootstrap

# Build the project
npm run build
```

### Pre-Deploy Analysis

**⚠️ IMPORTANTE**: Antes de hacer deploy, ejecuta el análisis de código:

```powershell
# Ejecutar análisis completo
.\scripts\run-pre-deploy-checks.ps1

# Revisar reportes en pre-deploy-reports/SUMMARY.md
```

Ver guía completa: [QUICK-START-ANALYSIS.md](QUICK-START-ANALYSIS.md)

### Deployment

```bash
# Deploy to development environment
ENVIRONMENT=dev npm run deploy

# Deploy to production environment
ENVIRONMENT=prod npm run deploy
```

### Development

```bash
# Watch mode for development
npm run watch

# Run tests
npm test

# Synthesize CloudFormation template
npm run synth

# Show differences
npm run diff
```

## AWS Account Architecture

### Principal Account (APES - Integration)
- **Account ID**: 224874703567
- **Purpose**: Centralized integration service
- **Components**: All Lambda, Step Functions, DynamoDB, S3, Secrets Manager

### Client Accounts (Parchita - Kong/WMS)
- **Staging**: 555569220783 (Kong API staging)
- **Production**: 901792597114 (Kong API production)

## Configuration

### Environment Variables

- `ENVIRONMENT`: Deployment environment (dev, staging, prod)
- `CDK_DEFAULT_ACCOUNT`: AWS account ID (default: 224874703567)
- `CDK_DEFAULT_REGION`: AWS region (default: us-east-1)

### Tenant Configuration

Each tenant is configured in DynamoDB with:

```json
{
  "tenantId": "parchita-staging",
  "configType": "PRODUCT_CONFIG",
  "productType": "KONG_RFID",
  "clientAccount": "555569220783",
  "siesaConfig": {
    "baseUrl": "https://serviciosqa.siesacloud.com/api/siesa/v3/",
    "credentialsSecretArn": "..."
  },
  "productConfig": {
    "baseUrl": "https://api-staging.technoapes.io/",
    "credentialsSecretArn": "..."
  },
  "syncConfig": {
    "schedule": "rate(1 hour)",
    "batchSize": 100,
    "retryAttempts": 3
  }
}
```

## Infrastructure Components

### DynamoDB Tables
- **Config Table**: Tenant configurations and product settings
- **Sync State Table**: Synchronization status and progress
- **Audit Table**: Operation logs and audit trail

### S3 Buckets
- **Config Bucket**: Field mappings and configuration files

### Secrets Manager
- **Siesa Credentials**: Per-tenant Siesa API credentials
- **Kong Credentials**: Per-tenant Kong API credentials
- **WMS Credentials**: Per-tenant WMS API credentials

### IAM Roles
- **Lambda Execution Role**: Permissions for Lambda functions
- **Step Functions Role**: Permissions for workflow orchestration
- **EventBridge Role**: Permissions for scheduled executions

### CloudWatch
- **Log Groups**: Lambda and Step Functions logs
- **Metrics**: Custom metrics for monitoring
- **Alarms**: Failure and performance alerts

### SNS Topics
- **Alert Topic**: Notifications for failures and errors

## Monitoring

### CloudWatch Dashboards
- Execution success rate (per tenant)
- Average execution duration
- Records processed (time series)
- Lambda errors (by function)
- API call latency

### Alarms
- Sync failure rate > 10%
- Lambda errors > 5 in 5 minutes
- Step Function execution failed
- Sync duration > 30 minutes

## Security

- **IAM Roles**: Least privilege access
- **Secrets Manager**: Secure credential storage
- **Encryption**: At rest (DynamoDB, S3) and in transit (TLS)
- **VPC**: Optional VPC deployment for Lambda functions
- **Code Analysis**: Automated security scanning with Bandit, pip-audit
- **Quality Gates**: Pre-deploy checks prevent vulnerable code deployment

### Security Analysis

```powershell
# Ejecutar análisis de seguridad
.\scripts\run-pre-deploy-checks.ps1

# Ver reporte de seguridad
cat pre-deploy-reports/bandit-report.txt
```

Ver: [PRE-DEPLOY-ANALYSIS-GUIDE.md](PRE-DEPLOY-ANALYSIS-GUIDE.md)

## Testing

```bash
# Run unit tests
npm test

# Run integration tests (to be implemented)
npm run test:integration

# Run end-to-end tests (to be implemented)
npm run test:e2e
```

## Troubleshooting

### Common Issues

1. **CDK Bootstrap**: Ensure CDK is bootstrapped in account 224874703567
2. **Permissions**: Check IAM permissions for deployment
3. **Credentials**: Verify AWS credentials are configured
4. **Region**: Ensure correct AWS region is set (us-east-1)

### Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/siesa-integration-dev --follow

# View Step Functions logs
aws logs tail /aws/stepfunctions/siesa-integration-dev --follow
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For support, contact the APES Integration Team.

## Next Steps

After infrastructure deployment (Task 1):
- Task 2: Implement Lambda functions (Extractor, Transformer, Loader)
- Task 3: Create Step Functions workflow
- Task 4: Configure field mappings
- Task 5: Set up monitoring and alerts
- Task 6: Deploy and test with Kong staging

## Documentation

- [AWS Accounts Architecture](../../integrations/siesa-integration/AWS-ACCOUNTS-ARCHITECTURE.md)
- [Kong API Documentation](../../integrations/siesa-integration/KONG-API-DOCUMENTATION.md)
- [Field Mappings](../../integrations/siesa-integration/FIELD-MAPPINGS-CONSOLIDATED.md)
- [Requirements](../../.kiro/specs/siesa-integration-week1/requirements.md)
- [Design](../../.kiro/specs/siesa-integration-week1/design.md)
- [Tasks](../../.kiro/specs/siesa-integration-week1/tasks.md)
