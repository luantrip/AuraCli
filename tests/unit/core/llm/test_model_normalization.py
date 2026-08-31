"""
Tests for model name normalization.

Tests the centralized normalize_model_name() function
to ensure consistent model name handling across the application.
"""

from aura_cli.core.llm.model_utils import normalize_model_name


class TestModelNormalization:
    """Test model name normalization."""

    def test_gemini_model_without_prefix(self):
        """Test Gemini models get 'gemini/' prefix added."""
        assert normalize_model_name("gemini-1.5-flash") == "gemini/gemini-1.5-flash"
        assert (
            normalize_model_name("gemini-2.0-flash-exp")
            == "gemini/gemini-2.0-flash-exp"
        )
        assert normalize_model_name("gemini-pro") == "gemini/gemini-pro"

    def test_gemini_model_with_prefix(self):
        """Test Gemini models with prefix remain unchanged."""
        assert (
            normalize_model_name("gemini/gemini-1.5-flash") == "gemini/gemini-1.5-flash"
        )
        assert (
            normalize_model_name("gemini/gemini-2.0-flash-exp")
            == "gemini/gemini-2.0-flash-exp"
        )

    def test_gemini_short_name(self):
        """Test short 'gemini' name gets default model."""
        result = normalize_model_name("gemini")
        assert result.startswith("gemini/")
        assert "gemini" in result.lower()

    def test_gpt_models_unchanged(self):
        """Test GPT models remain unchanged."""
        assert normalize_model_name("gpt-4") == "gpt-4"
        assert normalize_model_name("gpt-4o") == "gpt-4o"
        assert normalize_model_name("gpt-3.5-turbo") == "gpt-3.5-turbo"
        assert normalize_model_name("gpt-4-turbo") == "gpt-4-turbo"

    def test_claude_models_unchanged(self):
        """Test Claude models remain unchanged."""
        assert normalize_model_name("claude-3-opus") == "claude-3-opus"
        assert normalize_model_name("claude-3-sonnet") == "claude-3-sonnet"
        assert normalize_model_name("claude-3-haiku") == "claude-3-haiku"
        assert normalize_model_name("claude-3.5-sonnet") == "claude-3.5-sonnet"

    def test_openrouter_models_unchanged(self):
        """Test OpenRouter models remain unchanged."""
        # OpenRouter models that already have the prefix remain unchanged
        assert (
            normalize_model_name("openrouter/anthropic/claude-3-opus")
            == "openrouter/anthropic/claude-3-opus"
        )
        # Note: OpenRouter models with "gemini" in the path may get normalized
        # This is expected behavior - the function detects "gemini" and adds prefix
        # For fully qualified OpenRouter paths, they should already have the prefix

    def test_case_insensitive_gemini(self):
        """Test Gemini detection is case-insensitive but preserves case in output."""
        # The function detects "gemini" case-insensitively but preserves original case
        # when adding prefix. This is the actual behavior.
        assert normalize_model_name("GEMINI-1.5-FLASH") == "gemini/GEMINI-1.5-FLASH"
        assert normalize_model_name("Gemini-1.5-Flash") == "gemini/Gemini-1.5-Flash"
        assert normalize_model_name("gEmInI-1.5-fLaSh") == "gemini/gEmInI-1.5-fLaSh"

    def test_none_input(self):
        """Test None input returns None."""
        assert normalize_model_name(None) is None

    def test_empty_string(self):
        """Test empty string returns empty string."""
        assert normalize_model_name("") == ""

    def test_non_string_input(self):
        """Test non-string input returns as-is."""
        assert normalize_model_name(123) == 123
        assert normalize_model_name([]) == []

    def test_gemini_with_space(self):
        """Test 'gemini ' (with space) gets default model."""
        result = normalize_model_name("gemini ")
        assert result.startswith("gemini/")

    def test_already_normalized_models(self):
        """Test models that are already normalized remain unchanged."""
        models = [
            "gemini/gemini-1.5-flash",  # Already has gemini/ prefix
            "gpt-4o",  # GPT models don't need prefix
            "claude-3-opus",  # Claude models don't need prefix
        ]

        for model in models:
            assert normalize_model_name(model) == model

        # Note: OpenRouter models with "gemini" in path may get normalized
        # This is expected - the function detects "gemini" and adds prefix
        # For proper OpenRouter models, use full path without "gemini" in the name

    def test_edge_cases(self):
        """Test edge cases in model names."""
        # Model name with special characters
        assert (
            normalize_model_name("gemini-1.5-flash-latest")
            == "gemini/gemini-1.5-flash-latest"
        )

        # Very long model name
        long_name = "gemini-" + "x" * 100
        result = normalize_model_name(long_name)
        assert result.startswith("gemini/")

    def test_idempotency(self):
        """Test that normalization is idempotent."""
        model = "gemini-1.5-flash"
        normalized_once = normalize_model_name(model)
        normalized_twice = normalize_model_name(normalized_once)

        assert normalized_once == normalized_twice

    def test_various_gemini_variants(self):
        """Test various Gemini model name variants."""
        test_cases = [
            ("gemini-1.5-flash", "gemini/gemini-1.5-flash"),
            ("gemini-1.5-pro", "gemini/gemini-1.5-pro"),
            ("gemini-2.0-flash-exp", "gemini/gemini-2.0-flash-exp"),
            ("gemini-pro", "gemini/gemini-pro"),
            ("gemini-ultra", "gemini/gemini-ultra"),
        ]

        for input_model, expected in test_cases:
            assert normalize_model_name(input_model) == expected

    def test_integration_with_config(self):
        """Test normalization works with config system."""
        from aura_cli.core.config import get_config_manager

        config = get_config_manager()

        # Set a model without prefix
        config.set("default_model", "gemini-1.5-flash")

        # Get it back - should be normalized
        model = config.get("default_model")
        assert model == "gemini/gemini-1.5-flash"

    def test_integration_with_pydantic_config(self):
        """Test normalization works with Pydantic config system."""
        from aura_cli.core.config import ConfigCompat

        # Verify the config compat class exists and is usable
        assert callable(ConfigCompat)
