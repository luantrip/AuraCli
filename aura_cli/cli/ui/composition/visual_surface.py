"""Shared emission and chrome helpers for the Rich conversation flow."""

from __future__ import annotations

from typing import Any

import rich.box as box
from rich.console import Console, RenderableType
from rich.panel import Panel

from aura_cli.application.presentation.cli_visual import SurfaceChrome
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.layout_contract import layout_for_width


def surface_panel(
    content: RenderableType,
    *,
    title: Any = None,
    chrome: SurfaceChrome = SurfaceChrome.GROUP,
    border_style: str = "dim",
    console_width: int = 80,
) -> RenderableType:
    """Apply the visual hierarchy without adding external whitespace."""
    if chrome is SurfaceChrome.FLOW:
        return content
    metrics = layout_for_width(console_width)
    return Panel(
        content,
        title=title,
        title_align="left",
        border_style=border_style,
        padding=metrics.focus_padding
        if chrome is SurfaceChrome.FOCUS
        else metrics.group_padding,
        box=box.ROUNDED,
        expand=False,
    )


class VisualEmitter:
    """Own vertical rhythm for sequential renderables."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console if console is not None else get_console()
        self._has_content = False

    def emit(self, renderable: RenderableType, *, separate: bool = False) -> None:
        if separate and self._has_content:
            self.console.print()
        self.console.print(renderable)
        self._has_content = True

    def reset(self) -> None:
        self._has_content = False


__all__ = ["VisualEmitter", "surface_panel"]
