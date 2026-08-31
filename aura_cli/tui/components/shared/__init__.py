"""
Shared TUI Components — reusable, tool-agnostic primitives.

These components are designed to be used usados em qualquer ferramenta TUI
(code, paint, file_manager, monitor, etc.) and also in Aura screens and widgets
a TUI, garantindo UX consistente and reducing code duplication.

MUST NOT depend on Aura-specific state (chat, LLM, agents).
For widgets que dependem do contexto do Aura, use aura_cli.tui.widgets/.
"""

from aura_cli.tui.components.shared.data_display import (
    KeyValueTable,
    TreeNode,
    TreeView,
)
from aura_cli.tui.components.shared.dialogs import (
    BaseDialog,
    ConfirmDialog,
    InputDialog,
    ProgressDialog,
    SelectDialog,
)
from aura_cli.tui.components.shared.loading import (
    LoadingSpinner,
    ProgressIndicator,
    PulseAnimation,
)
from aura_cli.tui.components.shared.navigation import (
    Breadcrumb,
    BreadcrumbItem,
    Tab,
    TabBar,
)
from aura_cli.tui.components.shared.notifications import (
    NotificationCenter,
    Toast,
    ToastType,
)
from aura_cli.tui.components.shared.panels import (
    CollapsiblePanel,
    SplitDirection,
    SplitPanel,
)
from aura_cli.tui.components.shared.status import MiniStatusBar, StatusBar, StatusItem

__all__ = [
    # Dialogs
    "BaseDialog",
    # Navigation
    "Breadcrumb",
    "BreadcrumbItem",
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
    "PulseAnimation",
    "SelectDialog",
    "SplitDirection",
    "SplitPanel",
    # Status
    "StatusBar",
    "StatusItem",
    "Tab",
    "TabBar",
    # Notifications
    "Toast",
    "ToastType",
    "TreeNode",
    "TreeView",
]
