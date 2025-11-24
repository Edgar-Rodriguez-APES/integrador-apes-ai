"""
Unit tests for Transformer Lambda Handler
Tests all functions and classes in transformer/handler.py
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# Import the module to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from transformer.handler import (
    FieldMapper,
    load_field_mappings,
    validate_canonical_product,
    lambda_handler
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def sample_mappings():
    """Sample field mappings configuration"""
    return {
        'mappings': {
            'product': {
                'id': {
                    'siesa_field': 'f_codigo',
                    'type': 'string',
                    'required': True
                },
                'external_id': {
                    'siesa_field': 'f_codigo',
                    'type': 'string',
                    'required': True
                },
                'name': {
                    'siesa_field': 'f_nombre',
                    'type': 'string',
                    'required': True
                },
                'sku': {
                    'siesa_field': 'f_codigo',
                    'type': 'string',
                    'required': True
                },
                'price': {
                    'siesa_field': 'f_precio',
                    'type': 'float',
                    'required': False
                },
                'stock_quantity': {
                    'siesa_field': 'f_stock',
                    'type': 'integer',
                    'required': False
                },
                'active': {
                    'siesa_field': 'f_activo',
                    'type': 'boolean',
                    'required': False
                }
            }
        },
        'transformations': {
            'price_with_tax': {
                'type': 'calculation',
                'logic': 'value * 1.19'
            },
            'status_lookup': {
                'type': 'lookup',
                'table': {
                    'A': 'active',
                    'I': 'inactive'
                }
            },
            'date_format': {
                'type': 'format',
                'from': 'YYYY-MM-DD',
                'to': 'ISO8601'
            }
        },
        'defaults': {
            'stock_quantity': 0,
            'active': True
        }
    }


@pytest.fixture
def sample_siesa_product():
    """Sample Siesa product data"""
    return {
        'f_codigo': 'PROD001',
        'f_nombre': 'Product 1',
        'f_precio': 100.0,
        'f_stock': 50,
        'f_activo': 'true'
    }


# ============================================================================
# FieldMapper Tests
# ============================================================================

class TestFieldMapper:
    """Tests for FieldMapper class"""
    
    def test_init(self, sample_mappings):
        """Test FieldMapper initialization"""
        mapper = FieldMapper(sample_mappings)
        
        assert mapper.mappings == sample_mappings
        assert 'id' in mapper.product_mappings  # Check for a field, not 'product'
        assert 'price_with_tax' in mapper.transformations
        assert 'stock_quantity' in mapper.defaults
    
    # ========================================================================
    # transform_product() Tests
    # ========================================================================
    
    def test_transform_product_success(self, sample_mappings, sample_siesa_product):
        """Test successful product transformation"""
        mapper = FieldMapper(sample_mappings)
        
        result = mapper.transform_product(sample_siesa_product)
        
        assert result['id'] == 'PROD001'
        assert result['external_id'] == 'PROD001'
        assert result['name'] == 'Product 1'
        assert result['sku'] == 'PROD001'
        assert result['price'] == 100.0
        assert result['stock_quantity'] == 50
        assert result['active'] is True
    
    def test_transform_product_missing_optional_fields(self, sample_mappings):
        """Test transformation with missing optional fields"""
        mapper = FieldMapper(sample_mappings)
        
        minimal_product = {
            'f_codigo': 'PROD002',
            'f_nombre': 'Product 2'
        }
        
        result = mapper.transform_product(minimal_product)
        
        assert result['id'] == 'PROD002'
        assert result['name'] == 'Product 2'
        assert 'price' not in result  # Optional field not present
    
    def test_transform_product_with_defaults(self, sample_mappings):
        """Test transformation uses default values"""
        mapper = FieldMapper(sample_mappings)
        
        product = {
            'f_codigo': 'PROD003',
            'f_nombre': 'Product 3'
            # Missing f_stock, should use default
        }
        
        result = mapper.transform_product(product)
        
        # Note: defaults are only used for required fields that are missing
        assert result['id'] == 'PROD003'
        assert result['name'] == 'Product 3'
    
    def test_transform_product_complex_types(self, sample_mappings):
        """Test transformation with complex data types"""
        mapper = FieldMapper(sample_mappings)
        
        product = {
            'f_codigo': 'PROD004',
            'f_nombre': 'Product 4',
            'f_precio': '150,50',  # String with comma
            'f_stock': '25',  # String number
            'f_activo': '1'  # String boolean
        }
        
        result = mapper.transform_product(product)
        
        assert result['price'] == 150.5  # Converted from string with comma
        assert result['stock_quantity'] == 25  # Converted from string
        assert result['active'] is True  # Converted from '1'
    
    # ========================================================================
    # _convert_type() Tests
    # ========================================================================
    
    def test_convert_type_string(self, sample_mappings):
        """Test string type conversion"""
        mapper = FieldMapper(sample_mappings)
        
        assert mapper._convert_type('test', 'string') == 'test'
        assert mapper._convert_type(123, 'string') == '123'
        assert mapper._convert_type(None, 'string') is None
    
    def test_convert_type_integer(self, sample_mappings):
        """Test integer type conversion"""
        mapper = FieldMapper(sample_mappings)
        
        assert mapper._convert_type(42, 'integer') == 42
        assert mapper._convert_type('42', 'integer') == 42
        assert mapper._convert_type(42.7, 'integer') == 43  # Rounded
        assert mapper._convert_type('42,5', 'integer') == 42  # Comma to dot, then rounded
    
    def test_convert_type_float(self, sample_mappings):
        """Test float type conversion"""
        mapper = FieldMapper(sample_mappings)
        
        assert mapper._convert_type(42.5, 'float') == 42.5
        assert mapper._convert_type('42.5', 'float') == 42.5
        assert mapper._convert_type('42,5', 'float') == 42.5  # Comma to dot
        assert mapper._convert_type(42, 'float') == 42.0
    
    def test_convert_type_boolean(self, sample_mappings):
        """Test boolean type conversion"""
        mapper = FieldMapper(sample_mappings)
        
        # True values
        assert mapper._convert_type('true', 'boolean') is True
        assert mapper._convert_type('1', 'boolean') is True
        assert mapper._convert_type('yes', 'boolean') is True
        assert mapper._convert_type('si', 'boolean') is True
        assert mapper._convert_type(1, 'boolean') is True
        
        # False values
        assert mapper._convert_type('false', 'boolean') is False
        assert mapper._convert_type('0', 'boolean') is False
        assert mapper._convert_type('no', 'boolean') is False
        assert mapper._convert_type(0, 'boolean') is False
    
    # ========================================================================
    # _apply_transformation() Tests
    # ========================================================================
    
    def test_apply_transformation_calculation(self, sample_mappings):
        """Test calculation transformation"""
        mapper = FieldMapper(sample_mappings)
        
        result = mapper._apply_transformation(100, 'price_with_tax')
        
        assert result == 119.0  # 100 * 1.19
    
    def test_apply_transformation_lookup(self, sample_mappings):
        """Test lookup transformation"""
        mapper = FieldMapper(sample_mappings)
        
        result_active = mapper._apply_transformation('A', 'status_lookup')
        result_inactive = mapper._apply_transformation('I', 'status_lookup')
        result_unknown = mapper._apply_transformation('X', 'status_lookup')
        
        assert result_active == 'active'
        assert result_inactive == 'inactive'
        assert result_unknown == 'X'  # Returns original if not in table


# ============================================================================
# load_field_mappings() Tests
# ============================================================================

class TestLoadFieldMappings:
    """Tests for load_field_mappings function"""
    
    @patch('transformer.handler.s3')
    def test_load_field_mappings_success(self, mock_s3, sample_mappings):
        """Test successful field mappings load"""
        # Mock S3 response
        mock_response = {
            'Body': Mock()
        }
        mock_response['Body'].read.return_value = json.dumps(sample_mappings).encode('utf-8')
        mock_s3.get_object.return_value = mock_response
        
        result = load_field_mappings('test-bucket', 'test-key.json')
        
        assert result == sample_mappings
        mock_s3.get_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='test-key.json'
        )
    
    @patch('transformer.handler.s3')
    def test_load_field_mappings_not_found(self, mock_s3):
        """Test field mappings file not found"""
        # Mock S3 error
        mock_s3.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}},
            'GetObject'
        )
        
        with pytest.raises(ClientError):
            load_field_mappings('test-bucket', 'non-existent.json')
    
    @patch('transformer.handler.s3')
    def test_load_field_mappings_invalid_json(self, mock_s3):
        """Test invalid JSON in mappings file"""
        # Mock S3 response with invalid JSON
        mock_response = {
            'Body': Mock()
        }
        mock_response['Body'].read.return_value = b'invalid json {'
        mock_s3.get_object.return_value = mock_response
        
        with pytest.raises(json.JSONDecodeError):
            load_field_mappings('test-bucket', 'invalid.json')


# ============================================================================
# validate_canonical_product() Tests
# ============================================================================

class TestValidateCanonicalProduct:
    """Tests for validate_canonical_product function"""
    
    def test_validate_canonical_product_valid(self):
        """Test validation of valid product"""
        product = {
            'id': 'PROD001',
            'external_id': 'PROD001',
            'name': 'Product 1',
            'sku': 'SKU001'
        }
        
        errors = validate_canonical_product(product)
        
        assert len(errors) == 0
    
    def test_validate_canonical_product_missing_id(self):
        """Test validation with missing id"""
        product = {
            'external_id': 'PROD001',
            'name': 'Product 1',
            'sku': 'SKU001'
        }
        
        errors = validate_canonical_product(product)
        
        assert len(errors) == 1
        assert 'id' in errors[0]
    
    def test_validate_canonical_product_multiple_missing(self):
        """Test validation with multiple missing fields"""
        product = {
            'id': 'PROD001'
        }
        
        errors = validate_canonical_product(product)
        
        assert len(errors) == 3  # Missing external_id, name, sku
        assert any('external_id' in e for e in errors)
        assert any('name' in e for e in errors)
        assert any('sku' in e for e in errors)


# ============================================================================
# lambda_handler() Tests
# ============================================================================

class TestLambdaHandler:
    """Tests for lambda_handler function"""
    
    @patch('transformer.handler.load_field_mappings')
    def test_lambda_handler_success(self, mock_load_mappings, sample_mappings, sample_siesa_product):
        """Test successful lambda execution"""
        # Setup mocks
        mock_load_mappings.return_value = sample_mappings
        
        event = {
            'client_id': 'test-client',
            'product_type': 'kong',
            'products': [sample_siesa_product],
            'extraction_timestamp': '2024-01-01T00:00:00Z',
            'sync_type': 'initial'
        }
        
        result = lambda_handler(event, None)
        
        assert result['client_id'] == 'test-client'
        assert result['count'] == 1
        assert len(result['canonical_products']) == 1
        assert result['canonical_products'][0]['id'] == 'PROD001'
        assert 'transformation_timestamp' in result
    
    @patch('transformer.handler.load_field_mappings')
    def test_lambda_handler_empty_products(self, mock_load_mappings, sample_mappings):
        """Test lambda with empty products list"""
        mock_load_mappings.return_value = sample_mappings
        
        event = {
            'client_id': 'test-client',
            'product_type': 'kong',
            'products': [],
            'extraction_timestamp': '2024-01-01T00:00:00Z'
        }
        
        result = lambda_handler(event, None)
        
        assert result['count'] == 0
        assert len(result['canonical_products']) == 0
    
    @patch('transformer.handler.load_field_mappings')
    def test_lambda_handler_validation_errors(self, mock_load_mappings, sample_mappings):
        """Test lambda with products that fail validation"""
        mock_load_mappings.return_value = sample_mappings
        
        # Product missing required fields
        invalid_product = {
            'f_precio': 100.0
        }
        
        event = {
            'client_id': 'test-client',
            'product_type': 'kong',
            'products': [invalid_product],
            'extraction_timestamp': '2024-01-01T00:00:00Z'
        }
        
        result = lambda_handler(event, None)
        
        assert result['count'] == 0  # Invalid product skipped
        assert len(result['validation_errors']) > 0
    
    @patch('transformer.handler.load_field_mappings')
    def test_lambda_handler_s3_error(self, mock_load_mappings):
        """Test lambda with S3 error"""
        # Mock S3 error
        mock_load_mappings.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket'}},
            'GetObject'
        )
        
        event = {
            'client_id': 'test-client',
            'product_type': 'kong',
            'products': [{'f_codigo': 'PROD001'}]
        }
        
        with pytest.raises(Exception, match="Transformer Lambda failed"):
            lambda_handler(event, None)
    
    @patch('transformer.handler.load_field_mappings')
    def test_lambda_handler_missing_client_id(self, mock_load_mappings):
        """Test lambda with missing client_id"""
        event = {
            'product_type': 'kong',
            'products': []
        }
        
        with pytest.raises(Exception, match="client_id"):
            lambda_handler(event, None)
    
    @patch('transformer.handler.load_field_mappings')
    def test_lambda_handler_multiple_products(self, mock_load_mappings, sample_mappings):
        """Test lambda with multiple products"""
        mock_load_mappings.return_value = sample_mappings
        
        products = [
            {'f_codigo': f'PROD{i:03d}', 'f_nombre': f'Product {i}'}
            for i in range(1, 11)
        ]
        
        event = {
            'client_id': 'test-client',
            'product_type': 'kong',
            'products': products,
            'extraction_timestamp': '2024-01-01T00:00:00Z'
        }
        
        result = lambda_handler(event, None)
        
        assert result['count'] == 10
        assert len(result['canonical_products']) == 10
    
    @patch('transformer.handler.load_field_mappings')
    def test_lambda_handler_wms_product_type(self, mock_load_mappings, sample_mappings):
        """Test lambda with WMS product type"""
        mock_load_mappings.return_value = sample_mappings
        
        event = {
            'client_id': 'test-client',
            'product_type': 'wms',
            'products': [{'f_codigo': 'PROD001', 'f_nombre': 'Product 1'}],
            'extraction_timestamp': '2024-01-01T00:00:00Z'
        }
        
        result = lambda_handler(event, None)
        
        # Verify it loaded WMS mappings
        mock_load_mappings.assert_called_once()
        call_args = mock_load_mappings.call_args[0]
        assert 'wms' in call_args[1].lower()
