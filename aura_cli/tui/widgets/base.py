"""Base widget classes for Aura TUI.

ARCHITECTURAL NOTE:
    This module is exclusive to the TUI layer (Textual).
    A camada CLI (Rich) uses its own base at aura_cli/cli/ui/components/base.py
    (ComponentBase), pcause Rich uses an ABC rendering pattern incompatible with
    the widget lifecycle do Textual.

    CLI components  →  herdam ComponentBase  →  retornam RenderableType (Rich)
    TUI widgets     →  herdam Widget/Static   →  composition via compose() (Textual)

Classes:
    - TimerWidget: Base para widgets TUI that manage periodic timers.
                   For all  outros widgets, herdar diretamente de
                   textual.widgets.Static, Container, etc.
"""

from __future__ import annotations

from typing import Callable, Dict

from textual.timer import Timer
from textual.widgets import Static


class TimerWidget(Static):
    """Base class for widgets that manage periodic timers.

    Automatically stops all registered timers on unmount to prevent
    memory leaks and post-unmount errors.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._managed_timers: Dict[str, Timer] = {}

    def add_timer(self, name: str, interval: float, callback: Callable) -> Timer:
        """Register a managed interval timer."""
        timer = self.set_interval(interval, callback)
        self._managed_timers[name] = timer
        return timer

    def stop_timer(self, name: str) -> None:
        """Stop and remove a named timer."""
        timer = self._managed_timers.pop(name, None)
        if timer:
            timer.stop()

    def on_unmount(self) -> None:
        """Stop all managed timers on unmount."""
        for timer in self._managed_timers.values():
            timer.stop()
        self._managed_timers.clear()
