"""
Adapter Factory
Creates appropriate adapter based on product type
"""

import logging
from typing import Dict, Any
from .base_adapter import ProductAdapter
from .kong_adapter import KongAdapter

logger = logging.getLogger(__name__)


class AdapterFactory:
    """Factory to create appropriate adapter based on product type"""
    
    @staticmethod
    def create_adapter(product_type: str, credentials: Dict[str, Any], config: Dict[str, Any]) -> ProductAdapter:
        """
        Create appropriate adapter based on product type
        
        Args:
            product_type: Product type identifier ('kong', 'KONG_RFID', 'wms', 'WMS')
            credentials: Product API credentials
            config: Product configuration
        
        Returns:
            ProductAdapter instance
        
        Raises:
            ValueError: If product type is unknown
        """
        product_type_lower = product_type.lower()
        
        if product_type_lower in ['kong', 'kong_rfid']:
            logger.info(f"Creating KongAdapter for product type: {product_type}")
            return KongAdapter(credentials, config)
        
        elif product_type_lower in ['wms']:
            # WMS adapter will be implemented in Week 2
            raise NotImplementedError(f"WMS adapter not yet implemented. Coming in Week 2.")
        
        else:
            raise ValueError(f"Unknown product type: {product_type}")
