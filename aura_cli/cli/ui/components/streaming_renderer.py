"""
StreamingTextRenderer - Real-time text streaming with visual effects.

Provides smooth streaming display for LLM responses with:
- Character-by-character or chunk rendering
- Cursor animation
- Progress indication
- Markdown-aware streaming
"""

import contextlib
from dataclasses import dataclass
import time
from typing import Callable, Generator, Optional

from rich.console import Console, RenderableType
from rich.live import Live
from rich.text import Text

from aura_cli.cli.ui.components.markdown_display import AuraMarkdownDisplay
from aura_cli.cli.ui.theme_manager import get_theme_manager
from aura_cli.cli.utils.thread_manager import get_thread_manager


@dataclass
class StreamingConfig:
    """Configuration for streaming behavior."""

    chunk_delay: float = 0.02
    cursor_char: str = "▌"
    cursor_blink: bool = True
    show_progress: bool = True
    render_markdown: bool = True
    max_buffer_size: int = 4096


class StreamingTextRenderer:
    """
    Renders streaming text with visual effects.

    Supports both character-by-character and chunk-based streaming
    with cursor animation and progress indication.
    """

    def __init__(
        self,
        console: Optional[Console] = None,
        config: Optional[StreamingConfig] = None,
    ):
        """Initialize the instance."""
        self.console = console or Console()
        self.config = config or StreamingConfig()
        self._buffer = ""
        self._full_buffer = ""
        self._is_streaming = False
        self._live: Optional[Live] = None
        self._cursor_visible = True
        self._last_cursor_toggle = 0.0

    def start(self) -> None:
        """Start streaming session."""
        self._buffer = ""
        self._full_buffer = ""
        self._is_streaming = True
        self._live = Live(
            self._render_current(),
            console=self.console,
            refresh_per_second=30,
            transient=True,
        )
        self._live.start()

    def append(self, chunk: str) -> None:
        """Append chunk to streaming buffer."""
        if not self._is_streaming:
            return

        self._full_buffer += chunk
        self._buffer = self._full_buffer

        if len(self._buffer) > self.config.max_buffer_size:
            self._buffer = self._buffer[-self.config.max_buffer_size :]

        if self._live:
            self._live.update(self._render_current())

    def finish(self) -> str:
        """Finish streaming and return final content."""
        self._is_streaming = False

        if self._live:
            self._live.update(self._render_final())
            self._live.stop()
            self._live = None

        result = self._full_buffer
        self._buffer = ""
        self._full_buffer = ""
        return result

    def cancel(self) -> None:
        """Cancel streaming."""
        self._is_streaming = False
        if self._live:
            self._live.stop()
            self._live = None
        self._buffer = ""
        self._full_buffer = ""

    def render(self) -> RenderableType:
        """
        Render component (wrapper for ComponentBase compatibility).

        Returns current streaming state if active, or final content if finished.
        For streaming operations, use start(), append(), and finish() methods.
        """
        if self._is_streaming:
            return self._render_current()
        return self._render_final()

    def _render_current(self) -> RenderableType:
        """Render current streaming state with cursor."""
        theme = get_theme_manager()

        self._update_cursor_blink()

        result = Text()

        if self.config.render_markdown and self._looks_like_markdown():
            result.append(self._buffer, style=theme.get_style("body"))
        else:
            result.append(self._buffer, style=theme.get_style("body"))

        if self._is_streaming and self._cursor_visible:
            result.append(
                self.config.cursor_char, style=f"bold {theme.get_color('accent')}"
            )

        return result

    def _render_final(self) -> RenderableType:
        """Render final content (no cursor)."""
        if self.config.render_markdown and self._looks_like_markdown():
            md_renderer = AuraMarkdownDisplay()
            return md_renderer.render(self._buffer)

        theme = get_theme_manager()
        return Text(self._buffer, style=theme.get_style("body"))

    def _update_cursor_blink(self) -> None:
        """Update cursor blink state."""
        if not self.config.cursor_blink:
            self._cursor_visible = True
            return

        now = time.time()
        if now - self._last_cursor_toggle > 0.5:
            self._cursor_visible = not self._cursor_visible
            self._last_cursor_toggle = now

    def _looks_like_markdown(self) -> bool:
        """Check if content appears to be markdown."""
        indicators = ["```", "**", "##", "- ", "* ", "> ", "[", "|"]
        return any(ind in self._buffer for ind in indicators)

    def stream_text(
        self,
        text: str,
        char_delay: Optional[float] = None,
    ) -> None:
        """
        Stream text character by character (for typing effect).

        Args:
            text: Text to stream
            char_delay: Delay between characters (uses config default if None)
        """
        delay = char_delay or self.config.chunk_delay
        self.start()

        for char in text:
            self.append(char)
            time.sleep(delay)

        self.finish()

    def stream_chunks(
        self,
        chunks: Generator[str, None, None],
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Stream chunks from a generator.

        Args:
            chunks: Generator yielding text chunks
            on_chunk: Optional callback for each chunk

        Returns:
            Complete streamed text
        """
        self.start()

        for chunk in chunks:
            self.append(chunk)
            if on_chunk:
                on_chunk(chunk)
            time.sleep(self.config.chunk_delay)

        return self.finish()


class TypingIndicator:
    """
    Typing indicator animation.

    Shows animated dots or custom pattern while waiting for response.
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize the instance."""
        self.console = console or Console()
        self._live: Optional[Live] = None
        self._frame = 0
        self._is_active = False

    def start(self, message: str = "Aura is thinking") -> None:
        """Start typing indicator."""
        self._is_active = True
        self._frame = 0
        self._message = message

        self._live = Live(
            self._render_frame(),
            console=self.console,
            refresh_per_second=4,
            transient=True,
        )
        self._live.start()

        thread_manager = get_thread_manager()
        thread_name = f"streaming_renderer_{id(self)}"
        self._update_thread = thread_manager.register_thread(
            name=thread_name,
            target=self._animation_loop,
            daemon=True,
            shutdown_timeout=1.0,
        )

    def stop(self) -> None:
        """Stop typing indicator."""
        self._is_active = False
        live, self._live = self._live, None
        if live:
            live.stop()

    def _animation_loop(self) -> None:
        """Animation update loop."""
        while self._is_active:
            self._frame = (self._frame + 1) % 4
            live = self._live  # local copy — avoids TOCTOU with stop()
            if live is not None:
                with contextlib.suppress(Exception):
                    live.update(self._render_frame())
            time.sleep(0.25)

    def _render_frame(self) -> Text:
        """Render current animation frame."""
        theme = get_theme_manager()
        dots = "." * (self._frame + 1)

        result = Text()
        result.append("✦ ", style=f"bold {theme.get_color('accent')}")
        result.append(f"{self._message}", style="italic")
        result.append(dots.ljust(4), style=f"bold {theme.get_color('accent')}")

        return result


def create_streaming_renderer(
    console: Optional[Console] = None,
    render_markdown: bool = True,
) -> StreamingTextRenderer:
    """Create a configured streaming renderer."""
    config = StreamingConfig(render_markdown=render_markdown)
    return StreamingTextRenderer(console, config)
