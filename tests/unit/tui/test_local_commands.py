"""Behavioral tests for slash commands owned by the Textual adapter."""

from unittest.mock import Mock

from aura_cli.application.presentation.command_routing import PresentationCommandRouter
from aura_cli.tui.commands.local_commands import handle_local_command


def host() -> Mock:
    value = Mock()
    value.controller = PresentationCommandRouter()
    value.all_chat_messages = [{"content": "old"}]
    return value


def test_unhandled_and_model_commands_continue_to_app_loop() -> None:
    value = host()

    assert handle_local_command(value, "/unknown") is False
    assert handle_local_command(value, "/model list") is False
    value.post_message_to_chat.assert_called_once_with(
        "Sistema", "⟳ Processando comando de modelo..."
    )


def test_clear_owns_visual_and_in_memory_history() -> None:
    value = host()

    assert handle_local_command(value, "/clear") is True
    assert value.all_chat_messages == []
    value.post_message.assert_called_once()
    value.post_message_to_chat.assert_called_once_with("Sistema", "Chat limpo.")


def test_navigation_and_exit_delegate_to_host_actions() -> None:
    value = host()

    assert handle_local_command(value, "/settings") is True
    value._open_settings_screen.assert_called_once_with()

    assert handle_local_command(value, "/exit") is True
    value.set_timer.assert_called_once_with(0.5, value.exit)


def test_workspace_and_external_files_have_distinct_actions() -> None:
    value = host()

    assert handle_local_command(value, "/context") is True
    value.action_toggle_workspace_panel.assert_called_once_with()

    assert handle_local_command(value, "/files") is True
    value.action_push_file_manager_screen.assert_called_once_with()
