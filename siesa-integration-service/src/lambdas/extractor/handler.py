"""
Extractor Lambda Function
Extracts product data from Siesa ERP API
Adapted for Siesa Cloud v3 with ejecutarconsultaestandar
"""

import json
import os
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Import security utilities
from common.input_validation import (
    sanitize_dict, sanitize_log_message, sanitize_dynamodb_key
)
from common.logging_utils import get_safe_logger
from common.circuit_breaker import circuit_breaker
from common.rate_limiter import rate_limit
from common.metrics import get_metrics_publisher

# Configure logging
logger = get_safe_logger(__name__)

# AWS clients
dynamodb = boto3.resource('dynamodb')
secrets_manager = boto3.client('secretsmanager')

# Environment variables
CLIENTS_TABLE = os.environ.get('DYNAMODB_TABLE', 'clients-config-staging')


class SiesaAPIClient:
    """Client for Siesa ERP API v3 (Cloud)"""
    
    def __init__(self, base_url: str, credentials: Dict[str, str], id_compania: str, consulta_api: str):
        self.base_url = base_url.rstrip('/')
        self.credentials = credentials
        self.id_compania = id_compania
        self.consulta_api = consulta_api
        self.session = self._create_session()
    
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
    
    def _get_headers(self) -> Dict[str, str]:
        """Get standard headers for Siesa API with ConniKey and ConniToken"""
        return {
            "Content-Type": "application/json",
            "ConniKey": self.credentials.get('conniKey', ''),
            "ConniToken": self.credentials.get('conniToken', '')
        }
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30)
    @rate_limit(calls=100, period=60)
    def get_products(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """
        Get products from Siesa API using ejecutarconsultaestandar
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of records per page (max 100)
        
        Returns:
            Dict with products and pagination info
        """
        try:
            # Siesa ejecutarconsultaestandar endpoint
            url = f"{self.base_url}/ejecutarconsultaestandar"
            
            # Siesa pagination format: numPag=1|tamPag=100
            pagination_param = f"numPag={page}|tamPag={page_size}"
            
            # Query parameters
            params = {
                "idCompania": self.id_compania,
                "descripcion": self.consulta_api,  # API_v2_Items
                "paginacion": pagination_param
            }
            
            headers = self._get_headers()
            
            logger.info(f"Calling Siesa API: {url} with params: {params}")
            
            response = self.session.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Siesa returns data in different possible structures
            # Try common response formats
            products = []
            
            if isinstance(data, list):
                # Direct list of products
                products = data
            elif isinstance(data, dict):
                # Check common keys
                products = (
                    data.get('data', []) or 
                    data.get('items', []) or 
                    data.get('registros', []) or
                    data.get('resultados', []) or
                    []
                )
            
            # Validate response structure
            if not isinstance(products, list):
                logger.warning(f"Unexpected response structure from Siesa API: {type(products).__name__}")
                products = []
            
            # Sanitize products
            sanitized_products = []
            for product in products:
                if isinstance(product, dict):
                    sanitized_product = sanitize_dict(product)
                    sanitized_products.append(sanitized_product)
            
            pagination_info = {
                'current_page': page,
                'page_size': page_size,
                'records_in_page': len(sanitized_products),
                'has_more': len(sanitized_products) == page_size
            }
            
            logger.info(f"Retrieved {len(sanitized_products)} products from Siesa (page {page})")
            
            return {
                'products': sanitized_products,
                'pagination': pagination_info
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from Siesa API (page {page}): {e.response.status_code} - {sanitize_log_message(str(e))}")
            if e.response.status_code == 404:
                # API or company not found
                logger.error(f"API not found. Check idCompania ({self.id_compania}) and API name ({self.consulta_api})")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for page {page}: {sanitize_log_message(str(e))}")
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
                'client_id': sanitized_client_id
            }
        )
        
        if 'Item' not in response:
            raise ValueError(f"Client configuration not found for: {sanitize_log_message(client_id)}")
        
        config = response['Item']
        
        # Check if client is enabled
        if not config.get('enabled', False):
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
        Credentials dict with conniKey, conniToken, idCompania
    """
    try:
        response = secrets_manager.get_secret_value(SecretId=secret_arn)
        
        secret_string = response.get('SecretString')
        if not secret_string:
            raise ValueError(f"Secret has no string value: {secret_arn}")
        
        credentials = json.loads(secret_string)
        
        # Validate required fields
        if not credentials.get('conniKey'):
            raise ValueError("Missing conniKey in credentials")
        if not credentials.get('conniToken'):
            raise ValueError("Missing conniToken in credentials")
        
        logger.info(f"Retrieved Siesa credentials from: {secret_arn}")
        return credentials
        
    except ClientError as e:
        logger.error(f"Secrets Manager error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to get Siesa credentials: {str(e)}")
        raise


def extract_all_products(client: SiesaAPIClient, sync_type: str) -> List[Dict[str, Any]]:
    """
    Extract all products with pagination
    
    Args:
        client: Siesa API client
        sync_type: 'initial' or 'incremental' (currently both work the same)
    
    Returns:
        List of all products
    """
    all_products = []
    page = 1
    page_size = 100  # Siesa max page size
    
    logger.info(f"Starting product extraction (sync_type: {sync_type})")
    
    while True:
        try:
            result = client.get_products(page=page, page_size=page_size)
            
            products = result['products']
            pagination = result['pagination']
            
            all_products.extend(products)
            
            logger.info(f"Page {page}: Retrieved {len(products)} products. Total so far: {len(all_products)}")
            
            # Check if there are more pages
            if not pagination['has_more']:
                logger.info("No more pages available")
                break
            
            page += 1
            
            # Safety limit to prevent infinite loops
            if page > 1000:
                logger.warning("Reached maximum page limit (1000). Stopping pagination.")
                break
            
            # Small delay between pages to avoid rate limiting
            time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error on page {page}: {str(e)}")
            raise
    
    logger.info(f"Extraction complete. Total products: {len(all_products)}")
    return all_products


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Extractor function
    Adapted for Siesa Cloud v3 API
    
    Args:
        event: Lambda event with client_id and sync_type
        context: Lambda context
    
    Returns:
        Dict with extracted products and metadata
    """
    metrics = get_metrics_publisher()
    start_time = time.time()
    client_id = None
    
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
        id_compania = siesa_config.get('idCompania', '8585')
        consulta_api = siesa_config.get('consultaAPI', 'API_v2_Items')
        
        if not base_url or not credentials_secret:
            raise ValueError(f"Invalid Siesa configuration for client: {sanitize_log_message(client_id)}")
        
        logger.info(f"Siesa config: baseUrl={base_url}, idCompania={id_compania}, consultaAPI={consulta_api}")
        
        # Get Siesa credentials
        credentials = get_siesa_credentials(credentials_secret)
        
        # Create Siesa API client (NO authentication needed - uses ConniKey/Token)
        siesa_client = SiesaAPIClient(base_url, credentials, id_compania, consulta_api)
        
        # Extract products
        products = extract_all_products(siesa_client, sync_type)
        
        # Prepare response
        extraction_timestamp = datetime.now(timezone.utc).isoformat()
        product_type = config.get('productType', 'kong')
        
        response_data = {
            'client_id': client_id,
            'product_type': product_type,
            'products': products,
            'count': len(products),
            'sync_type': sync_type,
            'extraction_timestamp': extraction_timestamp
        }
        
        # Publish success metrics
        duration = time.time() - start_time
        metrics.put_sync_duration(client_id, duration)
        metrics.put_records_processed(client_id, len(products), True)
        metrics.put_api_call_duration(client_id, 'Siesa', duration)
        
        logger.info(f"Extraction completed successfully. Products: {len(products)}, Duration: {duration:.2f}s")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_data)
        }
        
    except ValueError as e:
        # Handle validation errors
        logger.error(f"Validation error: {sanitize_log_message(str(e))}")
        
        if client_id:
            duration = time.time() - start_time
            metrics.put_sync_duration(client_id, duration)
            metrics.put_records_processed(client_id, 0, False)
            metrics.put_error_count(client_id, 'ValidationError')
        
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'ValidationError',
                'message': str(e)
            })
        }
        
    except Exception as e:
        logger.error(f"Extraction failed: {sanitize_log_message(str(e))}", exc_info=True)
        
        if client_id:
            duration = time.time() - start_time
            metrics.put_sync_duration(client_id, duration)
            metrics.put_records_processed(client_id, 0, False)
            metrics.put_error_count(client_id, type(e).__name__)
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': type(e).__name__,
                'message': str(e)
            })
        }