"""
Confirm Dialog for Aura TUI.

A simple Yes/No confirmation dialog.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from textual.widgets import Static

from aura_cli.tui.widgets.dialogs.base_dialog import BaseDialog, DialogResult


class ConfirmDialog(BaseDialog):
    """
    Confirmation dialog with Yes/No buttons.

    Example:
        ```python
        dialog = ConfirmDialog(
            message="Delete this file?",
            title="Confirm Delete",
            on_confirm=lambda: delete_file(),
        )
        app.mount(dialog)
        ```
    """

    def __init__(
        self,
        message: str,
        title: str = "Confirmar",
        on_confirm: Optional[Callable[[], None]] = None,
        on_cancel: Optional[Callable[[], None]] = None,
        confirm_label: str = "Sim",
        cancel_label: str = "Não",
        **kwargs,
    ):
        """
        Initialize the confirmation dialog.

        Args:
            message: Confirmation message
            title: Dialog title
            on_confirm: Callback when confirmed
            on_cancel: Callback when cancelled
            confirm_label: Label for confirm button
            cancel_label: Label for cancel button
        """
        super().__init__(title=title, **kwargs)
        self.message = message
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label

    def get_content(self) -> List:
        """Return the dialog content widget."""
        return [
            Static(self.message, classes="confirm-message"),
        ]

    def get_actions(self) -> List[tuple]:
        """Return the list of dialog action buttons."""
        return [
            (self._confirm_label, "confirm", "primary"),
            (self._cancel_label, "cancel", "default"),
        ]

    def on_action(self, action: str) -> None:
        """Handle a dialog action button press."""
        if action == "confirm":
            if self._on_confirm:
                self._on_confirm()
            self.close(DialogResult(True, action="confirm"))
        else:
            if self._on_cancel:
                self._on_cancel()
            self.close(DialogResult(False, action="cancel"))
