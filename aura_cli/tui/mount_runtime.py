"""Mount-time composition helpers for the Textual application."""

from __future__ import annotations

from datetime import datetime
import logging
import time
from typing import Any

from aura_cli.tui.keybinds import KeybindManager
from aura_cli.tui.shell.window_stack import WindowStack
from aura_cli.tui.widgets.dialogs import DialogProvider

logger = logging.getLogger(__name__)


def mount_input_and_windows(app: Any) -> None:
    """Attach keybind, dialog and window adapters owned by the app."""
    manager = KeybindManager(app)
    for keybind in app.keybind_config.get_keybind_infos():
        manager.register(keybind)
    manager.leader.leader_key = app.keybind_config.leader_key
    manager.leader.timeout = app.keybind_config.leader_timeout
    app.keybind_manager = manager
    app.dialog_provider = DialogProvider(app)
    app.windows = WindowStack(app, app.dialog_provider)


def connect_app_loop(app: Any) -> None:
    """Connect shutdown and initialize the public TUI bridge lifecycle."""
    if app.app_loop is None:
        return
    app.app_loop.set_shutdown_event(app.shutdown_event)
    ui = getattr(app.app_loop, "ui", None)
    if ui is None or not hasattr(ui, "ensure_initialized"):
        return
    try:
        if ui.ensure_initialized():
            logger.info("SyncManager initialized during TUI mount")
        else:
            logger.warning("TUI bridge initialization returned False")
    except Exception as error:
        logger.warning("Failed to initialize TUI bridge: %s", error)


def stop_autosave_timer(app: Any) -> None:
    """Stop and clear the app-owned session autosave timer."""
    timer = getattr(app, "__dict__", {}).get("_autosave_timer")
    if timer is None:
        return
    app._autosave_timer = None
    stop = getattr(timer, "stop", None)
    if not callable(stop):
        return
    try:
        stop()
    except Exception as error:
        logger.debug("Session auto-save timer was already stopped: %s", error)


def initialize_tui_session(app: Any) -> None:
    """Initialize session metadata and schedule autosave when configured."""
    app.store.set("session.id", f"session_{int(time.time())}")
    app.store.set("session.started_at", datetime.now().isoformat())
    stop_autosave_timer(app)
    try:
        from aura_cli.core.sessions import get_session_manager

        interval = float(get_session_manager().auto_save_interval)
        if interval > 0:
            app._autosave_timer = app.set_interval(interval, app._on_autosave_interval)
    except Exception as error:
        logger.debug("Session auto-save interval not started: %s", error)


def mount_runtime(app: Any) -> None:
    """Compose non-visual TUI adapters in their required order."""
    mount_input_and_windows(app)
    connect_app_loop(app)
    app.plugin_manager.load_plugins()
    initialize_tui_session(app)
