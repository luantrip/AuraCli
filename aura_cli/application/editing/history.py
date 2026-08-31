"""Edit history records and aggregation policies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Optional
import uuid

from .planning import EditOperation


@dataclass
class EditRecord:
    id: str
    timestamp: datetime
    file_path: str
    description: str
    operation_type: str = "edit"
    old_content_preview: str = ""
    new_content_preview: str = ""
    success: bool = True
    backup_path: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = vars(self).copy()
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EditRecord:
        normalized = dict(data)
        normalized["timestamp"] = datetime.fromisoformat(normalized["timestamp"])
        return cls(**normalized)


def create_edit_record(
    operation: EditOperation,
    *,
    success: bool = True,
    backup_path: Optional[str] = None,
    now: datetime | None = None,
    record_id: str | None = None,
    preview_limit: int = 100,
) -> EditRecord:
    """Create a bounded audit record from an edit operation."""
    if preview_limit < 0:
        raise ValueError("Edit preview limit cannot be negative")

    def preview(content: str) -> str:
        return (
            f"{content[:preview_limit]}..." if len(content) > preview_limit else content
        )

    return EditRecord(
        id=record_id or str(uuid.uuid4())[:8],
        timestamp=now or datetime.now(),
        file_path=operation.file_path,
        description=operation.description,
        old_content_preview=preview(operation.old_content),
        new_content_preview=preview(operation.new_content),
        success=success,
        backup_path=backup_path,
    )


def summarize_edit_history(records: Iterable[EditRecord]) -> dict[str, Any]:
    """Aggregate edit outcomes without persistence or presentation concerns."""
    items = list(records)
    edits_per_file: dict[str, int] = {}
    for record in items:
        edits_per_file[record.file_path] = edits_per_file.get(record.file_path, 0) + 1
    successful = sum(1 for record in items if record.success)
    return {
        "total_edits": len(items),
        "successful_edits": successful,
        "failed_edits": len(items) - successful,
        "unique_files": len(edits_per_file),
        "edits_per_file": edits_per_file,
    }
