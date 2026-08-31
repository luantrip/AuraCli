"""Notebook Checksum System — integrity verification.

Detects corruption via SHA256 checksums.
"""

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Dict

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class NotebookChecksumManager:
    """Manages integrity checksums for notebook pages."""

    def __init__(self, notebook_path: Path):
        """Initialise the checksum manager."""
        self.notebook_path = notebook_path
        self.checksum_file = notebook_path / ".checksums.json"
        self._lock = threading.RLock()

    def calculate_checksum(self, content: str) -> str:
        """Calculate the SHA256 checksum of the content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def save_checksum(self, page_path: str, checksum: str) -> None:
        """Save the checksum for a notebook page."""
        with self._lock:
            checksums = self.load_checksums()
            checksums[page_path] = {
                "checksum": checksum,
                "timestamp": datetime.now().isoformat(),
            }
            self._save_checksums(checksums)

    def verify_page(self, page_path: str, content: str) -> bool:
        """Verify the checksum for a notebook page."""
        checksums = self.load_checksums()
        stored = checksums.get(page_path)

        if not stored:
            checksum = self.calculate_checksum(content)
            self.save_checksum(page_path, checksum)
            return True

        current_checksum = self.calculate_checksum(content)
        if current_checksum != stored["checksum"]:
            logger.warning(
                f"Invalid checksum for {page_path}: expected {stored['checksum'][:8]}..., got {current_checksum[:8]}..."
            )
            return False

        return True

    def load_checksums(self) -> Dict[str, Dict[str, str]]:
        """Load saved checksums from disk."""
        if not self.checksum_file.exists():
            return {}

        try:
            return json.loads(self.checksum_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Error loading checksums: {e}")
            return {}

    def _save_checksums(self, checksums: Dict[str, Dict[str, str]]) -> None:
        """Persist all checksums to disk."""
        temporary_path = None
        try:
            self.checksum_file.parent.mkdir(parents=True, exist_ok=True)
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.checksum_file.name}.",
                suffix=".tmp",
                dir=self.checksum_file.parent,
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                json.dump(checksums, handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self.checksum_file)
            temporary_path = None
        except Exception as e:
            logger.error(f"Error saving checksums: {e}")
            raise OSError(f"Failed to persist checksums: {self.checksum_file}") from e
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def verify_all_pages(self) -> Dict[str, bool]:
        """Verify checksums for all notebook pages."""
        results = {}

        for page_file in self.notebook_path.glob("pagina_*.txt"):
            try:
                content = page_file.read_text(encoding="utf-8")
                results[str(page_file)] = self.verify_page(str(page_file), content)
            except Exception as e:
                logger.error(f"Error verifying page {page_file}: {e}")
                results[str(page_file)] = False

        return results


def get_checksum_manager(notebook_path: Path) -> NotebookChecksumManager:
    """Get checksum manager for a notebook path."""
    return NotebookChecksumManager(notebook_path)
