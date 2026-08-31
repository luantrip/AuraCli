"""UI package for Aura CLI — Rich components, styling and display utilities.

Lazy-exports: display_file_edit, display_shell_command, display_tool_args,
display_run_terminal_command, format_tool_status_message, ToolStatus,
UIIcons, UIStyles, UIMessages, UILayout, ComponentBase, StatusBar,
FileDiff, ToolResult.
"""

from importlib import import_module

_LAZY_EXPORTS = {
    "ComponentBase": ("aura_cli.cli.ui.components.base", "ComponentBase"),
    "FileDiff": ("aura_cli.cli.ui.components.file_diff", "FileDiff"),
    "StatusBar": ("aura_cli.cli.ui.components.status_bar", "StatusBar"),
    "ToolResult": ("aura_cli.cli.ui.components.tool_result", "ToolResult"),
    "ToolStatus": ("aura_cli.cli.ui.tool_status", "ToolStatus"),
    "UIIcons": ("aura_cli.cli.ui.constants", "UIIcons"),
    "UILayout": ("aura_cli.cli.ui.constants", "UILayout"),
    "UIMessages": ("aura_cli.cli.ui.constants", "UIMessages"),
    "UIStyles": ("aura_cli.cli.ui.constants", "UIStyles"),
    "LayoutMetrics": ("aura_cli.cli.ui.layout_contract", "LayoutMetrics"),
    "layout_for_width": ("aura_cli.cli.ui.layout_contract", "layout_for_width"),
    "display_error": ("aura_cli.cli.ui.display_facade", "display_error"),
    "display_file_edit": ("aura_cli.cli.ui.display", "display_file_edit"),
    "display_info": ("aura_cli.cli.ui.display_facade", "display_info"),
    "display_run_terminal_command": (
        "aura_cli.cli.ui.terminal_command",
        "display_run_terminal_command",
    ),
    "display_shell_command": ("aura_cli.cli.ui.display", "display_shell_command"),
    "display_success": ("aura_cli.cli.ui.display_facade", "display_success"),
    "display_tool_args": ("aura_cli.cli.ui.display", "display_tool_args"),
    "display_warning": ("aura_cli.cli.ui.display_facade", "display_warning"),
    "format_tool_status_message": (
        "aura_cli.cli.ui.tool_status",
        "format_tool_status_message",
    ),
    "get_console": ("aura_cli.cli.ui.display_facade", "get_console"),
    "register_ui": ("aura_cli.cli.ui.display_facade", "register_ui"),
    "unregister_ui": ("aura_cli.cli.ui.display_facade", "unregister_ui"),
}


def __getattr__(name: str):
    """Keep package imports cheap while preserving the public UI API."""
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "ComponentBase",
    "FileDiff",
    "LayoutMetrics",
    "StatusBar",
    "ToolResult",
    "ToolStatus",
    "UIIcons",
    "UILayout",
    "UIMessages",
    "UIStyles",
    "display_error",
    "display_file_edit",
    "display_info",
    "display_run_terminal_command",
    "display_shell_command",
    "display_success",
    "display_tool_args",
    "display_warning",
    "format_tool_status_message",
    "get_console",
    "layout_for_width",
    "register_ui",
    "unregister_ui",
]
