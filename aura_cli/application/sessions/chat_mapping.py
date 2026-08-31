"""Presentation-neutral mapping between chat messages and session history."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable

DEFAULT_SENDER_ROLES = {
    "User": "user",
    "Aura": "assistant",
    "Sistema": "system",
    "Tool": "tool",
}
DEFAULT_ROLE_SENDERS = {role: sender for sender, role in DEFAULT_SENDER_ROLES.items()}


def chat_messages_to_history(
    messages: Iterable[dict[str, Any]],
    *,
    clock: Callable[[], datetime] = datetime.now,
    sender_roles: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Normalize visual chat messages into provider-compatible session entries."""
    mapping = sender_roles or DEFAULT_SENDER_ROLES
    history: list[dict[str, Any]] = []
    for message in messages:
        sender = str(message.get("sender", "Sistema"))
        content = message.get("content", "")
        if not content:
            continue
        history.append(
            {
                "role": mapping.get(sender, "assistant"),
                "content": content,
                "timestamp": clock().isoformat(),
                "metadata": {
                    "sender": sender,
                    "task_id": message.get("task_id"),
                },
            }
        )
    return history


def role_to_sender(
    role: str,
    *,
    role_senders: dict[str, str] | None = None,
) -> str:
    """Map a canonical conversation role to a visual sender label."""
    return (role_senders or DEFAULT_ROLE_SENDERS).get(role, "Aura")
