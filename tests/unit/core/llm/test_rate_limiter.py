"""
Tests for Rate Limiter.

Tests the rate limiting system for LLM API calls, including:
- Per-minute request limits
- Daily request limits
- Token-based limits
- Concurrent request limits
- Wait mechanisms
- Provider-specific limits
"""

from unittest.mock import patch

import pytest

from aura_cli.core.llm.rate_limiter import (
    DEFAULT_LIMITS,
    ProviderLimits,
    RateLimiter,
    get_rate_limiter,
)


@pytest.fixture
def limiter():
    """Create fresh rate limiter for each test."""
    limiter = RateLimiter()
    yield limiter
    limiter.reset()


class TestBasicFunctionality:
    """Test basic rate limiter operations."""

    def test_acquire_within_limits(self, limiter):
        """Should allow requests within rate limits."""
        result = limiter.acquire("gemini-2.5-flash")
        assert result is True
        assert limiter.total_requests == 1

    def test_acquire_exceeds_minute_limit(self, limiter):
        """Should block when per-minute limit exceeded."""
        # Set low limit for testing
        limiter.set_limits(
            "gemini", ProviderLimits(requests_per_minute=2, requests_per_day=100)
        )

        # First two should succeed
        assert limiter.acquire("gemini-2.5-flash") is True
        assert limiter.acquire("gemini-2.5-flash") is True

        # Third should fail
        assert limiter.acquire("gemini-2.5-flash") is False

    def test_acquire_exceeds_daily_limit(self, limiter):
        """Should block when daily limit exceeded."""
        limiter.set_limits(
            "gemini", ProviderLimits(requests_per_minute=100, requests_per_day=2)
        )

        assert limiter.acquire("gemini-2.5-flash") is True
        assert limiter.acquire("gemini-2.5-flash") is True
        assert limiter.acquire("gemini-2.5-flash") is False

    def test_release_decrements_concurrent(self, limiter):
        """Should decrement concurrent count on release."""
        limiter.acquire("gemini-2.5-flash")
        assert limiter.concurrent.get("gemini", 0) == 1

        limiter.release("gemini-2.5-flash")
        assert limiter.concurrent.get("gemini", 0) == 0

    def test_provider_detection(self, limiter):
        """Should correctly detect provider from model name."""
        assert limiter._get_provider("gemini-2.5-flash") == "gemini"
        assert limiter._get_provider("gpt-4o") == "openai"
        assert limiter._get_provider("claude-3-5-sonnet") == "anthropic"
        assert (
            limiter._get_provider("openai/nvidia/llama-3.3-nemotron-super-49b-v1")
            == "nvidia"
        )
        assert (
            limiter._get_provider("openrouter/meta-llama/llama-3.1-8b-instruct:free")
            == "openrouter"
        )
        assert limiter._get_provider("unknown-model") == "default"


class TestTokenLimiting:
    """Test token-based rate limiting."""

    def test_token_limit_enforcement(self, limiter):
        """Should block when token limit exceeded."""
        limiter.set_limits(
            "gemini",
            ProviderLimits(
                requests_per_minute=100, requests_per_day=1000, tokens_per_minute=1000
            ),
        )

        # Use 800 tokens
        assert limiter.acquire("gemini-2.5-flash", tokens=800) is True

        # Try to use 300 more (would exceed 1000)
        assert limiter.acquire("gemini-2.5-flash", tokens=300) is False

    def test_token_limit_cleanup(self, limiter):
        """Should remove old token records after 60 seconds."""
        limiter.set_limits(
            "gemini",
            ProviderLimits(
                requests_per_minute=100, requests_per_day=1000, tokens_per_minute=1000
            ),
        )

        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0
            limiter.acquire("gemini-2.5-flash", tokens=800)

            # Move time forward 61 seconds
            mock_time.return_value = 1061.0
            limiter._cleanup_old_requests("gemini")

            # Should be able to use 800 tokens again
            assert limiter.acquire("gemini-2.5-flash", tokens=800) is True

    def test_token_limit_disabled_when_zero(self, limiter):
        """Should not enforce token limit when set to 0."""
        limiter.set_limits(
            "local",
            ProviderLimits(
                requests_per_minute=100,
                requests_per_day=1000,
                tokens_per_minute=0,  # Disabled
            ),
        )

        # Should allow any amount of tokens
        assert limiter.acquire("local-model", tokens=999999) is True


class TestConcurrentRequests:
    """Test concurrent request limiting."""

    def test_concurrent_limit_enforcement(self, limiter):
        """Should enforce max concurrent requests."""
        limiter.set_limits(
            "gemini",
            ProviderLimits(
                requests_per_minute=100, requests_per_day=1000, concurrent_requests=2
            ),
        )

        assert limiter.acquire("gemini-2.5-flash") is True
        assert limiter.acquire("gemini-2.5-flash") is True
        assert limiter.acquire("gemini-2.5-flash") is False  # Exceeds concurrent limit

    def test_concurrent_release_allows_new_requests(self, limiter):
        """Should allow new requests after release."""
        limiter.set_limits(
            "gemini",
            ProviderLimits(
                requests_per_minute=100, requests_per_day=1000, concurrent_requests=1
            ),
        )

        assert limiter.acquire("gemini-2.5-flash") is True
        assert limiter.acquire("gemini-2.5-flash") is False

        limiter.release("gemini-2.5-flash")
        assert limiter.acquire("gemini-2.5-flash") is True


class TestWaitMechanism:
    """Test wait_if_needed blocking behavior."""

    def test_wait_if_needed_blocks_and_proceeds(self, limiter):
        """Should wait and then proceed when limit clears."""
        limiter.set_limits(
            "gemini", ProviderLimits(requests_per_minute=1, requests_per_day=100)
        )

        with patch("time.time") as mock_time, patch("time.sleep"):
            # First request at t=1000
            mock_time.return_value = 1000.0
            assert limiter.wait_if_needed("gemini-2.5-flash") is True

            # Second request at t=1061 (after 60s window)
            mock_time.return_value = 1061.0
            result = limiter.wait_if_needed("gemini-2.5-flash", max_wait=60.0)
            assert result is True

    def test_wait_if_needed_respects_max_wait(self, limiter):
        """Should return False when max_wait exceeded."""
        limiter.set_limits(
            "gemini", ProviderLimits(requests_per_minute=1, requests_per_day=100)
        )

        with patch("time.time") as mock_time, patch("time.sleep") as mock_sleep:
            mock_time.return_value = 1000.0
            limiter.wait_if_needed("gemini-2.5-flash")

            # Try second request with short max_wait
            mock_time.return_value = 1001.0
            mock_sleep.side_effect = lambda x: None  # Don't actually sleep
            result = limiter.wait_if_needed("gemini-2.5-flash", max_wait=0.1)
            assert result is False

    def test_wait_if_needed_multiple_reasons(self, limiter):
        """Should handle multiple limit types correctly."""
        limiter.set_limits(
            "gemini",
            ProviderLimits(
                requests_per_minute=1,
                requests_per_day=100,
                tokens_per_minute=100,
                concurrent_requests=1,
            ),
        )

        with patch("time.time") as mock_time, patch("time.sleep"):
            mock_time.return_value = 1000.0

            # First request succeeds
            assert limiter.wait_if_needed("gemini-2.5-flash", tokens=50) is True

            # Second request blocked by multiple limits
            mock_time.return_value = 1001.0
            result = limiter.wait_if_needed("gemini-2.5-flash", tokens=60, max_wait=0.1)
            assert result is False


class TestStatsAndManagement:
    """Test statistics and management functions."""

    def test_get_stats_accuracy(self, limiter):
        """Should return accurate statistics."""
        limiter.acquire("gemini-2.5-flash")
        limiter.acquire("gpt-4o")

        stats = limiter.get_stats()
        assert stats["total_requests"] == 2
        assert "gemini" in stats["providers"]
        assert "openai" in stats["providers"]
        assert stats["providers"]["gemini"]["requests_last_minute"] == 1
        assert stats["providers"]["openai"]["requests_last_minute"] == 1

    def test_reset_clears_state(self, limiter):
        """Should clear all state on reset."""
        limiter.acquire("gemini-2.5-flash")
        limiter.acquire("gpt-4o")

        # Reset clears per-provider state but not total_requests counter
        limiter.reset()

        # Check per-provider state is cleared
        assert len(limiter.requests) == 0
        assert len(limiter.daily_counts) == 0
        assert len(limiter.concurrent) == 0


class TestSingleton:
    """Test singleton pattern."""

    def test_get_rate_limiter_returns_singleton(self):
        """Should return same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2


class TestDefaultLimits:
    """Test default provider limits."""

    def test_default_limits_exist_for_all_providers(self):
        """Should have limits defined for all major providers."""
        assert "gemini" in DEFAULT_LIMITS
        assert "openai" in DEFAULT_LIMITS
        assert "anthropic" in DEFAULT_LIMITS
        assert "nvidia" in DEFAULT_LIMITS
        assert "openrouter" in DEFAULT_LIMITS
        assert "local" in DEFAULT_LIMITS
        assert "default" in DEFAULT_LIMITS

    def test_default_limits_are_reasonable(self):
        """Should have reasonable default values."""
        for _provider, limits in DEFAULT_LIMITS.items():
            assert limits.requests_per_minute > 0
            assert limits.requests_per_day > 0
            assert limits.concurrent_requests > 0
