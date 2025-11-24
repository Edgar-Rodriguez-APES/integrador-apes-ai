"""
Tests for logging utilities
"""
import pytest
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

from common.logging_utils import (
    get_safe_logger,
    log_with_context,
    mask_sensitive_data,
    format_log_message
)


class TestLoggingUtils:
    """Test suite for logging utilities"""

    def test_get_safe_logger(self):
        """Test safe logger creation"""
        logger = get_safe_logger('test_module')
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == 'test_module'

    def test_mask_sensitive_data_password(self):
        """Test masking password in data"""
        data = {
            'username': 'test_user',
            'password': 'secret123',
            'email': 'test@example.com'
        }
        
        masked = mask_sensitive_data(data)
        
        assert masked['username'] == 'test_user'
        assert masked['password'] == '***MASKED***'
        assert masked['email'] == 'test@example.com'

    def test_mask_sensitive_data_api_key(self):
        """Test masking API key in data"""
        data = {
            'api_key': 'abc123xyz',
            'name': 'Test'
        }
        
        masked = mask_sensitive_data(data)
        
        assert masked['api_key'] == '***MASKED***'
        assert masked['name'] == 'Test'

    def test_mask_sensitive_data_token(self):
        """Test masking token in data"""
        data = {
            'access_token': 'token123',
            'user_id': '12345'
        }
        
        masked = mask_sensitive_data(data)
        
        assert masked['access_token'] == '***MASKED***'
        assert masked['user_id'] == '12345'

    def test_mask_sensitive_data_nested(self):
        """Test masking sensitive data in nested dict"""
        data = {
            'user': {
                'name': 'Test User',
                'password': 'secret'
            },
            'config': {
                'api_key': 'key123'
            }
        }
        
        masked = mask_sensitive_data(data)
        
        assert masked['user']['password'] == '***MASKED***'
        assert masked['config']['api_key'] == '***MASKED***'
        assert masked['user']['name'] == 'Test User'

    def test_format_log_message_simple(self):
        """Test simple log message formatting"""
        message = format_log_message('Test message', {'key': 'value'})
        
        assert 'Test message' in message
        assert 'key' in message

    def test_format_log_message_with_context(self):
        """Test log message formatting with context"""
        context = {
            'tenant_id': 'test-tenant',
            'execution_id': 'exec-123'
        }
        
        message = format_log_message('Processing data', context)
        
        assert 'Processing data' in message
        assert 'test-tenant' in message
        assert 'exec-123' in message

    def test_log_with_context(self, caplog):
        """Test logging with context"""
        logger = get_safe_logger('test')
        context = {'tenant_id': 'test-tenant'}
        
        with caplog.at_level(logging.INFO):
            log_with_context(logger, 'info', 'Test message', context)
        
        assert 'Test message' in caplog.text

    def test_mask_sensitive_data_empty_dict(self):
        """Test masking with empty dict"""
        data = {}
        masked = mask_sensitive_data(data)
        
        assert masked == {}

    def test_mask_sensitive_data_no_sensitive_fields(self):
        """Test masking with no sensitive fields"""
        data = {
            'name': 'Test',
            'id': '123',
            'status': 'active'
        }
        
        masked = mask_sensitive_data(data)
        
        assert masked == data

    def test_format_log_message_with_error(self):
        """Test log message formatting with error"""
        try:
            raise ValueError('Test error')
        except ValueError as e:
            message = format_log_message('Error occurred', {'error': str(e)})
            
            assert 'Error occurred' in message
            assert 'Test error' in message
