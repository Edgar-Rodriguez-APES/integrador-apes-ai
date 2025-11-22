"""
Secure logging utilities
Filters sensitive data from logs to prevent information disclosure
"""

import re
import logging
from typing import Any

class SensitiveDataFilter(logging.Filter):
    """
    Logging filter to redact sensitive data from log messages
    Prevents exposure of credentials, tokens, and PII in CloudWatch Logs
    """
    
    # Patterns for sensitive data (pattern, replacement)
    SENSITIVE_PATTERNS = [
        # Passwords
        (r'password["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', r'password=***REDACTED***'),
        (r'passwd["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', r'passwd=***REDACTED***'),
        (r'pwd["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', r'pwd=***REDACTED***'),
        
        # Tokens and keys
        (r'token["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', r'token=***REDACTED***'),
        (r'auth_token["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', r'auth_token=***REDACTED***'),
        (r'access_token["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', r'access_token=***REDACTED***'),
        (r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', r'api_key=***REDACTED***'),
        (r'secret["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', r'secret=***REDACTED***'),
        
        # AWS ARNs for secrets
        (r'arn:aws:secretsmanager:[^:]+:[^:]+:secret:([^"\'}\s,/]+)', 
         r'arn:aws:secretsmanager:REGION:ACCOUNT:secret:***REDACTED***'),
        
        # Credentials in URLs
        (r'://([^:]+):([^@]+)@', r'://***REDACTED***:***REDACTED***@'),
        
        # Bearer tokens
        (r'Bearer\s+([A-Za-z0-9\-._~+/]+=*)', r'Bearer ***REDACTED***'),
        
        # Authorization headers
        (r'Authorization["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)', r'Authorization=***REDACTED***'),
        
        # Email addresses (PII)
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', r'***EMAIL_REDACTED***'),
        
        # Credit card numbers (PII)
        (r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', r'***CC_REDACTED***'),
        
        # SSN-like patterns (PII)
        (r'\b\d{3}-\d{2}-\d{4}\b', r'***SSN_REDACTED***'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to redact sensitive data
        
        Args:
            record: Log record to filter
        
        Returns:
            True to allow the record to be logged
        """
        # Redact sensitive data from message
        if isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)
        
        # Redact sensitive data from args
        if record.args:
            if isinstance(record.args, dict):
                record.args = self._redact_dict(record.args)
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(self._redact_value(arg) for arg in record.args)
        
        return True
    
    def _redact_dict(self, data: dict) -> dict:
        """Redact sensitive data from dictionary"""
        redacted = {}
        sensitive_keys = {
            'password', 'passwd', 'pwd', 'token', 'auth_token', 'access_token',
            'api_key', 'apikey', 'secret', 'authorization', 'credentials'
        }
        
        for key, value in data.items():
            if isinstance(key, str) and key.lower() in sensitive_keys:
                redacted[key] = '***REDACTED***'
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, str):
                redacted[key] = self._redact_value(value)
            else:
                redacted[key] = value
        
        return redacted
    
    def _redact_value(self, value: Any) -> Any:
        """Redact sensitive data from a single value"""
        if isinstance(value, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
        elif isinstance(value, dict):
            value = self._redact_dict(value)
        
        return value


def setup_secure_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure logging with sensitive data filtering
    
    Args:
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger with sensitive data filter
    """
    logger = logging.getLogger()
    
    # Set level
    logger.setLevel(level)
    
    # Add sensitive data filter if not already present
    has_filter = any(isinstance(f, SensitiveDataFilter) for f in logger.filters)
    if not has_filter:
        logger.addFilter(SensitiveDataFilter())
    
    return logger


def get_safe_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a logger with sensitive data filtering
    
    Args:
        name: Logger name
        level: Logging level
    
    Returns:
        Logger with sensitive data filter
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addFilter(SensitiveDataFilter())
    
    return logger
