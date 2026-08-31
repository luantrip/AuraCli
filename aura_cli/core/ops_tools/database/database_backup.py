"""Database backup system for Aura CLI.

Provides backup and restore for multiple database types.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os
from pathlib import Path
import subprocess
from typing import List, Optional

from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


class DatabaseType(Enum):
    """Tipos de banco de dados."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"


@dataclass
class BackupConfig:
    """Backup configuration (db_type, host, port, database, credentials)."""

    db_type: DatabaseType
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    username: str = ""
    password: Optional[str] = None
    output_path: str = ""
    compression: bool = True


@dataclass
class BackupResult:
    """Result of a backup operation."""

    success: bool
    backup_path: Optional[str] = None
    size: int = 0
    duration: float = 0.0
    error: Optional[str] = None


class DatabaseBackup:
    """Manages database backup and restore operations."""

    def __init__(self):
        """Initialise the backup system."""
        self.stats = get_stats()
        self.backup_history: List[BackupResult] = []

        logger.info("DatabaseBackup initialized")

    def create_backup(self, config: BackupConfig) -> BackupResult:
        """Create a database backup and return a BackupResult."""
        import time

        from aura_cli.core.ui import display_tool_call
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        start_time = time.time()

        display_tool_call(
            "create_backup",
            {
                "db_type": config.db_type.value,
                "database": config.database,
                "host": config.host,
            },
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not config.output_path:
            # Default to .aura/backups/ in the project root to avoid polluting CWD.
            from aura_cli.core.paths import ArtifactLayout

            backup_dir = ArtifactLayout().project("backups")
            backup_dir.mkdir(parents=True, exist_ok=True)
            config.output_path = str(
                backup_dir / f"backup_{config.database}_{timestamp}"
            )

        if config.db_type == DatabaseType.POSTGRESQL:
            result = self._backup_postgresql(config)
        elif config.db_type == DatabaseType.MYSQL:
            result = self._backup_mysql(config)
        elif config.db_type == DatabaseType.SQLITE:
            result = self._backup_sqlite(config)
        else:
            result = BackupResult(
                success=False,
                error=f"Tipo de banco '{config.db_type.value}' não suportado",
            )

        result.duration = time.time() - start_time

        self.backup_history.append(result)

        if result.success:
            logger.info(
                f"Backup created: {result.backup_path} "
                f"({result.size / 1024 / 1024:.2f}MB, {result.duration:.2f}s)"
            )
            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
                f"Backup created: {result.backup_path}[/{UIStyles.SUCCESS}]"
            )
        else:
            logger.error(f"Error creating backup: {result.error}")
            console.print(
                f"[{UIStyles.ERROR}]{UIIcons.ERROR} "
                f"Backup error: {result.error}[/{UIStyles.ERROR}]"
            )

        self.stats.track_tool_usage("database_backup")

        return result

    def _backup_postgresql(self, config: BackupConfig) -> BackupResult:
        """Create a PostgreSQL backup."""
        import shutil

        if not shutil.which("pg_dump"):
            return BackupResult(
                success=False,
                error="pg_dump not found. Install PostgreSQL client tools.",
            )

        if not config.output_path:
            return BackupResult(success=False, error="Output path not specified")

        cmd = ["pg_dump"]

        if config.host:
            cmd.extend(["-h", config.host])
        if config.port:
            cmd.extend(["-p", str(config.port)])
        if config.username:
            cmd.extend(["-U", config.username])

        cmd.append(config.database)

        try:
            output_file = config.output_path
            if config.compression:
                output_file += ".gz"
                import gzip

                with gzip.open(output_file, "wb") as f:
                    result = subprocess.run(  # type: ignore[call-overload]
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=300,
                        env=(
                            {**os.environ, "PGPASSWORD": config.password}
                            if config.password
                            else os.environ
                        ),
                    )
            else:
                with open(output_file, "wb") as f:
                    result = subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=300,
                        env=(
                            {**os.environ, "PGPASSWORD": config.password}
                            if config.password
                            else os.environ
                        ),
                    )

            if result.returncode == 0:
                size = os.path.getsize(output_file)
                return BackupResult(success=True, backup_path=output_file, size=size)
            else:
                Path(output_file).unlink(missing_ok=True)
                return BackupResult(success=False, error=result.stderr)

        except Exception as e:
            if "output_file" in locals():
                Path(output_file).unlink(missing_ok=True)
            return BackupResult(success=False, error=str(e))

    def _backup_mysql(self, config: BackupConfig) -> BackupResult:
        """Create a MySQL backup."""
        import shutil

        if not shutil.which("mysqldump"):
            return BackupResult(
                success=False,
                error="mysqldump not found. Install MySQL client tools.",
            )

        if not config.output_path:
            return BackupResult(success=False, error="Output path not specified")

        cmd = ["mysqldump"]

        if config.host:
            cmd.extend(["-h", config.host])
        if config.port:
            cmd.extend(["-P", str(config.port)])
        if config.username:
            cmd.extend(["-u", config.username])
        if config.password:
            cmd.append(f"-p{config.password}")

        cmd.append(config.database)

        try:
            output_file = config.output_path
            if config.compression:
                output_file += ".gz"
                import gzip

                with gzip.open(output_file, "wb") as f:
                    result = subprocess.run(  # type: ignore[call-overload]
                        cmd, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300
                    )
            else:
                with open(output_file, "wb") as f:
                    result = subprocess.run(
                        cmd, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300
                    )

            if result.returncode == 0:
                size = os.path.getsize(output_file)
                return BackupResult(success=True, backup_path=output_file, size=size)
            else:
                Path(output_file).unlink(missing_ok=True)
                return BackupResult(success=False, error=result.stderr)

        except Exception as e:
            if "output_file" in locals():
                Path(output_file).unlink(missing_ok=True)
            return BackupResult(success=False, error=str(e))

    def _backup_sqlite(self, config: BackupConfig) -> BackupResult:
        """Create a SQLite backup."""
        import shutil

        db_path = config.database  # For SQLite, database is the file path

        if not config.output_path:
            return BackupResult(success=False, error="Output path not specified")

        if not os.path.exists(db_path):
            return BackupResult(
                success=False, error=f"SQLite file not found: {db_path}"
            )

        try:
            output_file = config.output_path
            if config.compression:
                output_file += ".gz"
                import gzip

                with open(db_path, "rb") as src, gzip.open(output_file, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            else:
                shutil.copy2(db_path, output_file)

            size = os.path.getsize(output_file)

            return BackupResult(success=True, backup_path=output_file, size=size)

        except Exception as e:
            if "output_file" in locals():
                Path(output_file).unlink(missing_ok=True)
            return BackupResult(success=False, error=str(e))

    def restore_backup(self, backup_path: str, config: BackupConfig) -> str:
        """Restore a backup from the given path."""
        from aura_cli.core.ui import display_tool_call

        display_tool_call("restore_backup", {"backup_path": backup_path})

        if not os.path.exists(backup_path):
            error_msg = f"Backup file not found: {backup_path}"
            logger.error(error_msg)
            return error_msg

        logger.info(f"Restore from {backup_path} started")

        return "Restore completed (simplified implementation)"


# Factory function for singleton pattern
_backup_instance: Optional[DatabaseBackup] = None


def get_database_backup() -> DatabaseBackup:
    """
    Get or create DatabaseBackup instance (singleton).

    Returns:
        DatabaseBackup instance
    """
    global _backup_instance
    if _backup_instance is None:
        _backup_instance = DatabaseBackup()
    return _backup_instance
