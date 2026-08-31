"""Tests for core/llm/circuit_breaker.py and core/llm/rate_limiter.py."""

import pytest

from aura_cli.core.llm.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_circuit_breaker,
    reset_circuit_breaker,
)
from aura_cli.core.llm.rate_limiter import RateLimiter, get_rate_limiter

# ── Circuit Breaker ──────────────────────────────────────────────────────────


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED

    def test_successful_call_stays_closed(self):
        cb = CircuitBreaker()
        result = cb.call(lambda: "ok")
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitState.OPEN

    def test_open_circuit_raises_immediately(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        with pytest.raises(RuntimeError):
            cb.call(lambda: "should not run")

    def test_reset_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_get_stats_returns_dict(self):
        cb = CircuitBreaker()
        stats = cb.get_stats()
        assert "state" in stats
        assert "failure_count" in stats

    def test_get_circuit_breaker_returns_same_instance(self):
        cb1 = get_circuit_breaker("google")
        cb2 = get_circuit_breaker("google")
        assert cb1 is cb2

    def test_different_providers_different_instances(self):
        cb_google = get_circuit_breaker("google")
        cb_openai = get_circuit_breaker("openai")
        assert cb_google is not cb_openai

    def test_reset_circuit_breaker_creates_new(self):
        get_circuit_breaker("test_provider_reset")
        reset_circuit_breaker("test_provider_reset")
        cb2 = get_circuit_breaker("test_provider_reset")
        # After reset, failure count should be 0
        assert cb2.failure_count == 0


# ── Rate Limiter ─────────────────────────────────────────────────────────────


class TestRateLimiter:
    def test_acquire_and_release(self):
        rl = RateLimiter()
        result = rl.wait_if_needed("gemini/gemini-2.5-flash", max_wait=1.0)
        assert result is True
        rl.release("gemini/gemini-2.5-flash")

    def test_wait_if_needed_returns_bool(self):
        rl = RateLimiter()
        result = rl.wait_if_needed("gpt-4o", max_wait=0.1)
        assert isinstance(result, bool)
        rl.release("gpt-4o")

    def test_get_stats_returns_dict(self):
        rl = RateLimiter()
        stats = rl.get_stats()
        assert isinstance(stats, dict)

    def test_set_limits(self):
        from aura_cli.core.llm.rate_limiter import ProviderLimits

        rl = RateLimiter()
        rl.set_limits(
            "custom", ProviderLimits(requests_per_minute=10, requests_per_day=100)
        )
        assert "custom" in rl.limits

    def test_get_rate_limiter_singleton(self):
        rl1 = get_rate_limiter()
        rl2 = get_rate_limiter()
        assert rl1 is rl2
