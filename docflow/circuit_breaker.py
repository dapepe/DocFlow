"""Circuit Breaker pattern implementation for fault tolerance.

Protects against cascading failures when external services are unavailable.
Implements the standard three-state pattern: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.
"""

import time
from enum import Enum
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class CircuitBreakerState(Enum):
    """States of the circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and request cannot be executed."""

    pass


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures.

    Implements the standard three-state pattern:
    - CLOSED: Normal operation, counting failures
    - OPEN: Failing fast, rejecting requests
    - HALF_OPEN: Testing if service recovered, allowing one trial request

    Args:
        failure_threshold: Number of failures before opening circuit (default: 5)
        recovery_timeout: Seconds to wait before attempting recovery (default: 60)
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures to trigger OPEN state
            recovery_timeout: Seconds to wait in OPEN state before trying HALF_OPEN
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change_time = time.monotonic()

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    def can_execute(self) -> bool:
        """Check if a request can be executed.

        Returns:
            True if request can proceed, False if circuit is open.

        Raises:
            CircuitBreakerOpenError: If circuit is open and recovery timeout not elapsed.
        """
        if self._state == CircuitBreakerState.CLOSED:
            return True

        if self._state == CircuitBreakerState.HALF_OPEN:
            # Allow one trial request in HALF_OPEN state
            return True

        # OPEN state: check if recovery timeout has elapsed
        if self._state == CircuitBreakerState.OPEN:
            elapsed = time.monotonic() - self._last_state_change_time
            if elapsed >= self.recovery_timeout:
                # Transition to HALF_OPEN to test recovery
                self._transition_to(CircuitBreakerState.HALF_OPEN)
                return True
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open. "
                    f"Recovery in {self.recovery_timeout - elapsed:.1f}s"
                )

        return False

    def record_success(self) -> None:
        """Record a successful request.

        Resets failure count and transitions to CLOSED if in HALF_OPEN.
        """
        if self._state == CircuitBreakerState.HALF_OPEN:
            logger.info(
                "circuit_breaker_recovered",
                previous_state=self._state.value,
                failure_count=self._failure_count,
            )
            self._transition_to(CircuitBreakerState.CLOSED)
            self._failure_count = 0
            self._last_failure_time = None
        elif self._state == CircuitBreakerState.CLOSED:
            # Success in CLOSED state: reset failure count
            if self._failure_count > 0:
                self._failure_count = 0
                logger.debug("circuit_breaker_failure_count_reset")

    def record_failure(self) -> None:
        """Record a failed request.

        Increments failure count and transitions to OPEN if threshold reached.
        In HALF_OPEN state, immediately returns to OPEN.
        """
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitBreakerState.HALF_OPEN:
            # Failure during recovery attempt: back to OPEN
            logger.warning(
                "circuit_breaker_recovery_failed",
                failure_count=self._failure_count,
            )
            self._transition_to(CircuitBreakerState.OPEN)
        elif self._state == CircuitBreakerState.CLOSED:
            # Check if threshold reached
            if self._failure_count >= self.failure_threshold:
                logger.error(
                    "circuit_breaker_opened",
                    failure_count=self._failure_count,
                    threshold=self.failure_threshold,
                    recovery_timeout=self.recovery_timeout,
                )
                self._transition_to(CircuitBreakerState.OPEN)
            else:
                logger.warning(
                    "circuit_breaker_failure_recorded",
                    failure_count=self._failure_count,
                    threshold=self.failure_threshold,
                )

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state.

        Clears all failure counts and state.
        """
        logger.info(
            "circuit_breaker_reset",
            previous_state=self._state.value,
            failure_count=self._failure_count,
        )
        self._transition_to(CircuitBreakerState.CLOSED)
        self._failure_count = 0
        self._last_failure_time = None

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        """Transition to a new state and log the change.

        Args:
            new_state: The target state to transition to
        """
        if new_state != self._state:
            old_state = self._state
            self._state = new_state
            self._last_state_change_time = time.monotonic()
            logger.info(
                "circuit_breaker_state_change",
                from_state=old_state.value,
                to_state=new_state.value,
                failure_count=self._failure_count,
            )
