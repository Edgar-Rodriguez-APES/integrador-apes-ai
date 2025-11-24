"""
Loader Lambda Function
Loads transformed data to product APIs using Product Adapter Pattern
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any
import boto3
from botocore.exceptions import ClientError
from adapters import AdapterFactory

# Import security utilities
import sys
import os
# Add parent directory to path to import common module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.input_validation import sanitize_dict, sanitize_log_message, sanitize_dynamodb_key
from common.logging_utils import get_safe_logger

# Configure logging
logger = get_safe_logger(__name__)

# AWS clients
dynamodb = boto3.resource('dynamodb')
secrets_manager = boto3.client('secretsmanager')

# Environment variables
CLIENTS_TABLE = os.environ.get('CLIENTS_TABLE', 'siesa-integration-config-dev')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '100'))


def get_client_config(client_id: str) -> Dict[str, Any]:
    """
    Retrieve client configuration from DynamoDB with input sanitization
    
    Args:
        client_id: Client identifier
    
    Returns:
        Client configuration dict
    """
    try:
        # Sanitize client_id to prevent NoSQL injection
        sanitized_client_id = sanitize_dynamodb_key(client_id)
        
        table = dynamodb.Table(CLIENTS_TABLE)
        
        response = table.get_item(
            Key={
                'tenantId': sanitized_client_id,
                'configType': 'PRODUCT_CONFIG'
            }
        )
        
        if 'Item' not in response:
            raise ValueError(f"Client configuration not found for: {sanitize_log_message(client_id)}")
        
        config = response['Item']
        
        logger.info(f"Retrieved configuration for client: {sanitize_log_message(client_id)}")
        return config
        
    except ClientError as e:
        logger.error(f"DynamoDB error: {sanitize_log_message(str(e))}")
        raise
    except ValueError as e:
        logger.error(f"Input validation error: {sanitize_log_message(str(e))}")
        raise


def get_product_credentials(secret_arn: str) -> Dict[str, str]:
    """
    Retrieve product credentials from Secrets Manager
    
    Args:
        secret_arn: ARN or name of the secret
    
    Returns:
        Credentials dict
    """
    try:
        response = secrets_manager.get_secret_value(SecretId=secret_arn)
        
        secret_string = response.get('SecretString')
        if not secret_string:
            raise ValueError(f"Secret has no string value: {secret_arn}")
        
        credentials = json.loads(secret_string)
        
        logger.info(f"Retrieved product credentials from: {secret_arn}")
        return credentials
        
    except ClientError as e:
        logger.error(f"Secrets Manager error: {str(e)}")
        raise


def update_sync_status(client_id: str, status: str, records_success: int, records_failed: int) -> None:
    """
    Update sync status in DynamoDB with input sanitization
    
    Args:
        client_id: Client identifier
        status: Sync status ('success', 'partial', 'failed')
        records_success: Number of successful records
        records_failed: Number of failed records
    """
    try:
        # Sanitize inputs
        sanitized_client_id = sanitize_dynamodb_key(client_id)
        
        # Validate status values
        valid_statuses = ['success', 'partial', 'failed']
        if status not in valid_statuses:
            logger.warning(f"Invalid status value: {sanitize_log_message(status)}, defaulting to 'failed'")
            status = 'failed'
        
        table = dynamodb.Table(CLIENTS_TABLE)
        
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Use parameterized update to prevent injection
        table.update_item(
            Key={
                'tenantId': sanitized_client_id,
                'configType': 'PRODUCT_CONFIG'
            },
            UpdateExpression='SET lastSyncTimestamp = :timestamp, lastSyncStatus = :status, lastSyncRecords = :records',
            ExpressionAttributeValues={
                ':timestamp': timestamp,
                ':status': status,
                ':records': records_success
            }
        )
        
        logger.info(f"Updated sync status for client {sanitize_log_message(client_id)}: {status}")
        
    except ClientError as e:
        logger.error(f"Failed to update sync status: {sanitize_log_message(str(e))}")
        # Don't raise - this is not critical
    except ValueError as e:
        logger.error(f"Input validation error in update_sync_status: {sanitize_log_message(str(e))}")
        # Don't raise - this is not critical


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Loader function with security improvements
    
    Args:
        event: Lambda event with canonical products from Transformer
        context: Lambda context
    
    Returns:
        Dict with loading results and summary
    """
    try:
        # Sanitize input event
        event = sanitize_dict(event)
        
        # Extract parameters from event
        client_id = event.get('client_id') or event.get('tenantId')
        product_type = event.get('productType', 'KONG_RFID')
        canonical_products = event.get('canonical_products', [])
        transformation_timestamp = event.get('transformation_timestamp')
        
        if not client_id:
            raise ValueError("Missing required parameter: client_id")
        
        if not canonical_products:
            logger.warning(f"No products to load for client: {sanitize_log_message(client_id)}")
            return {
                'client_id': client_id,
                'tenantId': client_id,
                'productType': product_type,
                'status': 'success',
                'records_processed': 0,
                'records_success': 0,
                'records_failed': 0,
                'transformation_timestamp': transformation_timestamp,
                'load_timestamp': datetime.now(timezone.utc).isoformat(),
                'duration_seconds': 0
            }
        
        logger.info(f"Starting load for client: {sanitize_log_message(client_id)}, product_type: {product_type}, products: {len(canonical_products)}")
        
        start_time = datetime.now(timezone.utc)
        
        # Get client configuration
        config = get_client_config(client_id)
        
        # Get product configuration
        product_config = config.get('productConfig', {})
        credentials_secret = product_config.get('credentialsSecretArn')
        
        if not credentials_secret:
            raise ValueError(f"Invalid product configuration for client: {sanitize_log_message(client_id)}")
        
        # Get product credentials
        credentials = get_product_credentials(credentials_secret)
        
        # Create appropriate adapter using factory
        adapter = AdapterFactory.create_adapter(
            product_type=product_type,
            credentials=credentials,
            config=product_config
        )
        
        # Process products in batches
        results = adapter.process_batch(canonical_products, batch_size=BATCH_SIZE)
        
        # Calculate duration
        end_time = datetime.now(timezone.utc)
        duration_seconds = (end_time - start_time).total_seconds()
        
        # Determine overall status
        if results['total_failed'] == 0:
            status = 'success'
        elif results['total_success'] > 0:
            status = 'partial'
        else:
            status = 'failed'
        
        # Update sync status in DynamoDB
        update_sync_status(
            client_id=client_id,
            status=status,
            records_success=results['total_success'],
            records_failed=results['total_failed']
        )
        
        # Prepare response
        load_timestamp = datetime.now(timezone.utc).isoformat()
        
        response = {
            'client_id': client_id,
            'tenantId': client_id,
            'productType': product_type,
            'status': status,
            'records_processed': results['total_processed'],
            'records_success': results['total_success'],
            'records_failed': results['total_failed'],
            'validation_errors': results['validation_errors'],
            'batch_results': results['batch_results'],
            'transformation_timestamp': transformation_timestamp,
            'load_timestamp': load_timestamp,
            'duration_seconds': duration_seconds
        }
        
        logger.info(f"Load completed. Status: {status}, Success: {results['total_success']}, Failed: {results['total_failed']}, Duration: {duration_seconds}s")
        
        return response
        
    except Exception as e:
        logger.error(f"Load failed: {sanitize_log_message(str(e))}", exc_info=True)
        
        return {
            'client_id': event.get('client_id', 'unknown'),
            'tenantId': event.get('client_id', 'unknown'),
            'productType': event.get('productType', 'unknown'),
            'status': 'error',
            'error': sanitize_log_message(str(e)),
            'records_processed': 0,
            'records_success': 0,
            'records_failed': len(event.get('canonical_products', [])),
            'load_timestamp': datetime.now(timezone.utc).isoformat()
        }
