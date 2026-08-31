"""
Input Dialog for Aura TUI.

A dialog for text input with validation.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from textual.widgets import Input, Static

from aura_cli.tui.widgets.dialogs.base_dialog import BaseDialog, DialogResult


class InputDialog(BaseDialog):
    """
    Input dialog for text entry.

    Example:
        ```python
        dialog = InputDialog(
            prompt="Enter file name:",
            title="New File",
            placeholder="filename.py",
            validator=lambda x: len(x) > 0,
        )
        app.mount(dialog)
        ```
    """

    def __init__(
        self,
        prompt: str,
        title: str = "Input",
        default_value: str = "",
        placeholder: str = "",
        validator: Optional[Callable[[str], bool]] = None,
        error_message: str = "Invalid input",
        **kwargs,
    ):
        """
        Initialize the input dialog.

        Args:
            prompt: Prompt text
            title: Dialog title
            default_value: Initial value
            placeholder: Input placeholder
            validator: Validation function
            error_message: Message on validation failure
        """
        super().__init__(title=title, **kwargs)
        self.prompt = prompt
        self.default_value = default_value
        self.placeholder = placeholder
        self.validator = validator
        self.error_message = error_message
        self._error_visible = False

    def get_content(self) -> List:
        """Return the dialog content widget."""
        return [
            Static(self.prompt, classes="input-prompt"),
            Input(
                value=self.default_value,
                placeholder=self.placeholder,
                id="dialog_input",
            ),
            Static("", id="input_error", classes="input-error"),
        ]

    def get_actions(self) -> List[tuple]:
        """Return the list of dialog action buttons."""
        return [
            ("OK", "ok", "primary"),
            ("Cancelar", "cancel", "default"),
        ]

    def on_mount(self) -> None:
        """Focus input on mount."""
        self.query_one("#dialog_input", Input).focus()

    def on_action(self, action: str) -> None:
        """Handle a dialog action button press."""
        if action == "ok":
            input_widget = self.query_one("#dialog_input", Input)
            value = input_widget.value

            # Validate
            if self.validator and not self.validator(value):
                error_widget = self.query_one("#input_error", Static)
                error_widget.update(self.error_message)
                return

            self.close(DialogResult(True, value=value, action="ok"))
        else:
            self.close(DialogResult(False, action="cancel"))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter key in input."""
        if event.input.id == "dialog_input":
            self.on_action("ok")
