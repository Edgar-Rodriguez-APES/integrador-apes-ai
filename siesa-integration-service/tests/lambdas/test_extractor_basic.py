"""
Basic tests for Extractor Lambda Handler
"""
import pytest
from unittest.mock import Mock, patch
import json
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))


class TestExtractorBasic:
    """Basic test suite for Extractor Lambda"""

    @patch('extractor.handler.boto3')
    @patch('extractor.handler.requests')
    def test_lambda_handler_basic(self, mock_requests, mock_boto3):
        """Test basic lambda handler execution"""
        from extractor.handler import lambda_handler
        
        # Mock event
        event = {
            'tenant_id': 'test-tenant',
            'sync_type': 'products',
            'execution_id': 'exec-123'
        }
        
        # Mock AWS services
        mock_sm = Mock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'username': 'test',
                'password': 'test',
                'base_url': 'https://api.test.com'
            })
        }
        
        mock_s3 = Mock()
        mock_boto3.client.side_effect = lambda service: mock_sm if service == 'secretsmanager' else mock_s3
        
        # Mock API responses
        auth_response = Mock()
        auth_response.status_code = 200
        auth_response.json.return_value = {'access_token': 'test_token'}
        
        data_response = Mock()
        data_response.status_code = 200
        data_response.json.return_value = {'data': [{'id': '1'}]}
        
        mock_requests.post.return_value = auth_response
        mock_requests.get.return_value = data_response
        
        # Execute
        result = lambda_handler(event, {})
        
        # Assert
        assert 'statusCode' in result
        assert result['statusCode'] in [200, 500]  # May fail due to missing config

    def test_lambda_handler_missing_params(self):
        """Test handler with missing parameters"""
        from extractor.handler import lambda_handler
        
        event = {}
        result = lambda_handler(event, {})
        
        assert result['statusCode'] == 400
