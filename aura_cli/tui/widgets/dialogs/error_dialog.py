"""
Error Dialog for Aura TUI.

A dialog for displaying fatal errors with recovery options.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from textual.containers import Vertical
from textual.widgets import Static

from aura_cli.tui.widgets.dialogs.base_dialog import BaseDialog, DialogResult


class FatalErrorDialog(BaseDialog):
    """Fatal error dialog with recovery options.

    Shows error type, message and traceback, plus Reset, Report bug
    (GitHub issue) and Exit action buttons.
    """

    def __init__(
        self,
        error_info: Dict[str, Any],
        on_reset: Optional[Callable[[], None]] = None,
        on_report: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        """
        Initialize the error dialog.

        Args:
            error_info: Dictionary with error details
            on_reset: Callback to reset application
            on_report: Callback to report bug
            on_exit: Callback to exit application
        """
        super().__init__(title="Erro fatal", **kwargs)
        self.error_info = error_info
        self._on_reset = on_reset
        self._on_report = on_report
        self._on_exit = on_exit

    def get_content(self) -> List:
        """Return the dialog content widget."""
        content = []

        # Error icon
        content.append(Static("⚠️ Ocorreu um erro inesperado", classes="error-icon"))

        # Error type
        error_type = self.error_info.get("error_type", "Erro")
        content.append(Static(f"Tipo: {error_type}", classes="error-type"))

        # Error message
        message = self.error_info.get("message", "Erro desconhecido")
        content.append(Static(f"Mensagem: {message}", classes="error-message"))

        # Traceback (if available)
        traceback = self.error_info.get("traceback", "")
        if traceback:
            with Vertical(classes="error-traceback"):
                # Truncate long tracebacks
                lines = traceback.split("\n")
                if len(lines) > 15:
                    display_tb = "\n".join([*lines[:5], "...", "", *lines[-8:]])
                else:
                    display_tb = traceback
                content.append(Static(display_tb))

        # Help text
        content.append(
            Static(
                "Você pode tentar resetar a aplicação, relatar este bug ou sair.",
                classes="error-help",
            )
        )

        return content

    def get_actions(self) -> List[tuple]:
        """Return the list of dialog action buttons."""
        actions = []

        if self._on_reset:
            actions.append(("Resetar aplicação", "reset", "warning"))

        if self._on_report:
            actions.append(("Relatar bug", "report", "primary"))

        actions.append(("Sair", "exit", "error"))

        return actions

    def on_action(self, action: str) -> None:
        """Handle a dialog action button press."""
        if action == "reset":
            if self._on_reset:
                self._on_reset()
            self.close(DialogResult(True, action="reset"))

        elif action == "report":
            if self._on_report:
                self._on_report()
            # Don't close - let user continue after reporting

        elif action == "exit":
            if self._on_exit:
                self._on_exit()
            self.close(DialogResult(False, action="exit"))


class ErrorNotification(Static):
    """
    Inline error notification for non-fatal errors.

    A less intrusive error display that appears at the top
    of a widget or screen.
    """

    def __init__(self, **kwargs):
        """Initialize the widget."""
        super().__init__(**kwargs)
        self._message = ""

    def show_error(self, message: str, dismissible: bool = True) -> None:
        """Show an error message."""
        self._message = message
        self.add_class("-visible")
        self.refresh()

    def hide_error(self) -> None:
        """Hide the error."""
        self.remove_class("-visible")

    def render(self) -> str:
        """Render the widget content."""
        return f"⚠️ {self._message}"
