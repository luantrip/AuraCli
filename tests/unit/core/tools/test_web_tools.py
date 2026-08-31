"""Tests for web.py - Web search tools."""

from unittest.mock import Mock, patch

import pytest

from aura_cli.core.tools.web import _web_search_cache, web_search


@pytest.fixture(autouse=True)
def clear_web_cache():
    """Clear web search cache before and after each test to ensure isolation."""
    _web_search_cache.clear()
    yield
    _web_search_cache.clear()


class TestWebSearch:
    """Test suite for web_search."""

    @patch("aura_cli.core.tools.web._search_ddgs")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.web.Console")
    def test_web_search_success(self, mock_console_class, mock_display, mock_ddgs):
        """Test successful web search."""
        mock_ddgs.return_value = [
            {
                "title": "Test Title",
                "url": "https://example.com",
                "description": "Test description",
            }
        ]
        mock_console_class.return_value = Mock()

        result = web_search("Python programming", num_results=5)

        assert "Test Title" in result
        assert "https://example.com" in result
        assert "Test description" in result
        mock_ddgs.assert_called_once_with("Python programming", 5)

    @patch("aura_cli.core.tools.web._search_ddgs")
    @patch("aura_cli.core.tools.web._search_google")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.web.Console")
    def test_web_search_no_results(
        self, mock_console_class, mock_display, mock_google, mock_ddgs
    ):
        """Test web search with no results from any backend."""
        mock_ddgs.return_value = []
        mock_google.return_value = []
        mock_console_class.return_value = Mock()

        result = web_search("nonexistent query xyz123", num_results=5)

        assert "nenhum resultado" in result.lower()

    @patch("aura_cli.core.tools.web._search_ddgs")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.web.Console")
    def test_web_search_multiple_results(
        self, mock_console_class, mock_display, mock_ddgs
    ):
        """Test web search with multiple results."""
        mock_ddgs.return_value = [
            {
                "title": f"Result {i + 1}",
                "url": f"https://example.com/{i + 1}",
                "description": f"Description {i + 1}",
            }
            for i in range(3)
        ]
        mock_console_class.return_value = Mock()

        result = web_search("test query multiple", num_results=3)

        assert "Result 1" in result
        assert "Result 2" in result
        assert "Result 3" in result

    @patch("aura_cli.core.tools.web._search_ddgs")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.web.Console")
    def test_web_search_error(self, mock_console_class, mock_display, mock_ddgs):
        """Test web search with error."""
        mock_ddgs.side_effect = Exception("Network error")
        mock_console_class.return_value = Mock()

        result = web_search("test query error")

        assert "erro" in result.lower() or "error" in result.lower()

    @patch("aura_cli.core.tools.web._search_ddgs")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.web.Console")
    def test_web_search_default_num_results(
        self, mock_console_class, mock_display, mock_ddgs
    ):
        """Test web search uses default num_results=5."""
        mock_ddgs.return_value = []
        mock_console_class.return_value = Mock()

        web_search("test query default")

        mock_ddgs.assert_called_once_with("test query default", 5)

    @patch("aura_cli.core.tools.web._search_ddgs")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.web.Console")
    def test_web_search_custom_num_results(
        self, mock_console_class, mock_display, mock_ddgs
    ):
        """Test web search passes custom num_results."""
        mock_ddgs.return_value = []
        mock_console_class.return_value = Mock()

        web_search("test query custom", num_results=10)

        mock_ddgs.assert_called_once_with("test query custom", 10)

    @patch("aura_cli.core.tools.web._search_ddgs")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.web.Console")
    def test_web_search_formats_results(
        self, mock_console_class, mock_display, mock_ddgs
    ):
        """Test web search formats results correctly."""
        mock_ddgs.return_value = [
            {
                "title": "Title",
                "url": "https://example.com",
                "description": "Description",
            }
        ]
        mock_console_class.return_value = Mock()

        result = web_search("test query format")

        assert "1." in result
        assert "Link:" in result
        assert "Descrição:" in result

    @patch("aura_cli.core.tools.web._search_ddgs")
    @patch("aura_cli.core.tools.web._search_google")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.web.Console")
    def test_web_search_fallback_to_google(
        self, mock_console_class, mock_display, mock_google, mock_ddgs
    ):
        """Test web search falls back to Google when DDG returns empty."""
        import aura_cli.core.tools.web as web_module

        mock_ddgs.return_value = []
        mock_google.return_value = [
            {
                "title": "Google Result",
                "url": "https://google.com/result",
                "description": "From Google",
            }
        ]
        mock_console_class.return_value = Mock()

        # The fallback only triggers when google_search is not None.
        # Patch the module-level google_search sentinel so the branch is taken.
        original = web_module.google_search
        try:
            web_module.google_search = object()  # truthy non-None sentinel
            result = web_search("test fallback")
        finally:
            web_module.google_search = original

        assert "Google Result" in result
        mock_ddgs.assert_called_once()
        mock_google.assert_called_once()

    @patch("aura_cli.core.tools.web._search_ddgs")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.web.Console")
    def test_web_search_caches_successful_results(
        self, mock_console_class, mock_display, mock_ddgs
    ):
        """Test that successful results are cached."""
        mock_ddgs.return_value = [
            {
                "title": "Cached",
                "url": "https://cached.com",
                "description": "Cached result",
            }
        ]
        mock_console_class.return_value = Mock()

        # First call
        web_search("cache test")
        # Second call should use cache
        result = web_search("cache test")

        assert "Cached" in result
        # DDG should only be called once (second call uses cache)
        assert mock_ddgs.call_count == 1

    @patch("aura_cli.core.tools.web._search_ddgs")
    @patch("aura_cli.core.tools.web._search_google")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.web.Console")
    def test_web_search_does_not_cache_empty_results(
        self, mock_console_class, mock_display, mock_google, mock_ddgs
    ):
        """Test that empty results are NOT cached."""
        mock_ddgs.return_value = []
        mock_google.return_value = []
        mock_console_class.return_value = Mock()

        # First call (empty)
        web_search("empty test")
        # Second call should hit network again (not cached)
        web_search("empty test")

        assert mock_ddgs.call_count == 2

    @patch("aura_cli.core.tools.web._ddgs_available", False)
    @patch("aura_cli.core.tools.web.google_search", None)
    @patch("aura_cli.core.ui.display_tool_call")
    def test_web_search_no_backend_available(self, mock_display):
        """Test error when no search backend is available."""
        result = web_search("test no backend")

        assert "nenhum pacote" in result.lower() or "erro" in result.lower()
