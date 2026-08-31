"""Unified Chat Log Widget for Aura TUI.

Modern chat interface using native Textual widgets for consistent premium experience.

Features:
- MessageBubble integration for consistent styling
- Streaming message support with typing indicators
- Code block rendering with syntax highlighting
- Markdown rendering
- Message reactions and metadata
- Thinking bubbles for AI processing
"""

from datetime import datetime
from typing import List, Optional

from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

from aura_cli.tui.widgets.message_bubble import (
    MessageBubble,
    MessageMetadata,
    MessageType,
    Reaction,
    StreamingBubble,
    ThinkingBubble,
)


class AuraChatLog(VerticalScroll):
    """Unified chat log widget using native Textual MessageBubble widgets.

    Features:
    - Modern message bubbles styled via CSS
    - Streaming response support
    - Typing indicators
    - Reactions support
    - Code blocks with syntax highlighting
    - Message threading
    """

    MAX_HISTORY = 1000

    class ClearHistory(Message):
        """Posted to clear the chat history."""

    is_typing: reactive[bool] = reactive(False)
    typing_sender: reactive[str] = reactive("")

    def __init__(self, **kwargs):
        """Initialize the chat log with empty bubble tracking state."""
        super().__init__(**kwargs)
        self._streaming_bubble: Optional[StreamingBubble] = None
        self._thinking_bubble: Optional[ThinkingBubble] = None
        self._message_history: List[MessageBubble] = []
        self._animation_timer = None

    def on_mount(self) -> None:
        """Initialize animation timers."""
        self._animation_timer = self.set_interval(0.3, self._update_animations)

    def on_unmount(self) -> None:
        """Cancel animation timer to prevent callbacks on a removed widget."""
        if self._animation_timer is not None:
            self._animation_timer.stop()
            self._animation_timer = None

    def _update_animations(self) -> None:
        """Update typing/thinking animations."""
        if self.is_typing and self._thinking_bubble:
            self._thinking_bubble.update_animation()

    def on_clear_history(self, event: "AuraChatLog.ClearHistory") -> None:
        """Handle the ClearHistory message."""
        self.clear_history()

    def write_bubble(
        self,
        sender: str,
        content: str,
        message_type: MessageType = MessageType.ASSISTANT,
        timestamp: Optional[datetime] = None,
        metadata: Optional[MessageMetadata] = None,
        reactions: Optional[List[Reaction]] = None,
        message_id: Optional[str] = None,
    ) -> MessageBubble:
        """Write a modern message bubble to the log.

        Args:
            sender: Message sender name
            content: Message content (supports markdown)
            message_type: Type for styling (USER, ASSISTANT, SYSTEM, etc.)
            timestamp: Optional message timestamp
            metadata: Optional metadata (tokens, duration, model)
            reactions: Optional list of reactions
            message_id: Optional unique message ID

        Returns:
            The created MessageBubble instance
        """
        if not isinstance(content, str):
            try:
                content = str(content)
            except Exception:
                content = repr(content)

        bubble = MessageBubble(
            sender=sender,
            content=content,
            message_type=message_type,
            timestamp=timestamp or datetime.now(),
            metadata=metadata or MessageMetadata(),
            reactions=reactions or [],
            message_id=message_id,
        )

        self.mount(bubble)
        self.scroll_end()

        self._message_history.append(bubble)
        if len(self._message_history) > self.MAX_HISTORY:
            self._message_history = self._message_history[-self.MAX_HISTORY :]
        return bubble

    def write_user_message(self, content: str, sender: str = "Você") -> MessageBubble:
        """Write a user message."""
        return self.write_bubble(
            sender=sender,
            content=content,
            message_type=MessageType.USER,
        )

    def write_assistant_message(
        self,
        content: str,
        sender: str = "Aura",
        tokens: Optional[int] = None,
        duration: Optional[float] = None,
        model: Optional[str] = None,
    ) -> MessageBubble:
        """Write an assistant message with optional metadata."""
        return self.write_bubble(
            sender=sender,
            content=content,
            message_type=MessageType.ASSISTANT,
            metadata=MessageMetadata(
                tokens=tokens,
                duration=duration,
                model=model,
            ),
        )

    def write_system_message(self, content: str) -> MessageBubble:
        """Write a system message."""
        return self.write_bubble(
            sender="Sistema",
            content=content,
            message_type=MessageType.SYSTEM,
        )

    def write_error_message(self, content: str) -> MessageBubble:
        """Write an error message."""
        return self.write_bubble(
            sender="Erro",
            content=content,
            message_type=MessageType.ERROR,
        )

    def write_success_message(self, content: str) -> MessageBubble:
        """Write a success message."""
        return self.write_bubble(
            sender="Sucesso",
            content=content,
            message_type=MessageType.SUCCESS,
        )

    def write_tool_message(
        self,
        content: str,
        tool_name: str,
    ) -> MessageBubble:
        """Write a tool execution message."""
        return self.write_bubble(
            sender="Ferramenta",
            content=content,
            message_type=MessageType.TOOL,
            metadata=MessageMetadata(tool_name=tool_name),
        )

    def start_streaming(self, sender: str = "Aura") -> None:
        """Start a streaming response."""
        self._streaming_bubble = StreamingBubble(sender)
        self.mount(self._streaming_bubble)
        self.is_typing = True
        self.typing_sender = sender

    def append_streaming(self, chunk: str) -> None:
        """Append chunk to streaming response."""
        if self._streaming_bubble:
            self._streaming_bubble.append(chunk)
            if len(self._streaming_bubble.content) % 20 == 0:
                self.refresh()

    def end_streaming(
        self,
        tokens: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> Optional[str]:
        """End streaming and finalize message."""
        content = None
        if self._streaming_bubble:
            self._streaming_bubble.finalize(tokens, duration)
            content = self._streaming_bubble.content
            self._message_history.append(self._streaming_bubble)

        self._streaming_bubble = None
        self.is_typing = False
        self.typing_sender = ""
        return content

    def show_thinking(self, sender: str = "Aura") -> None:
        """Show one thinking indicator, replacing any previous one."""
        self.hide_thinking()
        self.is_typing = True
        self.typing_sender = sender
        self._thinking_bubble = ThinkingBubble(sender)
        self.mount(self._thinking_bubble)
        self.scroll_end()

    def hide_thinking(self) -> None:
        """Hide thinking indicator."""
        if self._thinking_bubble:
            self._thinking_bubble.remove()
        self.is_typing = False
        self.typing_sender = ""
        self._thinking_bubble = None

    def write_code(
        self,
        code: str,
        language: str = "text",
        title: Optional[str] = None,
    ) -> None:
        """Write a syntax-highlighted code block."""
        code_content = f"```{language}\n{code}\n```"
        if title:
            code_content = f"**{title}**\n\n{code_content}"
        self.write_bubble(
            sender="Código",
            content=code_content,
            message_type=MessageType.SYSTEM,
        )

    def write_divider(self, label: str = "") -> None:
        """Write a visual divider with optional label."""
        divider_text = f"─── {label} ───" if label else "─" * 30
        self.mount(Static(divider_text, classes="chat-divider"))
        self.scroll_end()

    def add_reaction(self, message_id: str, emoji: str, user: str = "Você"):
        """Add a reaction to a message."""
        for bubble in self._message_history:
            if bubble.message_id == message_id:
                existing = next((r for r in bubble.reactions if r.emoji == emoji), None)
                if existing:
                    existing.count += 1
                    if user not in existing.users:
                        existing.users.append(user)
                else:
                    bubble.reactions.append(
                        Reaction(emoji=emoji, count=1, users=[user])
                    )
                break

    def get_message(self, message_id: str) -> Optional[MessageBubble]:
        """Get a message by ID."""
        for bubble in self._message_history:
            if bubble.message_id == message_id:
                return bubble
        return None

    def clear_history(self) -> None:
        """Clear message history and transient streaming indicators."""
        self._message_history.clear()
        self._streaming_bubble = None
        self._thinking_bubble = None
        self.is_typing = False
        self.typing_sender = ""
        for child in list(self.children):
            child.remove()

    # === Internal helpers (kept for internal use only) ===

    def _write_message(self, message) -> None:
        """Internal helper: mount a MessageBubble or display a plain string."""
        if isinstance(message, MessageBubble):
            self.mount(message)
            self.scroll_end()
        elif isinstance(message, str):
            self.write_bubble(
                sender="Sistema",
                content=message,
                message_type=MessageType.SYSTEM,
            )

    def _write_styled_message(
        self,
        sender: str,
        content: str,
        message_type: str = "normal",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Internal helper: write a bubble with a string-based message type."""
        type_map = {
            "user": MessageType.USER,
            "agent": MessageType.ASSISTANT,
            "assistant": MessageType.ASSISTANT,
            "system": MessageType.SYSTEM,
            "error": MessageType.ERROR,
            "success": MessageType.SUCCESS,
            "normal": MessageType.ASSISTANT,
        }
        msg_type = type_map.get(message_type.lower(), MessageType.ASSISTANT)
        self.write_bubble(
            sender=sender,
            content=content,
            message_type=msg_type,
            timestamp=timestamp,
        )

    def write_styled_message(
        self,
        sender: str,
        content: str,
        message_type: str = "normal",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Write a styled message through the widget's public string-based API."""
        self._write_styled_message(sender, content, message_type, timestamp)

    def display_messages(self, messages: List) -> None:
        """Display a list of messages, replacing current history."""
        self.clear_history()
        for message in messages:
            self._write_message(message)
