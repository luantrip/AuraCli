"""History policy for headless Paint editing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from textual.geometry import Offset, Region

from .action import PaintAction
from .ansi_art_document import AnsiArtDocument


@dataclass(slots=True)
class HistoryOutcome:
    """Result of moving one step through document history."""

    changed: bool
    layer_state_restored: bool = False


@dataclass(slots=True)
class PaintHistory:
    """Own undo/redo stacks and the symmetric state-swap algorithm."""

    undos: list[PaintAction] = field(default_factory=list)
    redos: list[PaintAction] = field(default_factory=list)

    def clear(self) -> None:
        self.undos.clear()
        self.redos.clear()

    def add(self, action: PaintAction) -> None:
        self.redos.clear()
        self.undos.append(action)

    def undo(
        self,
        document: AnsiArtDocument,
        *,
        full_region: Region,
        cursor_position: Offset | None = None,
        layer_stack: Any = None,
        inverse_name: Callable[[str], str] = lambda name: name,
    ) -> HistoryOutcome:
        return self._swap(
            self.undos,
            self.redos,
            document,
            full_region=full_region,
            cursor_position=cursor_position,
            layer_stack=layer_stack,
            inverse_name=inverse_name,
        )

    def redo(
        self,
        document: AnsiArtDocument,
        *,
        full_region: Region,
        cursor_position: Offset | None = None,
        layer_stack: Any = None,
        inverse_name: Callable[[str], str] = lambda name: name,
    ) -> HistoryOutcome:
        return self._swap(
            self.redos,
            self.undos,
            document,
            full_region=full_region,
            cursor_position=cursor_position,
            layer_stack=layer_stack,
            inverse_name=inverse_name,
        )

    @staticmethod
    def _swap(
        source: list[PaintAction],
        destination: list[PaintAction],
        document: AnsiArtDocument,
        *,
        full_region: Region,
        cursor_position: Offset | None,
        layer_stack: Any,
        inverse_name: Callable[[str], str],
    ) -> HistoryOutcome:
        if not source:
            return HistoryOutcome(changed=False)

        action = source.pop()
        inverse_region = full_region if action.is_full_update else action.region
        inverse = PaintAction(inverse_name(action.name), inverse_region)
        inverse.is_full_update = action.is_full_update
        inverse.update(document)
        inverse.cursor_position_before = cursor_position
        if layer_stack is not None:
            inverse.update_layer_state(layer_stack)

        changed = action.undo(document)
        layer_restored = bool(
            layer_stack is not None and action.restore_layer_state(layer_stack)
        )
        if changed:
            destination.append(inverse)
        else:
            source.append(action)
        return HistoryOutcome(changed, layer_restored)


__all__ = ["HistoryOutcome", "PaintHistory"]
