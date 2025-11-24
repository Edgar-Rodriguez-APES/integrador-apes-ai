"""
Tests for Transformer Lambda Handler
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

# Import the handler
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from transformer.handler import (
    lambda_handler,
    transform_data,
    load_field_mappings,
    apply_field_mapping,
    validate_transformed_data,
    apply_transformations,
    handle_custom_fields
)


class TestTransformerHandler:
    """Test suite for Transformer Lambda handler"""

    @patch('transformer.handler.boto3')
    def test_lambda_handler_success(self, mock_boto3):
        """Test successful lambda handler execution"""
        # Mock event
        event = {
            'tenant_id': 'test-tenant',
            'product_type': 'kong',
            'execution_id': 'exec-123',
            's3_input_key': 'raw/test.json'
        }
        
        # Mock S3
        mock_s3 = Mock()
        mock_s3.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps([
                {'f_codigo': '001', 'f_nombre': 'Product 1'}
            ]).encode())
        }
        mock_boto3.client.return_value = mock_s3
        
        # Execute
        result = lambda_handler(event, {})
        
        # Assert
        assert result['statusCode'] == 200
        assert 'records_transformed' in json.loads(result['body'])

    def test_lambda_handler_missing_tenant_id(self):
        """Test handler with missing tenant_id"""
        event = {
            'product_type': 'kong'
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
        assert 'tenant_id' in result['body']

    @patch('transformer.handler.boto3')
    def test_load_field_mappings_success(self, mock_boto3):
        """Test successful field mappings loading"""
        # Mock S3
        mock_s3 = Mock()
        mock_s3.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps({
                'mappings': {
                    'product': {
                        'id': {'siesa_field': 'f_codigo'}
                    }
                }
            }).encode())
        }
        mock_boto3.client.return_value = mock_s3
        
        # Execute
        mappings = load_field_mappings('kong', 'test-bucket')
        
        # Assert
        assert 'mappings' in mappings
        assert 'product' in mappings['mappings']

    def test_apply_field_mapping_simple(self):
        """Test simple field mapping"""
        source_data = {
            'f_codigo': '001',
            'f_nombre': 'Product 1'
        }
        
        mapping = {
            'id': {'siesa_field': 'f_codigo', 'type': 'string'},
            'name': {'siesa_field': 'f_nombre', 'type': 'string'}
        }
        
        # Execute
        result = apply_field_mapping(source_data, mapping)
        
        # Assert
        assert result['id'] == '001'
        assert result['name'] == 'Product 1'

    def test_apply_field_mapping_with_defaults(self):
        """Test field mapping with default values"""
        source_data = {
            'f_codigo': '001'
        }
        
        mapping = {
            'id': {'siesa_field': 'f_codigo', 'type': 'string'},
            'status': {'siesa_field': 'f_estado', 'type': 'string', 'default': 'active'}
        }
        
        # Execute
        result = apply_field_mapping(source_data, mapping)
        
        # Assert
        assert result['id'] == '001'
        assert result['status'] == 'active'

    def test_apply_field_mapping_with_type_conversion(self):
        """Test field mapping with type conversion"""
        source_data = {
            'f_codigo': '001',
            'f_cantidad': '100',
            'f_precio': '25.50'
        }
        
        mapping = {
            'id': {'siesa_field': 'f_codigo', 'type': 'string'},
            'quantity': {'siesa_field': 'f_cantidad', 'type': 'integer'},
            'price': {'siesa_field': 'f_precio', 'type': 'decimal'}
        }
        
        # Execute
        result = apply_field_mapping(source_data, mapping)
        
        # Assert
        assert result['id'] == '001'
        assert result['quantity'] == 100
        assert isinstance(result['quantity'], int)
        assert result['price'] == 25.50

    def test_validate_transformed_data_success(self):
        """Test successful data validation"""
        data = {
            'id': '001',
            'name': 'Product 1',
            'ean': '1234567890123'
        }
        
        validation_rules = {
            'ean': {
                'pattern': '^[0-9]{13}$',
                'message': 'EAN must be 13 digits'
            }
        }
        
        # Execute
        is_valid, errors = validate_transformed_data(data, validation_rules)
        
        # Assert
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_transformed_data_failure(self):
        """Test data validation failure"""
        data = {
            'id': '001',
            'ean': '123'  # Invalid EAN
        }
        
        validation_rules = {
            'ean': {
                'pattern': '^[0-9]{13}$',
                'message': 'EAN must be 13 digits'
            }
        }
        
        # Execute
        is_valid, errors = validate_transformed_data(data, validation_rules)
        
        # Assert
        assert is_valid is False
        assert len(errors) > 0

    def test_apply_transformations_date_format(self):
        """Test date format transformation"""
        data = {
            'created_date': '2025-01-15'
        }
        
        transformations = {
            'date_format': {
                'from': 'YYYY-MM-DD',
                'to': 'ISO8601'
            }
        }
        
        # Execute
        result = apply_transformations(data, transformations)
        
        # Assert
        assert 'created_date' in result

    def test_apply_transformations_decimal_separator(self):
        """Test decimal separator transformation"""
        data = {
            'price': '25,50'
        }
        
        transformations = {
            'decimal_separator': {
                'from': ',',
                'to': '.'
            }
        }
        
        # Execute
        result = apply_transformations(data, transformations)
        
        # Assert
        assert result['price'] == '25.50'

    def test_handle_custom_fields(self):
        """Test custom fields handling"""
        source_data = {
            'f_codigo': '001',
            'f_color': 'red',
            'f_size': 'L'
        }
        
        standard_fields = ['f_codigo']
        
        # Execute
        custom_fields = handle_custom_fields(source_data, standard_fields)
        
        # Assert
        assert 'custom:f_color' in custom_fields
        assert 'custom:f_size' in custom_fields
        assert custom_fields['custom:f_color'] == 'red'

    @patch('transformer.handler.boto3')
    def test_transform_data_batch(self, mock_boto3):
        """Test batch data transformation"""
        # Mock S3
        mock_s3 = Mock()
        mock_s3.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps({
                'mappings': {
                    'product': {
                        'id': {'siesa_field': 'f_codigo', 'type': 'string'}
                    }
                }
            }).encode())
        }
        mock_boto3.client.return_value = mock_s3
        
        # Source data
        source_data = [
            {'f_codigo': '001'},
            {'f_codigo': '002'},
            {'f_codigo': '003'}
        ]
        
        # Execute
        result = transform_data(source_data, 'kong', 'test-bucket')
        
        # Assert
        assert len(result) == 3
        assert all('id' in item for item in result)

    def test_apply_field_mapping_missing_required_field(self):
        """Test mapping with missing required field"""
        source_data = {
            'f_nombre': 'Product 1'
        }
        
        mapping = {
            'id': {'siesa_field': 'f_codigo', 'type': 'string', 'required': True},
            'name': {'siesa_field': 'f_nombre', 'type': 'string'}
        }
        
        # Execute and assert
        with pytest.raises(ValueError):
            apply_field_mapping(source_data, mapping)

    def test_apply_field_mapping_with_validation_pattern(self):
        """Test mapping with validation pattern"""
        source_data = {
            'f_ean': '1234567890123'
        }
        
        mapping = {
            'ean': {
                'siesa_field': 'f_ean',
                'type': 'string',
                'validation': '^[0-9]{13}$'
            }
        }
        
        # Execute
        result = apply_field_mapping(source_data, mapping)
        
        # Assert
        assert result['ean'] == '1234567890123'

    def test_apply_field_mapping_invalid_validation_pattern(self):
        """Test mapping with invalid validation pattern"""
        source_data = {
            'f_ean': '123'  # Too short
        }
        
        mapping = {
            'ean': {
                'siesa_field': 'f_ean',
                'type': 'string',
                'validation': '^[0-9]{13}$'
            }
        }
        
        # Execute and assert
        with pytest.raises(ValueError):
            apply_field_mapping(source_data, mapping)

    @patch('transformer.handler.boto3')
    def test_lambda_handler_with_empty_data(self, mock_boto3):
        """Test handler with empty data"""
        event = {
            'tenant_id': 'test-tenant',
            'product_type': 'kong',
            'execution_id': 'exec-123',
            's3_input_key': 'raw/empty.json'
        }
        
        # Mock S3 with empty data
        mock_s3 = Mock()
        mock_s3.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps([]).encode())
        }
        mock_boto3.client.return_value = mock_s3
        
        # Execute
        result = lambda_handler(event, {})
        
        # Assert
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['records_transformed'] == 0

    def test_apply_transformations_boolean_conversion(self):
        """Test boolean conversion transformation"""
        data = {
            'active': 'S',
            'available': 'N'
        }
        
        transformations = {
            'boolean_conversion': {
                'true_values': ['S', 'SI', '1'],
                'false_values': ['N', 'NO', '0']
            }
        }
        
        # Execute
        result = apply_transformations(data, transformations)
        
        # Assert
        assert result['active'] is True
        assert result['available'] is False
