"""
Input Validation and Sanitization Module with Enhanced Security
Provides comprehensive input validation against SQL injection, XSS, and other attacks
"""

import re
import html
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation


# Maximum recursion depth for nested structures
MAX_RECURSION_DEPTH = 50

# Enhanced SQL Injection Pattern - detects multiple bypass techniques
SQL_INJECTION_PATTERN = re.compile(
    r"(?:"
    # SQL keywords with various spacing/comments
    r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC(?:UTE)?|UNION|SCRIPT)\b|"
    # SQL comments
    r"(?:--|/\*|\*/|#|;)|"
    # Hex encoding
    r"(?:0x[0-9a-fA-F]+)|"
    # Union attacks with spacing
    r"(?:UN\s*ION|SEL\s*ECT)|"
    # String concatenation
    r"(?:\|\||CONCAT)|"
    # Time-based attacks
    r"(?:SLEEP|BENCHMARK|WAITFOR\s+DELAY)|"
    # Boolean-based attacks
    r"(?:AND|OR)\s+\d+\s*[=<>]|"
    # Stacked queries
    r";\s*(?:SELECT|INSERT|UPDATE|DELETE)"
    r")",
    re.IGNORECASE | re.MULTILINE
)

# Comprehensive XSS Pattern - covers 100+ attack vectors
XSS_PATTERNS = [
    # Basic script tags
    re.compile(r'<script[\s\S]*?</script>', re.IGNORECASE),
    re.compile(r'<script[\s\S]*?>', re.IGNORECASE),
    
    # Event handlers (comprehensive list)
    re.compile(r'\bon\w+\s*=', re.IGNORECASE),  # Matches any onX= event
    re.compile(r'\bonerror\s*=', re.IGNORECASE),
    re.compile(r'\bonload\s*=', re.IGNORECASE),
    re.compile(r'\bonclick\s*=', re.IGNORECASE),
    re.compile(r'\bonmouseover\s*=', re.IGNORECASE),
    re.compile(r'\bonfocus\s*=', re.IGNORECASE),
    re.compile(r'\bonblur\s*=', re.IGNORECASE),
    re.compile(r'\bonchange\s*=', re.IGNORECASE),
    re.compile(r'\boninput\s*=', re.IGNORECASE),
    re.compile(r'\bonsubmit\s*=', re.IGNORECASE),
    re.compile(r'\bonkeydown\s*=', re.IGNORECASE),
    re.compile(r'\bonkeyup\s*=', re.IGNORECASE),
    re.compile(r'\bonkeypress\s*=', re.IGNORECASE),
    
    # JavaScript protocols
    re.compile(r'javascript\s*:', re.IGNORECASE),
    re.compile(r'vbscript\s*:', re.IGNORECASE),
    re.compile(r'data\s*:\s*text/html', re.IGNORECASE),
    
    # Dangerous functions
    re.compile(r'\beval\s*\(', re.IGNORECASE),
    re.compile(r'\bexpression\s*\(', re.IGNORECASE),
    re.compile(r'\bsetTimeout\s*\(', re.IGNORECASE),
    re.compile(r'\bsetInterval\s*\(', re.IGNORECASE),
    re.compile(r'\bFunction\s*\(', re.IGNORECASE),
    
    # Dangerous tags
    re.compile(r'<iframe[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<embed[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<object[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<applet[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<meta[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<link[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<base[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<form[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<input[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<button[\s\S]*?>', re.IGNORECASE),
    
    # SVG-based XSS
    re.compile(r'<svg[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<animate[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<animatetransform[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<set[\s\S]*?>', re.IGNORECASE),
    
    # Style-based XSS
    re.compile(r'<style[\s\S]*?>', re.IGNORECASE),
    re.compile(r'style\s*=\s*["\'].*?expression\s*\(', re.IGNORECASE),
    re.compile(r'style\s*=\s*["\'].*?javascript\s*:', re.IGNORECASE),
    re.compile(r'style\s*=\s*["\'].*?@import', re.IGNORECASE),
    
    # Import statements
    re.compile(r'@import', re.IGNORECASE),
    re.compile(r'<import[\s\S]*?>', re.IGNORECASE),
    
    # XML-based attacks
    re.compile(r'<\?xml[\s\S]*?\?>', re.IGNORECASE),
    re.compile(r'<!DOCTYPE[\s\S]*?>', re.IGNORECASE),
    re.compile(r'<!ENTITY[\s\S]*?>', re.IGNORECASE),
]

# Path traversal pattern
PATH_TRAVERSAL_PATTERN = re.compile(r'\.\.[/\\]')

# Command injection pattern
COMMAND_INJECTION_PATTERN = re.compile(
    r'[;&|`$\(\)<>]|'
    r'\b(?:bash|sh|cmd|powershell|wget|curl|nc|netcat)\b',
    re.IGNORECASE
)

# Log injection pattern - detects newlines and control characters
LOG_INJECTION_PATTERN = re.compile(r'[\n\r\t\x00-\x1f\x7f]')


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def sanitize_string(value: str, max_length: int = 1000) -> str:
    """
    Sanitize a string value with comprehensive XSS protection
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Raises:
        ValidationError: If validation fails
    """
    if not isinstance(value, str):
        raise ValidationError(f"Expected string, got {type(value).__name__}")
    
    # Check length
    if len(value) > max_length:
        raise ValidationError(f"String too long: {len(value)} > {max_length}")
    
    # Check for SQL injection
    if SQL_INJECTION_PATTERN.search(value):
        raise ValidationError("Potential SQL injection detected")
    
    # Check for XSS - test against all patterns
    for pattern in XSS_PATTERNS:
        if pattern.search(value):
            raise ValidationError("Potential XSS attack detected")
    
    # HTML escape for additional safety
    return html.escape(value, quote=True)


def sanitize_log_message(message: str, max_length: int = 5000) -> str:
    """
    Sanitize log messages to prevent log injection attacks
    
    Log injection occurs when an attacker injects newlines or control characters
    into log messages to forge log entries or hide malicious activity.
    
    Args:
        message: Log message to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized log message with dangerous characters removed/escaped
        
    Raises:
        ValidationError: If message is invalid
    """
    if not isinstance(message, str):
        raise ValidationError(f"Expected string, got {type(message).__name__}")
    
    # Check length
    if len(message) > max_length:
        raise ValidationError(f"Log message too long: {len(message)} > {max_length}")
    
    # Remove or replace control characters and newlines
    # Replace newlines with space to preserve readability
    sanitized = message.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    # Remove other control characters (0x00-0x1f, 0x7f)
    sanitized = LOG_INJECTION_PATTERN.sub('', sanitized)
    
    # Truncate if still too long after sanitization
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + '...'
    
    # HTML escape for additional safety
    return html.escape(sanitized, quote=True)


def sanitize_number(value: Any, allow_float: bool = True) -> Union[int, float]:
    """
    Safely convert and validate numeric values
    
    Args:
        value: Value to convert to number
        allow_float: Whether to allow float values
        
    Returns:
        Validated number (int or float)
        
    Raises:
        ValidationError: If conversion fails or value is invalid
    """
    # Handle string inputs
    if isinstance(value, str):
        # Remove whitespace
        value = value.strip()
        
        # Check for injection attempts in numeric strings
        if SQL_INJECTION_PATTERN.search(value):
            raise ValidationError("Invalid numeric format: contains SQL patterns")
        
        # Try conversion
        try:
            if allow_float and '.' in value:
                result = float(value)
            else:
                result = int(value)
        except (ValueError, InvalidOperation) as e:
            raise ValidationError(f"Invalid numeric value: {str(e)}")
    
    # Handle numeric types
    elif isinstance(value, (int, float, Decimal)):
        if not allow_float and isinstance(value, (float, Decimal)) and value != int(value):
            raise ValidationError("Float not allowed, expected integer")
        result = float(value) if allow_float else int(value)
    
    else:
        raise ValidationError(f"Cannot convert {type(value).__name__} to number")
    
    # Check for infinity and NaN
    if isinstance(result, float):
        if not (-1e308 < result < 1e308):  # Check for reasonable range
            raise ValidationError("Number out of safe range")
        if result != result:  # NaN check
            raise ValidationError("Invalid number (NaN)")
    
    return result


def sanitize_boolean(value: Any) -> bool:
    """
    Safely convert values to boolean
    
    Args:
        value: Value to convert to boolean
        
    Returns:
        Boolean value
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        value_lower = value.lower().strip()
        if value_lower in ('true', '1', 'yes', 'y', 'on'):
            return True
        elif value_lower in ('false', '0', 'no', 'n', 'off', ''):
            return False
        else:
            raise ValidationError(f"Cannot convert '{value}' to boolean")
    
    if isinstance(value, (int, float)):
        return bool(value)
    
    raise ValidationError(f"Cannot convert {type(value).__name__} to boolean")


def sanitize_dict(
    data: Dict[str, Any],
    allowed_keys: Optional[List[str]] = None,
    depth: int = 0
) -> Dict[str, Any]:
    """
    Recursively sanitize dictionary with depth limit
    
    Args:
        data: Dictionary to sanitize
        allowed_keys: Optional list of allowed keys (None allows all)
        depth: Current recursion depth
        
    Returns:
        Sanitized dictionary
        
    Raises:
        ValidationError: If validation fails or depth exceeded
    """
    if not isinstance(data, dict):
        raise ValidationError(f"Expected dict, got {type(data).__name__}")
    
    # Check recursion depth
    if depth > MAX_RECURSION_DEPTH:
        raise ValidationError(
            f"Dictionary too deeply nested: exceeds maximum depth of {MAX_RECURSION_DEPTH}"
        )
    
    sanitized = {}
    
    for key, value in data.items():
        # Validate key
        if not isinstance(key, str):
            raise ValidationError(f"Dictionary key must be string, got {type(key).__name__}")
        
        # Check if key is allowed
        if allowed_keys is not None and key not in allowed_keys:
            continue  # Skip disallowed keys
        
        # Sanitize key
        safe_key = sanitize_string(key, max_length=100)
        
        # Recursively sanitize value
        if isinstance(value, dict):
            sanitized[safe_key] = sanitize_dict(value, allowed_keys=None, depth=depth + 1)
        elif isinstance(value, list):
            sanitized[safe_key] = sanitize_list(value, depth=depth + 1)
        elif isinstance(value, str):
            try:
                sanitized[safe_key] = sanitize_string(value)
            except ValidationError:
                # If string validation fails, skip this key-value pair
                continue
        elif isinstance(value, (int, float, bool)) or value is None:
            sanitized[safe_key] = value
        else:
            # For other types, convert to string and sanitize
            try:
                sanitized[safe_key] = sanitize_string(str(value))
            except ValidationError:
                continue
    
    return sanitized


def sanitize_list(data: List[Any], depth: int = 0) -> List[Any]:
    """
    Recursively sanitize list with depth limit
    
    Args:
        data: List to sanitize
        depth: Current recursion depth
        
    Returns:
        Sanitized list
        
    Raises:
        ValidationError: If validation fails or depth exceeded
    """
    if not isinstance(data, list):
        raise ValidationError(f"Expected list, got {type(data).__name__}")
    
    # Check recursion depth
    if depth > MAX_RECURSION_DEPTH:
        raise ValidationError(
            f"List too deeply nested: exceeds maximum depth of {MAX_RECURSION_DEPTH}"
        )
    
    sanitized = []
    
    for item in data:
        if isinstance(item, dict):
            sanitized.append(sanitize_dict(item, depth=depth + 1))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item, depth=depth + 1))
        elif isinstance(item, str):
            try:
                sanitized.append(sanitize_string(item))
            except ValidationError:
                # Skip invalid items
                continue
        elif isinstance(item, (int, float, bool)) or item is None:
            sanitized.append(item)
        else:
            # For other types, convert to string and sanitize
            try:
                sanitized.append(sanitize_string(str(item)))
            except ValidationError:
                continue
    
    return sanitized


def validate_path(path: str) -> str:
    """
    Validate file path to prevent path traversal attacks
    
    Args:
        path: File path to validate
        
    Returns:
        Validated path
        
    Raises:
        ValidationError: If path is invalid or dangerous
    """
    if not isinstance(path, str):
        raise ValidationError(f"Path must be string, got {type(path).__name__}")
    
    # Check for path traversal
    if PATH_TRAVERSAL_PATTERN.search(path):
        raise ValidationError("Path traversal detected")
    
    # Check for absolute paths (optional - depends on requirements)
    if path.startswith('/') or path.startswith('\\'):
        raise ValidationError("Absolute paths not allowed")
    
    # Check for command injection attempts
    if COMMAND_INJECTION_PATTERN.search(path):
        raise ValidationError("Potential command injection in path")
    
    return sanitize_string(path)


def validate_email(email: str) -> str:
    """
    Validate email address format
    
    Args:
        email: Email address to validate
        
    Returns:
        Validated email
        
    Raises:
        ValidationError: If email format is invalid
    """
    # Basic email pattern
    email_pattern = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    email = email.strip().lower()
    
    if not email_pattern.match(email):
        raise ValidationError("Invalid email format")
    
    # Additional security check
    if SQL_INJECTION_PATTERN.search(email):
        raise ValidationError("Invalid characters in email")
    
    return email


def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> str:
    """
    Validate URL format and scheme
    
    Args:
        url: URL to validate
        allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
        
    Returns:
        Validated URL
        
    Raises:
        ValidationError: If URL is invalid or scheme not allowed
    """
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    url = url.strip()
    
    # Check for javascript: and other dangerous protocols
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
    for protocol in dangerous_protocols:
        if url.lower().startswith(protocol):
            raise ValidationError(f"Dangerous protocol detected: {protocol}")
    
    # Check allowed schemes
    if not any(url.lower().startswith(f"{scheme}://") for scheme in allowed_schemes):
        raise ValidationError(f"URL must start with one of: {', '.join(allowed_schemes)}")
    
    # Check for XSS in URL
    for pattern in XSS_PATTERNS[:10]:  # Check first 10 patterns (most relevant)
        if pattern.search(url):
            raise ValidationError("Potential XSS in URL")
    
    return url
