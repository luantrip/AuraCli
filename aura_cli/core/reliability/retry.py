"""Bounded retry and exponential backoff policies."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay: float = 0.25
    max_delay: float = 8.0
    multiplier: float = 2.0
    jitter: float = 0.1
    retryable_exceptions: tuple[type[BaseException], ...] = (Exception,)

    def delay(self, attempt: int, random_value: float | None = None) -> float:
        base = min(self.max_delay, self.initial_delay * (self.multiplier ** max(0, attempt - 1)))
        sample = random.random() if random_value is None else random_value
        return max(0.0, base * (1.0 + self.jitter * (sample * 2.0 - 1.0)))


def retry_call(function: Callable[..., T], *args, policy: RetryPolicy | None = None, **kwargs) -> T:
    """Call a function with bounded retries, preserving the final exception."""
    active = policy or RetryPolicy()
    if active.max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    for attempt in range(1, active.max_attempts + 1):
        try:
            return function(*args, **kwargs)
        except active.retryable_exceptions:
            if attempt >= active.max_attempts:
                raise
            time.sleep(active.delay(attempt))
    raise RuntimeError("retry loop exhausted unexpectedly")


async def async_retry_call(function: Callable[..., T], *args, policy: RetryPolicy | None = None, **kwargs) -> T:
    """Async counterpart that does not block the event loop while waiting."""
    active = policy or RetryPolicy()
    for attempt in range(1, active.max_attempts + 1):
        try:
            result = function(*args, **kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result
        except active.retryable_exceptions:
            if attempt >= active.max_attempts:
                raise
            await asyncio.sleep(active.delay(attempt))
    raise RuntimeError("retry loop exhausted unexpectedly")
