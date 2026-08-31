from __future__ import annotations

from unittest.mock import MagicMock, patch

from aura_cli.tui.app import AuraTUI
from aura_cli.tui.core.error_handler import get_error_handler, set_error_handler


def test_aura_tui_command_errors_use_tui_error_handler() -> None:
    previous = get_error_handler()
    handler = MagicMock()
    app = object.__new__(AuraTUI)
    app.notify = MagicMock()

    def failing_action() -> None:
        raise ValueError("synthetic TUI failure")

    set_error_handler(handler)
    try:
        with patch(
            "aura_cli.tui.app.resolve_command_action", return_value=failing_action
        ):
            app._execute_command("broken")
    finally:
        set_error_handler(previous)

    handler.handle_error.assert_called_once()
    assert handler.handle_error.call_args.args[0].args == ("synthetic TUI failure",)
    assert handler.handle_error.call_args.kwargs["context"] == "command:broken"
    assert handler.handle_error.call_args.kwargs["notify"] is True
