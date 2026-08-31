"""
Tool Panel Helper - Integration helper for AGI worker.

Provides context manager and utilities for AGI worker to use
ToolExecutionPanel seamlessly.
"""

from contextlib import contextmanager
from typing import Optional

from aura_cli.cli.ui.components.tool_execution_panel import (
    get_tool_panel,
    reset_tool_panel,
)
from aura_cli.cli.ui.composition import publish_tool_execution_panel
from aura_cli.core.ui_panel import disable_panel_mode, enable_panel_mode


@contextmanager
def tool_panel_context(task_id: Optional[int] = None, task_description: str = ""):
    """
    Context manager for tool panel execution.

    Usage:
        with tool_panel_context(task_id=3, task_description="Initialise Next.js"):
            # Execute tools here
            # They will be grouped in panel
            pass
        # Panel is displayed automatically on exit

    Args:
        task_id: Task ID
        task_description: Task description
    """
    reset_tool_panel(task_id, task_description)
    enable_panel_mode()

    try:
        yield get_tool_panel()
    finally:
        panel = get_tool_panel()
        if panel.executions:
            publish_tool_execution_panel(panel)
        disable_panel_mode()
