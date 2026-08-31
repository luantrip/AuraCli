"""Tests for tangent helpers in checkpoint_tools."""

from aura_cli.core.tangent.manager import TangentManager
from aura_cli.core.tools.checkpoint_tools import (
    enter_tangent_mode,
    exit_tangent_mode,
    forget_messages,
    set_tangent_manager,
)


def setup_function() -> None:
    """Reset tangent manager before each test."""
    set_tangent_manager(None)


def test_exit_tangent_mode_restores_checkpoint_messages() -> None:
    """exit_tangent_mode should use the real TangentManager contract."""
    manager = TangentManager()
    set_tangent_manager(manager)

    checkpoint_messages = [{"role": "user", "content": "base"}]
    tangent_messages = [
        *checkpoint_messages,
        {"role": "user", "content": "explore"},
        {"role": "assistant", "content": "reply"},
    ]

    enter_tangent_mode(checkpoint_messages)
    result = exit_tangent_mode(conversation_history=tangent_messages)

    assert result["success"] is True
    assert result["restored_conversation"] == checkpoint_messages
    assert result["in_tangent"] is False
    assert "restored" in result["message"].lower()


def test_exit_tangent_mode_with_tail_preserves_last_exchange() -> None:
    """Tail restore should preserve the last tangent exchange."""
    manager = TangentManager()
    set_tangent_manager(manager)

    checkpoint_messages = [{"role": "user", "content": "base"}]
    tangent_messages = [
        *checkpoint_messages,
        {"role": "user", "content": "explore"},
        {"role": "assistant", "content": "reply"},
    ]

    enter_tangent_mode(checkpoint_messages)
    result = exit_tangent_mode(keep_tail=True, conversation_history=tangent_messages)

    assert result["success"] is True
    assert result["restored_conversation"] == tangent_messages
    assert result["kept_tail"] is True
    assert "preserved" in result["message"].lower()


def test_forget_messages_uses_real_signature_and_reports_counts() -> None:
    """forget_messages should pass messages first and count via keyword."""
    manager = TangentManager()
    set_tangent_manager(manager)

    conversation = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply 1"},
        {"role": "user", "content": "second"},
        {"role": "assistant", "content": "reply 2"},
    ]

    result = forget_messages(1, conversation)

    assert result["success"] is True
    assert result["messages_removed"] == 1
    assert result["messages_trimmed"] == 2
    assert result["remaining_messages"] == 2
    assert result["new_history"] == conversation[:2]
    assert "forgot last 1" in result["message"].lower()
