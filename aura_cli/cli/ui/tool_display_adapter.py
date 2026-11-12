"""Rich adapter for the Core tool-call presentation port."""

from __future__ import annotations

from typing import Any, Dict

from aura_cli.cli.ui.components.agent.tool_header import AuraToolHeader
from aura_cli.cli.ui.components.display.turn_separator import ToolCallInline
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.core.ui_panel import configure_tool_call_presenter


def present_tool_call(
    tool_name: str,
    params: Dict[str, Any],
    compact_mode: bool,
    panel_enabled: bool,
) -> Any:
    """Render a tool call and return its optional tracked execution.

    Two canonical modes only: a compact inline line (default) or a full
    header. The former grouped `ToolExecutionPanel` mode was removed (G6) —
    it was unreachable because `compact_mode` is never disabled, so it only
    produced dead branches and an empty grouped panel. `panel_enabled` is kept
    in the signature for the stable Core presenter port but no longer selects a
    distinct renderer.
    """
    console = get_console()
    if compact_mode:
        inline = ToolCallInline()
        console.print(inline.render(tool_name, params, status="running"))
        return None

    header = AuraToolHeader().render(tool_name=tool_name, args=params)
    console.print(header)
    return None


configure_tool_call_presenter(present_tool_call)
