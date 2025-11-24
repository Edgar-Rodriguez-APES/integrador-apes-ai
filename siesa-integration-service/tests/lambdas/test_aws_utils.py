"""
Tests for AWS utilities
"""
import pytest
from unittest.mock import Mock, patch
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from common.aws_utils import (
    get_secret,
    get_s3_object,
    put_s3_object,
    get_dynamodb_item,
    put_dynamodb_item,
    send_sns_notification
)


class TestAWSUtils:
    """Test suite for AWS utilities"""

    @patch('common.aws_utils.boto3')
    def test_get_secret_success(self, mock_boto3):
        """Test successful secret retrieval"""
        # Mock Secrets Manager
        mock_sm = Mock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({'key': 'value'})
        }
        mock_boto3.client.return_value = mock_sm
        
        # Execute
        result = get_secret('test-secret')
        
        # Assert
        assert result == {'key': 'value'}
        mock_sm.get_secret_value.assert_called_once()

    @patch('common.aws_utils.boto3')
    def test_get_s3_object_success(self, mock_boto3):
        """Test successful S3 object retrieval"""
        # Mock S3
        mock_s3 = Mock()
        mock_s3.get_object.return_value = {
            'Body': Mock(read=lambda: b'test data')
        }
        mock_boto3.client.return_value = mock_s3
        
        # Execute
        result = get_s3_object('test-bucket', 'test-key')
        
        # Assert
        assert result == b'test data'

    @patch('common.aws_utils.boto3')
    def test_put_s3_object_success(self, mock_boto3):
        """Test successful S3 object upload"""
        # Mock S3
        mock_s3 = Mock()
        mock_boto3.client.return_value = mock_s3
        
        # Execute
        result = put_s3_object('test-bucket', 'test-key', b'test data')
        
        # Assert
        assert result is True
        mock_s3.put_object.assert_called_once()

    @patch('common.aws_utils.boto3')
    def test_get_dynamodb_item_success(self, mock_boto3):
        """Test successful DynamoDB item retrieval"""
        # Mock DynamoDB
        mock_ddb = Mock()
        mock_ddb.get_item.return_value = {
            'Item': {'id': {'S': 'test-id'}}
        }
        mock_boto3.client.return_value = mock_ddb
        
        # Execute
        result = get_dynamodb_item('test-table', {'id': 'test-id'})
        
        # Assert
        assert result is not None

    @patch('common.aws_utils.boto3')
    def test_put_dynamodb_item_success(self, mock_boto3):
        """Test successful DynamoDB item put"""
        # Mock DynamoDB
        mock_ddb = Mock()
        mock_boto3.client.return_value = mock_ddb
        
        # Execute
        result = put_dynamodb_item('test-table', {'id': 'test-id', 'data': 'test'})
        
        # Assert
        assert result is True
        mock_ddb.put_item.assert_called_once()

    @patch('common.aws_utils.boto3')
    def test_send_sns_notification_success(self, mock_boto3):
        """Test successful SNS notification"""
        # Mock SNS
        mock_sns = Mock()
        mock_boto3.client.return_value = mock_sns
        
        # Execute
        result = send_sns_notification('test-topic-arn', 'Test message', 'Test subject')
        
        # Assert
        assert result is True
        mock_sns.publish.assert_called_once()

    @patch('common.aws_utils.boto3')
    def test_get_secret_error(self, mock_boto3):
        """Test secret retrieval error"""
        # Mock Secrets Manager error
        mock_sm = Mock()
        mock_sm.get_secret_value.side_effect = Exception('Secret not found')
        mock_boto3.client.return_value = mock_sm
        
        # Execute and assert
        with pytest.raises(Exception):
            get_secret('non-existent-secret')

    @patch('common.aws_utils.boto3')
    def test_get_s3_object_error(self, mock_boto3):
        """Test S3 object retrieval error"""
        # Mock S3 error
        mock_s3 = Mock()
        mock_s3.get_object.side_effect = Exception('Object not found')
        mock_boto3.client.return_value = mock_s3
        
        # Execute and assert
        with pytest.raises(Exception):
            get_s3_object('test-bucket', 'non-existent-key')

    @patch('common.aws_utils.boto3')
    def test_put_s3_object_error(self, mock_boto3):
        """Test S3 object upload error"""
        # Mock S3 error
        mock_s3 = Mock()
        mock_s3.put_object.side_effect = Exception('Upload failed')
        mock_boto3.client.return_value = mock_s3
        
        # Execute
        result = put_s3_object('test-bucket', 'test-key', b'test data')
        
        # Assert
        assert result is False
