"""Tests for streaming_renderer module.

Tests for real-time text streaming with visual effects.
"""

from unittest.mock import patch

import pytest


class TestStreamingConfig:
    """Tests for StreamingConfig dataclass."""

    def test_streaming_config_defaults(self):
        """Test StreamingConfig has sensible defaults."""
        from aura_cli.cli.ui.components.streaming_renderer import StreamingConfig

        config = StreamingConfig()

        assert config.chunk_delay == 0.02
        assert config.cursor_char == "▌"
        assert config.cursor_blink is True
        assert config.show_progress is True
        assert config.render_markdown is True
        assert config.max_buffer_size == 4096

    def test_streaming_config_custom(self):
        """Test StreamingConfig with custom values."""
        from aura_cli.cli.ui.components.streaming_renderer import StreamingConfig

        config = StreamingConfig(
            chunk_delay=0.05, cursor_char="|", cursor_blink=False, max_buffer_size=2048
        )

        assert config.chunk_delay == 0.05
        assert config.cursor_char == "|"
        assert config.cursor_blink is False
        assert config.max_buffer_size == 2048


class TestStreamingTextRenderer:
    """Tests for StreamingTextRenderer class."""

    @pytest.fixture
    def renderer(self):
        """Create StreamingTextRenderer instance."""
        from aura_cli.cli.ui.components.streaming_renderer import StreamingTextRenderer

        return StreamingTextRenderer()

    def test_renderer_creation(self, renderer):
        """Test renderer can be created."""
        assert renderer is not None
        assert renderer._buffer == ""
        assert renderer._is_streaming is False
        assert renderer._live is None

    def test_renderer_with_custom_config(self):
        """Test renderer with custom config."""
        from aura_cli.cli.ui.components.streaming_renderer import (
            StreamingConfig,
            StreamingTextRenderer,
        )

        config = StreamingConfig(chunk_delay=0.1)
        renderer = StreamingTextRenderer(config=config)

        assert renderer.config.chunk_delay == 0.1

    def test_append_when_not_streaming(self, renderer):
        """Test append does nothing when not streaming."""
        renderer.append("test")
        assert renderer._buffer == ""

    def test_append_buffer_limit(self):
        """Test append respects max_buffer_size."""
        from aura_cli.cli.ui.components.streaming_renderer import (
            StreamingConfig,
            StreamingTextRenderer,
        )

        config = StreamingConfig(max_buffer_size=10)
        renderer = StreamingTextRenderer(config=config)
        renderer._is_streaming = True

        renderer.append("12345678901234567890")  # 20 chars

        # Buffer should be trimmed to last 10 chars
        assert len(renderer._buffer) <= 10

    def test_finish_preserves_full_content_beyond_display_buffer(self):
        from aura_cli.cli.ui.components.streaming_renderer import (
            StreamingConfig,
            StreamingTextRenderer,
        )

        renderer = StreamingTextRenderer(config=StreamingConfig(max_buffer_size=10))
        renderer.start()
        renderer.append("12345678901234567890")

        assert renderer.finish() == "12345678901234567890"

    def test_cancel(self, renderer):
        """Test canceling streaming."""
        renderer._is_streaming = True
        renderer._buffer = "some content"

        renderer.cancel()

        assert renderer._is_streaming is False
        assert renderer._buffer == ""
        assert renderer._live is None

    def test_looks_like_markdown_true(self, renderer):
        """Test _looks_like_markdown detects markdown."""
        renderer._buffer = "# Header\n\n```python\ncode\n```"
        assert renderer._looks_like_markdown() is True

    def test_looks_like_markdown_false(self, renderer):
        """Test _looks_like_markdown returns False for plain text."""
        renderer._buffer = "Just plain text without any special chars"
        assert renderer._looks_like_markdown() is False

    def test_looks_like_markdown_with_bold(self, renderer):
        """Test _looks_like_markdown detects bold."""
        renderer._buffer = "This is **bold** text"
        assert renderer._looks_like_markdown() is True

    def test_looks_like_markdown_with_list(self, renderer):
        """Test _looks_like_markdown detects list."""
        renderer._buffer = "- item 1\n- item 2"
        assert renderer._looks_like_markdown() is True

    def test_update_cursor_blink_disabled(self, renderer):
        """Test cursor blink when disabled."""
        renderer.config.cursor_blink = False

        renderer._update_cursor_blink()

        assert renderer._cursor_visible is True

    def test_update_cursor_blink_enabled(self, renderer):
        """Test cursor blink when enabled."""
        renderer.config.cursor_blink = True
        renderer._last_cursor_toggle = 0  # Force toggle

        initial = renderer._cursor_visible
        renderer._update_cursor_blink()

        # Should have toggled
        assert renderer._cursor_visible != initial


class TestTypingIndicator:
    """Tests for TypingIndicator class."""

    def test_typing_indicator_creation(self):
        """Test TypingIndicator can be created."""
        from aura_cli.cli.ui.components.streaming_renderer import TypingIndicator

        indicator = TypingIndicator()

        assert indicator is not None
        assert indicator._live is None
        assert indicator._is_active is False

    def test_typing_indicator_stop(self):
        """Test stopping indicator."""
        from aura_cli.cli.ui.components.streaming_renderer import TypingIndicator

        indicator = TypingIndicator()
        indicator._is_active = True

        indicator.stop()

        assert indicator._is_active is False
        assert indicator._live is None

    def test_render_frame(self):
        """Test rendering animation frame."""
        from rich.text import Text

        from aura_cli.cli.ui.components.streaming_renderer import TypingIndicator

        with patch(
            "aura_cli.cli.ui.components.streaming_renderer.get_theme_manager"
        ) as mock_theme:
            mock_theme.return_value.get_color.return_value = "cyan"

            indicator = TypingIndicator()
            indicator._message = "Thinking"
            indicator._frame = 2

            result = indicator._render_frame()

            assert isinstance(result, Text)


class TestCreateStreamingRenderer:
    """Tests for create_streaming_renderer function."""

    def test_create_streaming_renderer(self):
        """Test create_streaming_renderer factory."""
        from aura_cli.cli.ui.components.streaming_renderer import (
            StreamingTextRenderer,
            create_streaming_renderer,
        )

        renderer = create_streaming_renderer()

        assert isinstance(renderer, StreamingTextRenderer)

    def test_create_streaming_renderer_no_markdown(self):
        """Test create_streaming_renderer without markdown."""
        from aura_cli.cli.ui.components.streaming_renderer import (
            create_streaming_renderer,
        )

        renderer = create_streaming_renderer(render_markdown=False)

        assert renderer.config.render_markdown is False
