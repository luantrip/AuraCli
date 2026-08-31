"""
MessageBubble - Modern, minimal chat message component.

Provides a clean, elegant message display with:
- Minimal visual noise
- Clear sender identification
- Markdown rendering
- Subtle metadata display
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from rich.align import Align
from rich.console import Group, RenderableType
from rich.padding import Padding
from rich.text import Text

from aura_cli.application.messages import MessageMetadata, MessageType, Reaction
from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.components.markdown_display import AuraMarkdownDisplay
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.cli.ui.theme_manager import get_theme_manager


class MessageBubble(ComponentBase):
    """
    Modern, minimal message bubble.

    Features:
    - Clean, borderless design for user messages
    - Subtle styling for assistant messages
    - Avatar integration
    - Markdown rendering
    - Minimal metadata footer
    """

    def __init__(
        self,
        sender: str,
        content: str,
        message_type: MessageType = MessageType.ASSISTANT,
        timestamp: Optional[datetime] = None,
        metadata: Optional[MessageMetadata] = None,
        reactions: Optional[List[Reaction]] = None,
        message_id: Optional[str] = None,
    ):
        """Initialize the instance."""
        self.sender = sender
        self.content = content
        self.message_type = message_type
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or MessageMetadata()
        self.reactions = reactions or []
        self.message_id = message_id

    def render(self, console_width: int = 80) -> RenderableType:
        """Render the message bubble with minimal design."""
        theme = get_theme_manager()

        is_user = self.message_type == MessageType.USER
        chat_padding = theme.get_layout_property("chat_padding", (0, 2))
        chat_margin = theme.get_layout_property("chat_margin", (0, 0, 1, 0))
        metrics = layout_for_width(
            console_width,
            chat_width_ratio=theme.get_layout_property("chat_width_ratio", 0.85),
            chat_padding=tuple(chat_padding),
            chat_margin=tuple(chat_margin),
        )
        max_width = metrics.chat_width

        header = self._render_header(theme)
        body = self._render_body(theme)
        footer = self._render_footer(theme) if self._has_footer() else None
        reactions_row = self._render_reactions(theme) if self.reactions else None

        elements: list[Any] = [header]

        elements.append(Text())
        elements.append(body)

        if footer:
            elements.append(Text())
            elements.append(footer)

        if reactions_row:
            elements.append(Text())
            elements.append(reactions_row)

        inner_content = Group(*elements)

        styled_content = Padding(inner_content, metrics.chat_padding)

        align_func = Align.right if is_user else Align.left
        aligned = align_func(styled_content, width=max_width)
        return Padding(aligned, metrics.chat_margin)

    def _get_style_config(self, theme) -> Dict[str, Any]:
        """Get style configuration for message type."""
        configs = {
            MessageType.USER: {
                "border_color": theme.get_color("primary"),
                "text_color": theme.get_style("body"),
                "header_color": theme.get_color("primary"),
            },
            MessageType.ASSISTANT: {
                "border_color": theme.get_color("accent"),
                "text_color": theme.get_style("body"),
                "header_color": theme.get_color("accent"),
            },
            MessageType.SYSTEM: {
                "border_color": theme.get_color("muted"),
                "text_color": theme.get_color("muted"),
                "header_color": theme.get_color("muted"),
            },
            MessageType.ERROR: {
                "border_color": theme.get_color("error"),
                "text_color": theme.get_color("error"),
                "header_color": theme.get_color("error"),
            },
            MessageType.SUCCESS: {
                "border_color": theme.get_color("success"),
                "text_color": theme.get_color("success"),
                "header_color": theme.get_color("success"),
            },
            MessageType.TOOL: {
                "border_color": theme.get_color("warning"),
                "text_color": theme.get_color("warning"),
                "header_color": theme.get_color("warning"),
            },
            MessageType.THINKING: {
                "border_color": theme.get_color("muted"),
                "text_color": theme.get_color("muted"),
                "header_color": theme.get_color("muted"),
            },
        }
        return configs.get(self.message_type, configs[MessageType.ASSISTANT])

    def _render_header(self, theme) -> Text:
        """Render minimal message header — no avatar, just name + time."""
        is_user = self.message_type == MessageType.USER
        time_str = self.timestamp.strftime("%H:%M")
        config = self._get_style_config(theme)

        header = Text()

        if is_user:
            header.append("│ ", style=f"dim {config['border_color']}")
            header.append("➜ ", style=config["header_color"])
            header.append(self.sender, style=f"bold {config['header_color']}")
        else:
            header.append("➜ ", style=config["header_color"])
            header.append(self.sender, style=f"bold {config['header_color']}")

        header.append(f"  {time_str}", style=f"dim {theme.get_color('muted')}")

        if self.metadata.is_streaming:
            header.append("  ")
            header.append("●", style=f"blink {theme.get_color('warning')}")

        return header

    def _render_body(self, theme) -> RenderableType:
        """Render message body."""
        if self.message_type == MessageType.THINKING:
            return Text(self.content, style="dim italic")  # thinking style from theme

        if "```" in self.content or self.content.startswith("#"):
            md_renderer = AuraMarkdownDisplay()
            return md_renderer.render(self.content)

        return Text(self.content, style=theme.get_style("body"))

    def _render_body_text(self, theme) -> str:
        """Get body as plain text for line-by-line rendering."""
        return self.content

    def _render_footer(self, theme) -> Text:
        """Render minimal message footer with metadata."""
        footer = Text()
        parts: list[Any] = []

        if self.metadata.duration is not None:
            parts.append(f"{self.metadata.duration:.1f}s")

        if self.metadata.tokens is not None:
            parts.append(f"{self.metadata.tokens} tokens")

        if self.metadata.model:
            parts.append(self.metadata.model)

        if self.metadata.tool_name:
            parts.append(f"⚒ {self.metadata.tool_name}")

        if self.metadata.is_edited:
            parts.append("edited")

        if parts:
            footer.append(" · ".join(parts), style=f"dim {theme.get_color('muted')}")

        return footer

    def _render_reactions(self, theme) -> Text:
        """Render reactions row."""
        result = Text()
        for i, reaction in enumerate(self.reactions):
            if i > 0:
                result.append(" ")
            result.append(
                f"{reaction.emoji} {reaction.count}",
                style=f"dim {theme.get_color('muted')}",
            )
        return result

    def _has_footer(self) -> bool:
        """Check if footer should be rendered."""
        m = self.metadata
        return any(
            [
                m.duration is not None,
                m.tokens is not None,
                m.model,
                m.tool_name,
                m.is_edited,
            ]
        )


class ThinkingBubble(MessageBubble):
    """Specialized bubble for thinking/typing indicators."""

    def __init__(self, sender: str = "Aura"):
        """Initialize the instance."""
        super().__init__(
            sender=sender,
            content="thinking...",
            message_type=MessageType.THINKING,
        )
        self._frame = 0
        self._frames = ["thinking", "thinking.", "thinking..", "thinking..."]

    def update_animation(self) -> None:
        """Update animation frame."""
        self._frame = (self._frame + 1) % len(self._frames)
        self.content = self._frames[self._frame]


class StreamingBubble(MessageBubble):
    """Specialized bubble for streaming responses."""

    def __init__(self, sender: str = "Aura"):
        """Initialize the instance."""
        super().__init__(
            sender=sender,
            content="",
            message_type=MessageType.ASSISTANT,
            metadata=MessageMetadata(is_streaming=True),
        )
        self._buffer = ""

    def append(self, chunk: str) -> None:
        """Append chunk to streaming content."""
        self._buffer += chunk
        self.content = self._buffer

    def finalize(
        self, tokens: Optional[int] = None, duration: Optional[float] = None
    ) -> None:
        """Finalize streaming."""
        self.metadata.is_streaming = False
        self.metadata.tokens = tokens
        self.metadata.duration = duration
