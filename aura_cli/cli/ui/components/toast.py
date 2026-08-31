"""Toast notification system — temporary, non-intrusive UI feedback.

Supports types INFO/SUCCESS/WARNING/ERROR/LOADING, configurable duration,
6 positions, optional action callbacks, progress bar for loading toasts,
and a queue for concurrent toasts. Singleton via get_toast_manager().
"""

from dataclasses import dataclass, field
from enum import Enum
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.utils.thread_manager import get_thread_manager
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class ToastType(Enum):
    """Toast notification type enum."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    LOADING = "loading"


class ToastPosition(Enum):
    """Toast display position enum."""

    TOP = "top"
    TOP_RIGHT = "top_right"
    TOP_LEFT = "top_left"
    BOTTOM = "bottom"
    BOTTOM_RIGHT = "bottom_right"
    BOTTOM_LEFT = "bottom_left"


@dataclass
class Toast:
    """Individual toast notification.

    Attributes:
        id: Unique toast identifier.
        message: Message to display.
        type: Toast type (INFO, SUCCESS, etc.).
        duration: Display duration in seconds (default 3.0).
        position: Screen position (default BOTTOM_RIGHT).
        created_at: Creation timestamp.
        dismissible: Whether the user can close it manually.
        icon: Custom icon; uses type default if None.
        action: Optional callback for an action button.
        action_label: Label for the action button.
        progress: Progress value 0.0–1.0 for LOADING type.
    """

    id: str
    message: str
    type: ToastType = ToastType.INFO
    duration: float = 3.0
    position: ToastPosition = ToastPosition.BOTTOM_RIGHT
    created_at: float = field(default_factory=time.time)
    dismissible: bool = True
    icon: Optional[str] = None
    action: Optional[Callable] = None
    action_label: Optional[str] = None
    progress: Optional[float] = None  # 0.0 a 1.0 para loading

    @property
    def expires_at(self) -> float:
        """Return the toast expiry Unix timestamp."""
        return self.created_at + self.duration

    @property
    def is_expired(self) -> bool:
        """Return True if this toast has expired."""
        if self.type == ToastType.LOADING and self.progress is not None:
            return self.progress >= 1.0
        return time.time() > self.expires_at

    @property
    def remaining_time(self) -> float:
        """Return remaining display time in seconds."""
        return max(0, self.expires_at - time.time())

    def get_style(self) -> str:
        """Return the Rich style string for this toast type."""
        styles = {
            ToastType.INFO: UIStyles.safe_style("INFO", "blue"),
            ToastType.SUCCESS: UIStyles.safe_style("SUCCESS", "green"),
            ToastType.WARNING: UIStyles.safe_style("WARNING", "yellow"),
            ToastType.ERROR: UIStyles.safe_style("ERROR", "red"),
            ToastType.LOADING: UIStyles.safe_style("PRIMARY", "cyan"),
        }
        return styles.get(self.type, UIStyles.safe_style("INFO", "blue"))

    def get_icon(self) -> str:
        """Return the icon for this toast type."""
        if self.icon:
            return self.icon

        icons = {
            ToastType.INFO: UIIcons.INFO,
            ToastType.SUCCESS: UIIcons.SUCCESS,
            ToastType.WARNING: UIIcons.WARNING,
            ToastType.ERROR: UIIcons.ERROR,
            ToastType.LOADING: UIIcons.WORKING,
        }
        return icons.get(self.type, UIIcons.INFO)

    def get_border_style(self) -> str:
        """Return the Rich border style for this toast type."""
        styles = {
            ToastType.INFO: UIStyles.safe_style("BORDER_PRIMARY", "cyan"),
            ToastType.SUCCESS: UIStyles.safe_style("BORDER_SUCCESS", "green"),
            ToastType.WARNING: UIStyles.safe_style("BORDER_WARNING", "yellow"),
            ToastType.ERROR: UIStyles.safe_style("BORDER_ERROR", "red"),
            ToastType.LOADING: UIStyles.safe_style("BORDER_PRIMARY", "cyan"),
        }
        return styles.get(self.type, UIStyles.safe_style("BORDER_PRIMARY", "cyan"))


class ToastManager:
    """Toast notification manager with automatic expiry cleanup."""

    def __init__(self, console: Optional[Console] = None, max_visible: int = 3):
        """Initialise the toast manager."""
        self.console = console or Console()
        self.max_visible = max_visible

        self.queue: List[Toast] = []
        self.visible: List[Toast] = []
        self.lock = threading.RLock()

        self._counter = 0
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False

        self.on_toast_shown: Optional[Callable[[Toast], None]] = None
        self.on_toast_hidden: Optional[Callable[[Toast], None]] = None

    def _generate_id(self) -> str:
        """Generate a unique toast ID."""
        self._counter += 1
        return f"toast_{self._counter}_{int(time.time() * 1000)}"

    def show(
        self,
        message: str,
        toast_type: str = "info",
        duration: float = 3.0,
        position: str = "bottom_right",
        dismissible: bool = True,
        icon: Optional[str] = None,
        action: Optional[Callable] = None,
        action_label: Optional[str] = None,
    ) -> str:
        """Display a toast notification."""
        toast_type_enum = (
            ToastType(toast_type) if isinstance(toast_type, str) else toast_type
        )
        toast_position = (
            ToastPosition(position) if isinstance(position, str) else position
        )

        toast = Toast(
            id=self._generate_id(),
            message=message,
            type=toast_type_enum,
            duration=duration,
            position=toast_position,
            dismissible=dismissible,
            icon=icon,
            action=action,
            action_label=action_label,
        )

        with self.lock:
            if len(self.visible) < self.max_visible:
                self.visible.append(toast)
                self._render_toast(toast)

                if self.on_toast_shown:
                    self.on_toast_shown(toast)
            else:
                self.queue.append(toast)

        logger.debug(f"Toast created: {toast.id} - {message[:30]}...")
        return toast.id

    def info(self, message: str, **kwargs) -> str:
        """Shortcut — show an INFO toast."""
        return self.show(message, toast_type="info", **kwargs)

    def success(self, message: str, **kwargs) -> str:
        """Shortcut — show a SUCCESS toast."""
        return self.show(message, toast_type="success", **kwargs)

    def warning(self, message: str, **kwargs) -> str:
        """Shortcut — show a WARNING toast."""
        return self.show(message, toast_type="warning", **kwargs)

    def error(self, message: str, **kwargs) -> str:
        """Shortcut — show an ERROR toast."""
        kwargs.setdefault("duration", 5.0)  # Errors stay longer
        return self.show(message, toast_type="error", **kwargs)

    def loading(self, message: str, **kwargs) -> str:
        """Shortcut — show a LOADING toast."""
        kwargs.setdefault("duration", 30.0)  # Loading stays longer
        kwargs.setdefault("dismissible", False)
        return self.show(message, toast_type="loading", **kwargs)

    def update(self, toast_id: str, **kwargs) -> bool:
        """Update an existing toast."""
        with self.lock:
            for toast in self.visible + self.queue:
                if toast.id == toast_id:
                    for key, value in kwargs.items():
                        if hasattr(toast, key):
                            setattr(toast, key, value)
                    return True
        return False

    def dismiss(self, toast_id: str) -> bool:
        """Remove a toast notification."""
        with self.lock:
            for toast in self.visible[:]:
                if toast.id == toast_id:
                    self.visible.remove(toast)

                    if self.on_toast_hidden:
                        self.on_toast_hidden(toast)

                    # Promover da fila
                    if self.queue:
                        next_toast = self.queue.pop(0)
                        self.visible.append(next_toast)
                        self._render_toast(next_toast)

                    return True

            for toast in self.queue[:]:
                if toast.id == toast_id:
                    self.queue.remove(toast)
                    return True

        return False

    def clear_all(self):
        """Dismiss all active toasts."""
        with self.lock:
            self.visible.clear()
            self.queue.clear()

    def _render_toast(self, toast: Toast):
        """Renderiza um toast no console."""
        icon = toast.get_icon()
        style = toast.get_style()
        border_style = toast.get_border_style()

        content = Text()
        content.append(f"{icon} ", style=style)
        content.append(toast.message)

        # Add action button if exists
        if toast.action_label:
            content.append(f" [{toast.action_label}]", style=f"{style} underline")

        # Adicionar indicador de progresso para loading
        if toast.type == ToastType.LOADING and toast.progress is not None:
            progress_bar = self._create_progress_bar(toast.progress)
            content.append(f"\n{progress_bar}")

        panel = Panel(
            content,
            border_style=border_style,
            padding=(0, 1),
            width=min(50, self.console.width - 4),
        )

        self.console.print(panel)
        self.console.print()

    def _create_progress_bar(self, progress: float, width: int = 20) -> str:
        """Create a text progress bar string."""
        filled = int(progress * width)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}] {int(progress * 100)}%"

    def render(self, console: Optional[Console] = None) -> List[Panel]:
        """
        Render all toasts (wrapper for ComponentBase compatibility).

        Note: ToastManager is a manager pattern, not a visual component.
        This method provides optional ComponentBase compatibility.

        Args:
            console: Optional console (uses instance console if None)

        Returns:
            List of rendered toast panels
        """
        return self.render_all(console or self.console)

    def render_all(self, console: Optional[Console] = None) -> List[Panel]:
        """Render all visible toasts."""
        panels = []

        with self.lock:
            expired = [t for t in self.visible if t.is_expired]
            for toast in expired:
                self.visible.remove(toast)
                if self.on_toast_hidden:
                    self.on_toast_hidden(toast)

            # Promover da fila
            while self.queue and len(self.visible) < self.max_visible:
                toast = self.queue.pop(0)
                self.visible.append(toast)
                if self.on_toast_shown:
                    self.on_toast_shown(toast)

            for toast in self.visible:
                icon = toast.get_icon()
                style = toast.get_style()
                border_style = toast.get_border_style()

                content = Text()
                content.append(f"{icon} ", style=style)
                content.append(toast.message)

                if toast.type == ToastType.LOADING and toast.progress is not None:
                    content.append(f"\n{self._create_progress_bar(toast.progress)}")

                panel = Panel(
                    content,
                    border_style=border_style,
                    padding=(0, 1),
                    width=min(50, self.console.width - 4),
                )
                panels.append(panel)

        return panels

    def start_auto_cleanup(self, interval: float = 0.5):
        """Start the auto-cleanup background thread."""
        if self._running:
            return

        self._running = True

        def cleanup_loop():
            """Background loop to cleanup expired toasts."""
            while self._running:
                self.render_all()  # This also clears expired
                time.sleep(interval)

        thread_manager = get_thread_manager()
        thread_name = f"toast_cleanup_{id(self)}"
        self._cleanup_thread = thread_manager.register_thread(
            name=thread_name,
            target=cleanup_loop,
            daemon=True,
            shutdown_timeout=2.0,
        )

    def stop_auto_cleanup(self):
        """Stop the auto-cleanup background thread."""
        self._running = False
        if self._cleanup_thread:
            thread_manager = get_thread_manager()
            thread_name = (
                self._cleanup_thread.name
                if hasattr(self._cleanup_thread, "name")
                else None
            )
            if thread_name:
                thread_manager.stop_thread(thread_name, timeout=1.0)
            elif hasattr(self._cleanup_thread, "join"):
                self._cleanup_thread.join(timeout=1.0)

    def get_stats(self) -> Dict[str, Any]:
        """Return manager statistics as a dict."""
        with self.lock:
            return {
                "visible_count": len(self.visible),
                "queued_count": len(self.queue),
                "total_created": self._counter,
                "max_visible": self.max_visible,
            }


_toast_manager: Optional[ToastManager] = None


def get_toast_manager() -> ToastManager:
    """Return the global ToastManager singleton."""
    global _toast_manager
    if _toast_manager is None:
        _toast_manager = ToastManager()
    return _toast_manager
