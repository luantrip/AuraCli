"""Chat Window - Aura CLI Paint Tool.

Window widget for chat interaction with AI agent, supporting
message history and real-time conversation.

Features:
    - Scrollable message history
    - User input field
    - Message type styling (user/agent/system)
    - Auto-scroll to latest message
    - Message submission handling
"""

from typing import Any, Callable

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, Static

from aura_cli.application.paint.localization.i18n import get as _

from .windows import Window


class ChatWindow(Window):
    """Chat window for AI agent interaction.

    Provides a conversation interface with message history
    and input field for user messages.
    """

    class MessageSent(Message):
        """Message posted when user sends chat message.

        Attributes:
            message_text: Content of sent message
        """

        def __init__(self, message_text: str) -> None:
            super().__init__()
            self.message_text = message_text

    def __init__(
        self,
        title: str = _("Chat with Agent"),
        handle_button: Callable[[Button], None] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize chat window.

        Args:
            title: Window title
            handle_button: Button handler callback
            **kwargs: Additional window arguments
        """
        super().__init__(title=title, handle_button=handle_button, **kwargs)
        self.message_history = VerticalScroll(id="message_history")

    def compose(self) -> ComposeResult:
        """Compose chat window components."""
        with Container(id="chat_content"):
            yield self.message_history
            yield Input(placeholder=_("Type your message here..."), id="chat_input")
        yield from super().compose()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle message submission.

        Args:
            event: Input submission event
        """
        if event.input.id == "chat_input" and event.value.strip():
            self.post_message(self.MessageSent(event.value))
            self.add_message("You", event.value, "user")
            event.input.value = ""

    def add_message(self, sender: str, text: str, message_type: str = "agent") -> None:
        """Add message to chat history.

        Args:
            sender: Message sender name
            text: Message content
            message_type: Type of message (user/agent/system)
        """
        message_widget = Static(
            f"[bold {message_type}]{sender}:[/] {text}",
            classes=f"chat_message {message_type}_message",
        )
        self.message_history.mount(message_widget)
        self.message_history.scroll_end(animate=False)
