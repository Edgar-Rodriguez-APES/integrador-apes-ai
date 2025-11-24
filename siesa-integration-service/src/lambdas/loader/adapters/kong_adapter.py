"""
Kong (RFID) Product Adapter
Handles integration with Kong RFID backend
"""

import sys
import os
from typing import Dict, List, Any, Tuple
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .base_adapter import ProductAdapter

# Add parent directory to path to import common module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from common.logging_utils import get_safe_logger
from common.input_validation import sanitize_log_message
from common.circuit_breaker import circuit_breaker
from common.rate_limiter import rate_limit

logger = get_safe_logger(__name__)


class KongAPIClient:
    """Client for Kong RFID API"""
    
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
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE", "PATCH"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    @circuit_breaker(failure_threshold=5, recovery_timeout=60)
    @rate_limit(calls=100, period=60)
    def authenticate(self) -> bool:
        """Authenticate with Kong API (Djoser token-based)"""
        try:
            auth_url = f"{self.base_url}/auth/token/login/"
            
            payload = {
                "username": self.credentials.get('username'),
                "password": self.credentials.get('password')
            }
            
            response = self.session.post(auth_url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.token = data.get('auth_token') or data.get('token')
            
            logger.info("Successfully authenticated with Kong API")
            return True
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Kong API: {sanitize_log_message(str(e))}")
            raise
    
    @circuit_breaker(failure_threshold=3, recovery_timeout=30)
    @rate_limit(calls=50, period=60)
    def create_or_update_skus(self, skus: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create or update SKUs in Kong (upsert operation)
        
        Args:
            skus: List of SKUs in Kong format
        
        Returns:
            Dict with operation results
        """
        try:
            url = f"{self.base_url}/inventory/skus/"
            
            headers = {
                "Authorization": f"Token {self.token}",
                "Content-Type": "application/json"
            }
            
            # Kong API supports bulk upsert
            response = self.session.post(url, json=skus, headers=headers, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'success': True,
                'records_processed': len(skus),
                'records_success': len(skus),
                'records_failed': 0,
                'response': data
            }
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Kong API HTTP error: {e.response.status_code} - {sanitize_log_message(e.response.text)}")
            
            # Try to parse error response
            try:
                error_data = e.response.json()
            except:
                error_data = {'error': sanitize_log_message(e.response.text)}
            
            return {
                'success': False,
                'records_processed': len(skus),
                'records_success': 0,
                'records_failed': len(skus),
                'error': error_data
            }
            
        except Exception as e:
            logger.error(f"Kong API error: {sanitize_log_message(str(e))}")
            return {
                'success': False,
                'records_processed': len(skus),
                'records_success': 0,
                'records_failed': len(skus),
                'error': sanitize_log_message(str(e))
            }


class KongAdapter(ProductAdapter):
    """Adapter for Kong (RFID) product"""
    
    def get_api_client(self):
        """Initialize Kong API client"""
        base_url = self.credentials.get('baseUrl') or self.config.get('baseUrl')
        
        client = KongAPIClient(base_url, self.credentials)
        client.authenticate()
        
        return client
    
    def transform_products(self, canonical_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform canonical model to Kong SKU format
        
        Args:
            canonical_products: Products in canonical model
        
        Returns:
            Products in Kong SKU format
        """
        kong_skus = []
        
        for product in canonical_products:
            kong_sku = {
                'external_id': product.get('external_id') or product.get('id'),
                'name': product.get('name'),
                'display_name': product.get('display_name') or product.get('name'),
                'reference': product.get('sku'),
                'ean': product.get('ean'),
                'is_active': True
            }
            
            # Add optional fields
            if product.get('rfid_tag_id'):
                kong_sku['rfid_tag_id'] = product.get('rfid_tag_id')
            
            # Add type_id and group_id from config (required by Kong)
            if 'type_id' in self.config:
                kong_sku['type_id'] = self.config['type_id']
            
            if 'group_id' in self.config:
                kong_sku['group_id'] = self.config['group_id']
            
            if 'customer_id' in self.config:
                kong_sku['customer_id'] = self.config['customer_id']
            
            # Handle custom fields as properties
            properties = {}
            for key, value in product.items():
                if key.startswith('custom:'):
                    prop_name = key.replace('custom:', '')
                    properties[prop_name] = value
            
            if properties:
                kong_sku['properties'] = properties
            
            kong_skus.append(kong_sku)
        
        logger.info(f"Transformed {len(canonical_products)} products to Kong SKU format")
        return kong_skus
    
    def load_batch(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load batch to Kong API
        
        Args:
            products: Products in Kong SKU format
        
        Returns:
            Dict with operation results
        """
        if not self.api_client:
            self.api_client = self.get_api_client()
        
        result = self.api_client.create_or_update_skus(products)
        return result
    
    def validate_product(self, product: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate product for Kong-specific requirements
        
        Args:
            product: Product in Kong SKU format
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Required fields for Kong
        required_fields = ['external_id', 'name']
        
        for field in required_fields:
            if not product.get(field):
                return False, f"Missing required field: {field}"
        
        # Validate EAN format if present (13 digits)
        ean = product.get('ean')
        if ean and not (isinstance(ean, str) and len(ean) == 13 and ean.isdigit()):
            return False, f"Invalid EAN format: {ean} (must be 13 digits)"
        
        return True, ""
