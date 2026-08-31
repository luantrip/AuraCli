"""Modal layout primitives (compose/decompose building blocks)."""

from __future__ import annotations

from textual.widgets import Static


class ModalTitle(Static):
    """Standard modal header line."""

    def __init__(self, title: str, **kwargs) -> None:
        super().__init__(title, classes="settings-header modal-frame-title", **kwargs)


# Re-export vertical shell — use: ``with ModalFrame(): yield widgets...``
from textual.containers import Vertical


class ModalFrame(Vertical):
    """Vertical container with shared modal frame styling."""

    def __init__(self, *args, **kwargs) -> None:
        classes = kwargs.pop("classes", "")
        merged = "aura-modal-frame"
        if classes:
            merged = f"{merged} {classes}"
        super().__init__(*args, classes=merged, **kwargs)
