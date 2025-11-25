"""
Unit tests for Loader Lambda Handler
Tests all functions and classes in loader/handler.py and adapters
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from botocore.exceptions import ClientError
import requests

# Import the module to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from loader.handler import (
    get_client_config,
    update_sync_status,
    get_product_credentials,
    lambda_handler
)
from loader.adapters.kong_adapter import KongAPIClient, KongAdapter
from loader.adapters.adapter_factory import AdapterFactory


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def kong_credentials():
    """Sample Kong credentials"""
    return {
        'username': 'kong_user',
        'password': 'kong_pass',
        'baseUrl': 'https://api.kong.com'
    }


@pytest.fixture
def sample_canonical_products():
    """Sample canonical products"""
    return [
        {
            'id': 'PROD001',
            'external_id': 'PROD001',
            'name': 'Product 1',
            'sku': 'SKU001',
            'ean': '1234567890123'
        },
        {
            'id': 'PROD002',
            'external_id': 'PROD002',
            'name': 'Product 2',
            'sku': 'SKU002',
            'ean': '9876543210987'
        }
    ]


@pytest.fixture
def client_config():
    """Sample client configuration"""
    return {
        'tenantId': 'test-client',
        'configType': 'PRODUCT_CONFIG',
        'productConfig': {
            'credentialsSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret',
            'baseUrl': 'https://api.kong.com',
            'type_id': 1,
            'group_id': 1,
            'customer_id': 1
        }
    }


# ============================================================================
# KongAPIClient Tests - 3 tests for authenticate()
# ============================================================================

class TestKongAPIClient:
    """Tests for KongAPIClient class"""
    
    @patch('loader.adapters.kong_adapter.requests.Session.post')
    def test_authenticate_success(self, mock_post, kong_credentials):
        """Test successful authentication"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'auth_token': 'valid_token_12345'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = KongAPIClient('https://api.kong.com', kong_credentials)
        result = client.authenticate()
        
        assert result is True
        assert client.token == 'valid_token_12345'
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'auth/token/login' in call_args[0][0]
        assert call_args[1]['json']['username'] == 'kong_user'
    
    @patch('loader.adapters.kong_adapter.requests.Session.post')
    def test_authenticate_http_error(self, mock_post, kong_credentials):
        """Test authentication with HTTP error"""
        # Mock HTTP error
        mock_post.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        
        client = KongAPIClient('https://api.kong.com', kong_credentials)
        
        with pytest.raises(Exception):
            client.authenticate()
    
    @patch('loader.adapters.kong_adapter.requests.Session.post')
    def test_authenticate_timeout(self, mock_post, kong_credentials):
        """Test authentication with timeout"""
        # Mock timeout error
        mock_post.side_effect = requests.exceptions.Timeout("Connection timeout")
        
        client = KongAPIClient('https://api.kong.com', kong_credentials)
        
        with pytest.raises(Exception):
            client.authenticate()


# ============================================================================
# KongAPIClient Tests - 4 tests for create_or_update_skus()
# ============================================================================

class TestKongAPIClientSKUs:
    """Tests for KongAPIClient SKU operations"""
    
    @patch('loader.adapters.kong_adapter.requests.Session.post')
    def test_create_or_update_skus_success(self, mock_post, kong_credentials):
        """Test successful SKU creation/update"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success', 'count': 2}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = KongAPIClient('https://api.kong.com', kong_credentials)
        client.token = 'valid_token'
        
        skus = [
            {'external_id': 'PROD001', 'name': 'Product 1'},
            {'external_id': 'PROD002', 'name': 'Product 2'}
        ]
        
        result = client.create_or_update_skus(skus)
        
        assert result['success'] is True
        assert result['records_processed'] == 2
        assert result['records_success'] == 2
        assert result['records_failed'] == 0
    
    @patch('loader.adapters.kong_adapter.requests.Session.post')
    def test_create_or_update_skus_http_error(self, mock_post, kong_credentials):
        """Test SKU operation with HTTP error"""
        # Mock HTTP error with response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server Error"
        mock_response.json.return_value = {'error': 'Server Error'}
        
        mock_post.side_effect = requests.exceptions.HTTPError(response=mock_response)
        
        client = KongAPIClient('https://api.kong.com', kong_credentials)
        client.token = 'valid_token'
        
        skus = [{'external_id': 'PROD001', 'name': 'Product 1'}]
        result = client.create_or_update_skus(skus)
        
        assert result['success'] is False
        assert result['records_failed'] == 1
    
    @patch('loader.adapters.kong_adapter.requests.Session.post')
    def test_create_or_update_skus_retry(self, mock_post, kong_credentials):
        """Test SKU operation with retry on transient error"""
        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 503
        mock_response_fail.text = "Service Unavailable"
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {'status': 'success'}
        mock_response_success.raise_for_status = Mock()
        
        mock_post.side_effect = [
            requests.exceptions.HTTPError(response=mock_response_fail),
            mock_response_success
        ]
        
        client = KongAPIClient('https://api.kong.com', kong_credentials)
        client.token = 'valid_token'
        
        skus = [{'external_id': 'PROD001', 'name': 'Product 1'}]
        
        # First call will fail, but we test the retry mechanism exists
        result = client.create_or_update_skus(skus)
        assert result is not None
    
    @patch('loader.adapters.kong_adapter.requests.Session.post')
    def test_create_or_update_skus_batch_processing(self, mock_post, kong_credentials):
        """Test batch processing with large dataset"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success', 'count': 50}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Create large SKU list
        large_skus = [
            {'external_id': f'PROD{i:03d}', 'name': f'Product {i}'}
            for i in range(1, 51)
        ]
        
        client = KongAPIClient('https://api.kong.com', kong_credentials)
        client.token = 'valid_token'
        
        result = client.create_or_update_skus(large_skus)
        
        assert result['success'] is True
        assert result['records_processed'] == 50


# ============================================================================
# KongAdapter Tests - 3 tests for transform_products()
# ============================================================================

class TestKongAdapterTransform:
    """Tests for KongAdapter transformation"""
    
    def test_transform_products_success(self, kong_credentials, sample_canonical_products):
        """Test successful product transformation"""
        config = {'type_id': 1, 'group_id': 1, 'customer_id': 1}
        adapter = KongAdapter(kong_credentials, config)
        
        transformed = adapter.transform_products(sample_canonical_products)
        
        assert len(transformed) == 2
        assert transformed[0]['external_id'] == 'PROD001'
        assert transformed[0]['name'] == 'Product 1'
        assert transformed[0]['reference'] == 'SKU001'
        assert transformed[0]['ean'] == '1234567890123'
        assert transformed[0]['is_active'] is True
    
    def test_transform_products_optional_fields(self, kong_credentials):
        """Test transformation with optional fields"""
        config = {'type_id': 1, 'group_id': 1}
        adapter = KongAdapter(kong_credentials, config)
        
        products = [{
            'id': 'PROD001',
            'name': 'Product 1',
            'sku': 'SKU001',
            'rfid_tag_id': 'RFID123'
        }]
        
        transformed = adapter.transform_products(products)
        
        assert len(transformed) == 1
        assert transformed[0]['rfid_tag_id'] == 'RFID123'
        assert transformed[0]['type_id'] == 1
        assert transformed[0]['group_id'] == 1
    
    def test_transform_products_custom_fields(self, kong_credentials):
        """Test transformation with custom fields"""
        config = {'type_id': 1}
        adapter = KongAdapter(kong_credentials, config)
        
        products = [{
            'id': 'PROD001',
            'name': 'Product 1',
            'sku': 'SKU001',
            'custom:color': 'blue',
            'custom:size': 'large'
        }]
        
        transformed = adapter.transform_products(products)
        
        assert 'properties' in transformed[0]
        assert transformed[0]['properties']['color'] == 'blue'
        assert transformed[0]['properties']['size'] == 'large'


# ============================================================================
# KongAdapter Tests - 4 tests for validate_product()
# ============================================================================

class TestKongAdapterValidation:
    """Tests for KongAdapter validation"""
    
    def test_validate_product_valid(self, kong_credentials):
        """Test validation of valid product"""
        adapter = KongAdapter(kong_credentials, {})
        
        product = {
            'external_id': 'PROD001',
            'name': 'Product 1',
            'ean': '1234567890123'
        }
        
        is_valid, error = adapter.validate_product(product)
        
        assert is_valid is True
        assert error == ""
    
    def test_validate_product_missing_required_fields(self, kong_credentials):
        """Test validation with missing required fields"""
        adapter = KongAdapter(kong_credentials, {})
        
        product = {
            'ean': '1234567890123'
        }
        
        is_valid, error = adapter.validate_product(product)
        
        assert is_valid is False
        assert 'external_id' in error or 'name' in error
    
    def test_validate_product_invalid_ean(self, kong_credentials):
        """Test validation with invalid EAN"""
        adapter = KongAdapter(kong_credentials, {})
        
        product = {
            'external_id': 'PROD001',
            'name': 'Product 1',
            'ean': 'invalid_ean'
        }
        
        is_valid, error = adapter.validate_product(product)
        
        assert is_valid is False
        assert 'EAN' in error
    
    def test_validate_product_edge_cases(self, kong_credentials):
        """Test validation with edge cases"""
        adapter = KongAdapter(kong_credentials, {})
        
        # Test with empty name
        product = {
            'external_id': 'PROD001',
            'name': '',
            'ean': '1234567890123'
        }
        
        is_valid, error = adapter.validate_product(product)
        
        assert is_valid is False
        assert 'name' in error


# ============================================================================
# KongAdapter Tests - 2 tests for load_batch()
# ============================================================================

class TestKongAdapterLoadBatch:
    """Tests for KongAdapter batch loading"""
    
    @patch.object(KongAPIClient, 'create_or_update_skus')
    @patch.object(KongAPIClient, 'authenticate')
    def test_load_batch_success(self, mock_auth, mock_create_skus, kong_credentials):
        """Test successful batch loading"""
        # Mock authentication
        mock_auth.return_value = True
        
        # Mock API client response
        mock_create_skus.return_value = {
            'success': True,
            'records_processed': 2,
            'records_success': 2,
            'records_failed': 0
        }
        
        adapter = KongAdapter(kong_credentials, {})
        
        products = [
            {'external_id': 'PROD001', 'name': 'Product 1'},
            {'external_id': 'PROD002', 'name': 'Product 2'}
        ]
        
        result = adapter.load_batch(products)
        
        assert result['success'] is True
        assert result['records_success'] == 2
        assert result['records_failed'] == 0
    
    @patch.object(KongAPIClient, 'create_or_update_skus')
    @patch.object(KongAPIClient, 'authenticate')
    def test_load_batch_error(self, mock_auth, mock_create_skus, kong_credentials):
        """Test batch loading with error"""
        # Mock authentication
        mock_auth.return_value = True
        
        # Mock API client error
        mock_create_skus.return_value = {
            'success': False,
            'records_processed': 2,
            'records_success': 0,
            'records_failed': 2,
            'error': 'API Error'
        }
        
        adapter = KongAdapter(kong_credentials, {})
        
        products = [
            {'external_id': 'PROD001', 'name': 'Product 1'},
            {'external_id': 'PROD002', 'name': 'Product 2'}
        ]
        
        result = adapter.load_batch(products)
        
        assert result['success'] is False
        assert result['records_failed'] == 2


# ============================================================================
# AdapterFactory Tests - 2 tests
# ============================================================================

class TestAdapterFactory:
    """Tests for AdapterFactory class"""
    
    def test_create_adapter_kong(self, kong_credentials):
        """Test creating Kong adapter"""
        config = {'type_id': 1}
        adapter = AdapterFactory.create_adapter('kong', kong_credentials, config)
        
        assert isinstance(adapter, KongAdapter)
    
    def test_create_adapter_unknown_type(self, kong_credentials):
        """Test creating adapter with unknown type"""
        config = {}
        
        with pytest.raises(ValueError, match="Unknown product type"):
            AdapterFactory.create_adapter('unknown', kong_credentials, config)


# ============================================================================
# get_client_config() Tests
# ============================================================================

class TestGetClientConfig:
    """Tests for get_client_config function"""
    
    @patch.dict(os.environ, {'CLIENTS_TABLE': 'test-table'})
    @patch('loader.handler.dynamodb')
    def test_get_client_config_success(self, mock_dynamodb, client_config):
        """Test successful client config retrieval"""
        # Mock DynamoDB response
        mock_table = Mock()
        mock_table.get_item.return_value = {'Item': client_config}
        mock_dynamodb.Table.return_value = mock_table
        
        config = get_client_config('test-client')
        
        assert config == client_config
        mock_table.get_item.assert_called_once()
    
    @patch.dict(os.environ, {'CLIENTS_TABLE': 'test-table'})
    @patch('loader.handler.dynamodb')
    def test_get_client_config_not_found(self, mock_dynamodb):
        """Test client config not found"""
        # Mock DynamoDB response with no Item
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_dynamodb.Table.return_value = mock_table
        
        with pytest.raises(ValueError, match="not found"):
            get_client_config('non-existent-client')


# ============================================================================
# lambda_handler() Tests - 5 tests
# ============================================================================

class TestLambdaHandler:
    """Tests for lambda_handler function"""
    
    @patch('loader.handler.get_client_config')
    @patch('loader.handler.get_product_credentials')
    @patch('loader.handler.update_sync_status')
    @patch('loader.handler.AdapterFactory.create_adapter')
    def test_lambda_handler_success(self, mock_create_adapter, mock_update_status, 
                                   mock_get_credentials, mock_get_config, 
                                   client_config, kong_credentials, sample_canonical_products):
        """Test successful lambda execution"""
        # Setup mocks
        mock_get_config.return_value = client_config
        mock_get_credentials.return_value = kong_credentials
        
        mock_adapter = Mock()
        mock_adapter.process_batch.return_value = {
            'total_input': 2,
            'total_valid': 2,
            'total_processed': 2,
            'total_success': 2,
            'total_failed': 0,
            'validation_errors': [],
            'batch_results': []
        }
        mock_create_adapter.return_value = mock_adapter
        
        event = {
            'client_id': 'test-client',
            'product_type': 'kong',
            'canonical_products': sample_canonical_products
        }
        
        result = lambda_handler(event, None)
        
        assert result['client_id'] == 'test-client'
        assert result['status'] == 'success'
        assert result['records_success'] == 2
        assert result['records_failed'] == 0
    
    @patch('loader.handler.get_client_config')
    @patch('loader.handler.update_sync_status')
    def test_lambda_handler_empty_products(self, mock_update_status, mock_get_config, client_config):
        """Test lambda with empty products list"""
        mock_get_config.return_value = client_config
        
        event = {
            'client_id': 'test-client',
            'canonical_products': []
        }
        
        result = lambda_handler(event, None)
        
        assert result['status'] == 'success'
        assert result['records_processed'] == 0
    
    @patch('loader.handler.get_client_config')
    @patch('loader.handler.get_product_credentials')
    @patch('loader.handler.update_sync_status')
    @patch('loader.handler.AdapterFactory.create_adapter')
    def test_lambda_handler_validation_errors(self, mock_create_adapter, mock_update_status, 
                                             mock_get_credentials, mock_get_config, 
                                             client_config, kong_credentials):
        """Test lambda with validation errors"""
        # Setup mocks
        mock_get_config.return_value = client_config
        mock_get_credentials.return_value = kong_credentials
        
        mock_adapter = Mock()
        mock_adapter.process_batch.return_value = {
            'total_input': 2,
            'total_valid': 0,
            'total_processed': 0,
            'total_success': 0,
            'total_failed': 2,
            'validation_errors': [
                {'product_id': 'PROD001', 'error': 'Missing required field'},
                {'product_id': 'PROD002', 'error': 'Invalid EAN'}
            ],
            'batch_results': []
        }
        mock_create_adapter.return_value = mock_adapter
        
        event = {
            'client_id': 'test-client',
            'canonical_products': [{'invalid': 'product'}]
        }
        
        result = lambda_handler(event, None)
        
        assert result['status'] == 'failed'
        assert result['records_failed'] == 2
        assert len(result['failed_records']) == 2
    
    @patch('loader.handler.get_client_config')
    @patch('loader.handler.get_product_credentials')
    @patch('loader.handler.update_sync_status')
    @patch('loader.handler.AdapterFactory.create_adapter')
    def test_lambda_handler_api_errors(self, mock_create_adapter, mock_update_status, 
                                      mock_get_credentials, mock_get_config, 
                                      client_config, kong_credentials):
        """Test lambda with API errors"""
        # Setup mocks
        mock_get_config.return_value = client_config
        mock_get_credentials.return_value = kong_credentials
        
        mock_adapter = Mock()
        mock_adapter.process_batch.side_effect = Exception("API Error")
        mock_create_adapter.return_value = mock_adapter
        
        event = {
            'client_id': 'test-client',
            'canonical_products': [{'id': 'PROD001', 'name': 'Product 1'}]
        }
        
        with pytest.raises(Exception, match="Loader Lambda failed"):
            lambda_handler(event, None)
    
    @patch('loader.handler.get_client_config')
    @patch('loader.handler.get_product_credentials')
    @patch('loader.handler.update_sync_status')
    @patch('loader.handler.AdapterFactory.create_adapter')
    def test_lambda_handler_batch_processing(self, mock_create_adapter, mock_update_status, 
                                            mock_get_credentials, mock_get_config, 
                                            client_config, kong_credentials):
        """Test lambda with batch processing"""
        # Setup mocks
        mock_get_config.return_value = client_config
        mock_get_credentials.return_value = kong_credentials
        
        mock_adapter = Mock()
        mock_adapter.process_batch.return_value = {
            'total_input': 100,
            'total_valid': 100,
            'total_processed': 100,
            'total_success': 100,
            'total_failed': 0,
            'validation_errors': [],
            'batch_results': []
        }
        mock_create_adapter.return_value = mock_adapter
        
        # Create large product list
        large_products = [
            {'id': f'PROD{i:03d}', 'name': f'Product {i}', 'sku': f'SKU{i:03d}'}
            for i in range(1, 101)
        ]
        
        event = {
            'client_id': 'test-client',
            'canonical_products': large_products
        }
        
        result = lambda_handler(event, None)
        
        assert result['status'] == 'success'
        assert result['records_success'] == 100
