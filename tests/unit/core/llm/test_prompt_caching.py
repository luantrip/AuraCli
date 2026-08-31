"""Tests for T3.2 — Prompt Caching for Anthropic and Google models.

Verifies that _apply_cache_control correctly adds cache_control headers
to system messages and large user messages for supported providers,
and leaves messages unchanged for unsupported providers.
"""

from unittest.mock import MagicMock, patch

import pytest

from aura_cli.core.llm.base import _apply_cache_control

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_messages():
    """Standard messages list with system + user messages."""
    return [
        {
            "role": "system",
            "content": "You are a helpful AI assistant with extensive capabilities.",
        },
        {"role": "user", "content": "Hello, how are you?"},
    ]


@pytest.fixture
def messages_with_large_user_context():
    """Messages where the first user message is large (>1000 chars)."""
    large_content = "x" * 1500  # 1500 chars, exceeds 1000 threshold
    return [
        {"role": "system", "content": "System prompt here."},
        {"role": "user", "content": large_content},
        {"role": "user", "content": "Follow-up question"},
    ]


@pytest.fixture
def messages_no_system():
    """Messages without a system message."""
    return [
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]


# ---------------------------------------------------------------------------
# Tests: Anthropic (claude-*) models
# ---------------------------------------------------------------------------


class TestCacheControlAnthropic:
    """Tests for cache_control application on Anthropic models."""

    def test_system_message_gets_cache_control(self, basic_messages):
        """System message should get cache_control for claude models."""
        result = _apply_cache_control(basic_messages, "claude-sonnet-4-6")
        assert result[0]["cache_control"] == {"type": "ephemeral"}

    def test_small_user_message_no_cache_control(self, basic_messages):
        """Small user messages (<1000 chars) should NOT get cache_control."""
        result = _apply_cache_control(basic_messages, "claude-sonnet-4-6")
        assert "cache_control" not in result[1]

    def test_large_user_message_gets_cache_control(
        self, messages_with_large_user_context
    ):
        """First user message >1000 chars should get cache_control."""
        result = _apply_cache_control(
            messages_with_large_user_context, "claude-haiku-4-5-20251001"
        )
        # System message cached
        assert result[0]["cache_control"] == {"type": "ephemeral"}
        # First large user message cached
        assert result[1]["cache_control"] == {"type": "ephemeral"}
        # Second user message NOT cached
        assert "cache_control" not in result[2]

    def test_claude_prefix_variants(self, basic_messages):
        """Various claude model name formats should all be detected."""
        models = [
            "claude-sonnet-4-6",
            "claude-haiku-4-5-20251001",
            "anthropic/claude-sonnet-4-6",
        ]
        for model in models:
            result = _apply_cache_control(basic_messages, model)
            assert result[0].get("cache_control") == {"type": "ephemeral"}, (
                f"Failed for model: {model}"
            )


# ---------------------------------------------------------------------------
# Tests: Google (gemini-*) models
# ---------------------------------------------------------------------------


class TestCacheControlGoogle:
    """Tests for cache_control application on Google Gemini models."""

    def test_system_message_gets_cache_control(self, basic_messages):
        """System message should get cache_control for gemini models."""
        result = _apply_cache_control(basic_messages, "gemini/gemini-2.5-flash")
        assert result[0]["cache_control"] == {"type": "ephemeral"}

    def test_large_user_message_gets_cache_control(
        self, messages_with_large_user_context
    ):
        """First user message >1000 chars should get cache_control for gemini."""
        result = _apply_cache_control(
            messages_with_large_user_context, "gemini/gemini-2.5-pro"
        )
        assert result[0]["cache_control"] == {"type": "ephemeral"}
        assert result[1]["cache_control"] == {"type": "ephemeral"}

    def test_gemini_variants(self, basic_messages):
        """Various gemini model name formats should all be detected."""
        models = [
            "gemini/gemini-2.5-flash",
            "gemini/gemini-2.5-pro",
            "gemini-2.5-flash",
        ]
        for model in models:
            result = _apply_cache_control(basic_messages, model)
            assert result[0].get("cache_control") == {"type": "ephemeral"}, (
                f"Failed for model: {model}"
            )


# ---------------------------------------------------------------------------
# Tests: Unsupported providers (OpenAI, OpenRouter)
# ---------------------------------------------------------------------------


class TestCacheControlUnsupported:
    """Tests that cache_control is NOT added for unsupported providers."""

    def test_openai_no_cache_control(self, basic_messages):
        """OpenAI models should NOT get cache_control."""
        result = _apply_cache_control(basic_messages, "gpt-4o")
        assert "cache_control" not in result[0]

    def test_openai_mini_no_cache_control(self, basic_messages):
        """GPT-4o-mini should NOT get cache_control."""
        result = _apply_cache_control(basic_messages, "gpt-4o-mini")
        assert "cache_control" not in result[0]

    def test_openrouter_no_cache_control(self, basic_messages):
        """OpenRouter models should NOT get cache_control."""
        result = _apply_cache_control(
            basic_messages, "openrouter/meta-llama/llama-3.3-70b-instruct:free"
        )
        assert "cache_control" not in result[0]

    def test_nvidia_no_cache_control(self, basic_messages):
        """NVIDIA models should NOT get cache_control."""
        result = _apply_cache_control(basic_messages, "nvidia/nemotron-3-super-120b")
        assert "cache_control" not in result[0]


# ---------------------------------------------------------------------------
# Tests: Edge cases
# ---------------------------------------------------------------------------


class TestCacheControlEdgeCases:
    """Tests for edge cases and robustness."""

    def test_empty_messages(self):
        """Empty messages list should return empty list."""
        result = _apply_cache_control([], "claude-sonnet-4-6")
        assert result == []

    def test_none_model(self, basic_messages):
        """None model should not crash, returns messages unchanged."""
        result = _apply_cache_control(basic_messages, None)
        assert "cache_control" not in result[0]

    def test_empty_model(self, basic_messages):
        """Empty string model should not crash, returns messages unchanged."""
        result = _apply_cache_control(basic_messages, "")
        assert "cache_control" not in result[0]

    def test_no_system_message(self, messages_no_system):
        """Messages without system should not crash."""
        result = _apply_cache_control(messages_no_system, "claude-sonnet-4-6")
        # No system message to cache
        for msg in result:
            if msg["role"] != "user" or len(msg.get("content", "")) <= 1000:
                assert "cache_control" not in msg

    def test_original_messages_not_mutated(self, basic_messages):
        """Original messages list should not be mutated."""
        original_copy = [dict(m) for m in basic_messages]
        _apply_cache_control(basic_messages, "claude-sonnet-4-6")
        assert basic_messages == original_copy

    def test_system_message_empty_content(self):
        """System message with empty content should NOT get cache_control."""
        messages = [
            {"role": "system", "content": ""},
            {"role": "user", "content": "Hello"},
        ]
        result = _apply_cache_control(messages, "claude-sonnet-4-6")
        assert "cache_control" not in result[0]

    @patch("aura_cli.core.config.get_config_manager")
    def test_config_disabled(self, mock_get_config, basic_messages):
        """When prompt_caching config is False, no cache_control should be added."""
        mock_config = MagicMock()
        mock_config.get.return_value = False
        mock_get_config.return_value = mock_config
        result = _apply_cache_control(basic_messages, "claude-sonnet-4-6")
        assert "cache_control" not in result[0]

    @patch("aura_cli.core.config.get_config_manager")
    def test_config_enabled_explicitly(self, mock_get_config, basic_messages):
        """When prompt_caching config is True, cache_control should be added."""
        mock_config = MagicMock()
        mock_config.get.return_value = True
        mock_get_config.return_value = mock_config
        result = _apply_cache_control(basic_messages, "claude-sonnet-4-6")
        assert result[0]["cache_control"] == {"type": "ephemeral"}

    @patch("aura_cli.core.config.get_config_manager")
    def test_config_none_defaults_to_enabled(self, mock_get_config, basic_messages):
        """When prompt_caching config is None (not set), caching should be enabled."""
        mock_config = MagicMock()
        mock_config.get.return_value = None  # Not set
        mock_get_config.return_value = mock_config
        result = _apply_cache_control(basic_messages, "claude-sonnet-4-6")
        assert result[0]["cache_control"] == {"type": "ephemeral"}

    def test_only_first_large_user_message_cached(self):
        """Only the FIRST large user message should be cached, not subsequent ones."""
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "a" * 2000},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "b" * 2000},
        ]
        result = _apply_cache_control(messages, "gemini/gemini-2.5-flash")
        assert result[1]["cache_control"] == {"type": "ephemeral"}
        assert "cache_control" not in result[3]
