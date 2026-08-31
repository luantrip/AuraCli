"""Edit executor with automatic rollback.

Provides safe edit execution with backup creation and rollback on error.
"""

from dataclasses import dataclass
from datetime import datetime
import os
import shutil
import threading
from typing import Dict, List, Optional

from rich.console import Console

from aura_cli.core.edit.edit_planner import EditOperation
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()

_file_locks: Dict[str, threading.Lock] = {}
_file_locks_lock = threading.Lock()


def _get_file_lock(file_path: str) -> threading.Lock:
    """Get or create a lock for a specific file.

    Args:
        file_path: Path to the file.

    Returns:
        Lock object for the file.
    """
    abs_path = os.path.abspath(file_path)
    with _file_locks_lock:
        if abs_path not in _file_locks:
            _file_locks[abs_path] = threading.Lock()
        return _file_locks[abs_path]


@dataclass
class ExecutionResult:
    """Result of an edit operation execution."""

    success: bool
    file_path: str
    backup_path: Optional[str] = None
    rolled_back: bool = False
    error: Optional[str] = None


class EditExecutor:
    """Edit executor with automatic backup and rollback."""

    def __init__(self, auto_backup: bool = True):
        """Initialise the executor."""
        self.auto_backup = auto_backup
        self.stats = get_stats()
        self.backups: Dict[str, str] = {}

        logger.info(f"EditExecutor initialized (auto_backup: {auto_backup})")

    def execute(
        self, operation: EditOperation, validate_after: bool = True
    ) -> ExecutionResult:
        """Execute an edit operation and return the result."""
        from aura_cli.core.ui import display_tool_call
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        display_tool_call(
            "edit_executor_execute",
            {"file_path": operation.file_path, "description": operation.description},
        )

        backup_path = None
        file_lock = _get_file_lock(operation.file_path)

        with file_lock:
            try:
                if self.auto_backup:
                    backup_path = self._create_backup(operation.file_path)
                    self.backups[operation.file_path] = backup_path

                with open(operation.file_path, encoding="utf-8") as f:
                    content = f.read()

                if operation.old_content not in content:
                    error_msg = (
                        f"Content to replace not found in {operation.file_path}"
                    )
                    logger.error(error_msg)
                    return ExecutionResult(
                        success=False,
                        file_path=operation.file_path,
                        backup_path=backup_path,
                        error=error_msg,
                    )

                new_content = content.replace(
                    operation.old_content, operation.new_content, 1
                )

                with open(operation.file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                if (
                    validate_after
                    and operation.file_path.endswith(".py")
                    and not self._validate_python_syntax(new_content)
                ):
                    if backup_path:
                        self._rollback(operation.file_path, backup_path)
                    error_msg = "Sintaxe inválida após edição, rollback realizado"
                    logger.error(error_msg)
                    return ExecutionResult(
                        success=False,
                        file_path=operation.file_path,
                        backup_path=backup_path,
                        rolled_back=True,
                        error=error_msg,
                    )
                logger.info(f"File {operation.file_path} edited successfully")

                self.stats.track_tool_usage("edit_executor")

                success_style = UIStyles.safe_style("SUCCESS", "green")
                console.print(
                    f"[{success_style}]{UIIcons.SUCCESS} "
                    f"Arquivo {operation.file_path} editado[/{success_style}]"
                )

                return ExecutionResult(
                    success=True, file_path=operation.file_path, backup_path=backup_path
                )

            except Exception as e:
                error_msg = f"Error editing {operation.file_path}: {e}"
                logger.error(error_msg, exc_info=True)

                rolled_back = False
                if backup_path and os.path.exists(backup_path):
                    self._rollback(operation.file_path, backup_path)
                    rolled_back = True

                return ExecutionResult(
                    success=False,
                    file_path=operation.file_path,
                    backup_path=backup_path,
                    rolled_back=rolled_back,
                    error=error_msg,
                )

    def _create_backup(self, file_path: str) -> str:
        """Create a backup of a file before editing."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{file_path}.backup.{timestamp}"

        shutil.copy2(file_path, backup_path)

        logger.debug(f"Backup created: {backup_path}")

        return backup_path

    def _rollback(self, file_path: str, backup_path: str) -> None:
        """Roll back a file to its backup."""
        try:
            shutil.copy2(backup_path, file_path)
            logger.info(f"Rollback realizado: {file_path} restaurado de {backup_path}")
        except Exception as e:
            logger.error(f"Error during rollback: {e}", exc_info=True)

    def _validate_python_syntax(self, code: str) -> bool:
        """Return True if the Python code has valid syntax."""
        try:
            import ast

            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def cleanup_backups(self, keep_recent: int = 5) -> None:
        """Remove old backups, keeping only the most recent N."""
        backups_by_file: Dict[str, List[str]] = {}
        for file_path, backup_path in self.backups.items():
            if file_path not in backups_by_file:
                backups_by_file[file_path] = []
            backups_by_file[file_path].append(backup_path)

        for backups in backups_by_file.values():
            if len(backups) > keep_recent:
                backups_sorted = sorted(backups, reverse=True)
                to_remove = backups_sorted[keep_recent:]

                for backup in to_remove:
                    try:
                        os.remove(backup)
                        logger.debug(f"Old backup removed: {backup}")
                    except Exception as e:
                        logger.warning(f"Error removing backup {backup}: {e}")
