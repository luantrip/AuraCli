"""
UI Panel Integration - Wrapper for unified tool execution display.

Provides backward-compatible wrapper that replaces individual tool calls
with grouped panel display while maintaining existing API.
"""

from typing import Any, Callable, Dict, Optional

_panel_enabled = True
_compact_mode = True  # Show tools as compact inline by default
_current_execution: Optional[Any] = None
_tool_call_presenter: Optional[Callable[[str, Dict[str, Any], bool, bool], Any]] = None


def configure_tool_call_presenter(
    presenter: Optional[Callable[[str, Dict[str, Any], bool, bool], Any]],
) -> None:
    """Configure the host adapter responsible for rendering tool calls."""
    global _tool_call_presenter
    _tool_call_presenter = presenter


def enable_panel_mode():
    """Enable grouped panel mode."""
    global _panel_enabled
    _panel_enabled = True


def disable_panel_mode():
    """Disable panel mode (use individual display)."""
    global _panel_enabled
    _panel_enabled = False


def set_compact_mode(enabled: bool = True):
    """Set compact inline tool display mode."""
    global _compact_mode
    _compact_mode = enabled


def is_panel_mode() -> bool:
    """Check if panel mode is enabled."""
    return _panel_enabled


def display_tool_call(tool_name: str, params: Dict[str, Any]):
    """
    Display tool call - uses compact inline, panel, or individual display.

    Args:
        tool_name: Tool name
        params: Tool parameters
    """
    global _current_execution

    if _tool_call_presenter is None:
        return
    try:
        _current_execution = _tool_call_presenter(
            tool_name, params, _compact_mode, _panel_enabled
        )
    except Exception:
        _current_execution = None


def mark_tool_success(result: str, duration: Optional[float] = None):
    """Mark current tool as successful — update inline display."""
    global _current_execution
    if _current_execution:
        _current_execution.mark_success(result, duration)
        _current_execution = None


def mark_tool_error(error: str, duration: Optional[float] = None):
    """Mark current tool as failed — update inline display."""
    global _current_execution
    if _current_execution:
        _current_execution.mark_error(error, duration)
        _current_execution = None
