"""Portuguese copy contracts for fatal TUI errors."""

from aura_cli.tui.widgets.dialogs.error_dialog import FatalErrorDialog


def test_fatal_error_dialog_uses_portuguese_copy() -> None:
    dialog = FatalErrorDialog(
        {"error_type": "RuntimeError", "message": "Falhou"},
        on_reset=lambda: None,
        on_report=lambda: None,
    )

    rendered = [widget.render().plain for widget in dialog.get_content()]
    labels = [label for label, _action, _variant in dialog.get_actions()]

    assert any("Ocorreu um erro inesperado" in line for line in rendered)
    assert "Tipo: RuntimeError" in rendered
    assert "Mensagem: Falhou" in rendered
    assert "You can try resetting the application, reporting this bug or quitting." in rendered
    assert labels == ["Reset application", "Report bug", "Exit"]


def test_fatal_error_dialog_uses_portuguese_fallbacks() -> None:
    dialog = FatalErrorDialog({})

    rendered = [widget.render().plain for widget in dialog.get_content()]

    assert "Tipo: Erro" in rendered
    assert "Mensagem: Erro desconhecido" in rendered
    assert dialog.get_actions() == [("Exit", "exit", "error")]
