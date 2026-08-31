"""Instrumentation adapters for agent backends exposing send/receive methods."""

from __future__ import annotations

from typing import Any, Callable

MessageObserver = Callable[[Any, str, str, str], None]


def _name(value: Any, fallback: str) -> str:
    return str(getattr(value, "name", fallback))


def instrument_agent_conversation(
    *,
    user_proxy: Any,
    assistant: Any,
    observer: MessageObserver,
) -> None:
    """Observe backend messages while preserving original call order and results."""
    if hasattr(user_proxy, "send"):
        original_send = user_proxy.send

        def send_with_observer(
            message: Any,
            recipient: Any,
            request_reply: Any = None,
            silent: bool = False,
        ) -> Any:
            observer(
                message,
                _name(user_proxy, "user"),
                _name(recipient, "unknown"),
                "send",
            )
            return original_send(message, recipient, request_reply, silent)

        user_proxy.send = send_with_observer

    if hasattr(assistant, "receive"):
        original_receive = assistant.receive

        def receive_with_observer(
            message: Any,
            sender: Any,
            request_reply: Any = None,
            silent: bool = False,
        ) -> Any:
            observer(
                message,
                _name(sender, "unknown"),
                _name(assistant, "assistant"),
                "receive",
            )
            return original_receive(message, sender, request_reply, silent)

        assistant.receive = receive_with_observer


__all__ = ["MessageObserver", "instrument_agent_conversation"]
