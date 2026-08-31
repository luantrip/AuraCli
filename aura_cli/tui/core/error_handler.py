"""Error Handler for Aura TUI.

Global error handling with graceful recovery and bug reporting.

Features:
- Error boundaries for graceful recovery
- GitHub issue integration for bug reports
- Error logging and history tracking
- User-friendly error display
- Fatal vs recoverable error classification
- Error suppression support
- Context manager for error catching

Components:
- ErrorInfo: Detailed error information dataclass
- TUIErrorHandler: Main error handler
- ErrorCatcher: Context manager for error catching
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import logging
import os
import platform
import sys
import traceback
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
import urllib.parse
import webbrowser

from aura_cli.tui.core.event_bus import emit_error

if TYPE_CHECKING:
    from textual.app import App

logger = logging.getLogger(__name__)


@dataclass
class ErrorInfo:
    """Detailed error information container.

    Attributes:
        error_type: Exception type name
        message: Error message
        traceback: Full traceback string
        context: Context where error occurred
        timestamp: Error occurrence time
        fatal: Whether error is fatal
        handled: Whether error has been handled
    """

    error_type: str
    message: str
    traceback: str
    context: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    fatal: bool = False
    handled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "error_type": self.error_type,
            "message": self.message,
            "traceback": self.traceback,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "fatal": self.fatal,
            "handled": self.handled,
        }


class TUIErrorHandler:
    """Global error handler for the TUI application.

    Classifies errors as fatal (SystemExit, KeyboardInterrupt, MemoryError,
    RecursionError) or recoverable, logs all errors, displays user-friendly
    messages, maintains a bounded error history, and offers GitHub issue
    creation with pre-filled details. Use as context manager via catch_errors().
    """

    GITHUB_REPO = "luantrip/AuraCli"
    MAX_ERROR_HISTORY = 100

    FATAL_ERRORS = (
        SystemExit,
        KeyboardInterrupt,
        MemoryError,
        RecursionError,
    )

    def __init__(self, app: App):
        """Initialize error handler.

        Args:
            app: Textual App instance
        """
        self.app = app
        self._error_history: List[ErrorInfo] = []
        self._on_error_callbacks: List[Callable[[ErrorInfo], None]] = []
        self._suppressed_errors: set = set()

    def handle_error(
        self,
        error: Exception,
        context: str = "",
        show_notification: bool = True,
        log: bool = True,
        notify: Optional[bool] = None,
        notify_callback: Optional[Callable[..., None]] = None,
    ) -> ErrorInfo:
        """Handle error with appropriate response.

        Args:
            error: Exception that occurred
            context: Description of where error occurred
            show_notification: Whether to show user notification
            log: Whether to log the error

        Returns:
            ErrorInfo with error details
        """
        if notify is not None:
            show_notification = notify

        error_info = ErrorInfo(
            error_type=type(error).__name__,
            message=str(error),
            traceback=traceback.format_exc(),
            context=context,
            fatal=self._is_fatal(error),
        )

        self._error_history.append(error_info)
        if len(self._error_history) > self.MAX_ERROR_HISTORY:
            self._error_history = self._error_history[-self.MAX_ERROR_HISTORY :]

        if log:
            if error_info.fatal:
                logger.critical(
                    f"Fatal error in {context}: {error_info.error_type}: {error_info.message}\n"
                    f"{error_info.traceback}"
                )
            else:
                logger.error(
                    f"Error in {context}: {error_info.error_type}: {error_info.message}"
                )

        emit_error(
            error_info.error_type,
            error_info.message,
            context,
            error_info.fatal,
            error_info.traceback,
        )

        for callback in self._on_error_callbacks:
            try:
                callback(error_info)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")

        if error_info.fatal:
            self._show_fatal_error(error_info)
        elif show_notification:
            if notify_callback is not None:
                message = f"{error_info.error_type}: {error_info.message}"
                try:
                    notify_callback(message, severity="error")
                except TypeError:
                    notify_callback(message)
                except Exception as callback_error:
                    logger.error("Failed to show error callback: %s", callback_error)
            else:
                self._show_error_notification(error_info)

        error_info.handled = True
        return error_info

    def _is_fatal(self, error: Exception) -> bool:
        """Determine if error is fatal.

        Args:
            error: Exception to check

        Returns:
            True if fatal
        """
        return isinstance(error, self.FATAL_ERRORS)

    def _show_error_notification(self, error_info: ErrorInfo) -> None:
        """Show non-fatal error as notification.

        Args:
            error_info: Error information
        """
        try:
            message = f"{error_info.error_type}: {error_info.message}"
            if len(message) > 100:
                message = message[:97] + "..."

            self.app.notify(message, title="Erro", severity="error", timeout=10)
        except Exception as e:
            logger.error(f"Failed to show error notification: {e}")

    def _show_fatal_error(self, error_info: ErrorInfo) -> None:
        """Show fatal error screen.

        Args:
            error_info: Error information
        """
        try:
            from aura_cli.tui.widgets.dialogs.error_dialog import FatalErrorDialog

            dialog = FatalErrorDialog(
                error_info=error_info,  # type: ignore[arg-type]
                on_reset=self._reset_app,
                on_report=lambda: self.open_github_issue(error_info),
                on_exit=self._exit_app,
            )
            self.app.mount(dialog)
        except ImportError:
            self.app.notify(
                f"Erro fatal: {error_info.message}\n\nPressione Ctrl+C para sair.",
                title="Erro fatal",
                severity="error",
                timeout=0,
            )
        except Exception as e:
            logger.error(f"Failed to show fatal error screen: {e}")

    def _reset_app(self) -> None:
        """Return the TUI to a recoverable idle state after a fatal error."""
        try:
            self._error_history.clear()

            transition_runtime = getattr(self.app, "_transition_runtime", None)
            if callable(transition_runtime):
                from aura_cli.application.presentation.tui_runtime_state import (
                    RuntimeAction,
                )

                transition_runtime(RuntimeAction.READY)

            dismiss_navigation = getattr(self.app, "_action_cancel", None)
            if callable(dismiss_navigation):
                dismiss_navigation()
            restore_focus = getattr(self.app, "_restore_composer_focus", None)
            if callable(restore_focus):
                restore_focus()

            self.app.notify(
                "Aplicação reiniciada. Parte do estado pode ter sido perdida.",
                title="Reinicialização concluída",
                severity="warning",
            )

        except Exception as e:
            logger.error(f"Failed to reset app: {e}")

    def _exit_app(self) -> None:
        """Exit the application."""
        try:
            self.app.exit()
        except Exception:
            sys.exit(1)

    def open_github_issue(self, error_info: ErrorInfo) -> None:
        """Open GitHub issue page with pre-filled error details.

        Args:
            error_info: Error information to include
        """
        title = f"[TUI Error] {error_info.error_type}: {error_info.message[:50]}"

        try:
            from aura_cli import __version__

            version = __version__
        except ImportError:
            version = "unknown"

        body = f"""## Error Details

**Type:** `{error_info.error_type}`
**Message:** `{error_info.message}`
**Context:** {error_info.context or "N/A"}
**Timestamp:** {error_info.timestamp.isoformat()}
**Fatal:** {error_info.fatal}

Traceback

```
{error_info.traceback}
```

Environment

- **OS:** {platform.system()} {platform.release()}
- **Python:** {sys.version}
- **Aura CLI:** {version}
- **Terminal:** {os.environ.get("TERM_PROGRAM", "unknown")}
- **Shell:** {os.environ.get("SHELL", "unknown")}

Steps to Reproduce

1. [Please describe what you were doing when the error occurred]
2.
3.

Expected Behavior

[What did you expect to happen?]


[Any additional information that might be helpful]

---
*This issue was auto-generated by Aura CLI TUI error handler*
"""

        base_url = f"https://github.com/{self.GITHUB_REPO}/issues/new"
        params = urllib.parse.urlencode(
            {"title": title, "body": body, "labels": "bug,tui,auto-generated"}
        )

        url = f"{base_url}?{params}"

        try:
            webbrowser.open(url)
            self.app.notify(
                "Abrindo a página de issue no GitHub...",
                title="Relatar problema",
                severity="information",
            )
        except Exception as e:
            logger.error(f"Failed to open browser: {e}")
            self.app.notify(
                f"Não foi possível abrir o navegador. URL: {url}",
                title="Relatar problema",
                severity="warning",
                timeout=0,
            )

    def on_error(self, callback: Callable[[ErrorInfo], None]) -> Callable[[], None]:
        """Register error callback.

        Args:
            callback: Function to call when error occurs

        Returns:
            Unregister function
        """
        self._on_error_callbacks.append(callback)
        return lambda: self._on_error_callbacks.remove(callback)

    def suppress_error(self, error_type: str) -> None:
        """Suppress notifications for specific error type.

        Args:
            error_type: Error type name to suppress
        """
        self._suppressed_errors.add(error_type)

    def unsuppress_error(self, error_type: str) -> None:
        """Stop suppressing specific error type.

        Args:
            error_type: Error type name to unsuppress
        """
        self._suppressed_errors.discard(error_type)

    def catch_errors(self, context: str = ""):
        """Context manager for catching errors.

        Args:
            context: Description of the operation

        Returns:
            ErrorCatcher context manager

        Example:
            ```python
            with handler.catch_errors("render_widget"):
                widget.render()
            ```
        """
        return ErrorCatcher(self, context)

    def get_error_history(self, limit: int = 20) -> List[ErrorInfo]:
        """Get recent error history.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of recent ErrorInfo objects
        """
        return self._error_history[-limit:]

    def clear_history(self) -> None:
        """Clear error history."""
        self._error_history.clear()

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors.

        Returns:
            Dictionary with error statistics
        """
        if not self._error_history:
            return {"total": 0, "fatal": 0, "by_type": {}, "recent": []}

        by_type: Dict[str, int] = {}
        fatal_count = 0

        for error in self._error_history:
            by_type[error.error_type] = by_type.get(error.error_type, 0) + 1
            if error.fatal:
                fatal_count += 1

        return {
            "total": len(self._error_history),
            "fatal": fatal_count,
            "by_type": by_type,
            "recent": [e.to_dict() for e in self._error_history[-5:]],
        }


class ErrorCatcher:
    """Context manager for catching errors.

    Attributes:
        handler: TUIErrorHandler instance
        context: Context description
    """

    def __init__(self, handler: TUIErrorHandler, context: str):
        """Initialize error catcher.

        Args:
            handler: TUIErrorHandler instance
            context: Context description
        """
        self.handler = handler
        self.context = context

    def __enter__(self):
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and clean up."""
        if exc_val is not None:
            self.handler.handle_error(exc_val, context=self.context)
            return not self.handler._is_fatal(exc_val)
        return False


_global_handler: Optional[TUIErrorHandler] = None


def get_error_handler() -> Optional[TUIErrorHandler]:
    """Get global error handler.

    Returns:
        Global TUIErrorHandler instance or None
    """
    return _global_handler


def set_error_handler(handler: TUIErrorHandler) -> None:
    """Set global error handler.

    Args:
        handler: TUIErrorHandler instance
    """
    global _global_handler
    _global_handler = handler


def handle_error(error: Exception, context: str = "") -> Optional[ErrorInfo]:
    """Handle error using global handler.

    Args:
        error: Exception to handle
        context: Context description

    Returns:
        ErrorInfo if handler exists, None otherwise
    """
    if _global_handler:
        return _global_handler.handle_error(error, context)
    else:
        logger.error(f"Unhandled error (no handler): {error}")
        return None
