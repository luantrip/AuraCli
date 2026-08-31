"""Routing decisions shared by the terminal presentation adapters."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def is_textual_ui(ui: Any) -> bool:
    """Return whether ``ui`` represents the Textual presentation adapter."""
    if ui is None:
        return False
    return type(ui).__name__ == "TextualUIManager" or bool(getattr(ui, "is_tui", False))


def open_settings_for_ui(ui: Any) -> bool:
    """Ask an active presentation adapter to open its settings surface."""
    if not is_textual_ui(ui):
        return False

    app = getattr(ui, "app", None)
    if app is None or not hasattr(app, "_open_settings_screen"):
        return False

    def open_screen() -> None:
        app._open_settings_screen()

    opened = False
    if hasattr(ui, "_safe_call_from_thread"):
        opened = bool(ui._safe_call_from_thread(open_screen))
    if not opened and hasattr(app, "call_from_thread"):
        try:
            app.call_from_thread(open_screen)
            opened = True
        except Exception as exc:
            logger.debug("call_from_thread settings failed: %s", exc)
    if not opened:
        try:
            open_screen()
            opened = True
        except Exception as exc:
            logger.warning("Failed to open TUI settings: %s", exc)
    return opened
