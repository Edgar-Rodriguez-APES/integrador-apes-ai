import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';

export interface SiesaIntegrationStackProps extends cdk.StackProps {
  environment: string;
}

export class SiesaIntegrationStack extends cdk.Stack {
  public readonly configTable: dynamodb.Table;
  public readonly syncStateTable: dynamodb.Table;
  public readonly auditTable: dynamodb.Table;
  public readonly configBucket: s3.Bucket;
  public readonly alertTopic: sns.Topic;
  public readonly lambdaExecutionRole: iam.Role;
  
  constructor(scope: Construct, id: string, props: SiesaIntegrationStackProps) {
    super(scope, id, props);

    const { environment } = props;

    // ===========================================
    // 1. DynamoDB Tables
    // ===========================================
    
    // Configuration table for tenant and product settings
    this.configTable = new dynamodb.Table(this, 'ConfigTable', {
      tableName: `siesa-integration-config-${environment}`,
      partitionKey: {
        name: 'tenantId',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'configType',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
    });

    // Add GSI for product type queries
    this.configTable.addGlobalSecondaryIndex({
      indexName: 'ProductTypeIndex',
      partitionKey: {
        name: 'productType',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'tenantId',
        type: dynamodb.AttributeType.STRING
      }
    });

    // Add GSI for enabled status queries
    this.configTable.addGlobalSecondaryIndex({
      indexName: 'EnabledIndex',
      partitionKey: {
        name: 'enabled',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'tenantId',
        type: dynamodb.AttributeType.STRING
      }
    });

    // Sync state table for tracking synchronization status
    this.syncStateTable = new dynamodb.Table(this, 'SyncStateTable', {
      tableName: `siesa-integration-sync-state-${environment}`,
      partitionKey: {
        name: 'tenantId',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'syncId',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      timeToLiveAttribute: 'ttl',
      removalPolicy: cdk.RemovalPolicy.RETAIN
    });

    // Add GSI for status queries
    this.syncStateTable.addGlobalSecondaryIndex({
      indexName: 'StatusIndex',
      partitionKey: {
        name: 'status',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'createdAt',
        type: dynamodb.AttributeType.STRING
      }
    });

    // Audit table for tracking all operations
    this.auditTable = new dynamodb.Table(this, 'AuditTable', {
      tableName: `siesa-integration-audit-${environment}`,
      partitionKey: {
        name: 'tenantId',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'timestamp',
        type: dynamodb.AttributeType.STRING
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      timeToLiveAttribute: 'ttl',
      removalPolicy: cdk.RemovalPolicy.RETAIN
    });

    // ===========================================
    // 2. S3 Bucket for Configuration Files
    // ===========================================
    
    this.configBucket = new s3.Bucket(this, 'ConfigBucket', {
      bucketName: `siesa-integration-config-${environment}-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      lifecycleRules: [
        {
          id: 'DeleteOldVersions',
          enabled: true,
          noncurrentVersionExpiration: cdk.Duration.days(30)
        }
      ],
      removalPolicy: cdk.RemovalPolicy.RETAIN
    });

    // ===========================================
    // 3. Secrets Manager for API Credentials
    // ===========================================
    
    // Create placeholder secrets (actual values will be added manually)
    const siesaCredentialsTemplate = new secretsmanager.Secret(this, 'SiesaCredentialsTemplate', {
      secretName: `siesa-integration/template/siesa-${environment}`,
      description: 'Template for Siesa ERP API credentials',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          baseUrl: 'https://serviciosqa.siesacloud.com/api/siesa/v3/',
          username: 'REPLACE_WITH_ACTUAL_USERNAME',
          password: 'REPLACE_WITH_ACTUAL_PASSWORD',
          conniKey: 'REPLACE_WITH_ACTUAL_CONNI_KEY',
          conniToken: 'REPLACE_WITH_ACTUAL_CONNI_TOKEN'
        }),
        generateStringKey: 'apiKey',
        excludeCharacters: '"@/\\\\'
      }
    });

    const kongCredentialsTemplate = new secretsmanager.Secret(this, 'KongCredentialsTemplate', {
      secretName: `siesa-integration/template/kong-${environment}`,
      description: 'Template for Kong RFID API credentials',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          productType: 'kong',
          baseUrl: 'https://api-staging.technoapes.io/',
          username: 'REPLACE_WITH_ACTUAL_USERNAME',
          password: 'REPLACE_WITH_ACTUAL_PASSWORD'
        }),
        generateStringKey: 'token',
        excludeCharacters: '"@/\\\\'
      }
    });

    // ===========================================
    // 4. SNS Topic for Alerts
    // ===========================================
    
    this.alertTopic = new sns.Topic(this, 'AlertTopic', {
      topicName: `siesa-integration-alerts-${environment}`,
      displayName: 'Siesa Integration Alerts',
      fifo: false
    });

    // Add email subscription (replace with actual email)
    // this.alertTopic.addSubscription(
    //   new subscriptions.EmailSubscription('ops-team@empresa.com')
    // );

    // ===========================================
    // 5. IAM Roles and Policies
    // ===========================================
    
    // Lambda execution role
    this.lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
      roleName: `siesa-integration-lambda-role-${environment}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaVPCAccessExecutionRole')
      ]
    });

    // Add permissions for DynamoDB
    this.lambdaExecutionRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
        'dynamodb:Query',
        'dynamodb:Scan',
        'dynamodb:BatchGetItem',
        'dynamodb:BatchWriteItem'
      ],
      resources: [
        this.configTable.tableArn,
        this.syncStateTable.tableArn,
        this.auditTable.tableArn,
        `${this.configTable.tableArn}/index/*`,
        `${this.syncStateTable.tableArn}/index/*`
      ]
    }));

    // Add permissions for Secrets Manager
    this.lambdaExecutionRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'secretsmanager:GetSecretValue',
        'secretsmanager:DescribeSecret'
      ],
      resources: [
        `arn:aws:secretsmanager:${this.region}:${this.account}:secret:siesa-integration/*`
      ]
    }));

    // Add permissions for S3
    this.lambdaExecutionRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        's3:GetObject',
        's3:PutObject',
        's3:DeleteObject',
        's3:ListBucket'
      ],
      resources: [
        this.configBucket.bucketArn,
        `${this.configBucket.bucketArn}/*`
      ]
    }));

    // Add permissions for Step Functions
    this.lambdaExecutionRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'states:StartExecution',
        'states:DescribeExecution',
        'states:StopExecution'
      ],
      resources: [`arn:aws:states:${this.region}:${this.account}:stateMachine:*`]
    }));

    // Step Functions execution role
    const stepFunctionsRole = new iam.Role(this, 'StepFunctionsRole', {
      roleName: `siesa-integration-stepfunctions-role-${environment}`,
      assumedBy: new iam.ServicePrincipal('states.amazonaws.com')
    });

    // Add permissions for Lambda invocation
    stepFunctionsRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['lambda:InvokeFunction'],
      resources: [`arn:aws:lambda:${this.region}:${this.account}:function:siesa-integration-*`]
    }));

    // Add permissions for DynamoDB
    stepFunctionsRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['dynamodb:UpdateItem', 'dynamodb:PutItem'],
      resources: [this.configTable.tableArn, this.syncStateTable.tableArn]
    }));

    // Add permissions for SNS
    stepFunctionsRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['sns:Publish'],
      resources: [this.alertTopic.topicArn]
    }));

    // EventBridge execution role
    const eventBridgeRole = new iam.Role(this, 'EventBridgeRole', {
      roleName: `siesa-integration-eventbridge-role-${environment}`,
      assumedBy: new iam.ServicePrincipal('events.amazonaws.com')
    });

    eventBridgeRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['states:StartExecution'],
      resources: [`arn:aws:states:${this.region}:${this.account}:stateMachine:*`]
    }));

    // ===========================================
    // 6. KMS Key for CloudWatch Logs Encryption
    // ===========================================
    
    const logsKmsKey = new kms.Key(this, 'LogsKmsKey', {
      alias: `siesa-integration-logs-${environment}`,
      description: 'KMS key for encrypting CloudWatch Logs',
      enableKeyRotation: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN
    });

    // Grant CloudWatch Logs permission to use the key
    logsKmsKey.addToResourcePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      principals: [new iam.ServicePrincipal(`logs.${this.region}.amazonaws.com`)],
      actions: [
        'kms:Encrypt',
        'kms:Decrypt',
        'kms:ReEncrypt*',
        'kms:GenerateDataKey*',
        'kms:CreateGrant',
        'kms:DescribeKey'
      ],
      resources: ['*'],
      conditions: {
        ArnLike: {
          'kms:EncryptionContext:aws:logs:arn': `arn:aws:logs:${this.region}:${this.account}:log-group:/aws/lambda/siesa-integration-*`
        }
      }
    }));

    // ===========================================
    // 7. CloudWatch Log Groups (Per Lambda Function)
    // ===========================================
    
    // Extractor Lambda Log Group
    const extractorLogGroup = new logs.LogGroup(this, 'ExtractorLogGroup', {
      logGroupName: `/aws/lambda/siesa-integration-extractor-${environment}`,
      retention: environment === 'prod' ? logs.RetentionDays.ONE_MONTH : logs.RetentionDays.ONE_WEEK,
      encryptionKey: logsKmsKey,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // Transformer Lambda Log Group
    const transformerLogGroup = new logs.LogGroup(this, 'TransformerLogGroup', {
      logGroupName: `/aws/lambda/siesa-integration-transformer-${environment}`,
      retention: environment === 'prod' ? logs.RetentionDays.ONE_MONTH : logs.RetentionDays.ONE_WEEK,
      encryptionKey: logsKmsKey,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // Loader Lambda Log Group
    const loaderLogGroup = new logs.LogGroup(this, 'LoaderLogGroup', {
      logGroupName: `/aws/lambda/siesa-integration-loader-${environment}`,
      retention: environment === 'prod' ? logs.RetentionDays.ONE_MONTH : logs.RetentionDays.ONE_WEEK,
      encryptionKey: logsKmsKey,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // Step Functions Log Group
    const stepFunctionsLogGroup = new logs.LogGroup(this, 'StepFunctionsLogGroup', {
      logGroupName: `/aws/stepfunctions/siesa-integration-workflow-${environment}`,
      retention: environment === 'prod' ? logs.RetentionDays.ONE_MONTH : logs.RetentionDays.ONE_WEEK,
      encryptionKey: logsKmsKey,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // API Gateway Log Group (for future use)
    const apiGatewayLogGroup = new logs.LogGroup(this, 'ApiGatewayLogGroup', {
      logGroupName: `/aws/apigateway/siesa-integration-${environment}`,
      retention: environment === 'prod' ? logs.RetentionDays.ONE_MONTH : logs.RetentionDays.ONE_WEEK,
      encryptionKey: logsKmsKey,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // ===========================================
    // 8. Stack Outputs
    // ===========================================
    
    new cdk.CfnOutput(this, 'ConfigTableName', {
      value: this.configTable.tableName,
      description: 'Configuration DynamoDB table name',
      exportName: `SiesaIntegration-ConfigTable-${environment}`
    });

    new cdk.CfnOutput(this, 'SyncStateTableName', {
      value: this.syncStateTable.tableName,
      description: 'Sync state DynamoDB table name',
      exportName: `SiesaIntegration-SyncStateTable-${environment}`
    });

    new cdk.CfnOutput(this, 'AuditTableName', {
      value: this.auditTable.tableName,
      description: 'Audit DynamoDB table name',
      exportName: `SiesaIntegration-AuditTable-${environment}`
    });

    new cdk.CfnOutput(this, 'ConfigBucketName', {
      value: this.configBucket.bucketName,
      description: 'Configuration S3 bucket name',
      exportName: `SiesaIntegration-ConfigBucket-${environment}`
    });

    new cdk.CfnOutput(this, 'AlertTopicArn', {
      value: this.alertTopic.topicArn,
      description: 'SNS Alert Topic ARN',
      exportName: `SiesaIntegration-AlertTopic-${environment}`
    });

    new cdk.CfnOutput(this, 'LambdaExecutionRoleArn', {
      value: this.lambdaExecutionRole.roleArn,
      description: 'Lambda execution role ARN',
      exportName: `SiesaIntegration-LambdaRole-${environment}`
    });

    new cdk.CfnOutput(this, 'StepFunctionsRoleArn', {
      value: stepFunctionsRole.roleArn,
      description: 'Step Functions execution role ARN',
      exportName: `SiesaIntegration-StepFunctionsRole-${environment}`
    });

    new cdk.CfnOutput(this, 'EventBridgeRoleArn', {
      value: eventBridgeRole.roleArn,
      description: 'EventBridge execution role ARN',
      exportName: `SiesaIntegration-EventBridgeRole-${environment}`
    });

    new cdk.CfnOutput(this, 'LogsKmsKeyArn', {
      value: logsKmsKey.keyArn,
      description: 'KMS key ARN for CloudWatch Logs encryption',
      exportName: `SiesaIntegration-LogsKmsKey-${environment}`
    });

    new cdk.CfnOutput(this, 'ExtractorLogGroupName', {
      value: extractorLogGroup.logGroupName,
      description: 'Extractor Lambda log group name',
      exportName: `SiesaIntegration-ExtractorLogGroup-${environment}`
    });

    new cdk.CfnOutput(this, 'TransformerLogGroupName', {
      value: transformerLogGroup.logGroupName,
      description: 'Transformer Lambda log group name',
      exportName: `SiesaIntegration-TransformerLogGroup-${environment}`
    });

    new cdk.CfnOutput(this, 'LoaderLogGroupName', {
      value: loaderLogGroup.logGroupName,
      description: 'Loader Lambda log group name',
      exportName: `SiesaIntegration-LoaderLogGroup-${environment}`
    });

    // ===========================================
    // 9. Tags
    // ===========================================
    
    cdk.Tags.of(this).add('Project', 'SiesaIntegration');
    cdk.Tags.of(this).add('Environment', environment);
    cdk.Tags.of(this).add('Owner', 'APES-Team');
    cdk.Tags.of(this).add('CostCenter', 'Integration');
    cdk.Tags.of(this).add('Purpose', 'ERP-Integration');
    cdk.Tags.of(this).add('ManagedBy', 'CDK');
  }
}
