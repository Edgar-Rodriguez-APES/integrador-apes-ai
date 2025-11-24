import time
from collections import deque
from functools import wraps


class RateLimiter:
    def __init__(self, calls, period):
        self.calls = calls
        self.period = period
        self.call_times = deque()

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            
            while self.call_times and self.call_times[0] < now - self.period:
                self.call_times.popleft()
            
            if len(self.call_times) >= self.calls:
                sleep_time = self.period - (now - self.call_times[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
            
            try:
                result = func(*args, **kwargs)
                self.call_times.append(time.time())
                return result
            except Exception:
                # Count failed calls toward rate limit
                self.call_times.append(time.time())
                raise
        return wrapper


def rate_limit(calls, period):
    return RateLimiter(calls, period)
