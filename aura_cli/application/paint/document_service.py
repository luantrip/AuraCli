"""Widget-independent lifecycle and persistence for Paint documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from rich.style import Style


class PaintDocument(Protocol):
    width: int
    height: int

    def encode_to_format(self, output_format: str) -> bytes: ...


@dataclass(frozen=True, slots=True)
class PaintCellSample:
    character: str
    foreground: str
    background: str


def sample_document_cell(document: Any, x: int, y: int) -> PaintCellSample | None:
    """Return a normalized cell sample, or ``None`` outside the document."""
    if x < 0 or y < 0 or x >= document.width or y >= document.height:
        return None
    style: Style = document.st[y][x]
    if style.color is None or style.bgcolor is None:
        return None
    return PaintCellSample(
        character=document.ch[y][x],
        foreground=style.color.get_truecolor().hex,
        background=style.bgcolor.get_truecolor().hex,
    )


class PaintDocumentService:
    """Own the active document without knowing its UI implementation."""

    def __init__(self, document: PaintDocument | None = None) -> None:
        self.document = document

    def replace(self, document: PaintDocument) -> None:
        self.document = document

    def save(self, file_path: str | Path, output_format: str = "ans") -> dict[str, Any]:
        if self.document is None:
            return {"success": False, "error": "Paint document is unavailable"}
        target = Path(file_path)
        normalized_format = (
            "ANSI" if output_format.upper() == "ANS" else output_format.upper()
        )
        try:
            content = self.document.encode_to_format(normalized_format)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            return {
                "success": True,
                "file_path": str(target.absolute()),
                "format": output_format,
                "size": len(content),
            }
        except Exception as exc:
            return {"success": False, "error": str(exc), "file_path": str(target)}
