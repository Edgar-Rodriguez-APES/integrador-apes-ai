"""
Base Product Adapter
Abstract base class for all product adapters
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Tuple
import sys
import os

# Add parent directory to path to import common module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from common.logging_utils import get_safe_logger
from common.input_validation import sanitize_log_message

logger = get_safe_logger(__name__)


class ProductAdapter(ABC):
    """Base adapter interface for all products"""
    
    def __init__(self, credentials: Dict[str, Any], config: Dict[str, Any]):
        """
        Initialize adapter
        
        Args:
            credentials: Product API credentials
            config: Product configuration
        """
        self.credentials = credentials
        self.config = config
        self.api_client = None
    
    @abstractmethod
    def get_api_client(self):
        """
        Initialize product-specific API client
        
        Returns:
            API client instance
        """
        pass
    
    @abstractmethod
    def transform_products(self, canonical_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform canonical model to product-specific format
        
        Args:
            canonical_products: Products in canonical model
        
        Returns:
            Products in product-specific format
        """
        pass
    
    @abstractmethod
    def load_batch(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Load batch to product API and return results
        
        Args:
            products: Products in product-specific format
        
        Returns:
            Dict with success status and results
        """
        pass
    
    @abstractmethod
    def validate_product(self, product: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate product for product-specific requirements
        
        Args:
            product: Product in product-specific format
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    def process_batch(self, canonical_products: List[Dict[str, Any]], batch_size: int = 100) -> Dict[str, Any]:
        """
        Process products in batches
        
        Args:
            canonical_products: Products in canonical model
            batch_size: Number of products per batch
        
        Returns:
            Summary of processing results
        """
        # Transform to product-specific format
        product_data = self.transform_products(canonical_products)
        
        # Validate products
        valid_products = []
        validation_errors = []
        
        for i, product in enumerate(product_data):
            is_valid, error_msg = self.validate_product(product)
            if is_valid:
                valid_products.append(product)
            else:
                validation_errors.append({
                    'index': i,
                    'product_id': product.get('id') or product.get('external_id'),
                    'error': error_msg
                })
                logger.warning(f"Product {i} validation failed: {sanitize_log_message(error_msg)}")
        
        # Process in batches
        total_processed = 0
        total_success = 0
        total_failed = 0
        batch_results = []
        
        for i in range(0, len(valid_products), batch_size):
            batch = valid_products[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            try:
                result = self.load_batch(batch)
                
                batch_processed = result.get('records_processed', len(batch))
                batch_success = result.get('records_success', batch_processed)
                batch_failed = result.get('records_failed', 0)
                
                total_processed += batch_processed
                total_success += batch_success
                total_failed += batch_failed
                
                batch_results.append({
                    'batch_number': batch_num,
                    'processed': batch_processed,
                    'success': batch_success,
                    'failed': batch_failed
                })
                
                logger.info(f"Batch {batch_num}: Processed {batch_processed}, Success {batch_success}, Failed {batch_failed}")
                
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {sanitize_log_message(str(e))}")
                total_failed += len(batch)
                batch_results.append({
                    'batch_number': batch_num,
                    'processed': len(batch),
                    'success': 0,
                    'failed': len(batch),
                    'error': sanitize_log_message(str(e))
                })
        
        return {
            'total_input': len(canonical_products),
            'total_valid': len(valid_products),
            'total_processed': total_processed,
            'total_success': total_success,
            'total_failed': total_failed + len(validation_errors),
            'validation_errors': validation_errors,
            'batch_results': batch_results
        }
