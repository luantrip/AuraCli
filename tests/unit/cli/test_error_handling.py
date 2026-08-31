"""Tests for cli/error_handling.py."""

from unittest.mock import MagicMock, patch

from aura_cli.cli.error_handling import (
    detect_provider_from_error,
    handle_generic_exception,
    handle_rate_limit_error,
    handle_rate_limit_in_exception,
)


class TestDetectProviderFromError:
    def test_google(self):
        assert detect_provider_from_error("gemini error") == "google"
        assert detect_provider_from_error("google api") == "google"

    def test_openai(self):
        assert detect_provider_from_error("openai key") == "openai"
        assert detect_provider_from_error("gpt-4 error") == "openai"

    def test_anthropic(self):
        assert detect_provider_from_error("anthropic api") == "anthropic"
        assert detect_provider_from_error("claude issue") == "anthropic"

    def test_unknown(self):
        assert detect_provider_from_error("random error") == "unknown"


class TestHandleRateLimitError:
    def test_free_tier(self):
        error = Exception("free_tier quota exceeded")
        msg = handle_rate_limit_error(error, model="gemini")
        assert "Plano Gratuito" in msg

    def test_normal_rate_limit(self):
        error = Exception("rate limit hit")
        msg = handle_rate_limit_error(error, model="gpt-4o")
        assert "Limite de uso" in msg
        assert "gpt-4o" in msg

    def test_retry_after(self):
        error = Exception("rate limit")
        msg = handle_rate_limit_error(error, retry_after=90, model="x")
        assert "1min 30s" in msg

    def test_retry_after_from_error_attr(self):
        error = Exception("rate limit")
        error.retry_after = 45
        msg = handle_rate_limit_error(error, model="x")
        assert "45s" in msg


class TestHandleRateLimitInException:
    @patch("aura_cli.core.error_handler.get_error_handler", return_value=MagicMock())
    def test_detects_429(self, _):
        error = Exception("Error 429: rate limit exceeded")
        assert handle_rate_limit_in_exception(error, "model") is True

    @patch("aura_cli.core.error_handler.get_error_handler", return_value=MagicMock())
    def test_detects_quota(self, _):
        error = Exception("quota exceeded for resource")
        assert handle_rate_limit_in_exception(error, "model") is True

    def test_ignores_unrelated(self):
        error = Exception("file not found")
        assert handle_rate_limit_in_exception(error, "model") is False


class TestHandleGenericException:
    @patch("aura_cli.core.error_handler.get_error_handler", return_value=MagicMock())
    def test_rate_limit_handled(self, mock_handler):
        error = Exception("429 rate limit")
        ui = MagicMock()
        handle_generic_exception(error, "model", ui=ui)
        # Rate limit is detected and handled via error_handler
        mock_handler.return_value.handle_error.assert_called()

    @patch("aura_cli.core.error_handler.get_error_handler", return_value=MagicMock())
    def test_console_render_error(self, _):
        error = Exception("'Console' object has no attribute 'xyz'")
        ui = MagicMock()
        handle_generic_exception(error, "model", ui=ui)
        ui.display_error.assert_called()
        assert "renderização" in ui.display_error.call_args[0][0]

    @patch("aura_cli.core.error_handler.get_error_handler", return_value=MagicMock())
    def test_generic_error(self, mock_handler):
        error = RuntimeError("something unexpected")
        ui = MagicMock()
        handle_generic_exception(error, "model", ui=ui)
        mock_handler.return_value.handle_error.assert_called()
