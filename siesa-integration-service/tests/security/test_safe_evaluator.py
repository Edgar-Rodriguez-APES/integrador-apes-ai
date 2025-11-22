"""
Tests for SafeExpressionEvaluator
Tests the security of expression evaluation without eval()
"""

import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src/lambdas'))

# SECURITY FIX: Import from safe_eval module instead of transformer
from common.safe_eval import safe_eval, apply_transformation_logic, evaluate_condition, SafeEvalError


class TestSafeEval:
    """Test suite for safe_eval function"""
    
    def test_simple_arithmetic_addition(self):
        """Test simple addition operation"""
        result = safe_eval("value + 10", {"value": 5})
        assert result == 15
    
    def test_simple_arithmetic_subtraction(self):
        """Test simple subtraction operation"""
        result = safe_eval("value - 3", {"value": 10})
        assert result == 7
    
    def test_simple_arithmetic_multiplication(self):
        """Test simple multiplication operation"""
        result = safe_eval("value * 2", {"value": 5})
        assert result == 10
    
    def test_simple_arithmetic_division(self):
        """Test simple division operation"""
        result = safe_eval("value / 2", {"value": 10})
        assert result == 5.0
    
    def test_comparison_greater_than(self):
        """Test greater than comparison"""
        result = safe_eval("value > 5", {"value": 10})
        assert result is True
        
        result = safe_eval("value > 5", {"value": 3})
        assert result is False
    
    def test_comparison_less_than(self):
        """Test less than comparison"""
        result = safe_eval("value < 10", {"value": 5})
        assert result is True
    
    def test_comparison_equal(self):
        """Test equality comparison"""
        result = safe_eval("value == 5", {"value": 5})
        assert result is True
        
        result = safe_eval("value == 5", {"value": 10})
        assert result is False
    
    def test_safe_function_upper(self):
        """Test upper() function - V2 removed this function for security"""
        with pytest.raises(SafeEvalError, match="Function not allowed"):
            safe_eval("upper(value)", {"value": "hello"})
    
    def test_safe_function_lower(self):
        """Test lower() function - V2 removed this function for security"""
        with pytest.raises(SafeEvalError, match="Function not allowed"):
            safe_eval("lower(value)", {"value": "HELLO"})
    
    def test_safe_function_strip(self):
        """Test strip() function - V2 removed this function for security"""
        with pytest.raises(SafeEvalError, match="Function not allowed"):
            safe_eval("strip(value)", {"value": "  hello  "})
    
    def test_safe_function_len(self):
        """Test len() function"""
        result = safe_eval("len(value)", {"value": "hello"})
        assert result == 5
    
    def test_safe_function_abs(self):
        """Test abs() function"""
        result = safe_eval("abs(value)", {"value": -5})
        assert result == 5
    
    def test_safe_function_round(self):
        """Test round() function"""
        result = safe_eval("round(value)", {"value": 3.7})
        assert result == 4
    
    def test_attribute_access_blocked(self):
        """Test that attribute access is blocked"""
        with pytest.raises(SafeEvalError, match="Attribute access and subscripting not allowed"):
            safe_eval("value.__class__", {"value": ""})
    
    def test_subscript_access_blocked(self):
        """Test that subscript access is blocked"""
        with pytest.raises(SafeEvalError, match="Attribute access and subscripting not allowed"):
            safe_eval("value[0]", {"value": "hello"})
    
    def test_empty_expression_rejected(self):
        """Test that empty expressions are rejected"""
        with pytest.raises(SafeEvalError, match="Invalid expression syntax"):
            safe_eval("", {})
    
    def test_non_string_expression_rejected(self):
        """Test that non-string expressions are rejected"""
        with pytest.raises(TypeError, match="object of type 'int' has no len"):
            safe_eval(123, {})
    
    def test_unknown_variable_rejected(self):
        """Test that unknown variables are rejected"""
        with pytest.raises(SafeEvalError, match="Undefined variable"):
            safe_eval("unknown_var + 1", {"value": 5})
    
    def test_complex_expression(self):
        """Test complex but safe expression"""
        result = safe_eval("value * 2 + 10", {"value": 5})
        assert result == 20
    
    def test_unary_minus(self):
        """Test unary minus operator"""
        result = safe_eval("-value", {"value": 5})
        assert result == -5
    
    def test_unary_plus(self):
        """Test unary plus operator"""
        result = safe_eval("+value", {"value": 5})
        assert result == 5


class TestApplyTransformationLogic:
    """Test suite for apply_transformation_logic wrapper"""
    
    def test_successful_transformation(self):
        """Test successful transformation"""
        result = apply_transformation_logic(5, "value * 2")
        assert result == 10
    
    def test_failed_transformation_returns_original(self):
        """Test that failed transformation returns original value"""
        result = apply_transformation_logic(5, "invalid expression !!!")
        assert result == 5  # Should return original value on error


class TestEvaluateCondition:
    """Test suite for evaluate_condition wrapper"""
    
    def test_true_condition(self):
        """Test condition that evaluates to True"""
        result = evaluate_condition(10, "value > 5")
        assert result is True
    
    def test_false_condition(self):
        """Test condition that evaluates to False"""
        result = evaluate_condition(3, "value > 5")
        assert result is False
    
    def test_failed_condition_returns_false(self):
        """Test that failed condition returns False"""
        result = evaluate_condition(5, "invalid condition !!!")
        assert result is False  # Should return False on error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
