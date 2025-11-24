"""
Unit tests for Extractor Lambda Handler
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import sys
import os
import requests

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from extractor.handler import SiesaAPIClient, lambda_handler


class TestSiesaAPIClient:
    """Test suite for SiesaAPIClient"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return SiesaAPIClient(
            'https://test.siesa.com',
            {
                'username': 'test_user',
                'password': 'test_pass',
                'conniKey': 'test_key',
                'conniToken': 'test_token'
            }
        )

    def test_authenticate_success(self, client):
        """Test successful authentication"""
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {'token': 'test_access_token_12345'}
        mock_resp.raise_for_status = Mock()
        
        with patch.object(client.session, 'post', return_value=mock_resp):
            result = client.authenticate()
            
            assert result is True
            assert client.token == 'test_access_token_12345'

    def test_authenticate_with_access_token_key(self, client):
        """Test authentication with access_token key"""
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {'access_token': 'bearer_token_xyz'}
        mock_resp.raise_for_status = Mock()
        
        with patch.object(client.session, 'post', return_value=mock_resp):
            result = client.authenticate()
            
            assert result is True
            assert client.token == 'bearer_token_xyz'

    def test_authenticate_no_token(self, client):
        """Test authentication failure when no token returned"""
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {'status': 'ok'}  # No token
        mock_resp.raise_for_status = Mock()
        
        with patch.object(client.session, 'post', return_value=mock_resp):
            with pytest.raises(ValueError, match="no token received"):
                client.authenticate()

    def test_authenticate_invalid_token_format(self, client):
        """Test authentication with invalid token format"""
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = {'token': '123'}  # Too short
        mock_resp.raise_for_status = Mock()
        
        with patch.object(client.session, 'post', return_value=mock_resp):
            with pytest.raises(ValueError, match="Invalid token format"):
                client.authenticate()

    def test_authenticate_http_error(self, client):
        """Test authentication with HTTP error"""
        mock_resp = Mock(status_code=401)
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        
        with patch.object(client.session, 'post', return_value=mock_resp):
            with pytest.raises(requests.exceptions.HTTPError):
                client.authenticate()

    def test_authenticate_timeout(self, client):
        """Test authentication timeout"""
        with patch.object(client.session, 'post', side_effect=requests.exceptions.Timeout):
            with pytest.raises(requests.exceptions.Timeout):
                client.authenticate()

    def test_create_session_with_retry(self, client):
        """Test session creation with retry logic"""
        assert client.session is not None
        assert len(client.session.adapters) > 0

    def test_base_url_trailing_slash(self):
        """Test base URL trailing slash removal"""
        client = SiesaAPIClient(
            'https://test.siesa.com/',
            {'username': 'test', 'password': 'test'}
        )
        assert client.base_url == 'https://test.siesa.com'

    @patch('extractor.handler.requests.Session')
    def test_session_retry_configuration(self, mock_session_class):
        """Test retry configuration"""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        client = SiesaAPIClient(
            'https://test.com',
            {'username': 'test', 'password': 'test'}
        )
        
        # Verify session was created
        assert mock_session_class.called


class TestLambdaHandler:
    """Test suite for Lambda handler"""

    @patch('extractor.handler.dynamodb')
    @patch('extractor.handler.secrets_manager')
    @patch('extractor.handler.SiesaAPIClient')
    def test_lambda_handler_success(self, mock_client_class, mock_sm, mock_ddb):
        """Test successful lambda handler execution"""
        # Mock event
        event = {
            'client_id': 'test-client',
            'sync_type': 'full'
        }
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'tenantId': 'test-client',
                'productType': 'kong',
                'siesaConfig': {
                    'baseUrl': 'https://test.com',
                    'credentialsSecretArn': 'arn:aws:secretsmanager:us-east-1:123:secret:test'
                }
            }
        }
        mock_ddb.Table.return_value = mock_table
        
        # Mock Secrets Manager
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'username': 'test',
                'password': 'test'
            })
        }
        
        # Mock Siesa API Client
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client.get_products.return_value = {
            'products': [{'f_codigo': '001', 'f_nombre': 'Product 1'}],
            'pagination': {'has_more': False}
        }
        mock_client_class.return_value = mock_client
        
        # Execute
        result = lambda_handler(event, None)
        
        # Assert
        assert result['client_id'] == 'test-client'
        assert 'products' in result
        assert len(result['products']) == 1

    @patch('extractor.handler.dynamodb')
    def test_lambda_handler_missing_client_id(self, mock_ddb):
        """Test handler with missing client_id"""
        event = {'sync_type': 'full'}
        
        result = lambda_handler(event, None)
        
        assert 'error' in result
        assert 'client_id' in result['error'].lower()

    @patch('extractor.handler.dynamodb')
    def test_lambda_handler_client_not_found(self, mock_ddb):
        """Test handler when client config not found"""
        event = {
            'client_id': 'non-existent',
            'sync_type': 'full'
        }
        
        mock_table = Mock()
        mock_table.get_item.return_value = {}  # No Item
        mock_ddb.Table.return_value = mock_table
        
        result = lambda_handler(event, None)
        
        assert 'error' in result

    @patch('extractor.handler.dynamodb')
    @patch('extractor.handler.secrets_manager')
    def test_lambda_handler_secrets_error(self, mock_sm, mock_ddb):
        """Test handler with secrets manager error"""
        event = {
            'client_id': 'test-client',
            'sync_type': 'full'
        }
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'tenantId': 'test-client',
                'siesaConfig': {
                    'baseUrl': 'https://test.com',
                    'credentialsSecretArn': 'arn:aws:secretsmanager:us-east-1:123:secret:test'
                }
            }
        }
        mock_ddb.Table.return_value = mock_table
        
        # Mock Secrets Manager error
        mock_sm.get_secret_value.side_effect = Exception('Secret not found')
        
        result = lambda_handler(event, None)
        
        assert 'error' in result

    @patch('extractor.handler.dynamodb')
    @patch('extractor.handler.secrets_manager')
    @patch('extractor.handler.SiesaAPIClient')
    def test_lambda_handler_authentication_failure(self, mock_client_class, mock_sm, mock_ddb):
        """Test handler with authentication failure"""
        event = {
            'client_id': 'test-client',
            'sync_type': 'full'
        }
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'tenantId': 'test-client',
                'siesaConfig': {
                    'baseUrl': 'https://test.com',
                    'credentialsSecretArn': 'arn:aws:secretsmanager:us-east-1:123:secret:test'
                }
            }
        }
        mock_ddb.Table.return_value = mock_table
        
        # Mock Secrets Manager
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'test', 'password': 'test'})
        }
        
        # Mock authentication failure
        mock_client = Mock()
        mock_client.authenticate.side_effect = Exception('Auth failed')
        mock_client_class.return_value = mock_client
        
        result = lambda_handler(event, None)
        
        assert 'error' in result

    @patch('extractor.handler.dynamodb')
    @patch('extractor.handler.secrets_manager')
    @patch('extractor.handler.SiesaAPIClient')
    def test_lambda_handler_with_pagination(self, mock_client_class, mock_sm, mock_ddb):
        """Test handler with paginated results"""
        event = {
            'client_id': 'test-client',
            'sync_type': 'full'
        }
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'tenantId': 'test-client',
                'siesaConfig': {
                    'baseUrl': 'https://test.com',
                    'credentialsSecretArn': 'arn:aws:secretsmanager:us-east-1:123:secret:test'
                }
            }
        }
        mock_ddb.Table.return_value = mock_table
        
        # Mock Secrets Manager
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'test', 'password': 'test'})
        }
        
        # Mock paginated responses
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client.get_products.side_effect = [
            {
                'products': [{'f_codigo': str(i)} for i in range(100)],
                'pagination': {'has_more': True, 'page': 1}
            },
            {
                'products': [{'f_codigo': str(i)} for i in range(100, 150)],
                'pagination': {'has_more': False, 'page': 2}
            }
        ]
        mock_client_class.return_value = mock_client
        
        result = lambda_handler(event, None)
        
        assert len(result['products']) == 150

    @patch('extractor.handler.dynamodb')
    @patch('extractor.handler.secrets_manager')
    @patch('extractor.handler.SiesaAPIClient')
    def test_lambda_handler_incremental_sync(self, mock_client_class, mock_sm, mock_ddb):
        """Test handler with incremental sync"""
        event = {
            'client_id': 'test-client',
            'sync_type': 'incremental',
            'last_sync_timestamp': '2025-01-01T00:00:00Z'
        }
        
        # Mock DynamoDB
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'tenantId': 'test-client',
                'siesaConfig': {
                    'baseUrl': 'https://test.com',
                    'credentialsSecretArn': 'arn:aws:secretsmanager:us-east-1:123:secret:test'
                }
            }
        }
        mock_ddb.Table.return_value = mock_table
        
        # Mock Secrets Manager
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'username': 'test', 'password': 'test'})
        }
        
        # Mock client
        mock_client = Mock()
        mock_client.authenticate.return_value = True
        mock_client.get_products.return_value = {
            'products': [{'f_codigo': '001'}],
            'pagination': {'has_more': False}
        }
        mock_client_class.return_value = mock_client
        
        result = lambda_handler(event, None)
        
        assert result['sync_type'] == 'incremental'
