"""
Transformer Lambda Function
Transforms Siesa data to canonical model using field mappings
"""

import json
import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError

# Import security utilities
from common.input_validation import sanitize_dict, sanitize_log_message, sanitize_string
from common.logging_utils import get_safe_logger
# SECURITY FIX: Import safe evaluation functions from safe_eval module
from common.safe_eval import apply_transformation_logic, evaluate_condition
from common.metrics import get_metrics_publisher
import time

# Configure logging
logger = get_safe_logger(__name__)

# AWS clients
s3 = boto3.client('s3')

# Environment variables
FIELD_MAPPINGS_S3_BUCKET = os.environ.get('FIELD_MAPPINGS_S3_BUCKET', 'siesa-integration-config-dev-224874703567')


# SECURITY FIX: SafeExpressionEvaluator, apply_transformation_logic, and evaluate_condition
# are now imported from common.safe_eval module (see imports above)
# This eliminates code duplication and ensures consistent security controls


class FieldMapper:
    """Handles field mapping and data transformation"""
    
    def __init__(self, mappings: Dict[str, Any]):
        self.mappings = mappings
        self.product_mappings = mappings.get('mappings', {}).get('product', {})
        self.transformations = mappings.get('transformations', {})
        self.defaults = mappings.get('defaults', {})
    
    def transform_product(self, siesa_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single Siesa product to canonical model
        
        Args:
            siesa_product: Product data from Siesa
        
        Returns:
            Product in canonical model format
        """
        canonical_product = {}
        validation_warnings = []
        
        # Apply field mappings
        for canonical_field, mapping_rule in self.product_mappings.items():
            siesa_field = mapping_rule.get('siesa_field')
            field_type = mapping_rule.get('type', 'string')
            required = mapping_rule.get('required', False)
            validation_pattern = mapping_rule.get('validation')
            transformation = mapping_rule.get('transformation')
            
            # Get value from Siesa product
            value = siesa_product.get(siesa_field)
            
            # Handle missing required fields
            if required and value is None:
                warning = f"Missing required field: {siesa_field} -> {canonical_field}"
                validation_warnings.append(warning)
                logger.warning(warning)
                
                # Use default value if available
                if canonical_field in self.defaults:
                    value = self.defaults[canonical_field]
                else:
                    continue
            
            # Skip if value is None and not required
            if value is None:
                continue
            
            # Apply type conversion
            try:
                value = self._convert_type(value, field_type)
            except Exception as e:
                warning = f"Type conversion failed for {canonical_field}: {str(e)}"
                validation_warnings.append(warning)
                logger.warning(warning)
                continue
            
            # Apply validation pattern
            if validation_pattern and isinstance(value, str):
                import re
                if not re.match(validation_pattern, value):
                    warning = f"Validation failed for {canonical_field}: {value} does not match {validation_pattern}"
                    validation_warnings.append(warning)
                    logger.warning(warning)
            
            # Apply transformation if specified
            if transformation and transformation in self.transformations:
                try:
                    value = self._apply_transformation(value, transformation)
                except Exception as e:
                    warning = f"Transformation failed for {canonical_field}: {str(e)}"
                    validation_warnings.append(warning)
                    logger.warning(warning)
            
            canonical_product[canonical_field] = value
        
        # Handle custom fields (fields starting with "custom:")
        for siesa_field, value in siesa_product.items():
            if siesa_field.startswith('custom:') or siesa_field.startswith('f120_custom_'):
                custom_field_name = siesa_field.replace('f120_custom_', 'custom:')
                canonical_product[custom_field_name] = value
        
        return canonical_product
    
    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type with security improvements"""
        if value is None:
            return None
        
        if target_type == 'string':
            # SECURITY FIX: Use safe conversion and sanitization
            try:
                str_value = str(value) if value is not None else ''
                return sanitize_string(str_value, max_length=1000)
            except (ValueError, TypeError) as e:
                logger.warning(f"Type conversion failed for string: {sanitize_log_message(str(e))}")
                return str(value) if value is not None else ''
        
        elif target_type in ['number', 'integer']:
            # SECURITY FIX: Safe numeric conversion
            try:
                if isinstance(value, str):
                    value = value.replace(',', '.')
                    # Sanitize before conversion
                    sanitized_value = sanitize_string(str(value), max_length=50)
                    float_value = float(sanitized_value)
                    return round(float_value)
                return round(float(value))
            except (ValueError, TypeError) as e:
                logger.warning(f"Type conversion failed for integer: {sanitize_log_message(str(e))}")
                return value
        
        elif target_type == 'float':
            # SECURITY FIX: Safe float conversion
            try:
                if isinstance(value, str):
                    value = value.replace(',', '.')
                    sanitized_value = sanitize_string(str(value), max_length=50)
                    return float(sanitized_value)
                return float(value)
            except (ValueError, TypeError) as e:
                logger.warning(f"Type conversion failed for float: {sanitize_log_message(str(e))}")
                return value
        
        elif target_type == 'boolean':
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'si', 's')
            return bool(value)
        
        elif target_type == 'object':
            if isinstance(value, str):
                return json.loads(value)
            return value
        
        elif target_type == 'array':
            if isinstance(value, str):
                return json.loads(value)
            if not isinstance(value, list):
                return [value]
            return value
        
        else:
            return value
    
    def _apply_transformation(self, value: Any, transformation_name: str) -> Any:
        """Apply named transformation to value"""
        transformation = self.transformations.get(transformation_name, {})
        trans_type = transformation.get('type')
        
        if trans_type == 'format':
            # Date format transformation
            from_format = transformation.get('from')
            to_format = transformation.get('to')
            
            if from_format == 'YYYY-MM-DD' and to_format == 'ISO8601':
                # Convert to ISO8601
                if isinstance(value, str) and len(value) == 10:
                    return f"{value}T00:00:00Z"
            
            return value
        
        elif trans_type == 'calculation':
            # Mathematical calculation
            logic = transformation.get('logic')
            # Use safe evaluator instead of dangerous eval()
            return apply_transformation_logic(value, logic)
        
        elif trans_type == 'lookup':
            # Lookup table transformation
            lookup_table = transformation.get('table', {})
            return lookup_table.get(str(value), value)
        
        elif trans_type == 'conditional':
            # Conditional transformation
            condition = transformation.get('condition')
            true_value = transformation.get('true_value')
            false_value = transformation.get('false_value')
            
            # Use safe evaluator instead of dangerous eval()
            if evaluate_condition(value, condition):
                return true_value
            else:
                return false_value
        
        return value


def load_field_mappings(bucket: str, key: str) -> Dict[str, Any]:
    """
    Load field mappings from S3
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
    
    Returns:
        Field mappings dict
    """
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        mappings = json.loads(content)
        
        logger.info(f"Loaded field mappings from s3://{bucket}/{key}")
        return mappings
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"Failed to load field mappings from S3: {error_code}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse field mappings JSON: {str(e)}")
        raise


def validate_canonical_product(product: Dict[str, Any]) -> List[str]:
    """
    Validate canonical product has required fields
    
    Args:
        product: Product in canonical model
    
    Returns:
        List of validation errors
    """
    errors = []
    
    # Required fields in canonical model
    required_fields = ['id', 'external_id', 'name', 'sku']
    
    for field in required_fields:
        if field not in product or product[field] is None:
            errors.append(f"Missing required field: {field}")
    
    return errors


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Transformer function with security improvements
    
    Args:
        event: Lambda event with products from Extractor
        context: Lambda context
    
    Returns:
        Dict with transformed products in canonical model
    """
    metrics = get_metrics_publisher()
    start_time = time.time()
    client_id = None
    
    try:
        # Sanitize input event
        event = sanitize_dict(event)
        
        # Extract parameters from event (support both formats)
        client_id = event.get('client_id') or event.get('tenantId')
        product_type = event.get('product_type') or event.get('productType', 'kong')
        products = event.get('products', [])
        extraction_timestamp = event.get('extraction_timestamp')
        sync_type = event.get('sync_type', 'incremental')
        
        if not client_id:
            raise ValueError("Missing required parameter: client_id")
        
        if not products:
            logger.warning(f"No products to transform for client: {sanitize_log_message(client_id)}")
            return {
                'client_id': client_id,
                'product_type': product_type,
                'canonical_products': [],
                'count': 0,
                'extraction_timestamp': extraction_timestamp,
                'transformation_timestamp': datetime.now(timezone.utc).isoformat(),
                'validation_errors': []
            }
        
        logger.info(f"Starting transformation for client: {sanitize_log_message(client_id)}, products: {len(products)}")
        
        # Determine field mappings file based on product type
        product_type_lower = product_type.lower()
        if product_type_lower in ['kong_rfid', 'kong']:
            mappings_key = 'field-mappings-kong.json'
        elif product_type_lower in ['wms']:
            mappings_key = 'field-mappings-wms.json'
        else:
            raise ValueError(f"Unknown product type: {product_type}")
        
        # Load field mappings from S3
        mappings = load_field_mappings(FIELD_MAPPINGS_S3_BUCKET, mappings_key)
        
        # Create field mapper
        mapper = FieldMapper(mappings)
        
        # Transform products
        canonical_products = []
        all_validation_errors = []
        
        for i, siesa_product in enumerate(products):
            try:
                canonical_product = mapper.transform_product(siesa_product)
                
                # Validate canonical product
                validation_errors = validate_canonical_product(canonical_product)
                
                if validation_errors:
                    error_msg = f"Product {i}: " + ", ".join(validation_errors)
                    all_validation_errors.append(error_msg)
                    logger.warning(error_msg)
                    # Skip invalid products
                    continue
                
                canonical_products.append(canonical_product)
                
            except Exception as e:
                error_msg = f"Product {i} transformation failed: {str(e)}"
                all_validation_errors.append(error_msg)
                logger.error(error_msg)
                # Continue with next product
                continue
        
        # Prepare response (format for Step Functions)
        transformation_timestamp = datetime.now(timezone.utc).isoformat()
        
        response = {
            'client_id': client_id,
            'product_type': product_type,
            'canonical_products': canonical_products,
            'count': len(canonical_products),
            'extraction_timestamp': extraction_timestamp,
            'transformation_timestamp': transformation_timestamp,
            'validation_errors': all_validation_errors[:10]  # Limit to 10 for response size
        }
        
        # Publish success metrics
        duration = time.time() - start_time
        metrics.put_sync_duration(client_id, duration)
        metrics.put_records_processed(client_id, len(canonical_products), True)
        if all_validation_errors:
            metrics.put_validation_errors(client_id, len(all_validation_errors))
        
        logger.info(f"Transformation completed. Canonical products: {len(canonical_products)}, Errors: {len(all_validation_errors)}, Duration: {duration:.2f}s")
        
        return response
        
    except Exception as e:
        logger.error(f"Transformation failed: {sanitize_log_message(str(e))}", exc_info=True)
        
        # Publish failure metrics
        if client_id:
            duration = time.time() - start_time
            metrics.put_sync_duration(client_id, duration)
            metrics.put_records_processed(client_id, 0, False)
            metrics.put_error_count(client_id, type(e).__name__)
        
        # Re-raise the exception so Step Functions can catch it
        raise Exception(f"Transformer Lambda failed: {sanitize_log_message(str(e))}")
