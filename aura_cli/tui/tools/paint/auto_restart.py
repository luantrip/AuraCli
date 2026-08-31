"""Auto Restart - Aura CLI Paint Tool

Automatic program restart on file changes for development.

Features:
    - Watchdog-based file monitoring
    - Terminal state cleanup before restart
    - File descriptor cleanup (psutil)
    - Unsaved changes prompt integration
    - Cross-platform support (Windows/Unix)
"""

from __future__ import annotations

import contextlib
import os
import sys
from typing import TYPE_CHECKING

from textual.app import ScreenStackError

if TYPE_CHECKING:
    from .gallery import GalleryApp
    from .paint import Paint as PaintApp


def _stop_observer() -> None:
    try:
        try:
            if observer:
                observer.stop()
                observer.join(timeout=1)
                if observer.is_alive():
                    print("Timed out waiting for file change observer thread to stop.")
        except RuntimeError as e:
            if str(e) != "cannot join current thread":
                raise
    except Exception as e:
        print("Error stopping file change observer:", e)


def _close_file_descriptors() -> None:
    try:
        try:
            import psutil
        except ImportError:
            print(
                "psutil module not available; skipping file descriptor cleanup for auto-restart."
            )
        else:
            p = psutil.Process(os.getpid())
            for handler in p.open_files() + p.connections():
                if handler.fd == -1:
                    continue
                try:
                    os.close(handler.fd)
                except Exception as e:
                    print(f"Error closing file descriptor ({handler.fd}):", e)
    except Exception as e:
        print("Error closing file descriptors:", e)


def restart_program() -> None:
    """Restart current program with clean terminal state."""
    if hasattr(_app, "discard_backup"):
        try:
            _app.discard_backup()  # type: ignore
        except Exception as e:
            print("Error discarding backup:", e)

    try:
        _app.exit()
        _app._driver.stop_application_mode()  # pyright: ignore[reportPrivateUsage, reportOptionalMemberAccess]
    except Exception as e:
        print(
            "Error stopping application mode. The command line may not work as expected. The `reset` command should restore it on Linux.",
            e,
        )

    _stop_observer()
    _close_file_descriptors()

    if os.name == "nt":
        # On Windows, os.exec* bungles the arguments: https://github.com/python/cpython/issues/64650
        # Workaround: reloaded process may have broken terminal state
        os.execl(
            sys.executable,
            *(
                (
                    '"' + arg.replace('"', '""') + '"'
                    if " " in arg
                    else arg.replace('"', '""')
                )
                for arg in sys.orig_argv
            ),
        )
    else:
        os.execl(sys.executable, *sys.orig_argv)


def restart_on_changes(app: PaintApp | GalleryApp) -> None:
    """Monitor filesystem and restart on Python file changes.

    Args:
        app: PaintApp or GalleryApp instance to monitor

    Note:
        Watches .py files recursively, ignoring dotfiles, node_modules,
        __pycache__, and virtual environments. Prompts for unsaved changes.
    """

    from watchdog.events import (
        EVENT_TYPE_CLOSED,
        EVENT_TYPE_OPENED,
        FileSystemEvent,
        RegexMatchingEventHandler,
    )
    from watchdog.observers import Observer

    class RestartHandler(RegexMatchingEventHandler):
        """File system event handler that triggers restart.

        Ignores open/close events and prompts for unsaved changes
        before restarting.
        """

        def on_any_event(self, event: FileSystemEvent) -> None:
            """Handle file system event.

            Args:
                event: FileSystemEvent with type and path
            """
            if event.event_type in (EVENT_TYPE_CLOSED, EVENT_TYPE_OPENED):
                return
            print("Reloading due to FS change:", event.event_type, event.src_path)
            with contextlib.suppress(ScreenStackError):
                _app.screen.styles.background = "red"
            if hasattr(app, "is_document_modified") and _app.is_document_modified():  # type: ignore
                _app.call_from_thread(_app.action_reload)
            else:
                restart_program()
            with contextlib.suppress(ScreenStackError):
                _app.screen.styles.background = "yellow"

    global observer, _app
    _app = app
    observer = Observer()
    handler = RestartHandler(
        regexes=[
            r".*\.py$",
        ],
        ignore_regexes=[
            r".*(/|\\|^)\.[^/\\]",
            r".*(/|\\|^)node_modules(/|\\|$)",
            r".*(/|\\|^)__pycache__(/|\\|$)",
            r".*(/|\\|^)v?env(/|\\|$)",
        ],
        ignore_directories=True,
    )
    observer.schedule(handler, path=".", recursive=True)
    observer.start()
