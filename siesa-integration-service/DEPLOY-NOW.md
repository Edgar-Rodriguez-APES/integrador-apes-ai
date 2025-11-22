# 🚀 Instrucciones de Despliegue - Task 1

## ✅ Estado Actual

**Task 1 está lista para desplegar**. Todos los archivos están creados y el código compiló exitosamente.

### Lo que ya está hecho:
- ✅ Código CDK creado y compilado
- ✅ Template CloudFormation sintetizado y validado
- ✅ Dependencias instaladas (530 packages)
- ✅ Sin errores de compilación
- ✅ 16 recursos AWS listos para crear

---

## ⚠️ Acción Requerida: Configurar Credenciales AWS

Antes de desplegar, necesitas configurar el acceso a la cuenta AWS **224874703567**.

### Opción 1: AWS SSO (Recomendado)

Si usas AWS SSO, renueva tu sesión:

```bash
aws sso login --profile apes-principal
```

### Opción 2: Credenciales IAM

Si usas credenciales IAM directas:

```bash
aws configure --profile apes-principal
# AWS Access Key ID: [TU_ACCESS_KEY]
# AWS Secret Access Key: [TU_SECRET_KEY]
# Default region name: us-east-1
# Default output format: json
```

### Verificar Acceso

```bash
aws sts get-caller-identity --profile apes-principal
```

Deberías ver:
```json
{
    "UserId": "...",
    "Account": "224874703567",
    "Arn": "..."
}
```

---

## 🚀 Pasos de Despliegue

### 1. Bootstrap CDK (Solo Primera Vez)

Si nunca has usado CDK en la cuenta 224874703567:

```bash
cd siesa-integration-service
set AWS_PROFILE=apes-principal
set CDK_DEFAULT_ACCOUNT=224874703567
set CDK_DEFAULT_REGION=us-east-1

cdk bootstrap aws://224874703567/us-east-1
```

**Nota**: Este paso solo se hace una vez por cuenta/región.

### 2. Desplegar Infraestructura

```bash
cd siesa-integration-service
set AWS_PROFILE=apes-principal
set ENVIRONMENT=dev

npm run deploy
```

O si prefieres aprobar manualmente cada cambio:

```bash
npm run deploy -- --require-approval never
```

### 3. Verificar Despliegue

Después del despliegue exitoso, verás:

```
✅  SiesaIntegrationStack-dev

Outputs:
SiesaIntegrationStack-dev.ConfigTableName = siesa-integration-config-dev
SiesaIntegrationStack-dev.SyncStateTableName = siesa-integration-sync-state-dev
SiesaIntegrationStack-dev.AuditTableName = siesa-integration-audit-dev
SiesaIntegrationStack-dev.ConfigBucketName = siesa-integration-config-dev-224874703567
SiesaIntegrationStack-dev.AlertTopicArn = arn:aws:sns:us-east-1:224874703567:siesa-integration-alerts-dev
SiesaIntegrationStack-dev.LambdaExecutionRoleArn = arn:aws:iam::224874703567:role/siesa-integration-lambda-role-dev
SiesaIntegrationStack-dev.StepFunctionsRoleArn = arn:aws:iam::224874703567:role/siesa-integration-stepfunctions-role-dev
SiesaIntegrationStack-dev.EventBridgeRoleArn = arn:aws:iam::224874703567:role/siesa-integration-eventbridge-role-dev

Stack ARN:
arn:aws:cloudformation:us-east-1:224874703567:stack/SiesaIntegrationStack-dev/...
```

---

## 🔍 Verificación Post-Despliegue

### Verificar Recursos en AWS Console

1. **DynamoDB Tables**:
   - https://console.aws.amazon.com/dynamodbv2/home?region=us-east-1#tables
   - Buscar: `siesa-integration-config-dev`

2. **S3 Bucket**:
   - https://console.aws.amazon.com/s3/home?region=us-east-1
   - Buscar: `siesa-integration-config-dev-224874703567`

3. **Secrets Manager**:
   - https://console.aws.amazon.com/secretsmanager/home?region=us-east-1
   - Buscar: `siesa-integration/template/`

4. **IAM Roles**:
   - https://console.aws.amazon.com/iam/home#/roles
   - Buscar: `siesa-integration-lambda-role-dev`

5. **SNS Topics**:
   - https://console.aws.amazon.com/sns/v3/home?region=us-east-1#/topics
   - Buscar: `siesa-integration-alerts-dev`

### Verificar con AWS CLI

```bash
# DynamoDB Tables
aws dynamodb list-tables --profile apes-principal | findstr siesa-integration

# S3 Buckets
aws s3 ls --profile apes-principal | findstr siesa-integration

# Secrets Manager
aws secretsmanager list-secrets --profile apes-principal | findstr siesa-integration

# IAM Roles
aws iam list-roles --profile apes-principal | findstr siesa-integration

# SNS Topics
aws sns list-topics --profile apes-principal | findstr siesa-integration

# CloudWatch Log Groups
aws logs describe-log-groups --profile apes-principal --log-group-name-prefix /aws/lambda/siesa-integration
```

---

## 📊 Recursos Creados

### DynamoDB Tables (3)

1. **siesa-integration-config-dev**
   - Purpose: Tenant configurations
   - Partition Key: tenantId
   - Sort Key: configType
   - GSI: ProductTypeIndex, EnabledIndex
   - Billing: On-Demand
   - Encryption: AWS Managed

2. **siesa-integration-sync-state-dev**
   - Purpose: Sync status tracking
   - Partition Key: tenantId
   - Sort Key: syncId
   - GSI: StatusIndex
   - TTL: Enabled
   - Billing: On-Demand

3. **siesa-integration-audit-dev**
   - Purpose: Audit trail
   - Partition Key: tenantId
   - Sort Key: timestamp
   - TTL: Enabled
   - Billing: On-Demand

### S3 Bucket (1)

**siesa-integration-config-dev-224874703567**
- Purpose: Field mappings and configuration files
- Versioning: Enabled
- Encryption: S3 Managed (AES256)
- Public Access: Blocked
- Lifecycle: Delete old versions after 30 days

### Secrets Manager (2)

1. **siesa-integration/template/siesa-dev**
   - Template for Siesa credentials
   - Contains: baseUrl, username, password, conniKey, conniToken

2. **siesa-integration/template/kong-dev**
   - Template for Kong credentials
   - Contains: productType, baseUrl, username, password

### IAM Roles (3)

1. **siesa-integration-lambda-role-dev**
   - For: Lambda functions
   - Permissions: DynamoDB, Secrets Manager, S3, Step Functions, CloudWatch

2. **siesa-integration-stepfunctions-role-dev**
   - For: Step Functions workflows
   - Permissions: Lambda invoke, DynamoDB, SNS

3. **siesa-integration-eventbridge-role-dev**
   - For: EventBridge scheduled rules
   - Permissions: Step Functions start execution

### CloudWatch Log Groups (2)

1. **/aws/lambda/siesa-integration-dev**
   - Retention: 7 days (dev)
   - Encryption: Default

2. **/aws/stepfunctions/siesa-integration-dev**
   - Retention: 7 days (dev)
   - Encryption: Default

### SNS Topic (1)

**siesa-integration-alerts-dev**
- Purpose: Failure notifications
- Type: Standard (not FIFO)
- Subscriptions: None (add manually)

---

## 💰 Costo Estimado

### Costo Mensual (Ambiente Dev - Uso Mínimo)

| Servicio | Costo Estimado |
|----------|----------------|
| DynamoDB (3 tables, on-demand) | ~$1.00 |
| S3 (minimal storage) | ~$0.50 |
| Secrets Manager (2 secrets) | ~$1.00 |
| CloudWatch Logs (minimal) | ~$1.00 |
| SNS (minimal notifications) | ~$0.10 |
| **Total** | **~$3.60/month** |

**Nota**: Lambda y Step Functions se agregarán en Task 2-3.

---

## 🔧 Troubleshooting

### Error: "Stack already exists"

Si el stack ya existe:

```bash
# Ver diferencias
npm run diff

# Actualizar stack existente
npm run deploy

# O destruir y recrear
npm run destroy
npm run deploy
```

### Error: "Insufficient permissions"

Verifica que tu usuario/role tenga permisos para:
- CloudFormation (CreateStack, UpdateStack)
- DynamoDB (CreateTable)
- S3 (CreateBucket)
- IAM (CreateRole, AttachRolePolicy)
- Secrets Manager (CreateSecret)
- SNS (CreateTopic)
- CloudWatch Logs (CreateLogGroup)

### Error: "CDK not bootstrapped"

```bash
cdk bootstrap aws://224874703567/us-east-1 --profile apes-principal
```

### Error: "Token has expired"

Renueva tu sesión AWS:

```bash
aws sso login --profile apes-principal
```

---

## ✅ Checklist de Despliegue

- [ ] Credenciales AWS configuradas
- [ ] Acceso verificado a cuenta 224874703567
- [ ] CDK bootstrapped (primera vez)
- [ ] `npm install` ejecutado
- [ ] `npm run build` exitoso
- [ ] `npm run synth` exitoso
- [ ] `npm run deploy` ejecutado
- [ ] Recursos verificados en AWS Console
- [ ] Outputs del stack guardados

---

## 📝 Próximos Pasos Después del Despliegue

1. **Subir field mappings a S3**:
   ```bash
   aws s3 cp field-mappings-kong.json s3://siesa-integration-config-dev-224874703567/ --profile apes-principal
   ```

2. **Crear configuración de tenant de prueba** en DynamoDB

3. **Almacenar credenciales reales** en Secrets Manager

4. **Continuar con Task 2**: Implementar Lambda functions

---

## 🆘 Soporte

Si encuentras problemas:

1. Revisa los logs de CloudFormation en AWS Console
2. Ejecuta `npm run synth` para ver el template generado
3. Verifica permisos IAM
4. Consulta `DEPLOYMENT-GUIDE.md` para más detalles

---

**Fecha**: 2025-01-21  
**Task**: 1 - AWS Infrastructure Foundation  
**Estado**: ✅ Listo para desplegar  
**Cuenta AWS**: 224874703567  
**Región**: us-east-1  
**Ambiente**: dev
