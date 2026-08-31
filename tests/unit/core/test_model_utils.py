"""Tests for core/llm/model_utils.py — normalize_model_name, get_provider_from_model."""

from aura_cli.core.llm.model_utils import (
    format_model_display_name,
    get_default_model_for_provider,
    get_model_catalog,
    get_models_for_provider,
    get_provider_from_model,
    get_valid_models,
    is_valid_model_format,
    normalize_model_name,
    normalize_provider_name,
    resolve_model_option,
)


class TestNormalizeModelName:
    def test_none_returns_none(self):
        assert normalize_model_name(None) is None

    def test_empty_returns_default(self):
        result = normalize_model_name("")
        assert result is not None

    def test_gemini_already_prefixed(self):
        assert (
            normalize_model_name("gemini/gemini-2.5-flash") == "gemini/gemini-2.5-flash"
        )

    def test_gemini_without_prefix(self):
        result = normalize_model_name("gemini-2.5-flash")
        assert result.startswith("gemini/")

    def test_gpt_already_correct(self):
        assert normalize_model_name("gpt-4o") == "gpt-4o"

    def test_gpt_without_dash(self):
        result = normalize_model_name("gpt4o")
        assert "gpt" in result

    def test_claude_already_correct(self):
        result = normalize_model_name("claude-3-5-sonnet-20241022")
        assert result == "claude-3-5-sonnet-20241022"

    def test_openrouter_already_prefixed(self):
        m = "openrouter/meta-llama/llama-3.3-70b-instruct:free"
        assert normalize_model_name(m) == m

    def test_nvidia_already_prefixed(self):
        m = "openai/nvidia/llama-3.3-nemotron-super-49b-v1"
        assert normalize_model_name(m) == m

    def test_grok_returns_grok(self):
        result = normalize_model_name("grok-beta")
        assert "grok" in result

    def test_free_model_gets_openrouter_prefix(self):
        result = normalize_model_name("some-model:free")
        assert result.startswith("openrouter/")


class TestCanonicalModelOptions:
    def test_provider_aliases_are_short_and_stable(self):
        assert normalize_provider_name("Google") == "gemini"
        assert normalize_provider_name("openai") == "gpt"
        assert normalize_provider_name("anthropic") == "claude"

    def test_provider_alias_model_resolves_to_catalog_default(self):
        assert resolve_model_option("google") == "gemini/gemini-2.5-flash"
        assert resolve_model_option("openai") == "gpt-4o"

    def test_auto_option_is_preserved(self):
        assert resolve_model_option(None) == "auto"
        assert resolve_model_option(" ") == "auto"
        assert resolve_model_option("AUTO") == "auto"

    def test_legacy_provider_prefixes_resolve_to_canonical_ids(self):
        cases = {
            "google/gemini-2.5-flash": "gemini/gemini-2.5-flash",
            "anthropic/claude-sonnet-4-6": "claude-sonnet-4-6",
            "openai/nvidia/llama-3.3-nemotron-super-49b-v1": (
                "openai/nvidia/llama-3.3-nemotron-super-49b-v1"
            ),
        }
        for raw_model, expected in cases.items():
            assert resolve_model_option(raw_model) == expected

    def test_default_model_aliases_use_the_same_catalog_entry(self):
        for alias, canonical in (
            ("google", "gemini"),
            ("openai", "gpt"),
            ("anthropic", "claude"),
        ):
            assert get_default_model_for_provider(
                alias
            ) == get_default_model_for_provider(canonical)
            assert (
                get_default_model_for_provider(alias)
                == get_models_for_provider(canonical)[0]
            )

    def test_normalization_is_idempotent_for_legacy_and_unknown_ids(self):
        for model in (
            "google/gemini-2.5-flash",
            "anthropic/claude-sonnet-4-6",
            "openai/nvidia/llama-3.3-nemotron-super-49b-v1",
            "some-unknown-model",
        ):
            normalized = normalize_model_name(model)
            assert normalize_model_name(normalized) == normalized

    def test_catalog_is_defensive_and_alias_aware(self):
        catalog = get_model_catalog()
        assert catalog["gemini"]
        assert get_models_for_provider("google") == catalog["gemini"]
        catalog["gemini"].clear()
        assert get_models_for_provider("gemini")


class TestGetProviderFromModel:
    def test_gemini(self):
        assert get_provider_from_model("gemini/gemini-2.5-flash") == "gemini"

    def test_openai(self):
        assert get_provider_from_model("gpt-4o") == "gpt"

    def test_anthropic(self):
        assert get_provider_from_model("claude-3-5-sonnet-20241022") == "claude"

    def test_openrouter(self):
        assert (
            get_provider_from_model("openrouter/meta-llama/llama-3.3-70b-instruct:free")
            == "openrouter"
        )

    def test_nvidia(self):
        assert (
            get_provider_from_model("openai/nvidia/llama-3.3-nemotron-super-49b-v1")
            == "nvidia"
        )

    def test_nemotron_by_name(self):
        assert (
            get_provider_from_model("nvidia/llama-3.3-nemotron-super-49b-v1")
            == "nvidia"
        )

    def test_auto(self):
        assert get_provider_from_model("auto") == "auto"

    def test_none_returns_none(self):
        assert get_provider_from_model(None) is None

    def test_unknown_returns_none(self):
        assert get_provider_from_model("unknown-model-xyz") is None


class TestGetValidModels:
    def test_returns_dict(self):
        models = get_valid_models()
        assert isinstance(models, dict)
        assert len(models) > 0

    def test_gemini_present(self):
        models = get_valid_models()
        gemini = [k for k in models if "gemini" in k]
        assert len(gemini) > 0

    def test_nvidia_present(self):
        models = get_valid_models()
        nvidia = [k for k in models if "nvidia" in k]
        assert len(nvidia) > 0

    def test_each_model_has_name_and_provider(self):
        for _model_id, info in get_valid_models().items():
            assert "name" in info
            assert "provider" in info


class TestFormatModelDisplayName:
    def test_gemini(self):
        assert (
            format_model_display_name("gemini/gemini-2.5-flash") == "gemini-2.5-flash"
        )

    def test_gpt(self):
        assert format_model_display_name("gpt-4o") == "gpt-4o"

    def test_claude(self):
        result = format_model_display_name("claude-3-5-sonnet-20241022")
        assert "claude" in result
        assert "sonnet" in result

    def test_nemotron(self):
        result = format_model_display_name(
            "openai/nvidia/llama-3.3-nemotron-super-49b-v1"
        )
        assert "nemotron" in result

    def test_auto(self):
        assert format_model_display_name("auto") == "auto"


class TestIsValidModelFormat:
    def test_gemini_with_prefix_valid(self):
        assert is_valid_model_format("gemini/gemini-2.5-flash") is True

    def test_gemini_without_prefix_invalid(self):
        assert is_valid_model_format("gemini-2.5-flash") is False

    def test_gpt_valid(self):
        assert is_valid_model_format("gpt-4o") is True

    def test_none_invalid(self):
        assert is_valid_model_format(None) is False

    def test_empty_invalid(self):
        assert is_valid_model_format("") is False
