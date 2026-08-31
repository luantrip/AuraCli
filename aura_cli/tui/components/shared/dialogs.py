"""
Shared Dialog Components.

Provides consistent dialog widgets across all Aura CLI tools.
"""

from __future__ import annotations

from typing import Any, Callable, ClassVar, List, Optional, Tuple

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Input, ProgressBar, Select, Static


class BaseDialog(ModalScreen):
    """
    Base class for modal dialogs.

    Provides consistent styling and behavior for all dialogs.
    """

    BINDINGS: ClassVar[list] = [
        Binding("escape", "cancel", "Cancel"),
    ]

    class Closed(Message):
        """Message sent when dialog is closed."""

        def __init__(self, result: Any = None, cancelled: bool = False) -> None:
            """Initialize the widget."""
            super().__init__()
            self.result = result
            self.cancelled = cancelled

    def __init__(self, title: str = "Dialog", **kwargs):
        """Initialize the widget."""
        super().__init__(**kwargs)
        self.title = title

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Container():
            yield Static(self.title, classes="dialog-title")  # type: ignore[arg-type]
            yield from self.compose_content()
            with Horizontal(classes="dialog-buttons"):
                yield from self.compose_buttons()

    def compose_content(self) -> ComposeResult:
        """Override to add dialog content."""
        yield Static("Dialog content", classes="dialog-content")

    def compose_buttons(self) -> ComposeResult:
        """Override to customize buttons."""
        yield Button("OK", variant="primary", id="ok")
        yield Button("Cancel", variant="default", id="cancel")

    def action_cancel(self) -> None:
        """Cancel the dialog."""
        self.dismiss(None)
        self.post_message(self.Closed(result=None, cancelled=True))

    @on(Button.Pressed, "#cancel")
    def on_cancel_pressed(self) -> None:
        """Handle cancel button press."""
        self.action_cancel()


class ConfirmDialog(BaseDialog):
    """
    Confirmation dialog with Yes/No buttons.

    Example:
        ```python
        result = await self.app.push_screen(
            ConfirmDialog("Delete file?", "This action cannot be undone."),
            wait_for_dismiss=True
        )
        if result:
            # User confirmed
        ```
    """

    def __init__(
        self,
        title: str = "Confirm",
        message: str = "Are you sure?",
        confirm_label: str = "Yes",
        cancel_label: str = "No",
        dangerous: bool = False,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(title=title, **kwargs)
        self.message = message
        self.confirm_label = confirm_label
        self.cancel_label = cancel_label
        self.dangerous = dangerous

    def compose_content(self) -> ComposeResult:
        """Compose the dialog content area."""
        yield Static(self.message, classes="dialog-content")

    def compose_buttons(self) -> ComposeResult:
        """Compose the dialog action buttons."""
        variant = "error" if self.dangerous else "primary"
        yield Button(self.confirm_label, variant=variant, id="confirm")  # type: ignore[arg-type]
        yield Button(self.cancel_label, variant="default", id="cancel")

    @on(Button.Pressed, "#confirm")
    def on_confirm_pressed(self) -> None:
        """Handle confirm button press."""
        self.dismiss(True)
        self.post_message(self.Closed(result=True, cancelled=False))


class InputDialog(BaseDialog):
    """
    Dialog with text input.

    Example:
        ```python
        result = await self.app.push_screen(
            InputDialog("Enter name:", placeholder="filename"),
            wait_for_dismiss=True
        )
        if result:
            print(f"User entered: {result}")
        ```
    """

    def __init__(
        self,
        title: str = "Input",
        message: str = "",
        placeholder: str = "",
        default: str = "",
        password: bool = False,
        validator: Optional[Callable[[str], bool]] = None,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(title=title, **kwargs)
        self.message = message
        self.placeholder = placeholder
        self.default = default
        self.password = password
        self.validator = validator

    def compose_content(self) -> ComposeResult:
        """Compose the dialog content area."""
        if self.message:
            yield Static(self.message, classes="dialog-content")
        yield Input(
            value=self.default,
            placeholder=self.placeholder,
            password=self.password,
            id="input",
        )

    def compose_buttons(self) -> ComposeResult:
        """Compose the dialog action buttons."""
        yield Button("OK", variant="primary", id="ok")
        yield Button("Cancel", variant="default", id="cancel")

    @on(Button.Pressed, "#ok")
    def on_ok_pressed(self) -> None:
        """Handle OK button press."""
        self._submit()

    @on(Input.Submitted)
    def on_input_submitted(self) -> None:
        """Handle input submission."""
        self._submit()

    def _submit(self) -> None:
        """Submit the dialog result."""
        input_widget = self.query_one("#input", Input)
        value = input_widget.value

        if self.validator and not self.validator(value):
            self.notify("Invalid input", severity="error")
            return

        self.dismiss(value)
        self.post_message(self.Closed(result=value, cancelled=False))


class SelectDialog(BaseDialog):
    """
    Dialog with selection from options.

    Example:
        ```python
        result = await self.app.push_screen(
            SelectDialog(
                "Choose option:",
                options=[("opt1", "Option 1"), ("opt2", "Option 2")]
            ),
            wait_for_dismiss=True
        )
        ```
    """

    def __init__(
        self,
        title: str = "Select",
        message: str = "",
        options: List[Tuple[str, str]] | None = None,
        default: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(title=title, **kwargs)
        self.message = message
        self.options = options or []
        self.default = default

    def compose_content(self) -> ComposeResult:
        """Compose the dialog content area."""
        if self.message:
            yield Static(self.message, classes="dialog-content")
        yield Select(
            [(label, value) for value, label in self.options],
            value=self.default,
            id="select",
        )

    @on(Button.Pressed, "#ok")
    def on_ok_pressed(self) -> None:
        """Handle OK button press."""
        select = self.query_one("#select", Select)
        value = select.value
        self.dismiss(value)
        self.post_message(self.Closed(result=value, cancelled=False))


class ProgressDialog(BaseDialog):
    """
    Dialog with progress indicator.

    Example:
        ```python
        dialog = ProgressDialog("Processing...", total=100)
        self.app.push_screen(dialog)

        for i in range(100):
            dialog.update_progress(i + 1)
            await asyncio.sleep(0.1)

        dialog.dismiss()
        ```
    """

    BINDINGS: ClassVar[list] = []  # No escape to cancel

    progress: reactive[float] = reactive(0.0)
    status: reactive[str] = reactive("")

    def __init__(
        self,
        title: str = "Progress",
        message: str = "",
        total: float = 100.0,
        cancellable: bool = False,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(title=title, **kwargs)
        self.message = message
        self.total = total
        self.cancellable = cancellable

    def compose_content(self) -> ComposeResult:
        """Compose the dialog content area."""
        if self.message:
            yield Static(self.message, classes="dialog-content")
        yield ProgressBar(total=self.total, id="progress")
        yield Static("", classes="progress-label", id="status")

    def compose_buttons(self) -> ComposeResult:
        """Compose the dialog action buttons."""
        if self.cancellable:
            yield Button("Cancel", variant="default", id="cancel")

    def update_progress(self, value: float, status: str = "") -> None:
        """Update progress value and status."""
        self.progress = value
        if status:
            self.status = status

    def watch_progress(self, value: float) -> None:
        """React to progress changes."""
        try:
            progress_bar = self.query_one("#progress", ProgressBar)
            progress_bar.update(progress=value)
        except Exception as error:
            self.log.debug("Dialog progress is not mounted yet: %s", error)

    def watch_status(self, value: str) -> None:
        """React to status message changes."""
        try:
            status_label = self.query_one("#status", Static)
            status_label.update(value)
        except Exception as error:
            self.log.debug("Dialog status is not mounted yet: %s", error)
