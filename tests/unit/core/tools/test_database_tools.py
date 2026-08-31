"""Testes para database tools."""


class TestDatabaseBackup:
    """Testes para database_backup."""

    def test_database_backup_import(self):
        """Testa importação do módulo database_backup."""
        from aura_cli.core.ops_tools.database import database_backup

        assert database_backup is not None


class TestDatabaseMigration:
    """Testes para database_migration."""

    def test_database_migration_import(self):
        """Testa importação do módulo database_migration."""
        from aura_cli.core.ops_tools.database import database_migration

        assert database_migration is not None


class TestDatabaseMonitor:
    """Testes para database_monitor."""

    def test_database_monitor_import(self):
        """Testa importação do módulo database_monitor."""
        from aura_cli.core.ops_tools.database import database_monitor

        assert database_monitor is not None


class TestQueryExecutor:
    """Testes para query_executor."""

    def test_query_executor_import(self):
        """Testa importação do módulo query_executor."""
        from aura_cli.core.ops_tools.database import query_executor

        assert query_executor is not None
