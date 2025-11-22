"""
Safe Expression Evaluator with Security Hardening
Evaluates mathematical and logical expressions safely without using eval()
Cross-platform compatible (Windows and Linux)
"""

import ast
import operator
import math
import re
import threading
from typing import Any, Dict, Optional, Set
from decimal import Decimal, InvalidOperation


class SafeEvalError(Exception):
    """Custom exception for safe evaluation errors"""
    pass


class TimeoutError(Exception):
    """Custom exception for evaluation timeout"""
    pass


# Maximum recursion depth for nested expressions
MAX_DEPTH = 50

# Maximum expression length
MAX_EXPRESSION_LENGTH = 10000

# Timeout for evaluation (seconds)
EVAL_TIMEOUT = 1


# Allowed operators
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Not: operator.not_,
}

# Allowed math functions - REMOVED dangerous type conversion functions
SAFE_FUNCTIONS = {
    'abs': abs,
    'round': round,
    'len': len,
    'sum': sum,
    'sqrt': math.sqrt,
    'pow': pow,
    'ceil': math.ceil,
    'floor': math.floor,
}


def _validate_ast_complexity(node: ast.AST, depth: int = 0) -> None:
    """
    Validate AST complexity to prevent DoS attacks
    
    Args:
        node: AST node to validate
        depth: Current recursion depth
        
    Raises:
        SafeEvalError: If complexity limits are exceeded
    """
    if depth > MAX_DEPTH:
        raise SafeEvalError(f"Expression too complex: exceeds maximum depth of {MAX_DEPTH}")
    
    # Block dangerous node types
    if isinstance(node, (ast.Attribute, ast.Subscript)):
        raise SafeEvalError(
            "Attribute access and subscripting not allowed for security reasons"
        )
    
    # Recursively validate child nodes
    for child in ast.iter_child_nodes(node):
        _validate_ast_complexity(child, depth + 1)


def _eval_node(node: ast.AST, context: Dict[str, Any], depth: int = 0) -> Any:
    """
    Recursively evaluate an AST node with depth tracking
    
    Args:
        node: AST node to evaluate
        context: Variable context for evaluation
        depth: Current recursion depth
        
    Returns:
        Evaluation result
        
    Raises:
        SafeEvalError: If evaluation fails or depth exceeded
    """
    # Check depth limit
    if depth > MAX_DEPTH:
        raise SafeEvalError(f"Expression too deep: exceeds maximum depth of {MAX_DEPTH}")
    
    # Numeric constants
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool)):
            return node.value
        raise SafeEvalError(f"Unsupported constant type: {type(node.value)}")
    
    # Legacy number nodes (Python < 3.8)
    if isinstance(node, ast.Num):
        return node.n
    
    # Variables
    if isinstance(node, ast.Name):
        if node.id in context:
            return context[node.id]
        raise SafeEvalError(f"Undefined variable: {node.id}")
    
    # Binary operations
    if isinstance(node, ast.BinOp):
        if type(node.op) not in SAFE_OPERATORS:
            raise SafeEvalError(f"Unsupported operator: {type(node.op).__name__}")
        
        left = _eval_node(node.left, context, depth + 1)
        right = _eval_node(node.right, context, depth + 1)
        
        # Prevent division by zero
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise SafeEvalError("Division by zero")
        
        return SAFE_OPERATORS[type(node.op)](left, right)
    
    # Unary operations
    if isinstance(node, ast.UnaryOp):
        if type(node.op) not in SAFE_OPERATORS:
            raise SafeEvalError(f"Unsupported unary operator: {type(node.op).__name__}")
        
        operand = _eval_node(node.operand, context, depth + 1)
        return SAFE_OPERATORS[type(node.op)](operand)
    
    # Comparison operations
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, context, depth + 1)
        
        for op, comparator in zip(node.ops, node.comparators):
            if type(op) not in SAFE_OPERATORS:
                raise SafeEvalError(f"Unsupported comparison: {type(op).__name__}")
            
            right = _eval_node(comparator, context, depth + 1)
            
            if not SAFE_OPERATORS[type(op)](left, right):
                return False
            
            left = right
        
        return True
    
    # Boolean operations
    if isinstance(node, ast.BoolOp):
        if type(node.op) not in SAFE_OPERATORS:
            raise SafeEvalError(f"Unsupported boolean operator: {type(node.op).__name__}")
        
        values = [_eval_node(value, context, depth + 1) for value in node.values]
        
        if isinstance(node.op, ast.And):
            return all(values)
        elif isinstance(node.op, ast.Or):
            return any(values)
    
    # Function calls
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise SafeEvalError("Only simple function calls are allowed")
        
        func_name = node.func.id
        if func_name not in SAFE_FUNCTIONS:
            raise SafeEvalError(f"Function not allowed: {func_name}")
        
        args = [_eval_node(arg, context, depth + 1) for arg in node.args]
        
        try:
            return SAFE_FUNCTIONS[func_name](*args)
        except Exception as e:
            raise SafeEvalError(f"Function call failed: {str(e)}")
    
    raise SafeEvalError(f"Unsupported node type: {type(node).__name__}")


def safe_eval(expression: str, context: Optional[Dict[str, Any]] = None) -> Any:
    """
    Safely evaluate a mathematical/logical expression with timeout
    Cross-platform compatible (uses threading instead of signal)
    
    Args:
        expression: String expression to evaluate
        context: Optional dictionary of variables
        
    Returns:
        Evaluation result
        
    Raises:
        SafeEvalError: If evaluation fails
        TimeoutError: If evaluation times out
    """
    if context is None:
        context = {}
    
    # Validate expression length
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise SafeEvalError(
            f"Expression too long: {len(expression)} > {MAX_EXPRESSION_LENGTH}"
        )
    
    # Container for result and exception
    result_container = {'result': None, 'exception': None, 'completed': False}
    
    def evaluate():
        """Inner function to run evaluation in thread"""
        try:
            # Parse expression
            try:
                tree = ast.parse(expression, mode='eval')
            except SyntaxError as e:
                result_container['exception'] = SafeEvalError(f"Invalid expression syntax: {str(e)}")
                return
            
            # Validate AST complexity and dangerous patterns
            _validate_ast_complexity(tree.body)
            
            # Evaluate
            result_container['result'] = _eval_node(tree.body, context)
            result_container['completed'] = True
            
        except SafeEvalError as e:
            result_container['exception'] = e
        except Exception as e:
            result_container['exception'] = SafeEvalError(f"Evaluation error: {str(e)}")
    
    # Create and start evaluation thread
    eval_thread = threading.Thread(target=evaluate)
    eval_thread.daemon = True
    eval_thread.start()
    
    # Wait for completion with timeout
    eval_thread.join(timeout=EVAL_TIMEOUT)
    
    # Check if thread is still alive (timeout occurred)
    if eval_thread.is_alive():
        raise TimeoutError("Expression evaluation timed out")
    
    # Check if exception occurred
    if result_container['exception']:
        raise result_container['exception']
    
    # Return result
    if result_container['completed']:
        return result_container['result']
    else:
        raise SafeEvalError("Evaluation failed for unknown reason")


def apply_transformation_logic(value: Any, logic: str) -> Any:
    """
    Apply transformation logic safely
    
    Args:
        value: Value to transform
        logic: Transformation logic expression
    
    Returns:
        Transformed value, or original value if transformation fails
    """
    try:
        return safe_eval(logic, {"value": value})
    except (SafeEvalError, TimeoutError) as e:
        # Log warning but return original value
        return value
    except Exception as e:
        return value


def evaluate_condition(value: Any, condition: str) -> bool:
    """
    Evaluate condition safely
    
    Args:
        value: Value to test
        condition: Condition expression
    
    Returns:
        Boolean result, or False if evaluation fails
    """
    try:
        result = safe_eval(condition, {"value": value})
        return bool(result)
    except (SafeEvalError, TimeoutError) as e:
        return False
    except Exception as e:
        return False
