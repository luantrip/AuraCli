"""Advanced UI components — interactive dashboard, toasts and virtualised list.

Re-exports InteractiveDashboard (keyboard/mouse navigation), ToastManager
(non-intrusive temporary notifications) and VirtualList (high-volume data).
"""

from aura_cli.cli.ui.components.collapsed_text import (
    CHAR_THRESHOLD,
    LINE_THRESHOLD,
    CollapsedTextDisplay,
    format_user_input_display,
    render_collapsed_input,
    should_collapse,
)
from aura_cli.cli.ui.components.interactive_dashboard import (
    DashboardColumn,
    DashboardFilter,
    InteractiveDashboard,
    SortOrder,
)
from aura_cli.cli.ui.components.subagent_panel import SubAgentPanel
from aura_cli.cli.ui.components.toast import (
    Toast,
    ToastManager,
    ToastPosition,
    ToastType,
    get_toast_manager,
)
from aura_cli.cli.ui.components.workspace_diff import WorkspaceDiffDisplay

__all__ = [
    "CHAR_THRESHOLD",
    "LINE_THRESHOLD",
    # Collapsed text display
    "CollapsedTextDisplay",
    "DashboardColumn",
    "DashboardFilter",
    "InteractiveDashboard",
    "SortOrder",
    "SubAgentPanel",
    "Toast",
    "ToastManager",
    "ToastPosition",
    "ToastType",
    "WorkspaceDiffDisplay",
    "format_user_input_display",
    "get_toast_manager",
    "render_collapsed_input",
    "should_collapse",
]
