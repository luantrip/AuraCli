"""Conversation state and rendering controller for the Textual host."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from aura_cli.application.presentation import filter_conversation_messages
from aura_cli.tui.widgets.chat import AuraChatLog
from aura_cli.tui.widgets.message_bubble import MessageType

if TYPE_CHECKING:
    from aura_cli.tui.app import AuraTUI


class ConversationController:
    """Own message history and translate it into chat widgets."""

    def __init__(self, host: AuraTUI) -> None:
        self.host = host
        self.messages: list[dict[str, Any]] = []

    @staticmethod
    def message_type(sender: str) -> MessageType:
        if sender == "User":
            return MessageType.USER
        if sender in ("Sistema", "System"):
            return MessageType.SYSTEM
        if sender in ("Tool", "Ferramenta"):
            return MessageType.TOOL
        if sender in ("Erro", "Error"):
            return MessageType.ERROR
        return MessageType.ASSISTANT

    def append(self, sender: str, content: str, task_id: str = "global_chat") -> Any:
        chat = self.host.query_one(AuraChatLog)
        bubble = chat.write_bubble(
            sender=sender,
            content=str(content),
            message_type=self.message_type(sender),
        )
        self.messages.append(
            {
                "sender": sender,
                "content": str(content),
                "task_id": task_id,
                "bubble": bubble,
            }
        )
        return bubble

    def render(self, task_id: str | None = None) -> None:
        chat = self.host.query_one(AuraChatLog)
        chat.clear_history()
        for message in filter_conversation_messages(self.messages, task_id):
            chat.write_bubble(
                sender=message.get("sender", "Sistema"),
                content=message.get("content", ""),
                message_type=self.message_type(message.get("sender", "Sistema")),
            )
        chat.scroll_end()

    def clear(self) -> None:
        self.messages.clear()


__all__ = ["ConversationController"]
