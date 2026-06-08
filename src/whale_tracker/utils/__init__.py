"""Utility helpers."""

from __future__ import annotations

import asyncio
import functools
import time
from typing import Any, Callable


class RateLimiter:
    """Simple rate limiter for RPC calls."""

    def __init__(self, calls_per_second: float = 5.0):
        self.delay = 1.0 / calls_per_second
        self.last_call = 0.0

    async def wait(self):
        """Wait if necessary to respect rate limit."""
        now = time.monotonic()
        elapsed = now - self.last_call
        if elapsed < self.delay:
            await asyncio.sleep(self.delay - elapsed)
        self.last_call = time.monotonic()


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Retry decorator with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            raise last_exception
        return wrapper
    return decorator


def wei_to_eth(wei: int) -> float:
    """Convert wei to ETH."""
    return wei / 1e18


def eth_to_usd(eth: float, price: float = 3000.0) -> float:
    """Convert ETH to USD."""
    return eth * price


def shorten_address(address: str, chars: int = 6) -> str:
    """Shorten an Ethereum address."""
    return f"{address[:chars + 2]}...{address[-chars:]}"
