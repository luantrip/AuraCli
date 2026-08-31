"""
Circuit Breaker implementation for LLM API calls.

Prevents cascading failures by temporarily stopping requests to a provider
when it's experiencing issues, allowing it to recover.
"""

from enum import Enum
import threading
import time
from typing import Optional


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests allowed
    OPEN = "open"  # Circuit is open, requests blocked
    HALF_OPEN = "half_open"  # Testing if provider recovered


class CircuitOpenError(RuntimeError):
    """Raised when a call is rejected while the circuit remains open."""


class CircuitBreaker:
    """
    Circuit breaker for LLM API calls.

    Implements the circuit breaker pattern to prevent cascading failures
    when a provider is experiencing issues. After a threshold of failures,
    the circuit opens and blocks requests for a cooldown period.

    Attributes:
        failure_threshold: Number of consecutive failures before opening circuit
        cooldown_seconds: Time in seconds to wait before attempting recovery
        success_threshold: Number of successes needed in half-open to close circuit
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        cooldown_seconds: float = 60.0,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening
            cooldown_seconds: Seconds to wait before attempting recovery
            success_threshold: Successes needed in half-open to close circuit
        """
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change_time: Optional[float] = None
        self._lock = threading.RLock()

    def call(self, func, *args, **kwargs):
        """
        Execute function call through circuit breaker.

        Args:
            func: Function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result of function call

        Raises:
            Exception: If circuit is open or function call fails
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self.last_failure_time and (
                    time.time() - self.last_failure_time >= self.cooldown_seconds
                ):
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                    self.last_state_change_time = time.time()
                else:
                    raise CircuitOpenError(
                        f"Circuit breaker is OPEN. "
                        f"Wait {self.cooldown_seconds - (time.time() - self.last_failure_time):.1f}s"
                    )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise

    def _record_success(self):
        """Record a successful call."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.last_state_change_time = time.time()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def _record_failure(self):
        """Record a failed call."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.success_count = 0
                self.last_state_change_time = time.time()
            elif (
                self.state == CircuitState.CLOSED
                and self.failure_count >= self.failure_threshold
            ):
                self.state = CircuitState.OPEN
                self.last_state_change_time = time.time()

    def reset(self):
        """Manually reset circuit breaker to closed state."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.last_state_change_time = None

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self.state

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "success_count": self.success_count,
                "last_failure_time": self.last_failure_time,
                "last_state_change_time": self.last_state_change_time,
            }


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    """
    Get or create circuit breaker for a provider via DI container.

    Args:
        provider: Provider name (e.g., "google", "openai", "anthropic")

    Returns:
        CircuitBreaker instance for the provider
    """
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.CIRCUIT_BREAKER_REGISTRY):
            registry = container.resolve(Services.CIRCUIT_BREAKER_REGISTRY)
            return registry.get(provider)
    except Exception:
        pass
    # Simple fallback (no globals needed — container handles thread safety)
    return CircuitBreaker()


def reset_circuit_breaker(provider: str):
    """Reset circuit breaker for a provider."""
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.CIRCUIT_BREAKER_REGISTRY):
            registry = container.resolve(Services.CIRCUIT_BREAKER_REGISTRY)
            registry.get(provider).reset()
            return
    except Exception:
        pass
