"""
Testes para o módulo database_backup.

Testa funcionalidades de backup e restauração de bancos de dados
com diferentes tipos e configurações.
"""

from unittest.mock import MagicMock, Mock, patch

from aura_cli.core.ops_tools.database.database_backup import (
    BackupConfig,
    BackupResult,
    DatabaseBackup,
    DatabaseType,
)


class TestDatabaseType:
    """Testa enum DatabaseType."""

    def test_database_types(self):
        """Testa valores dos tipos de banco."""
        assert DatabaseType.POSTGRESQL.value == "postgresql"
        assert DatabaseType.MYSQL.value == "mysql"
        assert DatabaseType.SQLITE.value == "sqlite"
        assert DatabaseType.MONGODB.value == "mongodb"


class TestBackupConfig:
    """Testa dataclass BackupConfig."""

    def test_backup_config_defaults(self):
        """Testa valores padrão da configuração."""
        config = BackupConfig(db_type=DatabaseType.POSTGRESQL)

        assert config.db_type == DatabaseType.POSTGRESQL
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == ""
        assert config.username == ""
        assert config.password is None
        assert config.output_path == ""
        assert config.compression is True

    def test_backup_config_custom_values(self):
        """Testa configuração com valores customizados."""
        config = BackupConfig(
            db_type=DatabaseType.MYSQL,
            host="db.example.com",
            port=3306,
            database="myapp",
            username="admin",
            password="secret",
            output_path="/backups/myapp.sql",
            compression=False,
        )

        assert config.db_type == DatabaseType.MYSQL
        assert config.host == "db.example.com"
        assert config.port == 3306
        assert config.database == "myapp"
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.output_path == "/backups/myapp.sql"
        assert config.compression is False


class TestBackupResult:
    """Testa dataclass BackupResult."""

    def test_backup_result_defaults(self):
        """Testa valores padrão do resultado."""
        result = BackupResult(success=True)

        assert result.success is True
        assert result.backup_path is None
        assert result.size == 0
        assert result.duration == 0.0
        assert result.error is None

    def test_backup_result_success(self):
        """Testa resultado de backup bem-sucedido."""
        result = BackupResult(
            success=True,
            backup_path="/backups/db_20240101_120000.sql.gz",
            size=1024000,
            duration=15.5,
        )

        assert result.success is True
        assert result.backup_path == "/backups/db_20240101_120000.sql.gz"
        assert result.size == 1024000
        assert result.duration == 15.5
        assert result.error is None

    def test_backup_result_failure(self):
        """Testa resultado de backup com falha."""
        result = BackupResult(success=False, error="Connection refused")

        assert result.success is False
        assert result.backup_path is None
        assert result.error == "Connection refused"


class TestDatabaseBackup:
    """Testa classe DatabaseBackup."""

    def setup_method(self):
        """Setup para cada teste."""
        self.backup = DatabaseBackup()

    def test_init(self):
        """Testa inicialização."""
        assert hasattr(self.backup, "stats")
        assert hasattr(self.backup, "backup_history")
        assert isinstance(self.backup.backup_history, list)
        assert len(self.backup.backup_history) == 0

    @patch("aura_cli.core.ui.display_tool_call")
    def test_create_backup_postgresql_success(self, mock_display):
        """Testa backup PostgreSQL bem-sucedido."""
        config = BackupConfig(
            db_type=DatabaseType.POSTGRESQL, database="testdb", username="user"
        )

        with patch.object(self.backup, "_backup_postgresql") as mock_pg:
            mock_pg.return_value = BackupResult(
                success=True,
                backup_path="/tmp/backup_testdb_20240101_120000.sql.gz",
                size=1024000,
            )

            result = self.backup.create_backup(config)

            assert result.success is True
            assert result.duration >= 0  # Apenas verificar que duração foi calculada
            assert len(self.backup.backup_history) == 1
            mock_display.assert_called_once()
            mock_pg.assert_called_once_with(config)

    @patch("aura_cli.core.ui.display_tool_call")
    def test_create_backup_unsupported_type(self, mock_display):
        """Testa backup com tipo não suportado."""
        # Criamos um tipo mock que não é suportado
        config = BackupConfig(db_type=DatabaseType.MONGODB)

        result = self.backup.create_backup(config)

        assert result.success is False
        assert "não suportado" in result.error
        assert result.duration >= 0  # Apenas verificar que duração foi calculada

    @patch("shutil.which")
    def test_backup_postgresql_no_pg_dump(self, mock_which):
        """Testa backup PostgreSQL sem pg_dump instalado."""
        mock_which.return_value = None

        config = BackupConfig(db_type=DatabaseType.POSTGRESQL, database="testdb")

        result = self.backup._backup_postgresql(config)

        assert result.success is False
        assert "pg_dump not found" in result.error

    @patch("shutil.which")
    @patch("subprocess.run")
    @patch("gzip.open")
    @patch("os.path.getsize")
    def test_backup_postgresql_with_compression(
        self, mock_getsize, mock_gzip, mock_run, mock_which
    ):
        """Testa backup PostgreSQL com compressão."""
        mock_which.return_value = "/usr/bin/pg_dump"
        mock_getsize.return_value = 512000

        # Mock do processo subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Mock do arquivo gzip
        mock_file = MagicMock()
        mock_gzip.return_value.__enter__.return_value = mock_file

        config = BackupConfig(
            db_type=DatabaseType.POSTGRESQL,
            database="testdb",
            username="user",
            password="secret",
            compression=True,
            output_path="/tmp/backup",
        )

        result = self.backup._backup_postgresql(config)

        assert result.success is True
        assert result.backup_path == "/tmp/backup.gz"
        assert result.size == 512000
        mock_gzip.assert_called_once_with("/tmp/backup.gz", "wb")

    @patch("shutil.which")
    @patch("subprocess.run")
    @patch("builtins.open")
    @patch("os.path.getsize")
    def test_backup_postgresql_without_compression(
        self, mock_getsize, mock_open, mock_run, mock_which
    ):
        """Testa backup PostgreSQL sem compressão."""
        mock_which.return_value = "/usr/bin/pg_dump"
        mock_getsize.return_value = 1024000

        # Mock do processo subprocess
        mock_process = Mock()
        mock_process.returncode = 0
        mock_run.return_value = mock_process

        # Mock do arquivo
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        config = BackupConfig(
            db_type=DatabaseType.POSTGRESQL,
            database="testdb",
            compression=False,
            output_path="/tmp/backup.sql",
        )

        result = self.backup._backup_postgresql(config)

        assert result.success is True
        assert result.backup_path == "/tmp/backup.sql"
        assert result.size == 1024000
        mock_open.assert_called_once_with("/tmp/backup.sql", "wb")

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_backup_postgresql_command_failure(self, mock_run, mock_which, tmp_path):
        """Testa falha no comando pg_dump."""
        mock_which.return_value = "/usr/bin/pg_dump"

        # Mock do processo com falha
        mock_process = Mock()
        mock_process.returncode = 1
        mock_process.stderr = "Connection refused"
        mock_run.return_value = mock_process

        config = BackupConfig(
            db_type=DatabaseType.POSTGRESQL,
            database="testdb",
            output_path=str(tmp_path / "failed-backup"),
        )

        result = self.backup._backup_postgresql(config)

        assert result.success is False
        assert result.error == "Connection refused"
        assert not (tmp_path / "failed-backup.gz").exists()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_backup_postgresql_exception(self, mock_run, mock_which, tmp_path):
        """Testa exceção durante backup PostgreSQL."""
        mock_which.return_value = "/usr/bin/pg_dump"
        mock_run.side_effect = Exception("Timeout error")

        config = BackupConfig(
            db_type=DatabaseType.POSTGRESQL,
            database="testdb",
            output_path=str(tmp_path / "backup"),
        )

        result = self.backup._backup_postgresql(config)

        assert result.success is False
        assert result.error == "Timeout error"
        assert not (tmp_path / "backup.gz").exists()

    @patch("shutil.which")
    def test_backup_mysql_no_mysqldump(self, mock_which):
        """Testa backup MySQL sem mysqldump instalado."""
        mock_which.return_value = None

        config = BackupConfig(db_type=DatabaseType.MYSQL, database="testdb")

        result = self.backup._backup_mysql(config)

        assert result.success is False
        assert "mysqldump not found" in result.error

    def test_backup_history_tracking(self):
        """Testa rastreamento do histórico de backups."""
        config = BackupConfig(db_type=DatabaseType.POSTGRESQL, database="testdb")

        with patch.object(self.backup, "_backup_postgresql") as mock_pg:
            mock_pg.return_value = BackupResult(success=True)

            # Primeiro backup
            self.backup.create_backup(config)
            assert len(self.backup.backup_history) == 1

            # Segundo backup
            self.backup.create_backup(config)
            assert len(self.backup.backup_history) == 2

    @patch("aura_cli.core.ops_tools.database.database_backup.datetime")
    def test_automatic_output_path_generation(
        self, mock_datetime, monkeypatch, tmp_path
    ):
        """Testa geração automática do caminho de saída."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("AURA_PROJECT_ROOT", str(tmp_path))
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"

        config = BackupConfig(
            db_type=DatabaseType.POSTGRESQL,
            database="myapp",
            output_path="",  # Vazio para gerar automaticamente
        )

        with patch.object(self.backup, "_backup_postgresql") as mock_pg:
            mock_pg.return_value = BackupResult(success=True)

            self.backup.create_backup(config)

        assert config.output_path == str(
            tmp_path / ".aura" / "backups" / "backup_myapp_20240101_120000"
        )
