"""
Base Dialog for Aura TUI.

Provides the foundation for all modal dialogs with:
- Consistent styling
- Focus management
- Keyboard navigation
- Animation support
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
import logging
from typing import TYPE_CHECKING, Any, Callable, ClassVar, List, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Static

from aura_cli.tui.core.event_bus import TUIEvents

if TYPE_CHECKING:
    from textual.app import App
    from textual.widget import Widget

logger = logging.getLogger(__name__)


@dataclass
class DialogResult:
    """Result from a dialog interaction."""

    confirmed: bool
    value: Any = None
    action: str = ""


class BaseDialog(Static):
    """Base class for all TUI dialog widgets.

    Provides modal overlay, title bar, content area, action buttons and
    focus trap. Subclasses override get_content(), get_actions() and
    on_action() to customise each dialog.
    """

    BINDINGS: ClassVar[list] = [
        Binding("escape", "close_dialog", "Fechar", show=False),
        Binding("enter", "confirm", "Confirm", show=False),
    ]

    title = reactive("Dialog")

    class Closed(Message):
        """Emitted when dialog is closed."""

        def __init__(self, result: DialogResult):
            """Initialize the Closed message with the dialog result."""
            super().__init__()
            self.result = result

    def __init__(
        self,
        title: str = "Dialog",
        on_close: Optional[Callable[[DialogResult], None]] = None,
        **kwargs,
    ):
        """
        Initialize the dialog.

        Args:
            title: Dialog title
            on_close: Callback when dialog closes
        """
        super().__init__(**kwargs)
        self.title = title
        self._on_close = on_close
        self._result: Optional[DialogResult] = None

    def compose(self) -> ComposeResult:
        """Compose the dialog structure."""
        # Title bar
        with Horizontal(classes="dialog-title-bar"):
            yield Static(self.title, classes="dialog-title")

        # Content area
        with Vertical(classes="dialog-content"):
            yield from self.get_content()

        # Actions bar
        with Horizontal(classes="dialog-actions"):
            for label, action_id, variant in self.get_actions():
                yield Button(label, id=f"dialog_action_{action_id}", variant=variant)

    def get_content(self) -> List[Widget]:
        """
        Get content widgets for the dialog.

        Override in subclasses to provide dialog content.

        Returns:
            List of widgets to display in content area
        """
        return []

    def get_actions(self) -> List[tuple]:
        """
        Get action buttons for the dialog.

        Override in subclasses to customize buttons.

        Returns:
            List of (label, action_id, variant) tuples
        """
        return [
            ("Fechar", "close", "default"),
        ]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle action button presses."""
        button_id = event.button.id or ""
        if button_id.startswith("dialog_action_"):
            action = button_id.replace("dialog_action_", "")
            self.on_action(action)

    def on_action(self, action: str) -> None:
        """
        Handle an action button click.

        Override in subclasses to handle specific actions.

        Args:
            action: Action identifier from get_actions()
        """
        if action == "close":
            self.close(DialogResult(False))

    def action_close_dialog(self) -> None:
        """Handle escape key."""
        self.close(DialogResult(False))

    def action_confirm(self) -> None:
        """Handle enter key - confirm primary action."""
        # Default to first action
        actions = self.get_actions()
        if actions:
            self.on_action(actions[0][1])

    def close(self, result: Optional[DialogResult] = None) -> None:
        """
        Close the dialog with a result.

        Args:
            result: Dialog result (defaults to cancelled)
        """
        self._result = result or DialogResult(False)

        # Call callback
        if self._on_close:
            try:
                self._on_close(self._result)
            except Exception as e:
                logger.error(f"Dialog close callback error: {e}")

        # Emit message
        self.post_message(self.Closed(self._result))

        # Emit event
        TUIEvents.bus.publish(
            "tui.dialog.close",
            {
                "dialog_id": self.id,
                "result": {
                    "confirmed": self._result.confirmed,
                    "value": self._result.value,
                    "action": self._result.action,
                },
            },
        )

        # Remove from DOM
        self.remove()

    @property
    def result(self) -> Optional[DialogResult]:
        """Get the dialog result."""
        return self._result


class DialogProvider:
    """
    Provider for managing dialog lifecycle.

    Handles:
    - Dialog stack management
    - Focus handling
    - Modal behavior

    Example:
        ```python
        provider = DialogProvider(app)

        # Show dialog
        result = await provider.show(ConfirmDialog("Delete file?"))
        if result.confirmed:
            delete_file()
        ```
    """

    def __init__(self, app: App):
        """
        Initialize the provider.

        Args:
            app: Textual App instance
        """
        self.app = app
        self._stack: List[BaseDialog] = []
        self._previous_focus: Optional[Widget] = None

    def show(self, dialog: BaseDialog) -> None:
        """
        Show a dialog.

        Args:
            dialog: Dialog to show
        """
        # Store current focus
        if not self._stack:
            self._previous_focus = self.app.focused

        # Add to stack
        self._stack.append(dialog)

        # Mount dialog
        self.app.mount(dialog)

        # Focus first interactive element
        try:
            buttons = dialog.query("Button")
            if buttons:
                buttons.first().focus()
        except Exception as error:
            self.app.log.debug("Dialog has no focusable button yet: %s", error)

        # Emit event
        TUIEvents.bus.publish(
            "tui.dialog.show",
            {"dialog_type": type(dialog).__name__, "title": dialog.title, "data": {}},
        )

    def close(self, dialog: Optional[BaseDialog] = None) -> None:
        """
        Close a dialog.

        Args:
            dialog: Specific dialog to close (top if None)
        """
        if not self._stack:
            return

        target = dialog or self._stack[-1]

        if target in self._stack:
            self._stack.remove(target)
            target.close()

        # Restore focus if stack empty
        if not self._stack and self._previous_focus:
            with contextlib.suppress(Exception):
                self._previous_focus.focus()
            self._previous_focus = None

    def close_all(self) -> None:
        """Close all dialogs."""
        while self._stack:
            self.close()

    @property
    def has_dialog(self) -> bool:
        """Check if any dialog is open."""
        return len(self._stack) > 0

    @property
    def current(self) -> Optional[BaseDialog]:
        """Get the current (top) dialog."""
        return self._stack[-1] if self._stack else None
