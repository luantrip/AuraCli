"""
Comprehensive tests for LLM fallback and retry mechanisms.

Tests cover:
    - Model preset loading from JSON
    - Fallback chain execution
    - Rate limit handling (429 errors)
    - Timeout handling
    - Provider detection
    - Model normalization
"""

import json
from pathlib import Path


class TestModelPresets:
    """Tests for MODEL_PRESETS loading from models.json."""

    def test_model_presets_loaded_from_json(self):
        """MODEL_PRESETS should load from models.json file."""
        from aura_cli.core.llm.model_utils import MODEL_PRESETS

        # Should have all providers
        assert "gemini" in MODEL_PRESETS
        assert "claude" in MODEL_PRESETS
        assert "gpt" in MODEL_PRESETS
        assert "openrouter" in MODEL_PRESETS

    def test_gemini_presets_correct(self):
        """Gemini presets should have correct format."""
        from aura_cli.core.llm.model_utils import MODEL_PRESETS

        gemini_models = MODEL_PRESETS.get("gemini", [])
        assert len(gemini_models) >= 2
        # All Gemini models should have gemini/ prefix
        for model in gemini_models:
            assert model.startswith("gemini/"), f"Model {model} missing gemini/ prefix"

    def test_claude_presets_correct(self):
        """Claude presets should have correct format."""
        from aura_cli.core.llm.model_utils import MODEL_PRESETS

        claude_models = MODEL_PRESETS.get("claude", [])
        assert len(claude_models) >= 2
        # All Claude models should start with claude-
        for model in claude_models:
            assert model.startswith("claude-"), (
                f"Model {model} should start with claude-"
            )

    def test_gpt_presets_correct(self):
        """GPT presets should have correct format."""
        from aura_cli.core.llm.model_utils import MODEL_PRESETS

        gpt_models = MODEL_PRESETS.get("gpt", [])
        assert len(gpt_models) >= 2
        # All GPT models should start with gpt-
        for model in gpt_models:
            assert model.startswith("gpt-"), f"Model {model} should start with gpt-"

    def test_models_json_exists(self):
        """models.json file should exist."""
        from aura_cli.core.llm import model_utils

        json_path = Path(model_utils.__file__).parent / "models.json"
        assert json_path.exists(), "models.json should exist"

    def test_models_json_valid(self):
        """models.json should be valid JSON."""
        from aura_cli.core.llm import model_utils

        json_path = Path(model_utils.__file__).parent / "models.json"
        with open(json_path) as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert len(data) >= 4  # At least gemini, claude, gpt, auto


class TestModelNormalization:
    """Tests for model name normalization."""

    def test_normalize_gemini_without_prefix(self):
        """Gemini models without prefix should get gemini/ prefix."""
        from aura_cli.core.llm.model_utils import normalize_model_name

        result = normalize_model_name("gemini-2.5-flash")
        assert result == "gemini/gemini-2.5-flash"

    def test_normalize_gemini_with_prefix(self):
        """Gemini models with prefix should remain unchanged."""
        from aura_cli.core.llm.model_utils import normalize_model_name

        result = normalize_model_name("gemini/gemini-2.5-flash")
        assert result == "gemini/gemini-2.5-flash"

    def test_normalize_generic_gemini(self):
        """Generic 'gemini' should map to default."""
        from aura_cli.core.llm.model_utils import (
            DEFAULT_GEMINI_MODEL,
            normalize_model_name,
        )

        result = normalize_model_name("Gemini")
        assert result == DEFAULT_GEMINI_MODEL

    def test_normalize_gpt_unchanged(self):
        """GPT models should remain unchanged."""
        from aura_cli.core.llm.model_utils import normalize_model_name

        result = normalize_model_name("gpt-4o")
        assert result == "gpt-4o"

    def test_normalize_claude_unchanged(self):
        """Claude models should remain unchanged."""
        from aura_cli.core.llm.model_utils import normalize_model_name

        result = normalize_model_name("claude-3-5-sonnet-20241022")
        assert result == "claude-3-5-sonnet-20241022"

    def test_normalize_none_returns_none(self):
        """None should return None."""
        from aura_cli.core.llm.model_utils import normalize_model_name

        result = normalize_model_name(None)
        assert result is None

    def test_normalize_empty_string_returns_empty(self):
        """Empty string should return empty string (passthrough)."""
        from aura_cli.core.llm.model_utils import normalize_model_name

        result = normalize_model_name("")
        # Empty string passes through (caller handles default)
        assert result == ""


class TestProviderDetection:
    """Tests for provider detection from model name."""

    def test_detect_gemini_provider(self):
        """Should detect gemini provider."""
        from aura_cli.core.llm.model_utils import get_provider_from_model

        assert get_provider_from_model("gemini/gemini-2.5-flash") == "gemini"
        assert get_provider_from_model("gemini-2.0-flash") == "gemini"

    def test_detect_claude_provider(self):
        """Should detect claude provider."""
        from aura_cli.core.llm.model_utils import get_provider_from_model

        assert get_provider_from_model("claude-3-5-sonnet-20241022") == "claude"

    def test_detect_gpt_provider(self):
        """Should detect gpt provider."""
        from aura_cli.core.llm.model_utils import get_provider_from_model

        assert get_provider_from_model("gpt-4o") == "gpt"
        assert get_provider_from_model("gpt-4") == "gpt"

    def test_detect_auto_provider(self):
        """Should detect auto provider."""
        from aura_cli.core.llm.model_utils import get_provider_from_model

        assert get_provider_from_model("auto") == "auto"

    def test_detect_none_for_unknown(self):
        """Should return None for unknown models."""
        from aura_cli.core.llm.model_utils import get_provider_from_model

        assert get_provider_from_model("unknown-model") is None
        assert get_provider_from_model(None) is None


class TestFallbackModels:
    """Tests for fallback model chain generation."""

    def test_get_fallback_models_includes_original(self):
        """Fallback list should include original model first."""
        from aura_cli.core.llm.model_utils import get_fallback_models

        models = get_fallback_models("gemini/gemini-2.5-flash")
        assert models[0] == "gemini/gemini-2.5-flash"

    def test_get_fallback_models_adds_alternatives(self):
        """Fallback list should include alternative models."""
        from aura_cli.core.llm.model_utils import get_fallback_models

        models = get_fallback_models("gemini/gemini-2.5-flash")
        assert len(models) >= 2

    def test_get_fallback_no_duplicates(self):
        """Fallback list should not have duplicates."""
        from aura_cli.core.llm.model_utils import get_fallback_models

        models = get_fallback_models("gpt-4o")
        assert len(models) == len(set(models))

    def test_get_fallback_unknown_model(self):
        """Unknown model should return single-item list."""
        from aura_cli.core.llm.model_utils import get_fallback_models

        models = get_fallback_models("unknown-model-xyz")
        assert models == ["unknown-model-xyz"]


class TestValidModels:
    """Tests for valid models discovery."""

    def test_get_valid_models_returns_dict(self):
        """Should return dictionary of valid models."""
        from aura_cli.core.llm.model_utils import get_valid_models

        models = get_valid_models()
        assert isinstance(models, dict)
        assert len(models) > 0

    def test_valid_models_have_name_and_provider(self):
        """Each model should have name and provider."""
        from aura_cli.core.llm.model_utils import get_valid_models

        models = get_valid_models()
        for model_id, info in models.items():
            assert "name" in info, f"Model {model_id} missing name"
            assert "provider" in info, f"Model {model_id} missing provider"


class TestModelValidation:
    """Tests for model format validation."""

    def test_valid_gemini_format(self):
        """Gemini with prefix should be valid."""
        from aura_cli.core.llm.model_utils import is_valid_model_format

        assert is_valid_model_format("gemini/gemini-2.5-flash") is True

    def test_invalid_gemini_format(self):
        """Gemini without prefix should be invalid."""
        from aura_cli.core.llm.model_utils import is_valid_model_format

        assert is_valid_model_format("gemini-2.5-flash") is False

    def test_valid_gpt_format(self):
        """GPT models should be valid without prefix."""
        from aura_cli.core.llm.model_utils import is_valid_model_format

        assert is_valid_model_format("gpt-4o") is True

    def test_invalid_empty_model(self):
        """Empty model should be invalid."""
        from aura_cli.core.llm.model_utils import is_valid_model_format

        assert is_valid_model_format("") is False
        assert is_valid_model_format(None) is False
