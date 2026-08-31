"""Notebook Backup System.

Provides automatic periodic backups of the Notebook with restore support.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class NotebookBackupManager:
    """Automatic Notebook backup manager."""

    def __init__(self, notebook_path: Path, backup_dir: Optional[Path] = None):
        """Initialise the notebook backup manager."""
        self.notebook_path = notebook_path
        self.backup_dir = backup_dir or notebook_path.parent / "notebooks_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.backup_interval_pages = 10  # Backup every 10 pages
        self.max_backups = 10  # Keep last 10 backups
        self._last_backup_page_count = 0

    def should_backup(self, current_page_count: int) -> bool:
        """Return True if a backup should be created now."""
        pages_since_backup = current_page_count - self._last_backup_page_count
        return pages_since_backup >= self.backup_interval_pages

    def create_backup(self, session_id: str) -> Optional[Path]:
        """Create a backup of the current notebook."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{session_id}_{timestamp}.tar.gz"
            backup_path = self.backup_dir / backup_name
            import tarfile

            with tarfile.open(backup_path, "w:gz") as tar:
                if self.notebook_path.exists():
                    tar.add(self.notebook_path, arcname=session_id)

            metadata = {
                "session_id": session_id,
                "timestamp": timestamp,
                "backup_path": str(backup_path),
                "page_count": len(list(self.notebook_path.glob("pagina_*.txt")))
                if self.notebook_path.exists()
                else 0,
            }

            metadata_path = self.backup_dir / f"{backup_name}.meta.json"
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            self._last_backup_page_count = int(metadata["page_count"])  # type: ignore[call-overload]
            self._cleanup_old_backups()

            logger.info(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available notebook backups."""
        backups = []

        for meta_file in self.backup_dir.glob("*.meta.json"):
            try:
                metadata = json.loads(meta_file.read_text(encoding="utf-8"))
                backup_path = Path(metadata["backup_path"])

                if backup_path.exists():
                    backups.append(
                        {
                            "backup_path": backup_path,
                            "metadata": metadata,
                            "size": backup_path.stat().st_size,
                            "age_days": (
                                datetime.now()
                                - datetime.strptime(
                                    metadata["timestamp"], "%Y%m%d_%H%M%S"
                                )
                            ).days,
                        }
                    )
            except Exception as e:
                logger.warning(f"Error reading backup metadata {meta_file}: {e}")

        backups.sort(key=lambda x: x["metadata"]["timestamp"], reverse=True)
        return backups

    def restore_backup(
        self, backup_path: Path, target_path: Optional[Path] = None
    ) -> bool:
        """Restore a backup to the target path."""
        try:
            target = target_path or self.notebook_path
            if target.exists():
                current_backup = self.create_backup("pre_restore")
                if current_backup:
                    logger.info(
                        f"Current state backup created before restore: {current_backup}"
                    )

            import tarfile

            base_dir = target.parent.resolve()
            with tarfile.open(backup_path, "r:gz") as tar:
                # Guard against path traversal (CVE-2007-4559 / zip-slip):
                # reject any member that would resolve outside base_dir.
                for member in tar.getmembers():
                    member_path = (base_dir / member.name).resolve()
                    if member_path != base_dir and base_dir not in member_path.parents:
                        raise ValueError(
                            f"Membro de backup inseguro (path traversal): {member.name}"
                        )
                    if member.issym() or member.islnk():
                        raise ValueError(
                            f"Membro de backup inseguro (link): {member.name}"
                        )
                # Members are validated against base_dir above and rejected if they
                # escape it or are sym/hard links.
                tar.extractall(base_dir)  # nosec B202

            logger.info(f"Backup restaurado: {backup_path} -> {target}")
            return True

        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False

    def _cleanup_old_backups(self) -> None:
        """Remove old backups, keeping only the most recent N."""
        backups = self.list_backups()

        if len(backups) <= self.max_backups:
            return

        to_remove = backups[self.max_backups :]
        for backup in to_remove:
            try:
                backup["backup_path"].unlink()
                meta_file = self.backup_dir / f"{backup['backup_path'].name}.meta.json"
                if meta_file.exists():
                    meta_file.unlink()
                logger.debug(f"Old backup removed: {backup['backup_path']}")
            except Exception as e:
                logger.warning(f"Error removing old backup: {e}")


def get_backup_manager(notebook_path: Path) -> NotebookBackupManager:
    """Get backup manager for a notebook path."""
    return NotebookBackupManager(notebook_path)
