"""
Unit tests for Extractor Lambda Handler
Tests all functions and classes in extractor/handler.py
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
from moto import mock_dynamodb, mock_secretsmanager
import boto3
import requests
from botocore.exceptions import ClientError

# Import the module to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from extractor.handler import (
    SiesaAPIClient,
    get_client_config,
    get_siesa_credentials,
    extract_all_products,
    lambda_handler
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def siesa_credentials():
    """Sample Siesa credentials"""
    return {
        'username': 'test_user',
        'password': 'test_pass',
        'conniKey': 'test_key',
        'conniToken': 'test_token'
    }


@pytest.fixture
def sample_products():
    """Sample product data"""
    return [
        {
            'f_codigo': 'PROD001',
            'f_nombre': 'Product 1',
            'f_ean': '1234567890123',
            'f_precio': 100.0
        },
        {
            'f_codigo': 'PROD002',
            'f_nombre': 'Product 2',
            'f_ean': '9876543210987',
            'f_precio': 200.0
        }
    ]


@pytest.fixture
def mock_dynamodb_table():
    """Create mock DynamoDB table"""
    with mock_dynamodb():
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        table = dynamodb.create_table(
            TableName='siesa-integration-config-dev',
            KeySchema=[
                {'AttributeName': 'tenantId', 'KeyType': 'HASH'},
                {'AttributeName': 'configType', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'tenantId', 'AttributeType': 'S'},
                {'AttributeName': 'configType', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test data
        table.put_item(Item={
            'tenantId': 'test-client',
            'configType': 'PRODUCT_CONFIG',
            'enabled': 'true',
            'productType': 'kong',
            'siesaConfig': {
                'baseUrl': 'https://api.siesa.com',
                'credentialsSecretArn': 'arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret'
            },
            'lastSyncTimestamp': '2024-01-01T00:00:00Z'
        })
        
        yield table


@pytest.fixture
def mock_secrets_manager():
    """Create mock Secrets Manager"""
    with mock_secretsmanager():
        client = boto3.client('secretsmanager', region_name='us-east-1')
        
        client.create_secret(
            Name='arn:aws:secretsmanager:us-east-1:123456789012:secret:test-secret',
            SecretString=json.dumps({
                'username': 'test_user',
                'password': 'test_pass',
                'conniKey': 'test_key',
                'conniToken': 'test_token'
            })
        )
        
        yield client


# ============================================================================
# SiesaAPIClient Tests
# ============================================================================

class TestSiesaAPIClient:
    """Tests for SiesaAPIClient class"""
    
    def test_create_session(self, siesa_credentials):
        """Test session creation with retry logic"""
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        
        assert client.session is not None
        assert isinstance(client.session, requests.Session)
        assert client.base_url == 'https://api.siesa.com'
        assert client.token is None
    
    def test_base_url_trailing_slash_removed(self, siesa_credentials):
        """Test that trailing slash is removed from base URL"""
        client = SiesaAPIClient('https://api.siesa.com/', siesa_credentials)
        assert client.base_url == 'https://api.siesa.com'
    
    # ========================================================================
    # authenticate() Tests
    # ========================================================================
    
    @patch('extractor.handler.requests.Session.post')
    def test_authenticate_success(self, mock_post, siesa_credentials):
        """Test successful authentication"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'token': 'valid_bearer_token_12345'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        result = client.authenticate()
        
        assert result is True
        assert client.token == 'valid_bearer_token_12345'
        
        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'auth/login' in call_args[0][0]
        assert call_args[1]['json']['username'] == 'test_user'
        assert call_args[1]['headers']['ConniKey'] == 'test_key'
    
    @patch('extractor.handler.requests.Session.post')
    def test_authenticate_no_token_in_response(self, mock_post, siesa_credentials):
        """Test authentication when response has no token"""
        # Mock response without token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success', 'user': 'test'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        
        with pytest.raises(ValueError, match="no token received"):
            client.authenticate()
    
    @patch('extractor.handler.circuit_breaker')
    @patch('extractor.handler.requests.Session.post')
    def test_authenticate_http_error(self, mock_post, mock_cb, siesa_credentials):
        """Test authentication with HTTP error"""
        # Disable circuit breaker for this test
        mock_cb.side_effect = lambda *args, **kwargs: lambda func: func
        
        # Mock HTTP error
        mock_post.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        
        with pytest.raises(requests.exceptions.HTTPError):
            client.authenticate()
    
    @patch('extractor.handler.circuit_breaker')
    @patch('extractor.handler.requests.Session.post')
    def test_authenticate_invalid_token_format(self, mock_post, mock_cb, siesa_credentials):
        """Test authentication with invalid token format"""
        # Disable circuit breaker for this test
        mock_cb.side_effect = lambda *args, **kwargs: lambda func: func
        
        # Mock response with invalid token
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'token': 'short'}  # Too short
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        
        with pytest.raises(ValueError, match="Invalid token format"):
            client.authenticate()
    
    # ========================================================================
    # get_products() Tests
    # ========================================================================
    
    @patch('extractor.handler.requests.Session.get')
    def test_get_products_success(self, mock_get, siesa_credentials, sample_products):
        """Test successful product retrieval"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': sample_products,
            'totalRegistros': 2
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        client.token = 'valid_token'
        
        result = client.get_products(page=1, page_size=100)
        
        assert 'products' in result
        assert 'pagination' in result
        assert len(result['products']) == 2
        assert result['pagination']['current_page'] == 1
        assert result['pagination']['total_records'] == 2
    
    @patch('extractor.handler.requests.Session.get')
    def test_get_products_with_pagination(self, mock_get, siesa_credentials, sample_products):
        """Test product retrieval with pagination"""
        # Mock response with full page (has_more = True)
        mock_response = Mock()
        mock_response.status_code = 200
        # Return exactly page_size products to trigger has_more
        products = sample_products * 50  # 100 products
        mock_response.json.return_value = {
            'data': products,
            'totalRegistros': 200
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        client.token = 'valid_token'
        
        result = client.get_products(page=1, page_size=100)
        
        assert result['pagination']['has_more'] is True
        assert len(result['products']) == 100
    
    @patch('extractor.handler.requests.Session.get')
    def test_get_products_empty_response(self, mock_get, siesa_credentials):
        """Test product retrieval with empty response"""
        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        client.token = 'valid_token'
        
        result = client.get_products(page=1, page_size=100)
        
        assert len(result['products']) == 0
        assert result['pagination']['has_more'] is False
    
    @patch('extractor.handler.requests.Session.get')
    def test_get_products_large_dataset(self, mock_get, siesa_credentials):
        """Test product retrieval with large dataset"""
        # Mock large response
        mock_response = Mock()
        mock_response.status_code = 200
        large_products = [
            {'f_codigo': f'PROD{i:04d}', 'f_nombre': f'Product {i}'}
            for i in range(1000)
        ]
        mock_response.json.return_value = {
            'data': large_products,
            'totalRegistros': 1000
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        client.token = 'valid_token'
        
        result = client.get_products(page=1, page_size=1000)
        
        assert len(result['products']) == 1000
    
    @patch('extractor.handler.requests.Session.get')
    def test_get_products_http_error(self, mock_get, siesa_credentials):
        """Test product retrieval with HTTP error"""
        # Mock HTTP error
        mock_get.side_effect = requests.exceptions.HTTPError("500 Server Error")
        
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        client.token = 'valid_token'
        
        with pytest.raises(requests.exceptions.HTTPError):
            client.get_products(page=1, page_size=100)
    
    @patch('extractor.handler.requests.Session.get')
    def test_get_products_with_modified_since(self, mock_get, siesa_credentials, sample_products):
        """Test product retrieval with modified_since filter"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'data': sample_products}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        client.token = 'valid_token'
        
        result = client.get_products(
            page=1,
            page_size=100,
            modified_since='2024-01-01T00:00:00Z'
        )
        
        assert len(result['products']) == 2
        # Verify modified_since was passed in params
        call_args = mock_get.call_args
        assert 'fechaModificacion' in call_args[1]['params']


# ============================================================================
# get_client_config() Tests
# ============================================================================

class TestGetClientConfig:
    """Tests for get_client_config function"""
    
    @patch.dict(os.environ, {'CLIENTS_TABLE': 'siesa-integration-config-dev'})
    @patch('extractor.handler.dynamodb')
    def test_get_client_config_success(self, mock_dynamodb):
        """Test successful client config retrieval"""
        # Mock DynamoDB response
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'tenantId': 'test-client',
                'configType': 'PRODUCT_CONFIG',
                'enabled': 'true',
                'productType': 'kong',
                'siesaConfig': {
                    'baseUrl': 'https://api.siesa.com',
                    'credentialsSecretArn': 'test-secret'
                }
            }
        }
        mock_dynamodb.Table.return_value = mock_table
        
        config = get_client_config('test-client')
        
        assert config is not None
        assert config['tenantId'] == 'test-client'
        assert config['enabled'] == 'true'
        assert 'siesaConfig' in config
    
    @patch.dict(os.environ, {'CLIENTS_TABLE': 'siesa-integration-config-dev'})
    @patch('extractor.handler.dynamodb')
    def test_get_client_config_not_found(self, mock_dynamodb):
        """Test client config not found"""
        # Mock DynamoDB response with no Item
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_dynamodb.Table.return_value = mock_table
        
        with pytest.raises(ValueError, match="not found"):
            get_client_config('non-existent-client')
    
    @patch.dict(os.environ, {'CLIENTS_TABLE': 'siesa-integration-config-dev'})
    @patch('extractor.handler.dynamodb')
    def test_get_client_config_disabled(self, mock_dynamodb):
        """Test disabled client"""
        # Mock DynamoDB response with disabled client
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'tenantId': 'disabled-client',
                'configType': 'PRODUCT_CONFIG',
                'enabled': 'false'
            }
        }
        mock_dynamodb.Table.return_value = mock_table
        
        with pytest.raises(ValueError, match="disabled"):
            get_client_config('disabled-client')
    
    @patch.dict(os.environ, {'CLIENTS_TABLE': 'siesa-integration-config-dev'})
    @patch('extractor.handler.dynamodb')
    def test_get_client_config_dynamodb_error(self, mock_dynamodb):
        """Test DynamoDB error handling"""
        # Mock DynamoDB error
        mock_table = Mock()
        mock_table.get_item.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetItem'
        )
        mock_dynamodb.Table.return_value = mock_table
        
        with pytest.raises(ClientError):
            get_client_config('test-client')


# ============================================================================
# get_siesa_credentials() Tests
# ============================================================================

class TestGetSiesaCredentials:
    """Tests for get_siesa_credentials function"""
    
    @patch('extractor.handler.secrets_manager')
    def test_get_siesa_credentials_success(self, mock_sm):
        """Test successful credentials retrieval"""
        # Mock Secrets Manager response
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'username': 'test_user',
                'password': 'test_pass',
                'conniKey': 'test_key',
                'conniToken': 'test_token'
            })
        }
        
        credentials = get_siesa_credentials('test-secret')
        
        assert credentials is not None
        assert credentials['username'] == 'test_user'
        assert credentials['password'] == 'test_pass'
        assert 'conniKey' in credentials
    
    @patch('extractor.handler.secrets_manager')
    def test_get_siesa_credentials_not_found(self, mock_sm):
        """Test credentials not found"""
        # Mock secret not found error
        mock_sm.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetSecretValue'
        )
        
        with pytest.raises(ClientError):
            get_siesa_credentials('non-existent-secret')
    
    @patch('extractor.handler.secrets_manager')
    def test_get_siesa_credentials_no_string_value(self, mock_sm):
        """Test secret with no string value"""
        # Mock response without SecretString
        mock_sm.get_secret_value.return_value = {'SecretBinary': b'binary_data'}
        
        with pytest.raises(ValueError, match="no string value"):
            get_siesa_credentials('test-secret')


# ============================================================================
# extract_all_products() Tests
# ============================================================================

class TestExtractAllProducts:
    """Tests for extract_all_products function"""
    
    def test_extract_all_products_single_page(self, siesa_credentials, sample_products):
        """Test extraction with single page"""
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        client.token = 'valid_token'
        
        # Mock get_products to return single page
        with patch.object(client, 'get_products') as mock_get:
            mock_get.return_value = {
                'products': sample_products,
                'pagination': {'has_more': False}
            }
            
            products = extract_all_products(client, 'initial')
            
            assert len(products) == 2
            mock_get.assert_called_once()
    
    def test_extract_all_products_multiple_pages(self, siesa_credentials, sample_products):
        """Test extraction with multiple pages"""
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        client.token = 'valid_token'
        
        # Mock get_products to return multiple pages
        with patch.object(client, 'get_products') as mock_get:
            mock_get.side_effect = [
                {
                    'products': sample_products,
                    'pagination': {'has_more': True}
                },
                {
                    'products': sample_products,
                    'pagination': {'has_more': True}
                },
                {
                    'products': sample_products,
                    'pagination': {'has_more': False}
                }
            ]
            
            products = extract_all_products(client, 'initial')
            
            assert len(products) == 6  # 3 pages * 2 products
            assert mock_get.call_count == 3
    
    def test_extract_all_products_incremental_sync(self, siesa_credentials, sample_products):
        """Test incremental sync with timestamp"""
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        client.token = 'valid_token'
        
        # Mock get_products
        with patch.object(client, 'get_products') as mock_get:
            mock_get.return_value = {
                'products': sample_products,
                'pagination': {'has_more': False}
            }
            
            products = extract_all_products(
                client,
                'incremental',
                last_sync_timestamp='2024-01-01T00:00:00Z'
            )
            
            assert len(products) == 2
            # Verify modified_since was passed
            call_args = mock_get.call_args
            assert call_args[1]['modified_since'] == '2024-01-01T00:00:00Z'
    
    def test_extract_all_products_max_page_limit(self, siesa_credentials, sample_products):
        """Test safety limit for maximum pages"""
        client = SiesaAPIClient('https://api.siesa.com', siesa_credentials)
        client.token = 'valid_token'
        
        # Mock get_products to always return has_more=True
        with patch.object(client, 'get_products') as mock_get:
            mock_get.return_value = {
                'products': sample_products,
                'pagination': {'has_more': True}
            }
            
            products = extract_all_products(client, 'initial')
            
            # Should stop at page 1000
            assert mock_get.call_count == 1000


# ============================================================================
# lambda_handler() Tests
# ============================================================================

class TestLambdaHandler:
    """Tests for lambda_handler function"""
    
    @patch.dict(os.environ, {'CLIENTS_TABLE': 'siesa-integration-config-dev'})
    @patch('extractor.handler.get_client_config')
    @patch('extractor.handler.get_siesa_credentials')
    @patch('extractor.handler.SiesaAPIClient')
    @patch('extractor.handler.extract_all_products')
    def test_lambda_handler_success(
        self,
        mock_extract,
        mock_client_class,
        mock_get_creds,
        mock_get_config,
        sample_products
    ):
        """Test successful lambda execution"""
        # Setup mocks
        mock_get_config.return_value = {
            'tenantId': 'test-client',
            'enabled': 'true',
            'productType': 'kong',
            'siesaConfig': {
                'baseUrl': 'https://api.siesa.com',
                'credentialsSecretArn': 'test-secret'
            }
        }
        mock_get_creds.return_value = {
            'username': 'test',
            'password': 'test'
        }
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        mock_extract.return_value = sample_products
        
        # Execute
        event = {'client_id': 'test-client', 'sync_type': 'initial'}
        result = lambda_handler(event, None)
        
        # Verify
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['client_id'] == 'test-client'
        assert body['count'] == 2
        assert 'products' in body
    
    def test_lambda_handler_missing_client_id(self):
        """Test lambda with missing client_id"""
        event = {'sync_type': 'initial'}
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert 'error' in body
        assert 'client_id' in body['message']
    
    @patch.dict(os.environ, {'CLIENTS_TABLE': 'siesa-integration-config-dev'})
    @patch('extractor.handler.get_client_config')
    def test_lambda_handler_client_not_found(self, mock_get_config):
        """Test lambda with non-existent client"""
        mock_get_config.side_effect = ValueError("Client configuration not found")
        
        event = {'client_id': 'non-existent', 'sync_type': 'initial'}
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 400
        body = json.loads(result['body'])
        assert body['error'] == 'ValidationError'
    
    @patch.dict(os.environ, {'CLIENTS_TABLE': 'siesa-integration-config-dev'})
    @patch('extractor.handler.get_client_config')
    @patch('extractor.handler.get_siesa_credentials')
    @patch('extractor.handler.SiesaAPIClient')
    def test_lambda_handler_authentication_error(
        self,
        mock_client_class,
        mock_get_creds,
        mock_get_config
    ):
        """Test lambda with authentication error"""
        # Setup mocks
        mock_get_config.return_value = {
            'siesaConfig': {
                'baseUrl': 'https://api.siesa.com',
                'credentialsSecretArn': 'test-secret'
            }
        }
        mock_get_creds.return_value = {'username': 'test', 'password': 'test'}
        mock_client = Mock()
        mock_client.authenticate.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_client_class.return_value = mock_client
        
        # Execute
        event = {'client_id': 'test-client', 'sync_type': 'initial'}
        result = lambda_handler(event, None)
        
        # Verify
        assert result['statusCode'] == 500
        body = json.loads(result['body'])
        assert 'error' in body
    
    @patch.dict(os.environ, {'CLIENTS_TABLE': 'siesa-integration-config-dev'})
    @patch('extractor.handler.get_client_config')
    @patch('extractor.handler.get_siesa_credentials')
    @patch('extractor.handler.SiesaAPIClient')
    @patch('extractor.handler.extract_all_products')
    def test_lambda_handler_pagination_success(
        self,
        mock_extract,
        mock_client_class,
        mock_get_creds,
        mock_get_config
    ):
        """Test lambda with pagination"""
        # Setup mocks
        mock_get_config.return_value = {
            'siesaConfig': {
                'baseUrl': 'https://api.siesa.com',
                'credentialsSecretArn': 'test-secret'
            },
            'productType': 'kong'
        }
        mock_get_creds.return_value = {'username': 'test', 'password': 'test'}
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client_class.return_value = mock_client
        
        # Return large dataset
        large_products = [
            {'f_codigo': f'PROD{i:04d}', 'f_nombre': f'Product {i}'}
            for i in range(250)
        ]
        mock_extract.return_value = large_products
        
        # Execute
        event = {'client_id': 'test-client', 'sync_type': 'initial'}
        result = lambda_handler(event, None)
        
        # Verify
        assert result['statusCode'] == 200
        body = json.loads(result['body'])
        assert body['count'] == 250
