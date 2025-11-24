"""
Tests for Loader Lambda Handler
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

# Import the handler
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from loader.handler import (
    lambda_handler,
    load_to_product_api,
    get_adapter,
    batch_load,
    handle_load_errors
)


class TestLoaderHandler:
    """Test suite for Loader Lambda handler"""

    @patch('loader.handler.boto3')
    @patch('loader.handler.get_adapter')
    def test_lambda_handler_success(self, mock_get_adapter, mock_boto3):
        """Test successful lambda handler execution"""
        # Mock event
        event = {
            'tenant_id': 'test-tenant',
            'product_type': 'kong',
            'execution_id': 'exec-123',
            's3_input_key': 'transformed/test.json'
        }
        
        # Mock S3
        mock_s3 = Mock()
        mock_s3.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps([
                {'id': '001', 'name': 'Product 1'}
            ]).encode())
        }
        mock_boto3.client.return_value = mock_s3
        
        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.load_products.return_value = {'success': 1, 'failed': 0}
        mock_get_adapter.return_value = mock_adapter
        
        # Execute
        result = lambda_handler(event, {})
        
        # Assert
        assert result['statusCode'] == 200
        assert 'records_loaded' in json.loads(result['body'])

    def test_lambda_handler_missing_tenant_id(self):
        """Test handler with missing tenant_id"""
        event = {
            'product_type': 'kong'
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
        assert 'tenant_id' in result['body']

    @patch('loader.handler.adapter_factory')
    def test_get_adapter_kong(self, mock_factory):
        """Test getting Kong adapter"""
        mock_adapter = Mock()
        mock_factory.get_adapter.return_value = mock_adapter
        
        # Execute
        adapter = get_adapter('kong', {'api_url': 'https://api.kong.com'})
        
        # Assert
        assert adapter is not None
        mock_factory.get_adapter.assert_called_once_with('kong', {'api_url': 'https://api.kong.com'})

    @patch('loader.handler.adapter_factory')
    def test_get_adapter_wms(self, mock_factory):
        """Test getting WMS adapter"""
        mock_adapter = Mock()
        mock_factory.get_adapter.return_value = mock_adapter
        
        # Execute
        adapter = get_adapter('wms', {'api_url': 'https://api.wms.com'})
        
        # Assert
        assert adapter is not None

    def test_batch_load_success(self):
        """Test successful batch loading"""
        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.load_product.return_value = {'success': True}
        
        # Data
        products = [
            {'id': '001', 'name': 'Product 1'},
            {'id': '002', 'name': 'Product 2'}
        ]
        
        # Execute
        result = batch_load(products, mock_adapter, batch_size=10)
        
        # Assert
        assert result['success'] == 2
        assert result['failed'] == 0

    def test_batch_load_with_failures(self):
        """Test batch loading with some failures"""
        # Mock adapter with one failure
        mock_adapter = Mock()
        mock_adapter.load_product.side_effect = [
            {'success': True},
            Exception('API Error'),
            {'success': True}
        ]
        
        # Data
        products = [
            {'id': '001'},
            {'id': '002'},
            {'id': '003'}
        ]
        
        # Execute
        result = batch_load(products, mock_adapter, batch_size=10)
        
        # Assert
        assert result['success'] == 2
        assert result['failed'] == 1

    def test_handle_load_errors(self):
        """Test error handling"""
        errors = [
            {'product_id': '001', 'error': 'API Error'},
            {'product_id': '002', 'error': 'Validation Error'}
        ]
        
        # Execute
        result = handle_load_errors(errors)
        
        # Assert
        assert len(result) == 2
        assert all('product_id' in err for err in result)

    @patch('loader.handler.boto3')
    @patch('loader.handler.get_adapter')
    def test_lambda_handler_with_batch_processing(self, mock_get_adapter, mock_boto3):
        """Test handler with batch processing"""
        event = {
            'tenant_id': 'test-tenant',
            'product_type': 'kong',
            'execution_id': 'exec-123',
            's3_input_key': 'transformed/batch.json',
            'batch_size': 50
        }
        
        # Mock S3 with large dataset
        products = [{'id': str(i), 'name': f'Product {i}'} for i in range(100)]
        mock_s3 = Mock()
        mock_s3.get_object.return_value = {
            'Body': Mock(read=lambda: json.dumps(products).encode())
        }
        mock_boto3.client.return_value = mock_s3
        
        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.load_products.return_value = {'success': 100, 'failed': 0}
        mock_get_adapter.return_value = mock_adapter
        
        # Execute
        result = lambda_handler(event, {})
        
        # Assert
        assert result['statusCode'] == 200

    @patch('loader.handler.get_adapter')
    def test_load_to_product_api_success(self, mock_get_adapter):
        """Test successful API loading"""
        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.load_products.return_value = {'success': 2, 'failed': 0}
        mock_get_adapter.return_value = mock_adapter
        
        # Data
        products = [
            {'id': '001', 'name': 'Product 1'},
            {'id': '002', 'name': 'Product 2'}
        ]
        
        # Execute
        result = load_to_product_api(products, 'kong', {})
        
        # Assert
        assert result['success'] == 2
        assert result['failed'] == 0

    @patch('loader.handler.boto3')
    @patch('loader.handler.get_adapter')
    def test_lambda_handler_with_empty_data(self, mock_get_adapter, mock_boto3):
        """Test handler with empty data"""
        event = {
            'tenant_id': 'test-tenant',
            'product_type': 'kong',
            'execution_id': 'exec-123',
            's3_input_key': 'transformed/empty.json'
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
        assert body['records_loaded'] == 0

    def test_batch_load_with_retry(self):
        """Test batch loading with retry logic"""
        # Mock adapter that fails first time, succeeds second time
        mock_adapter = Mock()
        mock_adapter.load_product.side_effect = [
            Exception('Temporary Error'),
            {'success': True}
        ]
        
        # Data
        products = [{'id': '001'}]
        
        # Execute with retry
        result = batch_load(products, mock_adapter, batch_size=10, max_retries=2)
        
        # Assert
        assert result['success'] == 1

    @patch('loader.handler.boto3')
    def test_lambda_handler_s3_error(self, mock_boto3):
        """Test handler with S3 error"""
        event = {
            'tenant_id': 'test-tenant',
            'product_type': 'kong',
            'execution_id': 'exec-123',
            's3_input_key': 'transformed/test.json'
        }
        
        # Mock S3 error
        mock_s3 = Mock()
        mock_s3.get_object.side_effect = Exception('S3 Error')
        mock_boto3.client.return_value = mock_s3
        
        # Execute
        result = lambda_handler(event, {})
        
        # Assert
        assert result['statusCode'] == 500

    @patch('loader.handler.get_adapter')
    def test_load_to_product_api_partial_failure(self, mock_get_adapter):
        """Test API loading with partial failures"""
        # Mock adapter with partial success
        mock_adapter = Mock()
        mock_adapter.load_products.return_value = {'success': 8, 'failed': 2}
        mock_get_adapter.return_value = mock_adapter
        
        # Data
        products = [{'id': str(i)} for i in range(10)]
        
        # Execute
        result = load_to_product_api(products, 'kong', {})
        
        # Assert
        assert result['success'] == 8
        assert result['failed'] == 2

    def test_handle_load_errors_with_categorization(self):
        """Test error handling with categorization"""
        errors = [
            {'product_id': '001', 'error': 'Validation Error', 'type': 'validation'},
            {'product_id': '002', 'error': 'API Error', 'type': 'api'},
            {'product_id': '003', 'error': 'Timeout', 'type': 'timeout'}
        ]
        
        # Execute
        result = handle_load_errors(errors)
        
        # Assert
        assert len(result) == 3
        validation_errors = [e for e in result if e.get('type') == 'validation']
        assert len(validation_errors) == 1
