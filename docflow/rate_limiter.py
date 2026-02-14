"""Rate limiting implementation using Token Bucket algorithm."""

import asyncio
import logging
import threading
import time
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded and wait=False."""

    pass


class TokenBucketRateLimiter:
    """Thread-safe and async-safe Token Bucket rate limiter.

    Implements the Token Bucket algorithm for rate limiting:
    - Tokens refill at a constant rate (refill_rate tokens per second)
    - Maximum capacity is capped at `capacity`
    - Each acquire() consumes 1.0 token
    - If tokens < 1.0 and wait=False, raises RateLimitExceededError
    - If tokens < 1.0 and wait=True, blocks until token available
    """

    def __init__(self, capacity: float, refill_rate: float):
        """Initialize the rate limiter.

        Args:
            capacity: Maximum number of tokens in the bucket
            refill_rate: Number of tokens to add per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()

        logger.info(
            "rate_limiter_initialized",
            capacity=capacity,
            refill_rate=refill_rate,
        )

    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill.

        This is an internal method that should be called while holding the lock.
        """
        now = time.monotonic()
        elapsed = now - self._last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self._last_refill = now

    def acquire(self, wait: bool = True, timeout: Optional[float] = None) -> bool:
        """Acquire one token from the bucket (thread-safe).

        Args:
            wait: If True, block until token available. If False, raise on limit.
            timeout: Maximum time to wait in seconds (only used if wait=True).

        Returns:
            True if token acquired successfully.

        Raises:
            RateLimitExceededError: If wait=False and no tokens available.
            TimeoutError: If wait=True and timeout exceeded.
        """
        start_time = time.monotonic()

        while True:
            with self._lock:
                self._refill()

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    logger.debug(
                        "token_acquired",
                        tokens_remaining=self.tokens,
                        wait=wait,
                    )
                    return True

                if not wait:
                    logger.warning(
                        "rate_limit_exceeded",
                        tokens_available=self.tokens,
                    )
                    raise RateLimitExceededError(
                        f"Rate limit exceeded. Tokens available: {self.tokens:.2f}"
                    )

            # Check timeout
            if timeout is not None:
                elapsed = time.monotonic() - start_time
                if elapsed >= timeout:
                    logger.error(
                        "rate_limit_timeout",
                        timeout=timeout,
                        elapsed=elapsed,
                    )
                    raise TimeoutError(f"Rate limit wait timeout after {elapsed:.2f}s")

            # Sleep briefly before retrying (avoid busy-waiting)
            sleep_time = min(0.01, (1.0 - self.tokens) / self.refill_rate)
            time.sleep(sleep_time)

    async def acquire_async(
        self, wait: bool = True, timeout: Optional[float] = None
    ) -> bool:
        """Acquire one token from the bucket (async-safe).

        Args:
            wait: If True, block until token available. If False, raise on limit.
            timeout: Maximum time to wait in seconds (only used if wait=True).

        Returns:
            True if token acquired successfully.

        Raises:
            RateLimitExceededError: If wait=False and no tokens available.
            TimeoutError: If wait=True and timeout exceeded.
        """
        start_time = time.monotonic()

        while True:
            async with self._async_lock:
                self._refill()

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    logger.debug(
                        "token_acquired_async",
                        tokens_remaining=self.tokens,
                        wait=wait,
                    )
                    return True

                if not wait:
                    logger.warning(
                        "rate_limit_exceeded_async",
                        tokens_available=self.tokens,
                    )
                    raise RateLimitExceededError(
                        f"Rate limit exceeded. Tokens available: {self.tokens:.2f}"
                    )

            # Check timeout
            if timeout is not None:
                elapsed = time.monotonic() - start_time
                if elapsed >= timeout:
                    logger.error(
                        "rate_limit_timeout_async",
                        timeout=timeout,
                        elapsed=elapsed,
                    )
                    raise TimeoutError(f"Rate limit wait timeout after {elapsed:.2f}s")

            # Sleep briefly before retrying (avoid busy-waiting)
            sleep_time = min(0.01, (1.0 - self.tokens) / self.refill_rate)
            await asyncio.sleep(sleep_time)
