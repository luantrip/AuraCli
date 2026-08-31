"""Presentation-neutral layout policy for the conversation-first TUI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TuiDensity(str, Enum):
    COMPACT = "compact"
    COMFORTABLE = "comfortable"
    SPACIOUS = "spacious"


class DrawerMode(str, Enum):
    OVERLAY = "overlay"
    SPLIT = "split"


class TuiDrawer(str, Enum):
    WORKSPACE = "workspace"
    ACTIVITY = "activity"


@dataclass(frozen=True)
class TuiLayoutState:
    width: int
    height: int
    requested_drawer: TuiDrawer | None = None
    focus_mode: bool = False


@dataclass(frozen=True)
class TuiLayoutPlan:
    drawer: TuiDrawer | None
    drawer_mode: DrawerMode
    drawer_width: int
    density: TuiDensity
    show_header: bool
    show_task_panel: bool
    show_footer_details: bool

    @property
    def conversation_width(self) -> int:
        return 0 if self.drawer_mode is DrawerMode.OVERLAY else self.drawer_width


def decide_tui_layout(state: TuiLayoutState) -> TuiLayoutPlan:
    """Allocate space by priority: conversation first, diagnostics on demand."""
    width = max(state.width, 1)
    height = max(state.height, 1)
    drawer = None if state.focus_mode else state.requested_drawer
    drawer_mode = DrawerMode.OVERLAY if width < 120 else DrawerMode.SPLIT
    drawer_width = 0
    if drawer is not None:
        drawer_width = (
            width if drawer_mode is DrawerMode.OVERLAY else min(44, max(32, width // 3))
        )
    density = (
        TuiDensity.COMPACT
        if width < 80 or height < 24
        else TuiDensity.SPACIOUS
        if width >= 160 and height >= 40
        else TuiDensity.COMFORTABLE
    )
    return TuiLayoutPlan(
        drawer=drawer,
        drawer_mode=drawer_mode,
        drawer_width=drawer_width,
        density=density,
        show_header=height >= 24,
        show_task_panel=height >= 32 and not state.focus_mode,
        show_footer_details=width >= 100 and height >= 24,
    )


__all__ = [
    "DrawerMode",
    "TuiDensity",
    "TuiDrawer",
    "TuiLayoutPlan",
    "TuiLayoutState",
    "decide_tui_layout",
]
