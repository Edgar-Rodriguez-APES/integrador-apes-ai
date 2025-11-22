"""
Common AWS utilities for Lambda functions
"""

import json
import logging
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# AWS clients (initialized once per Lambda container)
_dynamodb = None
_secrets_manager = None
_s3 = None


def get_dynamodb_resource():
    """Get DynamoDB resource (singleton)"""
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource('dynamodb')
    return _dynamodb


def get_secrets_manager_client():
    """Get Secrets Manager client (singleton)"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = boto3.client('secretsmanager')
    return _secrets_manager


def get_s3_client():
    """Get S3 client (singleton)"""
    global _s3
    if _s3 is None:
        _s3 = boto3.client('s3')
    return _s3


def get_secret(secret_id: str) -> Dict[str, Any]:
    """
    Retrieve secret from AWS Secrets Manager
    
    Args:
        secret_id: Secret ARN or name
    
    Returns:
        Secret value as dict
    
    Raises:
        ClientError: If secret retrieval fails
    """
    try:
        client = get_secrets_manager_client()
        response = client.get_secret_value(SecretId=secret_id)
        
        secret_string = response.get('SecretString')
        if not secret_string:
            raise ValueError(f"Secret has no string value: {secret_id}")
        
        return json.loads(secret_string)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"Failed to retrieve secret {secret_id}: {error_code}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse secret {secret_id} as JSON: {str(e)}")
        raise


def get_dynamodb_item(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get item from DynamoDB table
    
    Args:
        table_name: DynamoDB table name
        key: Primary key dict
    
    Returns:
        Item dict
    
    Raises:
        ValueError: If item not found
        ClientError: If DynamoDB operation fails
    """
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(table_name)
        
        response = table.get_item(Key=key)
        
        if 'Item' not in response:
            raise ValueError(f"Item not found in {table_name}: {key}")
        
        return response['Item']
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"DynamoDB error on {table_name}: {error_code}")
        raise


def put_dynamodb_item(table_name: str, item: Dict[str, Any]) -> None:
    """
    Put item to DynamoDB table
    
    Args:
        table_name: DynamoDB table name
        item: Item dict to put
    
    Raises:
        ClientError: If DynamoDB operation fails
    """
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(table_name)
        
        table.put_item(Item=item)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"DynamoDB put error on {table_name}: {error_code}")
        raise


def update_dynamodb_item(table_name: str, key: Dict[str, Any], updates: Dict[str, Any]) -> None:
    """
    Update item in DynamoDB table
    
    Args:
        table_name: DynamoDB table name
        key: Primary key dict
        updates: Dict of attribute names to new values
    
    Raises:
        ClientError: If DynamoDB operation fails
    """
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(table_name)
        
        # Build update expression
        update_expr_parts = []
        expr_attr_names = {}
        expr_attr_values = {}
        
        for i, (attr_name, value) in enumerate(updates.items()):
            placeholder_name = f"#attr{i}"
            placeholder_value = f":val{i}"
            
            update_expr_parts.append(f"{placeholder_name} = {placeholder_value}")
            expr_attr_names[placeholder_name] = attr_name
            expr_attr_values[placeholder_value] = value
        
        update_expression = "SET " + ", ".join(update_expr_parts)
        
        table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"DynamoDB update error on {table_name}: {error_code}")
        raise


def get_s3_object(bucket: str, key: str) -> str:
    """
    Get object from S3
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
    
    Returns:
        Object content as string
    
    Raises:
        ClientError: If S3 operation fails
    """
    try:
        s3 = get_s3_client()
        response = s3.get_object(Bucket=bucket, Key=key)
        
        content = response['Body'].read().decode('utf-8')
        return content
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"S3 error getting {bucket}/{key}: {error_code}")
        raise


def put_s3_object(bucket: str, key: str, content: str) -> None:
    """
    Put object to S3
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        content: Object content as string
    
    Raises:
        ClientError: If S3 operation fails
    """
    try:
        s3 = get_s3_client()
        s3.put_object(Bucket=bucket, Key=key, Body=content.encode('utf-8'))
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"S3 error putting {bucket}/{key}: {error_code}")
        raise
