"""
Rate Limiter for Broker APIs

Implements per-broker rate limiting to avoid exceeding API limits.

Rate Limits (per broker):
- SmartAPI: 1 request/second (WebSocket: unlimited)
- Kite: 10 requests/second
- Upstox: 50 requests/second
- Dhan: 10 requests/second
- Fyers: 10 requests/second (general); 1 req/sec for historical data; 100K requests/day total (not enforced here)
- Paytm: 10 requests/second
"""

import asyncio
import time
from collections import deque
from functools import wraps
from typing import Dict, Optional


class RateLimiter:
    """
    Token bucket rate limiter for broker APIs.

    Uses token bucket algorithm:
    - Bucket holds N tokens (requests per window)
    - Tokens regenerate at rate R (window duration)
    - Each API call consumes 1 token
    - If bucket empty, request waits until token available
    """

    # Rate limits per broker (requests per second)
    BROKER_LIMITS = {
        "smartapi": 1,   # 1 req/sec
        "kite": 10,      # 10 req/sec
        "upstox": 50,    # 50 req/sec
        "dhan": 10,      # 10 req/sec
        "fyers": 10,     # 10 req/sec general (historical: 1 req/sec — enforce separately; daily cap: 100K — not tracked here)
        "paytm": 10,     # 10 req/sec
    }

    def __init__(self, broker: str, requests_per_second: Optional[int] = None):
        """
        Initialize rate limiter for broker.

        Args:
            broker: Broker identifier
            requests_per_second: Override default rate limit
        """
        self.broker = broker
        self.rate = requests_per_second or self.BROKER_LIMITS.get(broker, 10)
        self.window = 1.0  # 1 second window
        self.tokens = self.rate  # Start with full bucket
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """
        Acquire a token (wait if necessary).

        Blocks until a token is available.
        """
        async with self.lock:
            now = time.time()

            # Refill tokens based on time elapsed
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * self.rate)
            self.last_update = now

            # If no tokens available, wait
            if self.tokens < 1:
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 1

            # Consume one token
            self.tokens -= 1

    def set_rate(self, requests_per_second: int) -> None:
        """Update rate limit dynamically."""
        self.rate = requests_per_second
        self.tokens = min(self.rate, self.tokens)


class BrokerRateLimiters:
    """
    Singleton manager for all broker rate limiters.

    Ensures one rate limiter per broker across the application.
    """

    _instance = None
    _limiters: Dict[str, RateLimiter] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_limiter(self, broker: str) -> RateLimiter:
        """Get or create rate limiter for broker."""
        if broker not in self._limiters:
            self._limiters[broker] = RateLimiter(broker)
        return self._limiters[broker]

    async def acquire(self, broker: str) -> None:
        """Acquire token for broker (convenience method)."""
        limiter = self.get_limiter(broker)
        await limiter.acquire()


# Global singleton instance
broker_rate_limiters = BrokerRateLimiters()


# Decorator for rate-limited functions
def rate_limited(broker: str):
    """
    Decorator to rate-limit async functions.

    Usage:
        @rate_limited("smartapi")
        async def get_quote(symbol):
            # API call
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await broker_rate_limiters.acquire(broker)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
