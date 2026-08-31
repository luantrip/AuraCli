"""
core/ui — stable facade for tool display utilities.

Re-exports from ui_panel.py (display_tool_call logic) so that all tool
modules share a single stable import path. This is the canonical import
surface for tool call display — do not import from ui_panel directly.

    from aura_cli.core.ui import display_tool_call
"""

from aura_cli.core.ui_panel import (
    disable_panel_mode,
    display_tool_call,
    enable_panel_mode,
    is_panel_mode,
    mark_tool_error,
    mark_tool_success,
    set_compact_mode,
)

__all__ = [
    "disable_panel_mode",
    "display_tool_call",
    "enable_panel_mode",
    "is_panel_mode",
    "mark_tool_error",
    "mark_tool_success",
    "set_compact_mode",
]
