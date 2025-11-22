"""Async rate limiter implementation."""
import asyncio
import time
from typing import Optional


class AsyncRateLimiter:
    """
    Async rate limiter using Token Bucket algorithm.
    
    Ensures that we don't exceed a specified number of requests per time period.
    """
    
    def __init__(self, max_rate: int, time_period: float = 60.0):
        """
        Initialize rate limiter.
        
        Args:
            max_rate: Maximum number of requests allowed
            time_period: Time period in seconds (default: 60s for RPM)
        """
        self.max_rate = max_rate
        self.time_period = time_period
        self.tokens = max_rate
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
        
    async def acquire(self):
        """
        Acquire a token. If no tokens are available, wait until one is.
        """
        async with self._lock:
            while True:
                now = time.monotonic()
                time_passed = now - self.last_update
                
                # Refill tokens based on time passed
                new_tokens = time_passed * (self.max_rate / self.time_period)
                if new_tokens > 0:
                    self.tokens = min(self.max_rate, self.tokens + new_tokens)
                    self.last_update = now
                
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                
                # Wait for enough time to get 1 token
                wait_time = (1 - self.tokens) * (self.time_period / self.max_rate)
                await asyncio.sleep(wait_time)
