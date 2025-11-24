"""
Tests for Extractor Lambda Handler
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime

# Import the handler
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from extractor.handler import (
    lambda_handler,
    extract_from_siesa,
    get_siesa_credentials,
    authenticate_siesa,
    fetch_products,
    fetch_inventory,
    save_to_s3
)


class TestExtractorHandler:
    """Test suite for Extractor Lambda handler"""

    @patch('extractor.handler.boto3')
    @patch('extractor.handler.requests')
    def test_lambda_handler_success(self, mock_requests, mock_boto3):
        """Test successful lambda handler execution"""
        # Mock event
        event = {
            'tenant_id': 'test-tenant',
            'sync_type': 'products',
            'execution_id': 'exec-123'
        }
        
        # Mock AWS services
        mock_s3 = Mock()
        mock_boto3.client.return_value = mock_s3
        
        # Mock Siesa API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{'id': '1', 'name': 'Product 1'}]
        }
        mock_requests.post.return_value = mock_response
        mock_requests.get.return_value = mock_response
        
        # Execute
        result = lambda_handler(event, {})
        
        # Assert
        assert result['statusCode'] == 200
        assert 'records_extracted' in json.loads(result['body'])

    def test_lambda_handler_missing_tenant_id(self):
        """Test handler with missing tenant_id"""
        event = {
            'sync_type': 'products'
        }
        
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
        assert 'tenant_id' in result['body']

    @patch('extractor.handler.boto3')
    def test_get_siesa_credentials_success(self, mock_boto3):
        """Test successful credential retrieval"""
        # Mock Secrets Manager
        mock_sm = Mock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'username': 'test_user',
                'password': 'test_pass',
                'api_key': 'test_key'
            })
        }
        mock_boto3.client.return_value = mock_sm
        
        # Execute
        creds = get_siesa_credentials('test-tenant')
        
        # Assert
        assert creds['username'] == 'test_user'
        assert creds['password'] == 'test_pass'
        assert creds['api_key'] == 'test_key'

    @patch('extractor.handler.requests')
    def test_authenticate_siesa_success(self, mock_requests):
        """Test successful Siesa authentication"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_requests.post.return_value = mock_response
        
        # Execute
        credentials = {
            'username': 'test_user',
            'password': 'test_pass',
            'base_url': 'https://api.siesa.com'
        }
        token = authenticate_siesa(credentials)
        
        # Assert
        assert token == 'test_token'

    @patch('extractor.handler.requests')
    def test_fetch_products_success(self, mock_requests):
        """Test successful product fetching"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'id': '1', 'name': 'Product 1'},
                {'id': '2', 'name': 'Product 2'}
            ],
            'total': 2
        }
        mock_requests.get.return_value = mock_response
        
        # Execute
        products = fetch_products('test_token', 'https://api.siesa.com')
        
        # Assert
        assert len(products) == 2
        assert products[0]['id'] == '1'

    @patch('extractor.handler.requests')
    def test_fetch_inventory_success(self, mock_requests):
        """Test successful inventory fetching"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'product_id': '1', 'quantity': 100},
                {'product_id': '2', 'quantity': 50}
            ]
        }
        mock_requests.get.return_value = mock_response
        
        # Execute
        inventory = fetch_inventory('test_token', 'https://api.siesa.com')
        
        # Assert
        assert len(inventory) == 2
        assert inventory[0]['quantity'] == 100

    @patch('extractor.handler.boto3')
    def test_save_to_s3_success(self, mock_boto3):
        """Test successful S3 save"""
        # Mock S3
        mock_s3 = Mock()
        mock_boto3.client.return_value = mock_s3
        
        # Execute
        data = [{'id': '1', 'name': 'Product 1'}]
        result = save_to_s3(data, 'test-bucket', 'test-key')
        
        # Assert
        assert result is True
        mock_s3.put_object.assert_called_once()

    @patch('extractor.handler.requests')
    def test_authenticate_siesa_failure(self, mock_requests):
        """Test Siesa authentication failure"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_requests.post.return_value = mock_response
        
        # Execute and assert
        credentials = {
            'username': 'test_user',
            'password': 'wrong_pass',
            'base_url': 'https://api.siesa.com'
        }
        
        with pytest.raises(Exception):
            authenticate_siesa(credentials)

    @patch('extractor.handler.requests')
    def test_fetch_products_api_error(self, mock_requests):
        """Test product fetching with API error"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_requests.get.return_value = mock_response
        
        # Execute and assert
        with pytest.raises(Exception):
            fetch_products('test_token', 'https://api.siesa.com')

    @patch('extractor.handler.boto3')
    def test_save_to_s3_failure(self, mock_boto3):
        """Test S3 save failure"""
        # Mock S3 error
        mock_s3 = Mock()
        mock_s3.put_object.side_effect = Exception('S3 Error')
        mock_boto3.client.return_value = mock_s3
        
        # Execute
        data = [{'id': '1'}]
        result = save_to_s3(data, 'test-bucket', 'test-key')
        
        # Assert
        assert result is False

    def test_extract_from_siesa_invalid_sync_type(self):
        """Test extraction with invalid sync type"""
        with pytest.raises(ValueError):
            extract_from_siesa('test-tenant', 'invalid_type', 'exec-123')

    @patch('extractor.handler.boto3')
    @patch('extractor.handler.requests')
    def test_lambda_handler_with_pagination(self, mock_requests, mock_boto3):
        """Test handler with paginated results"""
        event = {
            'tenant_id': 'test-tenant',
            'sync_type': 'products',
            'execution_id': 'exec-123',
            'page_size': 100
        }
        
        # Mock paginated responses
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            'data': [{'id': str(i)} for i in range(100)],
            'has_more': True
        }
        
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            'data': [{'id': str(i)} for i in range(100, 150)],
            'has_more': False
        }
        
        mock_requests.get.side_effect = [mock_response1, mock_response2]
        mock_requests.post.return_value = Mock(
            status_code=200,
            json=lambda: {'access_token': 'token'}
        )
        
        mock_boto3.client.return_value = Mock()
        
        # Execute
        result = lambda_handler(event, {})
        
        # Assert
        assert result['statusCode'] == 200
