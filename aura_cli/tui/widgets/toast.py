"""Toast Notification Widget for Aura TUI.

Toast notifications with fade animations and severity levels.
"""

from typing import ClassVar

from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Label, Static

from aura_cli.tui.constants import INFO, TOAST_SEVERITY_ICONS, TOAST_SEVERITY_TITLES


class AuraToast(Container):
    """Toast notification widget with severity levels.

    Features:
    - Multiple severity levels (success, error, warning, info)
    - Auto-dismiss with configurable timeout
    - Fade in/out animations
    - Icon and color per severity
    - CSS-based styling
    """

    message: reactive[str] = reactive("")
    severity: reactive[str] = reactive("info")
    title: reactive[str] = reactive("")

    # Imported from tui/constants.py — single source of truth for icons
    SEVERITY_ICONS: ClassVar[dict] = TOAST_SEVERITY_ICONS
    SEVERITY_TITLES: ClassVar[dict] = TOAST_SEVERITY_TITLES

    def __init__(
        self,
        message: str = "",
        severity: str = "info",
        title: str | None = None,
        timeout: float = 5.0,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.message = message
        self.severity = severity
        self.title = title or ""
        self._timeout = timeout

    def compose(self):
        """Compose toast structure."""
        with Vertical():
            if self.title or self.SEVERITY_TITLES.get(self.severity):
                display_title = self.title or self.SEVERITY_TITLES.get(
                    self.severity, "Info"
                )
                yield Label(display_title, classes="toast-title")

            with Horizontal():
                icon = self.SEVERITY_ICONS.get(self.severity, INFO)
                yield Label(icon, classes="toast-icon")
                yield Label(self.message, classes="toast-message")

    def on_mount(self) -> None:
        """Set up auto-dismiss timer and severity class."""
        self.add_class(f"toast-{self.severity}")
        if self._timeout > 0:
            self.set_timer(self._timeout, self._auto_dismiss)

    def watch_severity(self, severity: str) -> None:
        """Update severity class when severity changes."""
        self.remove_class("toast-success", "toast-error", "toast-warning", "toast-info")
        self.add_class(f"toast-{severity}")

    def watch_message(self, message: str) -> None:
        """Update message when it changes."""
        msg_label = self.query_one(".toast-message", Label)
        if msg_label:
            msg_label.update(message)

    def watch_title(self, title: str) -> None:
        """Update title when it changes."""
        try:
            title_label = self.query_one(".toast-title", Label)
            title_label.update(title or self.SEVERITY_TITLES.get(self.severity, "Info"))
        except Exception as error:
            self.log.debug("Toast title is not mounted yet: %s", error)

    def _auto_dismiss(self) -> None:
        """Auto-dismiss the toast."""
        self.remove()


class AuraToastContainer(Static):
    """Container for multiple stacked toasts.

    Manages the notification queue and animations.
    """

    def __init__(self, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self._max_visible = 3

    def show_toast(
        self,
        message: str,
        severity: str = "info",
        title: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        """Show a new toast notification.

        Args:
            message: The message to display
            severity: One of 'success', 'error', 'warning', 'info'
            title: Optional custom title
            timeout: Auto-dismiss time in seconds (0 for persistent)
        """
        toast = AuraToast(
            message=message, severity=severity, title=title, timeout=timeout
        )

        self.mount(toast)

        while len(self.children) > self._max_visible:
            oldest = self.children[0]
            oldest.remove()
