"""
Rate Limiter for LLM Requests.

This module implements a global rate limiting system for
requests to LLM providers, avoiding 429 errors (Too Many Requests).

Features:
    - Time window limit (sliding window)
    - Different limits per provider
    - Automatic exponential backoff
    - Thread-safe
    - Usage metrics

Usage:
    >>> from aura_cli.core.llm.rate_limiter import get_rate_limiter
    >>> limiter = get_rate_limiter()
    >>> limiter.wait_if_needed("gemini")  # Blocks if necessary
    >>> # ... make request ...
"""

from collections import deque
from dataclasses import dataclass
import threading
import time
from typing import Any, Deque, Dict, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProviderLimits:
    """Rate limits for a provider."""

    requests_per_minute: int
    requests_per_day: int
    tokens_per_minute: int = 0  # 0 = no limit
    concurrent_requests: int = 10


DEFAULT_LIMITS = {
    "gemini": ProviderLimits(
        requests_per_minute=60,
        requests_per_day=1500,
        tokens_per_minute=32000,
        concurrent_requests=10,
    ),
    "openai": ProviderLimits(
        requests_per_minute=60,
        requests_per_day=10000,
        tokens_per_minute=90000,
        concurrent_requests=20,
    ),
    "anthropic": ProviderLimits(
        requests_per_minute=60,
        requests_per_day=10000,
        tokens_per_minute=100000,
        concurrent_requests=20,
    ),
    "nvidia": ProviderLimits(
        requests_per_minute=60,
        requests_per_day=10000,
        tokens_per_minute=90000,
        concurrent_requests=20,
    ),
    "local": ProviderLimits(
        requests_per_minute=1000,  # No real limit for local
        requests_per_day=100000,
        tokens_per_minute=0,
        concurrent_requests=5,  # Limitado por recursos locais
    ),
    # OpenRouter: free models have no practical limit; paid follow user tier
    "openrouter": ProviderLimits(
        requests_per_minute=200,
        requests_per_day=50000,
        tokens_per_minute=200000,
        concurrent_requests=10,
    ),
    "groq": ProviderLimits(
        requests_per_minute=30,
        requests_per_day=1000,
        tokens_per_minute=8000,
        concurrent_requests=10,
    ),
    "default": ProviderLimits(
        requests_per_minute=30,
        requests_per_day=1000,
        tokens_per_minute=0,
        concurrent_requests=5,
    ),
}


class RateLimiter:
    """Token-bucket rate limiter for LLM API calls."""

    def __init__(self):
        """Initialise the rate limiter."""
        self.limits = DEFAULT_LIMITS.copy()
        self.lock = threading.RLock()
        self.requests: Dict[str, Deque[float]] = {}
        self.daily_counts: Dict[str, int] = {}
        self.daily_reset: Dict[str, float] = {}
        self.concurrent: Dict[str, int] = {}
        self.tokens_minute: Dict[str, Deque[tuple]] = {}  # (timestamp, tokens)
        self.total_requests = 0
        self.total_waits = 0
        self.total_wait_time = 0.0

        self._max_deque_size = 10000

        logger.info("RateLimiter initialized")

    def _get_provider(self, model: str) -> str:
        """Extract the provider name from a model name."""
        model_lower = model.lower()

        if "gemini" in model_lower:
            return "gemini"
        elif model_lower.startswith(("groq/", "groq-")):
            return "groq"
        elif (
            model_lower.startswith(("nvidia/", "openai/nvidia/"))
            or "nemotron" in model_lower
        ):
            return "nvidia"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "openrouter" in model_lower or model_lower.startswith("openrouter/"):
            return "openrouter"
        elif model_lower == "auto" or "local" in model_lower:
            return "local"
        else:
            return "default"

    def _get_limits(self, provider: str) -> ProviderLimits:
        """Return rate limits for a provider."""
        return self.limits.get(provider, self.limits["default"])

    def _cleanup_old_requests(self, provider: str):
        """Remove old requests outside the current window."""
        now = time.time()
        minute_ago = now - 60
        if provider in self.requests:
            while self.requests[provider] and self.requests[provider][0] < minute_ago:
                self.requests[provider].popleft()
            if len(self.requests[provider]) > self._max_deque_size:
                excess = len(self.requests[provider]) - self._max_deque_size
                for _ in range(excess):
                    self.requests[provider].popleft()
        if provider in self.tokens_minute:
            while (
                self.tokens_minute[provider]
                and self.tokens_minute[provider][0][0] < minute_ago
            ):
                self.tokens_minute[provider].popleft()
            if len(self.tokens_minute[provider]) > self._max_deque_size:
                excess = len(self.tokens_minute[provider]) - self._max_deque_size
                for _ in range(excess):
                    self.tokens_minute[provider].popleft()
        if (
            provider in self.daily_reset and now - self.daily_reset[provider] > 86400
        ):  # 24 horas:
            self.daily_counts[provider] = 0
            self.daily_reset[provider] = now

    def _can_make_request(self, provider: str, tokens: int = 0) -> tuple:
        """Return (can_proceed, wait_time, reason) for a request."""
        limits = self._get_limits(provider)
        self._cleanup_old_requests(provider)
        if provider not in self.requests:
            self.requests[provider] = deque()
        if provider not in self.daily_counts:
            self.daily_counts[provider] = 0
            self.daily_reset[provider] = time.time()
        if provider not in self.concurrent:
            self.concurrent[provider] = 0
        if provider not in self.tokens_minute:
            self.tokens_minute[provider] = deque()
        if len(self.requests[provider]) >= limits.requests_per_minute:
            oldest = self.requests[provider][0]
            wait_time = max(0.0, 60 - (time.time() - oldest) + 0.1)
            return False, wait_time, "rate_limit_minute"
        if self.daily_counts[provider] >= limits.requests_per_day:
            reset_time = self.daily_reset[provider] + 86400
            wait_time = max(0.0, reset_time - time.time())
            return False, wait_time, "rate_limit_daily"
        if self.concurrent[provider] >= limits.concurrent_requests:
            return False, 0.5, "concurrent_limit"
        if limits.tokens_per_minute > 0 and tokens > 0:
            tokens = min(tokens, limits.tokens_per_minute)
            current_tokens = sum(t[1] for t in self.tokens_minute[provider])
            if current_tokens + tokens > limits.tokens_per_minute:
                oldest = (
                    self.tokens_minute[provider][0][0]
                    if self.tokens_minute[provider]
                    else time.time()
                )
                wait_time = max(0.0, 60 - (time.time() - oldest) + 0.1)
                return False, wait_time, "token_limit"

        return True, 0, ""

    def acquire(self, model: str, tokens: int = 0) -> bool:
        """Acquire a rate-limit token, blocking if necessary."""
        provider = self._get_provider(model)

        with self.lock:
            can_proceed, _, _ = self._can_make_request(provider, tokens)

            if can_proceed:
                self.requests[provider].append(time.time())
                self.daily_counts[provider] += 1
                self.concurrent[provider] += 1
                self.total_requests += 1

                if tokens > 0:
                    self.tokens_minute[provider].append((time.time(), tokens))

            return can_proceed

    def release(self, model: str):
        """Release a concurrent request slot."""
        provider = self._get_provider(model)

        with self.lock:
            if provider in self.concurrent and self.concurrent[provider] > 0:
                self.concurrent[provider] -= 1

    def wait_if_needed(
        self, model: str, tokens: int = 0, max_wait: float = 60.0
    ) -> bool:
        """Wait if necessary before making a request."""
        provider = self._get_provider(model)
        total_waited = 0.0

        while total_waited < max_wait:
            with self.lock:
                can_proceed, wait_time, reason = self._can_make_request(
                    provider, tokens
                )

                if can_proceed:
                    self.requests[provider].append(time.time())
                    self.daily_counts[provider] += 1
                    self.concurrent[provider] += 1
                    self.total_requests += 1

                    if tokens > 0:
                        self.tokens_minute[provider].append((time.time(), tokens))

                    return True
            actual_wait = min(wait_time, max_wait - total_waited, 5.0)  # Max 5s por vez
            if actual_wait <= 0:
                break

            logger.debug(
                f"Rate limit ({reason}): waiting {actual_wait:.1f}s para {provider}"
            )
            time.sleep(actual_wait)
            total_waited += actual_wait

            with self.lock:
                self.total_waits += 1
                self.total_wait_time += actual_wait

        logger.warning(f"Rate limit: tempo máximo de espera excedido para {provider}")
        return False

    def set_limits(self, provider: str, limits: ProviderLimits):
        """Update rate limits for a provider."""
        with self.lock:
            self.limits[provider] = limits
            logger.info(
                f"Limites atualizados para {provider}: {limits.requests_per_minute} req/min"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Return current rate limit statistics as a dict."""
        with self.lock:
            stats = {
                "total_requests": self.total_requests,
                "total_waits": self.total_waits,
                "total_wait_time": round(self.total_wait_time, 2),
                "avg_wait_time": (
                    round(self.total_wait_time / self.total_waits, 2)
                    if self.total_waits > 0
                    else 0
                ),
                "providers": {},
            }

            for provider in self.requests:
                limits = self._get_limits(provider)
                self._cleanup_old_requests(provider)

                stats["providers"][provider] = {
                    "requests_last_minute": len(self.requests.get(provider, [])),
                    "limit_per_minute": limits.requests_per_minute,
                    "daily_count": self.daily_counts.get(provider, 0),
                    "daily_limit": limits.requests_per_day,
                    "concurrent": self.concurrent.get(provider, 0),
                    "concurrent_limit": limits.concurrent_requests,
                }

            return stats

    def reset(self, provider: Optional[str] = None):
        """Reset rate limit counters for a provider."""
        with self.lock:
            if provider:
                self.requests[provider] = deque()
                self.daily_counts[provider] = 0
                self.daily_reset[provider] = time.time()
                self.concurrent[provider] = 0
                self.tokens_minute[provider] = deque()
            else:
                self.requests.clear()
                self.daily_counts.clear()
                self.daily_reset.clear()
                self.concurrent.clear()
                self.tokens_minute.clear()

            logger.info(f"Rate limiter resetado: {provider or 'all'}")


def get_rate_limiter() -> RateLimiter:
    """Return the global rate limiter singleton."""
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.RATE_LIMITER):
            return container.resolve(Services.RATE_LIMITER)
    except Exception:
        pass
    # Simple fallback (no globals needed — container handles thread safety)
    return RateLimiter()
