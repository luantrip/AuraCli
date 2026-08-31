"""
Shared Notification Components.

Provides toast notifications and notification center.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Callable, ClassVar, List, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Static


class ToastType(Enum):
    """Toast notification types."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ToastData:
    """Data for a toast notification."""

    message: str
    toast_type: ToastType = ToastType.INFO
    title: Optional[str] = None
    duration: float = 5.0
    dismissable: bool = True
    action: Optional[Callable] = None
    action_label: str = ""
    id: str = field(default_factory=lambda: str(time.time()))


class Toast(Widget):
    """
    Single toast notification widget.

    Example:
        ```python
        toast = Toast(
            message="File saved successfully!",
            toast_type=ToastType.SUCCESS,
            duration=3.0
        )
        ```
    """

    ICONS: ClassVar[dict] = {
        ToastType.INFO: "ℹ️",
        ToastType.SUCCESS: "✔",
        ToastType.WARNING: "⚠️",
        ToastType.ERROR: "✖",
    }

    class Dismissed(Message):
        """Message when toast is dismissed."""

        def __init__(self, toast_id: str) -> None:
            """Initialize the widget."""
            super().__init__()
            self.toast_id = toast_id

    def __init__(
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        title: Optional[str] = None,
        duration: float = 5.0,
        dismissable: bool = True,
        action: Optional[Callable] = None,
        action_label: str = "",
        toast_id: Optional[str] = None,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.message = message
        self.toast_type = toast_type
        self.title = title or toast_type.value.title()
        self.duration = duration
        self.dismissable = dismissable
        self.action = action
        self.action_label = action_label
        self.toast_id = toast_id or str(time.time())

        self.add_class(f"toast-{toast_type.value}")

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        from textual.containers import Horizontal

        with Horizontal(classes="toast-header"):
            yield Static(self.ICONS[self.toast_type], classes="toast-icon")
            yield Static(self.title, classes="toast-title")
            if self.dismissable:
                yield Button("×", classes="toast-close", id="close")

        yield Static(self.message, classes="toast-message")

        if self.action and self.action_label:
            yield Button(self.action_label, classes="toast-action", id="action")

    def on_mount(self) -> None:
        """Start auto-dismiss timer if duration > 0."""
        if self.duration > 0:
            self.set_timer(self.duration, self._auto_dismiss)

    def _auto_dismiss(self) -> None:
        """Auto-dismiss the toast."""
        self.dismiss()

    def dismiss(self) -> None:
        """Dismiss the toast."""
        self.post_message(self.Dismissed(self.toast_id))
        self.remove()

    @on(Button.Pressed, "#close")
    def on_close_pressed(self) -> None:
        """Handle close button press."""
        self.dismiss()

    @on(Button.Pressed, "#action")
    def on_action_pressed(self) -> None:
        """Handle action button press."""
        if self.action:
            self.action()
        self.dismiss()


class NotificationCenter(Widget):
    """
    Container for managing multiple toast notifications.

    Example:
        ```python
        center = NotificationCenter()
        center.notify("Hello!", ToastType.INFO)
        center.notify("Success!", ToastType.SUCCESS)
        ```
    """

    MAX_VISIBLE = 5

    def __init__(self, **kwargs):
        """Initialize the widget."""
        super().__init__(**kwargs)
        self._queue: List[ToastData] = []
        self._visible: List[str] = []

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Vertical(id="toast-container")

    def notify(  # type: ignore[override]
        self,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        title: Optional[str] = None,
        duration: float = 5.0,
        dismissable: bool = True,
        action: Optional[Callable] = None,
        action_label: str = "",
    ) -> str:
        """
        Show a notification.

        Returns:
            Toast ID
        """
        data = ToastData(
            message=message,
            toast_type=toast_type,
            title=title,
            duration=duration,
            dismissable=dismissable,
            action=action,
            action_label=action_label,
        )

        if len(self._visible) >= self.MAX_VISIBLE:
            self._queue.append(data)
        else:
            self._show_toast(data)

        return data.id

    def _show_toast(self, data: ToastData) -> None:
        """Show a toast notification."""
        toast = Toast(
            message=data.message,
            toast_type=data.toast_type,
            title=data.title,
            duration=data.duration,
            dismissable=data.dismissable,
            action=data.action,
            action_label=data.action_label,
            toast_id=data.id,
        )

        if not self.is_mounted:
            return

        try:
            container = self.query_one("#toast-container", Vertical)
            container.mount(toast)
            self._visible.append(data.id)
        except NoMatches:
            return

    @on(Toast.Dismissed)
    def on_toast_dismissed(self, event: Toast.Dismissed) -> None:
        """Handle toast dismissal."""
        if event.toast_id in self._visible:
            self._visible.remove(event.toast_id)

        # Show next queued toast
        if self._queue and len(self._visible) < self.MAX_VISIBLE:
            next_toast = self._queue.pop(0)
            self._show_toast(next_toast)

    def clear_all(self) -> None:
        """Clear all notifications."""
        self._queue.clear()
        if not self.is_mounted:
            return
        try:
            container = self.query_one("#toast-container", Vertical)
            for child in list(container.children):
                child.remove()
            self._visible.clear()
        except NoMatches:
            return

    def info(self, message: str, **kwargs) -> str:
        """Show info notification."""
        return self.notify(message, ToastType.INFO, **kwargs)

    def success(self, message: str, **kwargs) -> str:
        """Show success notification."""
        return self.notify(message, ToastType.SUCCESS, **kwargs)

    def warning(self, message: str, **kwargs) -> str:
        """Show warning notification."""
        return self.notify(message, ToastType.WARNING, **kwargs)

    def error(self, message: str, **kwargs) -> str:
        """Show error notification."""
        return self.notify(message, ToastType.ERROR, **kwargs)
