import pytest
import time
from src.lambdas.common.circuit_breaker import CircuitBreaker, CircuitState


def test_closed_allows_calls():
    """Test that closed circuit allows calls through"""
    cb = CircuitBreaker(failure_threshold=3)
    result = cb.call(lambda: "success")
    assert result == "success"
    assert cb.state == CircuitState.CLOSED


def test_opens_after_threshold():
    """Test that circuit opens after failure threshold"""
    cb = CircuitBreaker(failure_threshold=3)
    
    for _ in range(3):
        with pytest.raises(Exception):
            cb.call(lambda: exec('raise Exception("test error")'))
    
    assert cb.state == CircuitState.OPEN


def test_open_fails_fast():
    """Test that open circuit fails fast without calling function"""
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
    cb.state = CircuitState.OPEN
    cb.last_failure_time = time.time()
    
    with pytest.raises(Exception, match="Circuit breaker is OPEN"):
        cb.call(lambda: "should not reach")


def test_half_open_on_recovery():
    """Test that circuit transitions to half-open after recovery timeout"""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    # Trigger failures to open circuit
    for _ in range(2):
        with pytest.raises(Exception):
            cb.call(lambda: exec('raise Exception("test error")'))
    
    assert cb.state == CircuitState.OPEN
    
    # Wait for recovery timeout
    time.sleep(1.1)
    
    # Next call should transition to half-open
    result = cb.call(lambda: "success")
    assert result == "success"
    assert cb.state == CircuitState.CLOSED


def test_half_open_closes_on_success():
    """Test that half-open circuit closes on successful call"""
    cb = CircuitBreaker(failure_threshold=1)
    cb.state = CircuitState.HALF_OPEN
    
    result = cb.call(lambda: "success")
    assert result == "success"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_half_open_reopens_on_failure():
    """Test that half-open circuit reopens on failure"""
    cb = CircuitBreaker(failure_threshold=1)
    cb.state = CircuitState.HALF_OPEN
    cb.last_failure_time = time.time()
    
    with pytest.raises(Exception):
        cb.call(lambda: exec('raise Exception("test error")'))
    
    assert cb.state == CircuitState.OPEN


def test_failure_count_resets_on_success():
    """Test that failure count resets after successful call"""
    cb = CircuitBreaker(failure_threshold=3)
    
    # One failure
    with pytest.raises(Exception):
        cb.call(lambda: exec('raise Exception("test error")'))
    
    assert cb.failure_count == 1
    
    # Success resets count
    result = cb.call(lambda: "success")
    assert result == "success"
    assert cb.failure_count == 1  # Count doesn't reset in CLOSED state


def test_decorator_usage():
    """Test circuit breaker as decorator"""
    from src.lambdas.common.circuit_breaker import circuit_breaker
    
    call_count = {'value': 0}
    
    @circuit_breaker(failure_threshold=2, recovery_timeout=1)
    def test_function():
        call_count['value'] += 1
        if call_count['value'] < 3:
            raise Exception("test error")
        return "success"
    
    # First two calls fail
    with pytest.raises(Exception):
        test_function()
    
    with pytest.raises(Exception):
        test_function()
    
    # Circuit should be open now
    with pytest.raises(Exception, match="Circuit breaker is OPEN"):
        test_function()


def test_custom_thresholds():
    """Test circuit breaker with custom thresholds"""
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=2)
    
    # Should allow 4 failures before opening
    for i in range(4):
        with pytest.raises(Exception):
            cb.call(lambda: exec('raise Exception("test error")'))
        assert cb.state == CircuitState.CLOSED
    
    # 5th failure opens circuit
    with pytest.raises(Exception):
        cb.call(lambda: exec('raise Exception("test error")'))
    
    assert cb.state == CircuitState.OPEN


def test_exception_propagation():
    """Test that original exceptions are propagated"""
    cb = CircuitBreaker(failure_threshold=3)
    
    class CustomException(Exception):
        pass
    
    def raise_custom():
        raise CustomException("custom error")
    
    with pytest.raises(CustomException):
        cb.call(raise_custom)
