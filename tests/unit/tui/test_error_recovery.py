"""Recoverable TUI error-reset contracts."""

from types import SimpleNamespace
from unittest.mock import Mock

from aura_cli.application.presentation.tui_runtime_state import RuntimeAction
from aura_cli.tui.core.error_handler import TUIErrorHandler


def test_reset_app_returns_runtime_to_ready_and_restores_focus() -> None:
    app = SimpleNamespace(
        _transition_runtime=Mock(),
        _action_cancel=Mock(),
        _restore_composer_focus=Mock(),
        notify=Mock(),
    )
    handler = TUIErrorHandler(app)
    handler._error_history.append(Mock())

    handler._reset_app()

    assert handler.get_error_history() == []
    app._transition_runtime.assert_called_once_with(RuntimeAction.READY)
    app._action_cancel.assert_called_once_with()
    app._restore_composer_focus.assert_called_once_with()
    app.notify.assert_called_once_with(
        "Aplicação reiniciada. Parte do estado pode ter sido perdida.",
        title="Reinicialização concluída",
        severity="warning",
    )
