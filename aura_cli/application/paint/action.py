"""Undoable, widget-independent state transitions for Paint documents."""

from __future__ import annotations

from typing import Any

from textual.geometry import Offset, Region

from .ansi_art_document import AnsiArtDocument, Selection


class PaintAction:
    """Capture document and layer state required to undo one Paint operation."""

    def __init__(self, name: str, region: Region | None = None) -> None:
        self.name = name
        self.region = region
        self.is_full_update = False
        self.sub_image_before: AnsiArtDocument | None = None
        self.cursor_position_before: Offset | None = None
        self.layer_stack_state: dict[str, Any] | None = None
        self.affected_layers: list[int] = []
        self.frame_index = 0
        self.timeline_state: dict[str, Any] | None = None

    def update(self, document: AnsiArtDocument) -> None:
        """Capture the current document region as the before-state."""
        if self.region is None:
            raise ValueError("PaintAction.update requires a region")
        self.sub_image_before = AnsiArtDocument(self.region.width, self.region.height)
        self.sub_image_before.copy_region(document, self.region)

    def update_layer_state(self, layer_stack: Any) -> None:
        """Capture a serializable layer stack when the host provides one."""
        if hasattr(layer_stack, "to_dict"):
            self.layer_stack_state = layer_stack.to_dict()

    def undo(self, target_document: AnsiArtDocument) -> bool:
        """Restore the captured state and report whether restoration occurred."""
        if self.sub_image_before is None or self.region is None:
            return False
        if self.is_full_update:
            target_document.copy(self.sub_image_before)
        else:
            target_document.copy_region(
                self.sub_image_before, target_region=self.region
            )
        if self.cursor_position_before is not None:
            target_document.selection = Selection(
                Region.from_offset(self.cursor_position_before, (1, 1))
            )
            target_document.selection.textbox_mode = True
            target_document.selection.cursor_mode = True
            target_document.selection.copy_from_document(target_document)
        return True

    def restore_layer_state(self, layer_stack: Any) -> bool:
        """Restore serialized layers when supported by the concrete stack."""
        if self.layer_stack_state is None or not hasattr(layer_stack, "from_dict"):
            return False
        try:
            layer_stack.from_dict(self.layer_stack_state)
        except (KeyError, TypeError, ValueError):
            return False
        return True


# Historical public name retained while consumers migrate.
Action = PaintAction

__all__ = ["Action", "PaintAction"]
