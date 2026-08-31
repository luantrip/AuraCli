"""Aura CLI TUI shared component library.

components/shared/ — tool-agnostic primitives (dialogs, panels, navigation,
  status bars, spinners, notifications). No dependency on AuraTUI context.
widgets/ — Aura-TUI-specific widgets that use chat/agent/tool state.

Rule: reusable in any Textual TUI → components/shared/;
      uses Aura runtime data → widgets/.
"""

from aura_cli.tui.components.shared import (  # Dialogs; Navigation; Panels; Data display; Loading; Status; Notifications
    BaseDialog,
    Breadcrumb,
    CollapsiblePanel,
    ConfirmDialog,
    InputDialog,
    KeyValueTable,
    LoadingSpinner,
    MiniStatusBar,
    NotificationCenter,
    ProgressDialog,
    ProgressIndicator,
    SelectDialog,
    SplitPanel,
    StatusBar,
    TabBar,
    Toast,
    TreeView,
)

__all__ = [
    # Dialogs
    "BaseDialog",
    # Navigation
    "Breadcrumb",
    # Panels
    "CollapsiblePanel",
    "ConfirmDialog",
    "InputDialog",
    # Data display
    "KeyValueTable",
    # Loading
    "LoadingSpinner",
    "MiniStatusBar",
    "NotificationCenter",
    "ProgressDialog",
    "ProgressIndicator",
    "SelectDialog",
    "SplitPanel",
    # Status
    "StatusBar",
    "TabBar",
    # Notifications
    "Toast",
    "TreeView",
]
