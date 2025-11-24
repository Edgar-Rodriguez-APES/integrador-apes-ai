"""
Extractor Lambda Function
Extracts product data from Siesa ERP API
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import security utilities
from common.input_validation import (
    sanitize_dict, sanitize_log_message, sanitize_dynamodb_key,
    sanitize_filter_expression, validate_product_data
)
from common.logging_utils import get_safe_logger

# Configure logging
logger = get_safe_logger(__name__)

# AWS clients
dynamodb = boto3.resource('dynamodb')
secrets_manager = boto3.client('secretsmanager')

# Environment variables
CLIENTS_TABLE = os.environ.get('CLIENTS_TABLE', 'siesa-integration-config-dev')


class SiesaAPIClient:
    """Client for Siesa ERP API"""
    
    def __init__(self, base_url: str, credentials: Dict[str, str]):
        self.base_url = base_url.rstrip('/')
        self.credentials = credentials
        self.session = self._create_session()
        self.token = None
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def authenticate(self) -> bool:
        """Authenticate with Siesa API with improved validation"""
        try:
            # Siesa uses Bearer token + ConniKey + ConniToken
            auth_url = f"{self.base_url}/auth/login"
            
            payload = {
                "username": self.credentials.get('username'),
                "password": self.credentials.get('password')
            }
            
            headers = {
                "Content-Type": "application/json",
                "ConniKey": self.credentials.get('conniKey', ''),
                "ConniToken": self.credentials.get('conniToken', '')
            }
            
            response = self.session.post(auth_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.token = data.get('token') or data.get('access_token')
            
            # CRITICAL: Validate token was received
            if not self.token:
                logger.error(f"Authentication response missing token. Response keys: {list(data.keys())}")
                raise ValueError(
                    "Authentication succeeded but no token received. "
                    "Check Siesa API response format."
                )
            
            # Validate token format (basic check)
            if not isinstance(self.token, str) or len(self.token) < 10:
                logger.error(f"Invalid token format received: {type(self.token).__name__}")
                raise ValueError("Invalid token format received from Siesa API")
            
            logger.info("Successfully authenticated with Siesa API")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication request failed: {sanitize_log_message(str(e))}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Authentication validation failed: {sanitize_log_message(str(e))}")
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {sanitize_log_message(str(e))}")
            raise
    
    def get_products(self, page: int = 1, page_size: int = 100, modified_since: Optional[str] = None) -> Dict[str, Any]:
        """
        Get products from Siesa API with pagination and security improvements
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of records per page
            modified_since: ISO timestamp for incremental sync
        
        Returns:
            Dict with products and pagination info
        """
        try:
            # Siesa pagination format: paginacion=numPag=1|tamPag=100
            pagination_param = f"numPag={page}|tamPag={page_size}"
            
            url = f"{self.base_url}/inventarios/productos"
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "ConniKey": self.credentials.get('conniKey', ''),
                "ConniToken": self.credentials.get('conniToken', '')
            }
            
            params = {
                "paginacion": pagination_param
            }
            
            # Add incremental sync filter if provided (with sanitization)
            if modified_since:
                # Sanitize filter expression to prevent injection
                try:
                    filter_expr = f"fechaModificacion>={modified_since}"
                    sanitized_filter = sanitize_filter_expression(filter_expr)
                    params['fechaModificacion'] = modified_since
                except ValueError as e:
                    logger.error(f"Invalid filter expression: {sanitize_log_message(str(e))}")
                    # Continue without filter rather than fail
            
            response = self.session.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            
            # Sanitize response data
            data = sanitize_dict(response.json())
            
            # Extract products and pagination info
            products = data.get('data', []) or data.get('productos', []) or data.get('items', [])
            
            # Validate response structure
            if not isinstance(products, list):
                logger.warning(f"Unexpected response structure from Siesa API: {type(products).__name__}")
                products = []
            
            # Validate and sanitize each product
            validated_products = []
            for i, product in enumerate(products):
                try:
                    validated_product = validate_product_data(product)
                    validated_products.append(validated_product)
                except ValueError as e:
                    logger.warning(f"Product {i} validation failed: {sanitize_log_message(str(e))}, skipping")
                    continue
            
            pagination_info = {
                'current_page': page,
                'page_size': page_size,
                'total_records': data.get('totalRegistros', len(validated_products)),
                'has_more': len(validated_products) == page_size
            }
            
            logger.info(f"Retrieved and validated {len(validated_products)} products from page {page}")
            
            return {
                'products': validated_products,
                'pagination': pagination_info
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed for page {page}: {sanitize_log_message(str(e))}")
            raise
        except Exception as e:
            logger.error(f"Failed to get products from Siesa API: {sanitize_log_message(str(e))}")
            raise


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
        
        # Check if client is enabled
        if not config.get('enabled', 'false') == 'true':
            raise ValueError(f"Client is disabled: {sanitize_log_message(client_id)}")
        
        logger.info(f"Retrieved configuration for client: {sanitize_log_message(client_id)}")
        return config
        
    except ClientError as e:
        logger.error(f"DynamoDB error: {sanitize_log_message(str(e))}")
        raise
    except ValueError as e:
        logger.error(f"Input validation error: {sanitize_log_message(str(e))}")
        raise
    except Exception as e:
        logger.error(f"Failed to get client config: {sanitize_log_message(str(e))}")
        raise


def get_siesa_credentials(secret_arn: str) -> Dict[str, str]:
    """
    Retrieve Siesa credentials from Secrets Manager
    
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
        
        logger.info(f"Retrieved Siesa credentials from: {secret_arn}")
        return credentials
        
    except ClientError as e:
        logger.error(f"Secrets Manager error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to get Siesa credentials: {str(e)}")
        raise


def extract_all_products(client: SiesaAPIClient, sync_type: str, last_sync_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Extract all products with pagination
    
    Args:
        client: Siesa API client
        sync_type: 'initial' or 'incremental'
        last_sync_timestamp: Last sync timestamp for incremental sync
    
    Returns:
        List of all products
    """
    all_products = []
    page = 1
    page_size = 100
    
    # For incremental sync, use last sync timestamp
    modified_since = last_sync_timestamp if sync_type == 'incremental' else None
    
    while True:
        try:
            result = client.get_products(page=page, page_size=page_size, modified_since=modified_since)
            
            products = result['products']
            pagination = result['pagination']
            
            all_products.extend(products)
            
            logger.info(f"Page {page}: Retrieved {len(products)} products. Total so far: {len(all_products)}")
            
            # Check if there are more pages
            if not pagination['has_more']:
                break
            
            page += 1
            
            # Safety limit to prevent infinite loops
            if page > 1000:
                logger.warning("Reached maximum page limit (1000). Stopping pagination.")
                break
                
        except Exception as e:
            logger.error(f"Error on page {page}: {str(e)}")
            raise
    
    logger.info(f"Extraction complete. Total products: {len(all_products)}")
    return all_products


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Extractor function with security improvements
    
    Args:
        event: Lambda event with client_id and sync_type
        context: Lambda context
    
    Returns:
        Dict with extracted products and metadata
    """
    try:
        # Sanitize input event
        event = sanitize_dict(event)
        
        # Extract parameters from event
        client_id = event.get('client_id') or event.get('tenantId')
        sync_type = event.get('sync_type', 'incremental')
        
        if not client_id:
            raise ValueError("Missing required parameter: client_id")
        
        logger.info(f"Starting extraction for client: {sanitize_log_message(client_id)}, sync_type: {sync_type}")
        
        # Get client configuration
        config = get_client_config(client_id)
        
        # Get Siesa configuration
        siesa_config = config.get('siesaConfig', {})
        base_url = siesa_config.get('baseUrl')
        credentials_secret = siesa_config.get('credentialsSecretArn')
        
        if not base_url or not credentials_secret:
            raise ValueError(f"Invalid Siesa configuration for client: {sanitize_log_message(client_id)}")
        
        # Get Siesa credentials
        credentials = get_siesa_credentials(credentials_secret)
        
        # Create Siesa API client
        siesa_client = SiesaAPIClient(base_url, credentials)
        
        # Authenticate
        siesa_client.authenticate()
        
        # Get last sync timestamp for incremental sync
        last_sync_timestamp = config.get('lastSyncTimestamp') if sync_type == 'incremental' else None
        
        # Extract products
        products = extract_all_products(siesa_client, sync_type, last_sync_timestamp)
        
        # Prepare response (format for Step Functions)
        extraction_timestamp = datetime.now(timezone.utc).isoformat()
        product_type = config.get('productType', 'kong')
        
        response = {
            'client_id': client_id,
            'product_type': product_type,
            'products': products,
            'count': len(products),
            'sync_type': sync_type,
            'extraction_timestamp': extraction_timestamp
        }
        
        logger.info(f"Extraction completed successfully. Products: {len(products)}")
        
        return response
        
    except Exception as e:
        logger.error(f"Extraction failed: {sanitize_log_message(str(e))}", exc_info=True)
        
        # Re-raise the exception so Step Functions can catch it
        raise Exception(f"Extractor Lambda failed: {sanitize_log_message(str(e))}")
