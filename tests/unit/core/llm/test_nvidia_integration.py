"""Tests for NVIDIA/Nemotron integration in the LLM stack."""

from unittest.mock import Mock, patch

from aura_cli.core.llm.model_utils import (
    MODEL_PRESETS,
    format_model_display_name,
    get_provider_from_model,
)
from aura_cli.core.llm.rate_limiter import RateLimiter


def test_nvidia_provider_is_detected_from_model_name():
    """Nemotron models should resolve to the NVIDIA provider."""
    assert (
        get_provider_from_model("openai/nvidia/llama-3.3-nemotron-super-49b-v1")
        == "nvidia"
    )
    assert get_provider_from_model("nvidia/llama-3.1-nemotron-70b-instruct") == "nvidia"


def test_openrouter_nemotron_models_in_presets():
    """Free Nemotron models should appear in the openrouter presets."""
    assert "openrouter" in MODEL_PRESETS
    openrouter_models = MODEL_PRESETS["openrouter"]
    nemotron_models = [m for m in openrouter_models if "nemotron" in m]
    assert len(nemotron_models) >= 1


def test_nvidia_display_names_are_human_friendly():
    """Known Nemotron models should have readable display labels."""
    result1 = format_model_display_name("openai/nvidia/llama-3.3-nemotron-super-49b-v1")
    assert "nemotron" in result1
    assert "49b" in result1

    result2 = format_model_display_name("openai/nvidia/llama-3.1-nemotron-70b-instruct")
    assert "nemotron" in result2
    assert "70b" in result2


def test_rate_limiter_classifies_nvidia_models_separately():
    """NVIDIA models should not be bucketed as OpenAI or default."""
    limiter = RateLimiter()

    assert (
        limiter._get_provider("openai/nvidia/llama-3.3-nemotron-super-49b-v1")
        == "nvidia"
    )
    assert limiter._get_provider("nvidia/llama-3.1-nemotron-70b-instruct") == "nvidia"


@patch("aura_cli.core.llm.base.get_rate_limiter")
@patch("aura_cli.core.llm.base._execute_llm_call")
def test_query_with_fallback_uses_openrouter_presets(
    mock_execute_llm_call,
    mock_get_rate_limiter,
):
    """OpenRouter requests should fall back through the preset list."""
    from aura_cli.core.llm.base import query_with_fallback

    mock_limiter = Mock()
    mock_limiter.wait_if_needed.return_value = True
    mock_limiter.record_success.return_value = None
    mock_limiter.record_failure.return_value = None
    mock_limiter.release.return_value = None
    mock_get_rate_limiter.return_value = mock_limiter

    success_response = Mock()
    success_response.choices = [Mock(message=Mock(content="ok"))]

    def side_effect(current_model, messages, completion_params, loading=None):
        if "nemotron-3-super" in current_model:
            raise TimeoutError("timeout on primary model")
        return success_response

    mock_execute_llm_call.side_effect = side_effect

    result = query_with_fallback(
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        [{"role": "user", "content": "hi"}],
        max_retries=1,
    )

    assert result is success_response
    # Should have tried primary then fallen back to next openrouter model
    attempted = [call.args[0] for call in mock_execute_llm_call.call_args_list]
    assert len(attempted) >= 2
    assert attempted[0] == "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
