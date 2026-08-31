"""
Edit history tracking for Aura CLI.

Provides tracking and querying of edit history,
enabling review and audit capabilities.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from aura_cli.application.editing import (
    EditOperation,
    EditRecord,
    create_edit_record,
    summarize_edit_history,
)
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class EditHistory:
    """
    Edit history manager.

    Features:
    - History storage
    - Query by file, date, etc.
    - File persistence
    - Edit statistics
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        *,
        presenter: Optional[Callable[[Sequence[EditRecord]], None]] = None,
    ):
        """Initialise the edit history."""
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            from aura_cli.core.paths import get_aura_home

            aura_dir = get_aura_home()
            self.storage_path = aura_dir / "edit_history"

        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.records: List[EditRecord] = []
        self._presenter = presenter

        self._load_history()

        logger.info(
            f"EditHistory initialized "
            f"(storage: {self.storage_path}, records: {len(self.records)})"
        )

    def add_record(
        self,
        operation: EditOperation,
        success: bool = True,
        backup_path: Optional[str] = None,
    ) -> str:
        """Add an edit history record."""
        record = create_edit_record(
            operation,
            success=success,
            backup_path=backup_path,
        )

        self.records.append(record)

        self._save_history()

        logger.debug(f"Registro de edição {record.id} adicionado")

        return record.id

    def get_history(
        self, file_path: Optional[str] = None, limit: int = 50
    ) -> List[EditRecord]:
        """Return the full edit history."""
        records = self.records.copy()

        if file_path:
            records = [r for r in records if r.file_path == file_path]

        records.sort(key=lambda r: r.timestamp, reverse=True)

        return records[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Return edit history statistics as a dict."""
        return summarize_edit_history(self.records)

    def display_history(self, file_path: Optional[str] = None, limit: int = 20) -> None:
        """Display the edit history in the console."""
        records = self.get_history(file_path, limit)
        if self._presenter is not None:
            self._presenter(records)

    def _save_history(self) -> None:
        """Persist the edit history to disk."""
        file_path = self.storage_path / "history.json"

        try:
            data = {"records": [r.to_dict() for r in self.records]}

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Error saving history: {e}", exc_info=True)

    def _load_history(self) -> None:
        """Load the edit history from disk."""
        file_path = self.storage_path / "history.json"

        if not file_path.exists():
            return

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            self.records = [EditRecord.from_dict(r) for r in data.get("records", [])]

            logger.info(f"History loaded: {len(self.records)} records")
        except Exception as e:
            logger.warning(f"Error loading history: {e}", exc_info=True)
