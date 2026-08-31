"""Testes para llm/base.py."""

from unittest.mock import Mock, patch

from aura_cli.core.llm.model_utils import DEFAULT_MODEL


class TestLLMBase:
    """Testes para LLM base."""

    def setup_method(self):
        """Reset circuit breakers before each test to avoid cross-test contamination."""
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.CIRCUIT_BREAKER_REGISTRY) and container.is_resolved(
            Services.CIRCUIT_BREAKER_REGISTRY
        ):
            container.resolve(Services.CIRCUIT_BREAKER_REGISTRY).reset_all()

    @patch("aura_cli.core.llm.base.litellm.completion")
    def test_query_with_fallback(self, mock_completion):
        """Testa query com fallback."""
        from aura_cli.core.llm.base import query_with_fallback

        mock_completion.return_value = Mock(
            choices=[Mock(message=Mock(content="test response"))]
        )

        result = query_with_fallback(
            "gpt-4o", [{"role": "user", "content": "test query"}]
        )
        assert result is not None

    def test_resolve_model_auto_uses_central_default_on_profile_failure(self):
        """Auto mode should fall back to the central default model."""
        from aura_cli.core.llm.base import _resolve_model

        with patch(
            "aura_cli.core.llm.task_router.TaskRouter.select_model",
            side_effect=RuntimeError("boom"),
        ):
            result = _resolve_model("auto", [{"role": "user", "content": "test query"}])

        assert result == DEFAULT_MODEL

    def test_get_recommended_model_uses_central_provider_defaults(self):
        """Provider recommendations should come from the central catalog."""
        from aura_cli.core.llm.base import get_recommended_model

        assert get_recommended_model("nvidia") == "nvidia/nvidia/nemotron-3.5-lightning-30b-a3b"
        assert get_recommended_model("openai") == "gpt-4o"
        assert get_recommended_model("anthropic") == "claude-sonnet-4-6"
