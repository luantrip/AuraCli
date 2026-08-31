"""
Window / modal composition layer for Aura TUI.

See ``docs/architecture/tui-windows.md``.
"""

from aura_cli.tui.shell.base_modal import (
    BaseAuraModalScreen,
    BaseAuraResultModalScreen,
)
from aura_cli.tui.shell.base_tool_screen import BaseToolScreen
from aura_cli.tui.shell.modal_frame import ModalFrame, ModalTitle
from aura_cli.tui.shell.prompts import push_confirm, push_input
from aura_cli.tui.shell.screen_registry import (
    ScreenId,
    open_screen,
    open_screen_wait,
    screen_class,
)
from aura_cli.tui.shell.window_stack import OverlayKind, WindowStack

__all__ = [
    "BaseAuraModalScreen",
    "BaseAuraResultModalScreen",
    "BaseToolScreen",
    "ModalFrame",
    "ModalTitle",
    "OverlayKind",
    "ScreenId",
    "WindowStack",
    "open_screen",
    "open_screen_wait",
    "push_confirm",
    "push_input",
    "screen_class",
]
