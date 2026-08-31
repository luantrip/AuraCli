"""Rich adapter for the Core tool-call presentation port."""

from __future__ import annotations

from typing import Any, Dict

from aura_cli.cli.ui.components.tool_execution_panel import get_tool_panel
from aura_cli.cli.ui.components.tool_header import AuraToolHeader
from aura_cli.cli.ui.components.turn_separator import ToolCallInline
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.core.ui_panel import configure_tool_call_presenter


def present_tool_call(
    tool_name: str,
    params: Dict[str, Any],
    compact_mode: bool,
    panel_enabled: bool,
) -> Any:
    """Render a tool call and return its optional tracked execution."""
    console = get_console()
    if compact_mode:
        inline = ToolCallInline()
        console.print(inline.render(tool_name, params, status="running"))
        return None

    if panel_enabled:
        execution = get_tool_panel().add_tool(tool_name, params)
        execution.mark_running()
        return execution

    header = AuraToolHeader().render(tool_name=tool_name, args=params)
    console.print(header)
    return None


configure_tool_call_presenter(present_tool_call)
