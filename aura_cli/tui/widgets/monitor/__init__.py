"""Monitor browser UI widgets."""

from aura_cli.tui.widgets.monitor.address_bar import AddressBar
from aura_cli.tui.widgets.monitor.content_viewer import ContentViewer
from aura_cli.tui.widgets.monitor.status_bar import MonitorStatusBar
from aura_cli.tui.widgets.monitor.tab_bar import TabBar
from aura_cli.tui.widgets.monitor.unavailable_panel import MonitorUnavailablePanel

__all__ = [
    "AddressBar",
    "ContentViewer",
    "MonitorStatusBar",
    "MonitorUnavailablePanel",
    "TabBar",
]
