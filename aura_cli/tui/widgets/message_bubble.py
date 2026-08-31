"""MessageBubble widget for Aura TUI — modern chat message component styled via CSS."""

import contextlib
from datetime import datetime
import logging
from typing import Any, List, Optional

from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Label, Markdown, Static

from aura_cli.application.messages import (
    MessageMetadata,
    MessageType,
    Reaction,
)

logger = logging.getLogger(__name__)


class MessageBubble(Container):
    """Message bubble with CSS-based type styling, markdown, metadata and reactions."""

    sender: reactive[str] = reactive("")
    content: reactive[str] = reactive("")
    message_type: reactive[MessageType] = reactive(MessageType.ASSISTANT)
    timestamp: reactive[Optional[datetime]] = reactive(None)
    metadata: reactive[Optional[MessageMetadata]] = reactive(None)
    reactions: reactive[List[Reaction]] = reactive([])

    def __init__(
        self,
        sender: str,
        content: str,
        message_type: MessageType = MessageType.ASSISTANT,
        timestamp: Optional[datetime] = None,
        metadata: Optional[MessageMetadata] = None,
        reactions: Optional[List[Reaction]] = None,
        message_id: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.sender = sender
        self.content = content
        self.message_type = message_type
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or MessageMetadata()
        self.reactions = reactions or []
        self.message_id = message_id

        # Apply initial class based on message type
        self.add_class(f"message-{message_type.value}")

    def compose(self):
        """Compose message bubble structure."""
        is_user = self.message_type == MessageType.USER
        time_str = self.timestamp.strftime("%I:%M %p").lstrip("0")

        with Vertical():
            with Horizontal(
                classes=f"message-header message-{self.message_type.value}"
            ):
                yield from self._compose_header(is_user, time_str)

            with Container(classes="message-body"):
                yield from self._compose_body(is_user)

            if self._has_footer() and self.metadata:
                with Horizontal(classes="message-footer"):
                    yield from self._compose_footer()

            if self.reactions:
                with Horizontal(classes="message-reactions"):
                    for reaction in self.reactions:
                        yield Label(
                            f"{reaction.emoji} {reaction.count}",
                            classes="message-reaction",
                        )

    def _compose_header(self, is_user: bool, time_str: str):
        """Yield header widgets based on message type."""
        if is_user:
            yield Label(f"> {self.content}", classes="message-user-title")
            yield Label(time_str, classes="message-timestamp")
        elif self.message_type == MessageType.THINKING:
            duration_str = (
                f" for {self.metadata.duration:.1f}s"
                if self.metadata and self.metadata.duration
                else ""
            )
            yield Label(f"◆ Thought{duration_str}", classes="message-thinking-title")
            yield Label(time_str, classes="message-timestamp")
        elif self.message_type == MessageType.TOOL:
            tool_label = (
                f"| ◆ {self.metadata.tool_name or 'Executed Tool'}"
                if self.metadata and self.metadata.tool_name
                else f"| ◆ {self.sender}"
            )
            yield Label(tool_label, classes="message-tool-title")
            yield Label(time_str, classes="message-timestamp")
        else:
            yield Label(self.sender.upper(), classes="message-sender")
            yield Label(time_str, classes="message-timestamp")

        if self.metadata and self.metadata.is_streaming:
            yield Label("TRANSMITINDO", classes="message-streaming-indicator")
        if self.metadata and self.metadata.reply_to:
            yield Label("↩ resposta", classes="message-reply-indicator")

    def _compose_body(self, is_user: bool):
        """Yield body widgets based on message type."""
        if is_user:
            return  # User content is already shown in the header title.
        elif self.message_type == MessageType.THINKING:
            yield Label(f"  {self.content}", classes="message-thinking-content")
        elif self._is_markdown():
            yield Markdown(self.content)
        else:
            yield Static(self.content)

    def _compose_footer(self):
        """Yield footer label from metadata fields."""
        m = self.metadata
        parts = []
        if m.duration is not None:
            parts.append(f"Worked for {m.duration:.1f}s")
        if m.tokens is not None:
            parts.append(f"{m.tokens} tokens")
        if m.model:
            parts.append(m.model)
        if parts:
            yield Label(" · ".join(parts))

    def _is_markdown(self) -> bool:
        """Check if content contains markdown."""
        return "```" in self.content or self.content.strip().startswith("#")

    def _has_footer(self) -> bool:
        """Check if footer should be rendered."""
        m = self.metadata
        if not m:
            return False
        return any(
            [
                m.duration is not None,
                m.tokens is not None,
                m.model,
                m.tool_name,
                m.is_edited,
            ]
        )

    def watch_message_type(self, message_type: MessageType) -> None:
        """Update classes when message type changes."""
        self.remove_class(
            "message-user",
            "message-assistant",
            "message-system",
            "message-error",
            "message-success",
            "message-tool",
            "message-thinking",
        )
        self.add_class(f"message-{message_type.value}")

    def watch_content(self, content: str) -> None:
        """Update content when it changes."""
        try:
            # Find the content widget (Markdown or Static)
            body = self.query_one(".message-body", Container)
            content_widget: Any = None

            # Try to find Markdown widget first
            with contextlib.suppress(Exception):
                content_widget = body.query_one(Markdown)

            # If not found, try Static
            if not content_widget:
                with contextlib.suppress(Exception):
                    content_widget = body.query_one(Static)

            # Update the widget if found
            if content_widget:
                if isinstance(content_widget, Markdown):
                    # Markdown widget - update by replacing it
                    body.remove_children()
                    body.mount(Markdown(content))
                elif isinstance(content_widget, Static):
                    # Static widget - update directly
                    content_widget.update(content)
        except Exception as error:
            logger.debug("Message body is not ready for streaming update: %s", error)

    def watch_metadata(self, metadata: Optional[MessageMetadata]) -> None:
        """Update streaming indicator when metadata changes."""
        if metadata and metadata.is_streaming:
            self.add_class("message-streaming")
        else:
            self.remove_class("message-streaming")

    def on_mount(self) -> None:
        """Initialize message bubble classes."""
        self.add_class(f"message-{self.message_type.value}")
        if self.metadata and self.metadata.is_streaming:
            self.add_class("message-streaming")


class ThinkingBubble(MessageBubble):
    """Specialized bubble for thinking/typing indicators."""

    def __init__(self, sender: str = "Aura"):
        """Initialize the instance."""
        self._frame = 0
        # Localised animation frames (PT-BR); MessageType.THINKING = "thinking" (canonical)
        self._frames = ["pensando", "pensando.", "pensando..", "pensando..."]
        super().__init__(
            sender=sender,
            content=self._frames[0],
            message_type=MessageType.THINKING,
        )

    def update_animation(self) -> None:
        """Update animation frame."""
        self._frame = (self._frame + 1) % len(self._frames)
        self.content = self._frames[self._frame]


class StreamingBubble(MessageBubble):
    """Specialized bubble for streaming responses."""

    def __init__(self, sender: str = "Aura"):
        """Initialize the instance."""
        self._buffer = ""
        super().__init__(
            sender=sender,
            content="",
            message_type=MessageType.ASSISTANT,
            metadata=MessageMetadata(is_streaming=True),
        )

    def append(self, chunk: str) -> None:
        """Append chunk to streaming content."""
        self._buffer += chunk
        self.content = self._buffer

    def finalize(
        self, tokens: Optional[int] = None, duration: Optional[float] = None
    ) -> None:
        """Finalize streaming."""
        self.metadata = MessageMetadata(
            tokens=tokens,
            duration=duration,
            is_streaming=False,
        )
