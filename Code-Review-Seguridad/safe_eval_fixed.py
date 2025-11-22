"""
Safe expression evaluator - Hardened version with security fixes
Provides secure evaluation of transformation expressions
"""

import ast
import operator
import logging
import signal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Whitelist of safe operators
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

# Whitelist of safe functions - HARDENED
# Removed dangerous functions: str, int, float, min, max
SAFE_FUNCTIONS = {
    'upper': lambda x: str(x)[:1000].upper(),  # With length limit
    'lower': lambda x: str(x)[:1000].lower(),
    'strip': lambda x: str(x)[:1000].strip(),
    'len': len,
    'abs': abs,
    'round': lambda x, n=0: round(x, n) if isinstance(x, (int, float)) else x,
}

# Maximum recursion depth for AST evaluation
MAX_DEPTH = 50

# Maximum execution time (seconds)
MAX_EXECUTION_TIME = 1


class SafeEvalError(Exception):
    """Exception raised when safe evaluation fails"""
    pass


class EvaluationTimeout(SafeEvalError):
    """Exception raised when evaluation times out"""
    pass


def _timeout_handler(signum, frame):
    """Signal handler for evaluation timeout"""
    raise EvaluationTimeout("Expression evaluation exceeded time limit")


def safe_eval(
    expression: str, 
    context: Dict[str, Any], 
    max_depth: int = MAX_DEPTH,
    timeout: int = MAX_EXECUTION_TIME
) -> Any:
    """
    Safely evaluate expression without using eval()
    
    SECURITY IMPROVEMENTS:
    - Removed dangerous functions (str, int, float, min, max)
    - Added recursion depth limit
    - Added execution timeout
    - Blocks attribute access
    - Validates expression complexity
    
    Args:
        expression: Expression to evaluate (e.g., "value + 10", "upper(value)")
        context: Context dictionary with variables (e.g., {"value": 123})
        max_depth: Maximum recursion depth (default: 50)
        timeout: Maximum execution time in seconds (default: 1)
    
    Returns:
        Evaluation result
    
    Raises:
        SafeEvalError: If expression is invalid or unsafe
        EvaluationTimeout: If evaluation exceeds timeout
    """
    if not isinstance(expression, str):
        raise SafeEvalError(f"Expression must be string, got {type(expression).__name__}")
    
    if not expression.strip():
        raise SafeEvalError("Expression cannot be empty")
    
    # Check expression length to prevent DoS
    if len(expression) > 1000:
        raise SafeEvalError("Expression too long (max 1000 characters)")
    
    try:
        # Parse expression into AST
        tree = ast.parse(expression, mode='eval')
        
        # Validate AST complexity before evaluation
        _validate_ast_complexity(tree.body)
        
        # Set timeout (Unix only - gracefully handle Windows)
        timeout_set = False
        try:
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(timeout)
            timeout_set = True
        except (AttributeError, ValueError):
            # Windows doesn't support SIGALRM - continue without timeout
            logger.warning("Timeout not available on this platform")
        
        try:
            # Evaluate AST with depth limit
            result = _eval_node(tree.body, context, depth=0, max_depth=max_depth)
            return result
        finally:
            # Cancel alarm if it was set
            if timeout_set:
                signal.alarm(0)
        
    except EvaluationTimeout:
        raise
    except SafeEvalError:
        raise
    except SyntaxError as e:
        logger.error(f"Syntax error in expression: {expression}")
        raise SafeEvalError(f"Invalid expression syntax: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to evaluate expression: {expression}, error: {str(e)}")
        raise SafeEvalError(f"Evaluation failed: {str(e)}")


def _validate_ast_complexity(node: ast.AST, depth: int = 0, max_nodes: int = 100):
    """
    Validate that AST is not overly complex (prevents DoS)
    
    Args:
        node: AST node to validate
        depth: Current depth
        max_nodes: Maximum number of nodes allowed
    
    Raises:
        SafeEvalError: If AST is too complex
    """
    if depth > MAX_DEPTH:
        raise SafeEvalError(f"Expression nesting too deep (max: {MAX_DEPTH})")
    
    # Count nodes
    node_count = sum(1 for _ in ast.walk(node))
    if node_count > max_nodes:
        raise SafeEvalError(f"Expression too complex (max {max_nodes} nodes)")
    
    # Block dangerous node types
    for child in ast.walk(node):
        # Block attribute access (prevents __class__, __globals__, etc.)
        if isinstance(child, ast.Attribute):
            raise SafeEvalError("Attribute access not allowed")
        
        # Block subscript access (prevents __getitem__ exploits)
        if isinstance(child, ast.Subscript):
            raise SafeEvalError("Subscript access not allowed")
        
        # Block list/dict/set comprehensions
        if isinstance(child, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            raise SafeEvalError("Comprehensions not allowed")
        
        # Block lambda functions
        if isinstance(child, ast.Lambda):
            raise SafeEvalError("Lambda functions not allowed")


def _eval_node(node: ast.AST, context: Dict[str, Any], depth: int, max_depth: int) -> Any:
    """
    Recursively evaluate AST node with depth tracking
    
    Args:
        node: AST node to evaluate
        context: Context dictionary with variables
        depth: Current recursion depth
        max_depth: Maximum allowed depth
    
    Returns:
        Evaluation result
    
    Raises:
        SafeEvalError: If node type is not supported or depth exceeded
    """
    # Check depth limit
    if depth > max_depth:
        raise SafeEvalError(f"Expression too complex (max depth: {max_depth})")
    
    # Constants (numbers, strings, booleans, None)
    if isinstance(node, ast.Constant):
        # Limit string length in constants
        if isinstance(node.value, str) and len(node.value) > 1000:
            raise SafeEvalError("String constant too long")
        return node.value
    
    # Variables (e.g., "value")
    elif isinstance(node, ast.Name):
        if node.id in context:
            return context[node.id]
        elif node.id in SAFE_FUNCTIONS:
            return SAFE_FUNCTIONS[node.id]
        else:
            raise SafeEvalError(f"Unknown variable: {node.id}")
    
    # Binary operations (e.g., "value + 10")
    elif isinstance(node, ast.BinOp):
        left = _eval_node(node.left, context, depth + 1, max_depth)
        right = _eval_node(node.right, context, depth + 1, max_depth)
        
        op = SAFE_OPERATORS.get(type(node.op))
        if not op:
            raise SafeEvalError(f"Unsupported operator: {type(node.op).__name__}")
        
        # Prevent division by zero
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise SafeEvalError("Division by zero")
        
        # Prevent power operation DoS (e.g., 10**10**10)
        if isinstance(node.op, ast.Pow):
            if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
                raise SafeEvalError("Power operation requires numeric operands")
            if abs(left) > 1000 or abs(right) > 100:
                raise SafeEvalError("Power operation operands too large")
        
        try:
            return op(left, right)
        except OverflowError:
            raise SafeEvalError("Numeric overflow in operation")
        except Exception as e:
            raise SafeEvalError(f"Operation failed: {str(e)}")
    
    # Comparisons (e.g., "value > 100")
    elif isinstance(node, ast.Compare):
        left = _eval_node(node.left, context, depth + 1, max_depth)
        
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, context, depth + 1, max_depth)
            
            op_func = SAFE_OPERATORS.get(type(op))
            if not op_func:
                raise SafeEvalError(f"Unsupported comparison: {type(op).__name__}")
            
            if not op_func(left, right):
                return False
            
            left = right
        
        return True
    
    # Boolean operations (e.g., "value > 10 and value < 100")
    # FIXED: Proper short-circuit evaluation
    elif isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            # Short-circuit for AND
            for val in node.values:
                result = _eval_node(val, context, depth + 1, max_depth)
                if not result:
                    return False
            return True
        
        elif isinstance(node.op, ast.Or):
            # Short-circuit for OR
            for val in node.values:
                result = _eval_node(val, context, depth + 1, max_depth)
                if result:
                    return True
            return False
        
        else:
            raise SafeEvalError(f"Unsupported boolean operator: {type(node.op).__name__}")
    
    # Function calls (e.g., "upper(value)", "len(value)")
    elif isinstance(node, ast.Call):
        # Get function
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            if func_name not in SAFE_FUNCTIONS:
                raise SafeEvalError(f"Unsafe function: {func_name}")
            
            func = SAFE_FUNCTIONS[func_name]
            
            # Evaluate arguments
            args = [_eval_node(arg, context, depth + 1, max_depth) for arg in node.args]
            
            # Limit number of arguments
            if len(args) > 10:
                raise SafeEvalError("Too many function arguments")
            
            # Call function with error handling
            try:
                return func(*args)
            except Exception as e:
                raise SafeEvalError(f"Function {func_name} failed: {str(e)}")
        else:
            raise SafeEvalError("Only simple function calls are supported")
    
    # Unary operations (e.g., "-value", "not value")
    elif isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, context, depth + 1, max_depth)
        
        if isinstance(node.op, ast.USub):
            if not isinstance(operand, (int, float)):
                raise SafeEvalError("Unary minus requires numeric operand")
            return -operand
        elif isinstance(node.op, ast.UAdd):
            if not isinstance(operand, (int, float)):
                raise SafeEvalError("Unary plus requires numeric operand")
            return +operand
        elif isinstance(node.op, ast.Not):
            return not operand
        else:
            raise SafeEvalError(f"Unsupported unary operator: {type(node.op).__name__}")
    
    # Unsupported node type
    else:
        raise SafeEvalError(f"Unsupported expression type: {type(node).__name__}")


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
    except SafeEvalError as e:
        logger.warning(f"Transformation logic failed: {logic}, error: {str(e)}")
        return value  # Return original value on error
    except Exception as e:
        logger.error(f"Unexpected error in transformation: {str(e)}")
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
    except SafeEvalError as e:
        logger.warning(f"Condition evaluation failed: {condition}, error: {str(e)}")
        return False  # Default to False on error
    except Exception as e:
        logger.error(f"Unexpected error in condition: {str(e)}")
        return False
