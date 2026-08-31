"""Tests for core/llm/api_validator.py — API key validation logic."""

from unittest.mock import MagicMock, patch

import pytest

from aura_cli.core.llm.api_validator import (
    ValidationResult,
    ValidationStatus,
    quick_test_api_key,
    validate_anthropic_api_key,
    validate_api_key,
    validate_google_api_key,
    validate_nvidia_api_key,
    validate_openai_api_key,
    validate_openrouter_api_key,
)


class TestValidationStatus:
    def test_values(self):
        assert ValidationStatus.SUCCESS.value == "success"
        assert ValidationStatus.INVALID_KEY.value == "invalid_key"
        assert ValidationStatus.RATE_LIMITED.value == "rate_limited"
        assert ValidationStatus.NETWORK_ERROR.value == "network_error"
        assert ValidationStatus.TIMEOUT.value == "timeout"
        assert ValidationStatus.UNKNOWN_ERROR.value == "unknown_error"


class TestValidationResult:
    def test_creation(self):
        r = ValidationResult(
            status=ValidationStatus.SUCCESS, provider="openai", message="ok"
        )
        assert r.status == ValidationStatus.SUCCESS
        assert r.provider == "openai"
        assert r.message == "ok"
        assert r.model_tested is None
        assert r.response_preview is None

    def test_with_optional_fields(self):
        r = ValidationResult(
            status=ValidationStatus.SUCCESS,
            provider="google",
            message="ok",
            model_tested="gemini-2.5-flash",
            response_preview="Hello!",
        )
        assert r.model_tested == "gemini-2.5-flash"
        assert r.response_preview == "Hello!"


@pytest.fixture
def mock_litellm():
    """Patch litellm in sys.modules so local imports pick up the mock."""
    mock = MagicMock()
    with patch.dict("sys.modules", {"litellm": mock}):
        yield mock


class TestValidateGoogleApiKey:
    @patch.dict("os.environ", {}, clear=False)
    def test_valid_key(self, mock_litellm):
        mock_litellm.completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="hi"))]
        )
        result = validate_google_api_key("AIza-test123")
        assert result.status == ValidationStatus.SUCCESS
        assert result.provider == "Google (Gemini)"

    @patch.dict("os.environ", {}, clear=False)
    def test_invalid_key(self, mock_litellm):
        mock_litellm.completion.side_effect = Exception("API key not valid")
        result = validate_google_api_key("AIza-bad")
        assert result.status != ValidationStatus.SUCCESS


class TestValidateOpenAIApiKey:
    @patch.dict("os.environ", {}, clear=False)
    def test_valid_key(self, mock_litellm):
        mock_litellm.completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="hi"))]
        )
        result = validate_openai_api_key("sk-test123")
        assert result.status == ValidationStatus.SUCCESS

    @patch.dict("os.environ", {}, clear=False)
    def test_invalid_key(self, mock_litellm):
        mock_litellm.completion.side_effect = Exception("Incorrect API key provided")
        result = validate_openai_api_key("sk-bad")
        assert result.status != ValidationStatus.SUCCESS


class TestValidateAnthropicApiKey:
    @patch.dict("os.environ", {}, clear=False)
    def test_valid_key(self, mock_litellm):
        mock_litellm.completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="hi"))]
        )
        result = validate_anthropic_api_key("sk-ant-test")
        assert result.status == ValidationStatus.SUCCESS

    @patch.dict("os.environ", {}, clear=False)
    def test_invalid_key(self, mock_litellm):
        mock_litellm.completion.side_effect = Exception("Invalid API Key")
        result = validate_anthropic_api_key("sk-ant-bad")
        assert result.status != ValidationStatus.SUCCESS


class TestValidateOpenRouterApiKey:
    @patch.dict("os.environ", {}, clear=False)
    def test_valid_key(self, mock_litellm):
        mock_litellm.completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="hi"))]
        )
        result = validate_openrouter_api_key("sk-or-test")
        assert result.status == ValidationStatus.SUCCESS

    @patch.dict("os.environ", {}, clear=False)
    def test_invalid_key(self, mock_litellm):
        mock_litellm.completion.side_effect = Exception("Unauthorized")
        result = validate_openrouter_api_key("sk-or-bad")
        assert result.status != ValidationStatus.SUCCESS


class TestValidateNvidiaApiKey:
    @patch.dict("os.environ", {}, clear=False)
    def test_valid_key(self, mock_litellm):
        mock_litellm.completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="hi"))]
        )
        result = validate_nvidia_api_key("nvapi-test")
        assert result.status == ValidationStatus.SUCCESS

    @patch.dict("os.environ", {}, clear=False)
    def test_invalid_key(self, mock_litellm):
        mock_litellm.completion.side_effect = Exception("Invalid credentials")
        result = validate_nvidia_api_key("nvapi-bad")
        assert result.status != ValidationStatus.SUCCESS


class TestValidateApiKey:
    @patch("aura_cli.core.llm.api_validator.validate_openai_api_key")
    def test_routes_openai(self, mock_v):
        mock_v.return_value = ValidationResult(ValidationStatus.SUCCESS, "openai", "ok")
        result = validate_api_key("openai", "sk-abc123")
        mock_v.assert_called_once_with("sk-abc123")
        assert result.status == ValidationStatus.SUCCESS

    @patch("aura_cli.core.llm.api_validator.validate_anthropic_api_key")
    def test_routes_anthropic(self, mock_v):
        mock_v.return_value = ValidationResult(
            ValidationStatus.SUCCESS, "anthropic", "ok"
        )
        validate_api_key("anthropic", "sk-ant-x")
        mock_v.assert_called_once()

    @patch("aura_cli.core.llm.api_validator.validate_google_api_key")
    def test_routes_google(self, mock_v):
        mock_v.return_value = ValidationResult(ValidationStatus.SUCCESS, "google", "ok")
        validate_api_key("google", "AIza-x")
        mock_v.assert_called_once()

    @patch("aura_cli.core.llm.api_validator.validate_openrouter_api_key")
    def test_routes_openrouter(self, mock_v):
        mock_v.return_value = ValidationResult(
            ValidationStatus.SUCCESS, "openrouter", "ok"
        )
        validate_api_key("openrouter", "sk-or-x")
        mock_v.assert_called_once()

    @patch("aura_cli.core.llm.api_validator.validate_nvidia_api_key")
    def test_routes_nvidia(self, mock_v):
        mock_v.return_value = ValidationResult(ValidationStatus.SUCCESS, "nvidia", "ok")
        validate_api_key("nvidia", "nvapi-x")
        mock_v.assert_called_once()

    def test_unknown_provider(self):
        result = validate_api_key("unknown_xyz", "key123")
        assert result.status == ValidationStatus.UNKNOWN_ERROR
        assert "não suportado" in result.message

    def test_case_insensitive_provider(self):
        with patch("aura_cli.core.llm.api_validator.validate_openai_api_key") as mock_v:
            mock_v.return_value = ValidationResult(
                ValidationStatus.SUCCESS, "openai", "ok"
            )
            validate_api_key("OpenAI", "sk-x")
            mock_v.assert_called_once()

    def test_routes_canonical_provider_aliases(self):
        with (
            patch(
                "aura_cli.core.llm.api_validator.validate_google_api_key"
            ) as mock_gemini,
            patch(
                "aura_cli.core.llm.api_validator.validate_openai_api_key"
            ) as mock_gpt,
            patch(
                "aura_cli.core.llm.api_validator.validate_anthropic_api_key"
            ) as mock_claude,
        ):
            validate_api_key("gemini", "gemini-key")
            validate_api_key("gpt", "gpt-key")
            validate_api_key("claude", "claude-key")

        mock_gemini.assert_called_once_with("gemini-key")
        mock_gpt.assert_called_once_with("gpt-key")
        mock_claude.assert_called_once_with("claude-key")


class TestQuickTestApiKey:
    @patch("aura_cli.core.llm.api_validator.validate_api_key")
    def test_success_returns_true(self, mock_validate):
        mock_validate.return_value = ValidationResult(
            ValidationStatus.SUCCESS, "openai", "ok"
        )
        success, _msg = quick_test_api_key("openai", "sk-test")
        assert success is True

    @patch("aura_cli.core.llm.api_validator.validate_api_key")
    def test_invalid_returns_false(self, mock_validate):
        mock_validate.return_value = ValidationResult(
            ValidationStatus.INVALID_KEY, "openai", "bad key"
        )
        success, msg = quick_test_api_key("openai", "sk-bad")
        assert success is False
        assert "bad key" in msg

    @patch("aura_cli.core.llm.api_validator.validate_api_key")
    def test_rate_limited_returns_true(self, mock_validate):
        mock_validate.return_value = ValidationResult(
            ValidationStatus.RATE_LIMITED, "openai", "rate limited"
        )
        success, _msg = quick_test_api_key("openai", "sk-x")
        assert success is True

    @patch("aura_cli.core.llm.api_validator.validate_api_key")
    def test_timeout_returns_true(self, mock_validate):
        mock_validate.return_value = ValidationResult(
            ValidationStatus.TIMEOUT, "openai", "timed out"
        )
        success, _msg = quick_test_api_key("openai", "sk-x")
        assert success is True

    @patch("aura_cli.core.llm.api_validator.validate_api_key")
    def test_network_error_returns_false(self, mock_validate):
        mock_validate.return_value = ValidationResult(
            ValidationStatus.NETWORK_ERROR, "openai", "no network"
        )
        success, _msg = quick_test_api_key("openai", "sk-x")
        assert success is False
