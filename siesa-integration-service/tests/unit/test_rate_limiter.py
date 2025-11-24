import pytest
import time
from src.lambdas.common.rate_limiter import RateLimiter, rate_limit


def test_allows_calls_within_limit():
    """Test that rate limiter allows calls within limit"""
    limiter = RateLimiter(calls=5, period=1)
    
    @limiter
    def test_func():
        return "success"
    
    # Should allow 5 calls
    for _ in range(5):
        result = test_func()
        assert result == "success"


def test_blocks_calls_exceeding_limit():
    """Test that rate limiter blocks calls exceeding limit"""
    limiter = RateLimiter(calls=3, period=1)
    
    call_times = []
    
    @limiter
    def test_func():
        call_times.append(time.time())
        return "success"
    
    # Make 5 calls (3 allowed, 2 should be delayed)
    for _ in range(5):
        test_func()
    
    # Check that calls were rate limited
    assert len(call_times) == 5
    
    # First 3 calls should be immediate
    time_diff_1_2 = call_times[1] - call_times[0]
    time_diff_2_3 = call_times[2] - call_times[1]
    assert time_diff_1_2 < 0.1
    assert time_diff_2_3 < 0.1
    
    # 4th call should be delayed
    time_diff_3_4 = call_times[3] - call_times[2]
    assert time_diff_3_4 >= 0.9  # Should wait ~1 second


def test_sliding_window():
    """Test that rate limiter uses sliding window"""
    limiter = RateLimiter(calls=2, period=1)
    
    @limiter
    def test_func():
        return "success"
    
    # First 2 calls immediate
    test_func()
    test_func()
    
    # Wait half the period
    time.sleep(0.6)
    
    # Third call should still be delayed
    start = time.time()
    test_func()
    elapsed = time.time() - start
    
    # Should have waited ~0.4 seconds (to complete the 1 second window)
    assert elapsed >= 0.3


def test_decorator_usage():
    """Test rate limiter as decorator"""
    @rate_limit(calls=3, period=1)
    def test_function():
        return "success"
    
    # Should allow 3 calls quickly
    start = time.time()
    for _ in range(3):
        result = test_function()
        assert result == "success"
    elapsed = time.time() - start
    
    assert elapsed < 0.5  # Should be fast


def test_multiple_instances():
    """Test that multiple rate limiter instances are independent"""
    limiter1 = RateLimiter(calls=2, period=1)
    limiter2 = RateLimiter(calls=2, period=1)
    
    @limiter1
    def func1():
        return "func1"
    
    @limiter2
    def func2():
        return "func2"
    
    # Each should have independent limits
    func1()
    func1()
    func2()
    func2()
    
    # Both should now be at limit - third call should be delayed
    start1 = time.time()
    func1()
    elapsed1 = time.time() - start1
    
    # Reset for func2
    start2 = time.time()
    func2()
    elapsed2 = time.time() - start2
    
    # At least one should be delayed (timing can vary)
    assert (elapsed1 >= 0.8 or elapsed2 >= 0.8)


def test_custom_periods():
    """Test rate limiter with custom periods"""
    limiter = RateLimiter(calls=5, period=2)
    
    @limiter
    def test_func():
        return "success"
    
    # Should allow 5 calls in 2 seconds
    for _ in range(5):
        test_func()
    
    # 6th call should be delayed
    start = time.time()
    test_func()
    elapsed = time.time() - start
    
    assert elapsed >= 1.9


def test_zero_delay_for_first_calls():
    """Test that first calls have no delay"""
    limiter = RateLimiter(calls=10, period=1)
    
    @limiter
    def test_func():
        return time.time()
    
    start = time.time()
    for _ in range(10):
        test_func()
    elapsed = time.time() - start
    
    # All 10 calls should be immediate
    assert elapsed < 0.5


def test_call_times_cleanup():
    """Test that old call times are cleaned up"""
    limiter = RateLimiter(calls=2, period=1)
    
    @limiter
    def test_func():
        return "success"
    
    # Make 2 calls
    test_func()
    test_func()
    
    # Wait for period to expire
    time.sleep(1.1)
    
    # Should be able to make 2 more calls immediately
    start = time.time()
    test_func()
    test_func()
    elapsed = time.time() - start
    
    assert elapsed < 0.5


def test_with_exceptions():
    """Test that rate limiter counts calls even when function raises exceptions"""
    limiter = RateLimiter(calls=3, period=1)
    
    call_count = {'value': 0}
    
    @limiter
    def test_func(should_fail=False):
        call_count['value'] += 1
        if should_fail:
            raise ValueError("test error")
        return "success"
    
    # First two calls succeed
    result = test_func()
    assert result == "success"
    
    result = test_func()
    assert result == "success"
    
    # Third call fails but still counts toward rate limit
    with pytest.raises(ValueError):
        test_func(should_fail=True)
    
    # Verify all 3 calls were counted
    assert len(limiter.call_times) == 3
    assert call_count['value'] == 3
