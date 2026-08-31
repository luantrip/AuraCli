"""Database migration system for Aura CLI.

Provides schema migration management,
versioning and application.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

if TYPE_CHECKING:
    from aura_cli.core.ops_tools.database.query_executor import (
        DatabaseConnection,
        QueryExecutor,
    )

logger = get_logger(__name__)
console = Console()


class MigrationStatus(Enum):
    """Status of a database migration."""

    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    """Represents a single database migration (id, name, sql, checksum)."""

    id: str
    version: str
    name: str
    up_sql: str
    down_sql: str
    status: MigrationStatus = MigrationStatus.PENDING
    applied_at: Optional[datetime] = None


class DatabaseMigration:
    """Database migration manager."""

    MIGRATIONS_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS _aura_migrations (
        id TEXT PRIMARY KEY,
        version TEXT NOT NULL,
        name TEXT NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """

    def __init__(self, migrations_dir: str = "migrations") -> None:
        """Initialise the migration manager."""
        self.migrations_dir = migrations_dir
        self.migrations: Dict[str, Migration] = {}
        self.stats = get_stats()

        os.makedirs(migrations_dir, exist_ok=True)
        self._load_migrations()

        logger.info(f"DatabaseMigration initialized (directory: {migrations_dir})")

    def _get_executor(self) -> "QueryExecutor":
        """Return or create the SQL executor."""
        from aura_cli.core.ops_tools.database.query_executor import QueryExecutor

        return QueryExecutor()

    def _ensure_migrations_table(self, connection: "DatabaseConnection") -> None:
        """Ensure the migration control table exists."""
        executor = self._get_executor()

        if connection.db_type.lower() == "mysql":
            sql = """
            CREATE TABLE IF NOT EXISTS _aura_migrations (
                id VARCHAR(255) PRIMARY KEY,
                version VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        else:
            sql = self.MIGRATIONS_TABLE_SQL

        executor.execute_query(sql, connection)

    def _get_applied_migrations(self, connection: "DatabaseConnection") -> List[str]:
        """Return the list of already-applied migration IDs."""
        executor = self._get_executor()
        result = executor.execute_query("SELECT id FROM _aura_migrations", connection)

        if result.success:
            return [row["id"] for row in result.rows]
        return []

    def _record_migration(
        self, migration: Migration, connection: "DatabaseConnection"
    ) -> None:
        """Record a migration as applied in the control table."""
        executor = self._get_executor()

        if connection.db_type.lower() == "sqlite":
            sql = "INSERT INTO _aura_migrations (id, version, name) VALUES (?, ?, ?)"
            params: Any = (migration.id, migration.version, migration.name)
        else:
            sql = "INSERT INTO _aura_migrations (id, version, name) VALUES (%s, %s, %s)"
            params = [migration.id, migration.version, migration.name]

        executor.execute_query(sql, connection, params)

    def _remove_migration_record(
        self, migration_id: str, connection: "DatabaseConnection"
    ) -> None:
        """Remove a migration record from the control table."""
        executor = self._get_executor()

        if connection.db_type.lower() == "sqlite":
            sql = "DELETE FROM _aura_migrations WHERE id = ?"
            params: Any = (migration_id,)
        else:
            sql = "DELETE FROM _aura_migrations WHERE id = %s"
            params = [migration_id]

        executor.execute_query(sql, connection, params)

    def create_migration(self, name: str, up_sql: str, down_sql: str) -> Migration:
        """Create a new migration file."""
        import uuid

        version = datetime.now().strftime("%Y%m%d%H%M%S")
        migration_id = str(uuid.uuid4())[:8]

        migration = Migration(
            id=migration_id,
            version=version,
            name=name,
            up_sql=up_sql,
            down_sql=down_sql,
        )

        self.migrations[migration_id] = migration
        self._save_migration(migration)

        logger.info(f"Migração '{name}' (v{version}) criada")

        return migration

    def apply_migration(
        self, migration_id: str, connection_string: str, db_type: str = "sqlite"
    ) -> str:
        """Apply a single migration by ID."""
        from aura_cli.core.ops_tools.database.query_executor import (
            DatabaseConnection,
        )
        from aura_cli.core.ui import display_tool_call
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        display_tool_call("apply_migration", {"migration_id": migration_id})

        if migration_id not in self.migrations:
            error_msg = f"Migração {migration_id} não encontrada"
            logger.error(error_msg)
            return error_msg

        migration = self.migrations[migration_id]

        # Create connection
        connection = DatabaseConnection(
            db_type=db_type,
            database=connection_string,
        )

        try:
            self._ensure_migrations_table(connection)
            applied = self._get_applied_migrations(connection)
            if migration_id in applied:
                return f"Migração {migration_id} já está aplicada"

            executor = self._get_executor()
            statements = [s.strip() for s in migration.up_sql.split(";") if s.strip()]

            for statement in statements:
                result = executor.execute_query(statement, connection)
                if not result.success:
                    migration.status = MigrationStatus.FAILED
                    error_msg = f"Error applying migration: {result.error}"
                    logger.error(error_msg)
                    return error_msg

            self._record_migration(migration, connection)

            migration.status = MigrationStatus.APPLIED
            migration.applied_at = datetime.now()

            logger.info(f"Migração {migration_id} aplicada com sucesso")

            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
                f"Migração '{migration.name}' aplicada[/{UIStyles.SUCCESS}]"
            )

            self.stats.track_tool_usage("database_migration")

            return "Migração aplicada com sucesso"

        except Exception as e:
            migration.status = MigrationStatus.FAILED
            error_msg = f"Error applying migration: {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def rollback_migration(
        self, migration_id: str, connection_string: str, db_type: str = "sqlite"
    ) -> str:
        """Roll back a migration by ID."""
        from aura_cli.core.ops_tools.database.query_executor import (
            DatabaseConnection,
        )
        from aura_cli.core.ui import display_tool_call
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        display_tool_call("rollback_migration", {"migration_id": migration_id})

        if migration_id not in self.migrations:
            return f"Migração {migration_id} não encontrada"

        migration = self.migrations[migration_id]

        connection = DatabaseConnection(
            db_type=db_type,
            database=connection_string,
        )

        try:
            applied = self._get_applied_migrations(connection)
            if migration_id not in applied:
                return "Migração não está aplicada, não pode ser revertida"

            executor = self._get_executor()

            statements = [s.strip() for s in migration.down_sql.split(";") if s.strip()]

            for statement in statements:
                result = executor.execute_query(statement, connection)
                if not result.success:
                    error_msg = f"Error reverting migration: {result.error}"
                    logger.error(error_msg)
                    return error_msg

            self._remove_migration_record(migration_id, connection)

            migration.status = MigrationStatus.ROLLED_BACK
            migration.applied_at = None

            logger.info(f"Migração {migration_id} revertida com sucesso")

            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
                f"Migração '{migration.name}' revertida[/{UIStyles.SUCCESS}]"
            )

            return "Migração revertida com sucesso"

        except Exception as e:
            error_msg = f"Error reverting migration: {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def apply_all_pending(self, connection_string: str, db_type: str = "sqlite") -> str:
        """Apply all pending migrations in order."""
        from aura_cli.core.ops_tools.database.query_executor import DatabaseConnection

        connection = DatabaseConnection(
            db_type=db_type,
            database=connection_string,
        )

        self._ensure_migrations_table(connection)
        applied = self._get_applied_migrations(connection)

        pending = [
            m
            for m in sorted(self.migrations.values(), key=lambda m: m.version)
            if m.id not in applied
        ]

        if not pending:
            return "Nenhuma migração pendente"

        applied_count = 0
        for migration in pending:
            result = self.apply_migration(migration.id, connection_string, db_type)
            if "sucesso" in result.lower():
                applied_count += 1
            else:
                return f"Erro após aplicar {applied_count} migrações: {result}"

        return f"{applied_count} migrações aplicadas com sucesso"

    def _load_migrations(self) -> None:
        """Load migrations from the migrations directory."""
        if not os.path.exists(self.migrations_dir):
            return

        for filename in os.listdir(self.migrations_dir):
            if filename.endswith(".sql"):
                filepath = os.path.join(self.migrations_dir, filename)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()

                    migration = self._parse_migration_file(filename, content)
                    if migration:
                        self.migrations[migration.id] = migration
                except Exception as e:
                    logger.warning(f"Error loading migration {filename}: {e}")

    def _parse_migration_file(self, filename: str, content: str) -> Optional[Migration]:
        """Parse a migration file and return a Migration object."""
        import uuid

        parts = filename.replace(".sql", "").split("_", 1)
        if len(parts) != 2:
            return None

        version, name = parts

        if "-- DOWN" in content:
            up_down = content.split("-- DOWN")
            up_sql = up_down[0].replace("-- UP", "").strip()
            down_sql = up_down[1].strip() if len(up_down) > 1 else ""
        else:
            up_sql = content
            down_sql = ""

        migration_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, filename))[:8]

        return Migration(
            id=migration_id,
            version=version,
            name=name,
            up_sql=up_sql,
            down_sql=down_sql,
        )

    def _save_migration(self, migration: Migration) -> None:
        """Persist a migration record."""
        filename = f"{migration.version}_{migration.name}.sql"
        filepath = os.path.join(self.migrations_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"-- Migration: {migration.name}\n")
                f.write(f"-- Version: {migration.version}\n\n")
                f.write("-- UP\n")
                f.write(migration.up_sql)
                f.write("\n\n-- DOWN\n")
                f.write(migration.down_sql)

            logger.debug(f"Migração salva em {filepath}")

        except Exception as e:
            logger.error(f"Error saving migration: {e}", exc_info=True)

    def list_migrations(self) -> List[Dict[str, Any]]:
        """List all available migrations."""
        return [
            {
                "id": m.id,
                "version": m.version,
                "name": m.name,
                "status": m.status.value,
                "applied_at": m.applied_at.isoformat() if m.applied_at else None,
            }
            for m in sorted(self.migrations.values(), key=lambda m: m.version)
        ]

    def get_migration_status(
        self, connection_string: str, db_type: str = "sqlite"
    ) -> Dict[str, Any]:
        """Return the current migration status."""
        from aura_cli.core.ops_tools.database.query_executor import DatabaseConnection

        connection = DatabaseConnection(
            db_type=db_type,
            database=connection_string,
        )

        try:
            self._ensure_migrations_table(connection)
            applied = set(self._get_applied_migrations(connection))
        except Exception:
            applied = set()

        migrations_status = []
        for m in sorted(self.migrations.values(), key=lambda m: m.version):
            migrations_status.append(
                {
                    "id": m.id,
                    "version": m.version,
                    "name": m.name,
                    "applied": m.id in applied,
                }
            )

        return {
            "total": len(self.migrations),
            "applied": len(applied),
            "pending": len(self.migrations) - len(applied),
            "migrations": migrations_status,
        }


_migration_instance: Optional[DatabaseMigration] = None


def get_database_migration(migrations_dir: str = "migrations") -> DatabaseMigration:
    """
    Get or create DatabaseMigration instance (singleton).

    Args:
        migrations_dir: Directory for migration files

    Returns:
        DatabaseMigration instance
    """
    global _migration_instance
    if _migration_instance is None:
        _migration_instance = DatabaseMigration(migrations_dir=migrations_dir)
    return _migration_instance
