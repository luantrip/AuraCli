"""Unified chat rendering system for Aura CLI.

ChatRenderer composes MessageBubble, StreamingTextRenderer, TypingIndicator,
code-block syntax highlighting, reactions and threading into a single API.
ChatMessage is the data contract; render_history() / stream_response() are
the primary entry points.
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
import re
from typing import Any, Dict, Generator, List, Optional

from rich.console import Console, RenderableType

from aura_cli.cli.ui.chat import (
    CodeBlockEnhanced,
    MessageBubble,
    MessageMetadata,
    MessageType,
    Reaction,
    StreamingTextRenderer,
    TypingIndicator,
    create_streaming_renderer,
    get_avatar_system,
    get_icon_set,
    get_styled_text_engine,
)
from aura_cli.cli.ui.theme_manager import get_theme_manager


@dataclass
class ChatMessage:
    """
    Represents a complete chat message.

    Attributes:
        id: Unique message identifier
        sender: Sender name
        content: Message content
        message_type: Message type (MessageType enum)
        timestamp: Creation timestamp (default: now)
        metadata: Additional metadata (MessageMetadata)
        reactions: List of reactions (emojis)
        parent_id: Parent message ID (for threading)
    """

    id: str
    sender: str
    content: str
    message_type: MessageType
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
    reactions: List[Reaction] = field(default_factory=list)
    parent_id: Optional[str] = None


class ChatRenderer:
    """
    High-level chat rendering system.

    Provides unified interface for rendering complete conversations
    with support for streaming, typing indicators, code blocks, reactions
    and threading. Integrates avatar system, styled text engine and theme manager.

    Attributes:
        console: Rich Console for output
        theme: ThemeManager for colors and styles
        avatars: AvatarSystem for visual avatars
        styled: StyledTextEngine for styled text
        icons: IconSet for icons

    Example:
        >>> renderer = ChatRenderer()
        >>> message = ChatMessage(id="1", sender="Aura", content="Hello!", message_type=MessageType.ASSISTANT)
        >>> renderer.add_message(message)
        >>> renderer.render_history()
    """

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize ChatRenderer with console and integrated systems.

        Args:
            console: Custom Rich Console (creates new if None)
        """
        self.console = console or Console()
        self.theme = get_theme_manager()
        self.avatars = get_avatar_system()
        self.styled = get_styled_text_engine()
        self.icons = get_icon_set()
        self._messages: List[ChatMessage] = []
        self._streaming_renderer: Optional[StreamingTextRenderer] = None
        self._typing_indicator: Optional[TypingIndicator] = None
        self._current_streaming_id: Optional[str] = None

    def add_message(self, message: ChatMessage) -> None:
        """
        Add message to history.

        Args:
            message: ChatMessage to add
        """
        self._messages.append(message)

    def render_message(
        self, message: ChatMessage, width: Optional[int] = None
    ) -> RenderableType:
        """
        Render single message with bubble and avatar.

        Args:
            message: ChatMessage to render
            width: Optional width for bubble

        Returns:
            RenderableType for display with Rich

        Example:
            >>> rendered = renderer.render_message(message, width=80)
            >>> console.print(rendered)
        """
        bubble = MessageBubble(
            sender=message.sender,
            content=message.content,
            message_type=message.message_type,
            timestamp=message.timestamp,
            metadata=message.metadata,
            reactions=message.reactions,
            message_id=message.id,
        )
        return bubble.render(width or self.console.width)

    def render_user_message(
        self,
        content: str,
        message_id: Optional[str] = None,
    ) -> RenderableType:
        """Render a user message."""
        msg = ChatMessage(
            id=message_id or f"user_{datetime.now().timestamp()}",
            sender="You",
            content=content,
            message_type=MessageType.USER,
        )
        self.add_message(msg)
        return self.render_message(msg)

    def render_assistant_message(
        self,
        content: str,
        message_id: Optional[str] = None,
        tokens: Optional[int] = None,
        duration: Optional[float] = None,
        model: Optional[str] = None,
    ) -> RenderableType:
        """Render an assistant message."""
        msg = ChatMessage(
            id=message_id or f"assistant_{datetime.now().timestamp()}",
            sender="Aura",
            content=content,
            message_type=MessageType.ASSISTANT,
            metadata=MessageMetadata(
                tokens=tokens,
                duration=duration,
                model=model,
            ),
        )
        self.add_message(msg)
        return self.render_message(msg)

    def render_system_message(self, content: str) -> RenderableType:
        """Render a system message."""
        msg = ChatMessage(
            id=f"system_{datetime.now().timestamp()}",
            sender="System",
            content=content,
            message_type=MessageType.SYSTEM,
        )
        return self.render_message(msg)

    def render_error(self, content: str) -> RenderableType:
        """Render an error message."""
        msg = ChatMessage(
            id=f"error_{datetime.now().timestamp()}",
            sender="Erro",
            content=content,
            message_type=MessageType.ERROR,
        )
        return self.render_message(msg)

    def render_tool_message(
        self,
        tool_name: str,
        content: str,
    ) -> RenderableType:
        """Render a tool execution message."""
        msg = ChatMessage(
            id=f"tool_{datetime.now().timestamp()}",
            sender="Ferramenta",
            content=content,
            message_type=MessageType.TOOL,
            metadata=MessageMetadata(tool_name=tool_name),
        )
        return self.render_message(msg)

    def start_streaming(self, message_id: Optional[str] = None) -> None:
        """Start streaming response display."""
        self._current_streaming_id = (
            message_id or f"stream_{datetime.now().timestamp()}"
        )
        self._streaming_renderer = create_streaming_renderer(
            self.console,
            render_markdown=True,
        )
        self._streaming_renderer.start()

    def append_streaming(self, chunk: str) -> None:
        """Append chunk to streaming response."""
        if self._streaming_renderer:
            self._streaming_renderer.append(chunk)

    def finish_streaming(
        self,
        tokens: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> str:
        """
        Finish streaming and return final content.

        Args:
            tokens: Token count
            duration: Response duration

        Returns:
            Complete response text
        """
        content = ""
        if self._streaming_renderer:
            content = self._streaming_renderer.finish()
            msg = ChatMessage(
                id=self._current_streaming_id
                or f"assistant_{datetime.now().timestamp()}",
                sender="Aura",
                content=content,
                message_type=MessageType.ASSISTANT,
                metadata=MessageMetadata(
                    tokens=tokens,
                    duration=duration,
                ),
            )
            self.add_message(msg)
            self.console.print(self.render_message(msg))
        self._streaming_renderer = None
        self._current_streaming_id = None
        return content

    def cancel_streaming(self) -> None:
        """Cancel active streaming."""
        if self._streaming_renderer:
            self._streaming_renderer.cancel()
            self._streaming_renderer = None
            self._current_streaming_id = None

    def show_thinking(self, sender: str = "Aura") -> None:
        """Show thinking indicator."""
        self._typing_indicator = TypingIndicator(self.console)
        self._typing_indicator.start(f"{sender} is thinking")

    def hide_thinking(self) -> None:
        """Hide thinking indicator."""
        if self._typing_indicator:
            self._typing_indicator.stop()
            self._typing_indicator = None

    def render_code(
        self,
        code: str,
        language: str = "text",
        title: Optional[str] = None,
    ) -> RenderableType:
        """Render a code block."""
        block = CodeBlockEnhanced(code, language, title)
        return block.render(self.console.width)

    def render_history(
        self, limit: Optional[int] = None
    ) -> Generator[RenderableType, None, None]:
        """
        Render message history.

        Args:
            limit: Maximum messages to render
        Yields:
            Rendered messages
        """
        messages = self._messages
        if limit:
            messages = messages[-limit:]
        for msg in messages:
            yield self.render_message(msg)

    def clear_history(self) -> None:
        """Clear message history."""
        self._messages.clear()

    def search_messages(self, query: str, mode: str = "contains") -> List[ChatMessage]:
        """Search messages in history."""
        query_lower = query.lower()

        if mode == "regex":
            try:
                pattern = re.compile(query_lower, re.IGNORECASE)
                return [msg for msg in self._messages if pattern.search(msg.content)]
            except re.error:
                # Fallback para contains
                return [
                    msg for msg in self._messages if query_lower in msg.content.lower()
                ]
        elif mode == "fuzzy":
            # Fuzzy matching simples
            query_chars = set(query_lower)
            return [
                msg
                for msg in self._messages
                if len(query_chars.intersection(set(msg.content.lower())))
                >= len(query_chars) * 0.6
            ]
        else:  # contains
            return [msg for msg in self._messages if query_lower in msg.content.lower()]

    def filter_messages(
        self,
        sender: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[ChatMessage]:
        """Filter messages by criteria."""
        filtered = self._messages.copy()

        if sender:
            filtered = [msg for msg in filtered if msg.sender.lower() == sender.lower()]

        if message_type:
            filtered = [msg for msg in filtered if msg.message_type == message_type]

        if date_from:
            filtered = [msg for msg in filtered if msg.timestamp >= date_from]

        if date_to:
            filtered = [msg for msg in filtered if msg.timestamp <= date_to]

        return filtered

    def get_statistics(self) -> Dict[str, Any]:
        """Return chat history statistics as a dict."""
        from collections import Counter

        if not self._messages:
            return {
                "total_messages": 0,
                "by_sender": {},
                "by_type": {},
                "total_tokens": 0,
                "avg_duration": 0.0,
            }

        by_sender = Counter(msg.sender for msg in self._messages)
        by_type = Counter(msg.message_type.value for msg in self._messages)

        total_tokens = sum((msg.metadata.tokens or 0) for msg in self._messages)
        durations = [
            msg.metadata.duration for msg in self._messages if msg.metadata.duration
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        return {
            "total_messages": len(self._messages),
            "by_sender": dict(by_sender),
            "by_type": dict(by_type),
            "total_tokens": total_tokens,
            "avg_duration": avg_duration,
        }

    def export_conversation(self, fmt: str = "json") -> str:
        """Export the conversation in the specified format."""
        if fmt == "json":
            data = [
                {
                    "id": msg.id,
                    "sender": msg.sender,
                    "content": msg.content,
                    "message_type": msg.message_type.value,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": {
                        "tokens": msg.metadata.tokens,
                        "duration": msg.metadata.duration,
                        "model": msg.metadata.model,
                    },
                }
                for msg in self._messages
            ]
            return json.dumps(data, indent=2, default=str)

        elif fmt == "txt":
            lines = []
            for msg in self._messages:
                timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                lines.append(f"[{timestamp}] {msg.sender}:")
                lines.append(msg.content)
                lines.append("")
            return "\n".join(lines)

        return ""

    def print_message(self, message: ChatMessage) -> None:
        """Print a message to console."""
        self.console.print(self.render_message(message))

    def print_user(self, content: str) -> None:
        """Print user message."""
        self.console.print(self.render_user_message(content))

    def print_assistant(
        self,
        content: str,
        tokens: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> None:
        """Print assistant message."""
        self.console.print(
            self.render_assistant_message(content, tokens=tokens, duration=duration)
        )

    def print_error(self, content: str) -> None:
        """Print error message."""
        self.console.print(self.render_error(content))

    def print_divider(self, label: str = "") -> None:
        """Print visual divider."""
        from rich.text import Text

        text = Text()
        muted = self.theme.get_color("muted")
        if label:
            text.append("─" * 10, style=muted)
            text.append(f" {label} ", style=f"dim {muted}")
            text.append("─" * 10, style=muted)
        else:
            text.append("─" * 30, style=muted)
        self.console.print(text)


def get_chat_renderer(console: Optional[Console] = None) -> ChatRenderer:
    """Get a configured ChatRenderer instance."""
    return ChatRenderer(console)
