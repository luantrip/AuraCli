"""Composite layout: AGI task window + optional tool execution panel."""

from __future__ import annotations

from typing import Any, List

from rich.console import Group, RenderableType

from aura_cli.core.ui_panel import is_panel_mode


def render_task_composite_surface(
    task_window: Any,
    *,
    max_logs: int = 10,
    include_tool_panel: bool = True,
) -> RenderableType:
    """Single Rich group: task window plus live tool panel when panel mode is on."""
    parts: List[RenderableType] = [task_window.render(max_logs=max_logs)]

    if include_tool_panel and is_panel_mode():
        try:
            from aura_cli.cli.ui.components.tool_execution_panel import get_tool_panel

            panel = get_tool_panel()
            if panel.executions:
                parts.append(panel.render(show_summary=False))
        except Exception:
            pass

    if len(parts) == 1:
        return parts[0]
    return Group(*parts)
