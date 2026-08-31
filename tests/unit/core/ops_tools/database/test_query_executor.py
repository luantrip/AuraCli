"""
Testes para o módulo query_executor.

Testa funcionalidades de execução de queries SQL
com suporte a múltiplos tipos de banco de dados.
"""

import tempfile

import pytest

from aura_cli.core.ops_tools.database.query_executor import (
    DEFAULT_DB_PATH,
    DatabaseConnection,
    QueryExecutor,
    QueryResult,
)


class TestDatabaseConnection:
    """Testa dataclass DatabaseConnection."""

    def test_database_connection_defaults(self):
        """Testa valores padrão da conexão."""
        conn = DatabaseConnection()

        assert conn.db_type == "sqlite"
        assert conn.host == "localhost"
        assert conn.port is None
        assert conn.database == DEFAULT_DB_PATH
        assert conn.username == ""
        assert conn.password is None
        assert conn.connection_string is None
        assert conn.pool_size == 5
        assert conn.echo is False

    def test_database_connection_custom_values(self):
        """Testa conexão com valores customizados."""
        conn = DatabaseConnection(
            db_type="postgresql",
            host="db.example.com",
            port=5432,
            database="myapp",
            username="admin",
            password="secret",
            pool_size=10,
            echo=True,
        )

        assert conn.db_type == "postgresql"
        assert conn.host == "db.example.com"
        assert conn.port == 5432
        assert conn.database == "myapp"
        assert conn.username == "admin"
        assert conn.password == "secret"
        assert conn.pool_size == 10
        assert conn.echo is True

    def test_get_connection_url_sqlite(self):
        """Testa URL de conexão SQLite."""
        conn = DatabaseConnection(db_type="sqlite", database="/tmp/test.db")

        url = conn.get_connection_url()
        # SQLite URL usa 3 ou 4 barras dependendo do path absoluto
        assert url.startswith("sqlite:///")
        assert "/tmp/test.db" in url

    def test_get_connection_url_sqlite_with_expansion(self):
        """Testa URL SQLite com expansão de path."""
        conn = DatabaseConnection(db_type="sqlite", database="~/test.db")

        # get_connection_url usa os.path.expanduser internamente
        url = conn.get_connection_url()
        # URL SQLite pode ter 3 ou 4 barras dependendo do path
        assert url.startswith("sqlite:///")
        # Verificar que o path foi expandido (não contém ~)
        assert "~" not in url
        assert "test.db" in url

    def test_get_connection_url_postgresql(self):
        """Testa URL de conexão PostgreSQL."""
        conn = DatabaseConnection(
            db_type="postgresql",
            host="localhost",
            port=5432,
            database="myapp",
            username="user",
            password="pass",
        )

        url = conn.get_connection_url()
        assert url == "postgresql://user:pass@localhost:5432/myapp"

    def test_get_connection_url_postgresql_default_port(self):
        """Testa URL PostgreSQL com porta padrão."""
        conn = DatabaseConnection(
            db_type="postgresql",
            host="localhost",
            database="myapp",
            username="user",
            password="pass",
        )

        url = conn.get_connection_url()
        assert url == "postgresql://user:pass@localhost:5432/myapp"

    def test_get_connection_url_postgresql_no_auth(self):
        """Testa URL PostgreSQL sem autenticação."""
        conn = DatabaseConnection(
            db_type="postgresql", host="localhost", database="myapp"
        )

        url = conn.get_connection_url()
        assert url == "postgresql://localhost:5432/myapp"

    def test_get_connection_url_mysql(self):
        """Testa URL de conexão MySQL."""
        conn = DatabaseConnection(
            db_type="mysql",
            host="localhost",
            port=3306,
            database="webapp",
            username="root",
            password="secret",
        )

        url = conn.get_connection_url()
        assert url == "mysql+mysqlconnector://root:secret@localhost:3306/webapp"

    def test_get_connection_url_mysql_default_port(self):
        """Testa URL MySQL com porta padrão."""
        conn = DatabaseConnection(
            db_type="mysql",
            host="localhost",
            database="webapp",
            username="root",
            password="secret",
        )

        url = conn.get_connection_url()
        assert url == "mysql+mysqlconnector://root:secret@localhost:3306/webapp"

    def test_get_connection_url_oracle(self):
        """Testa URL de conexão Oracle."""
        conn = DatabaseConnection(
            db_type="oracle",
            host="oracle-server",
            port=1521,
            database="XE",
            username="hr",
            password="oracle",
        )

        url = conn.get_connection_url()
        assert url == "oracle+cx_oracle://hr:oracle@oracle-server:1521/XE"

    def test_get_connection_url_mssql(self):
        """Testa URL de conexão SQL Server."""
        conn = DatabaseConnection(
            db_type="mssql",
            host="sql-server",
            port=1433,
            database="MyDB",
            username="sa",
            password="password",
        )

        url = conn.get_connection_url()
        expected = "mssql+pyodbc://sa:password@sql-server:1433/MyDB?driver=ODBC+Driver+17+for+SQL+Server"
        assert url == expected

    def test_get_connection_url_custom_connection_string(self):
        """Testa URL com connection string customizada."""
        custom_url = "postgresql://custom:string@host:5432/db"
        conn = DatabaseConnection(connection_string=custom_url)

        url = conn.get_connection_url()
        assert url == custom_url

    def test_get_connection_url_unsupported_type(self):
        """Testa URL com tipo de banco não suportado."""
        conn = DatabaseConnection(db_type="unsupported")

        with pytest.raises(ValueError) as exc_info:
            conn.get_connection_url()

        assert "not supported" in str(exc_info.value)
        assert "unsupported" in str(exc_info.value)

    def test_case_insensitive_db_type(self):
        """Testa que db_type é case-insensitive."""
        conn_upper = DatabaseConnection(db_type="POSTGRESQL", database="test")
        conn_mixed = DatabaseConnection(db_type="PostgreSQL", database="test")

        url_upper = conn_upper.get_connection_url()
        url_mixed = conn_mixed.get_connection_url()

        assert "postgresql://" in url_upper
        assert "postgresql://" in url_mixed


class TestQueryResult:
    """Testa dataclass QueryResult."""

    def test_query_result_defaults(self):
        """Testa valores padrão do resultado."""
        # QueryResult requer success como parâmetro obrigatório
        result = QueryResult(success=False)

        assert result.success is False
        assert result.rows == []
        assert result.columns == []
        assert result.row_count == 0
        assert result.duration == 0.0
        assert result.error is None

    def test_query_result_success(self):
        """Testa resultado de query bem-sucedida."""
        rows = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        columns = ["id", "name"]

        result = QueryResult(
            success=True, rows=rows, columns=columns, row_count=2, duration=0.05
        )

        assert result.success is True
        assert result.rows == rows
        assert result.columns == columns
        assert result.row_count == 2
        assert result.duration == 0.05
        assert result.error is None

    def test_query_result_failure(self):
        """Testa resultado de query com falha."""
        result = QueryResult(success=False, error="Table 'users' doesn't exist")

        assert result.success is False
        assert result.rows == []
        assert result.error == "Table 'users' doesn't exist"


class TestQueryExecutor:
    """Testa classe QueryExecutor."""

    def setup_method(self):
        """Setup para cada teste."""
        self.executor = QueryExecutor()

    def test_init(self):
        """Testa inicialização."""
        assert hasattr(self.executor, "stats")
        assert hasattr(self.executor, "default_connection")
        # QueryExecutor pode ter cache interno, mas não é público
        assert self.executor.default_connection is not None

    def test_default_db_path_constant(self):
        """Testa constante do caminho padrão do banco."""
        from aura_cli.core.paths import aura_path

        assert str(aura_path("aura_data.db")) == DEFAULT_DB_PATH
        assert "~" not in DEFAULT_DB_PATH  # Deve estar expandido

    def test_get_engine_sqlite(self):
        """Testa criação de engine SQLite através de execute_query."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = DatabaseConnection(db_type="sqlite", database=db_path)

            # _get_engine é privado, testar através de execute_query
            # execute_query cria engine internamente
            result = self.executor.execute_query(
                "CREATE TABLE IF NOT EXISTS test_engine (id INTEGER)", connection=conn
            )

            assert result.success is True
            # Verificar que a conexão funciona
            assert result.error is None
        finally:
            import os

            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_get_engine_postgresql(self):
        """Testa URL de conexão PostgreSQL através de get_connection_url."""
        conn = DatabaseConnection(
            db_type="postgresql",
            host="localhost",
            database="myapp",
            username="user",
            password="pass",
        )

        # Verificar que get_connection_url funciona
        url = conn.get_connection_url()
        assert "postgresql://" in url
        assert "user:pass@localhost:5432/myapp" in url

    def test_connection_caching(self):
        """Testa cache de conexões através de múltiplas queries."""
        # Usar database único para evitar conflitos
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = DatabaseConnection(db_type="sqlite", database=db_path)

            # Criar tabela
            result1 = self.executor.execute_query(
                "CREATE TABLE test (id INTEGER)", connection=conn
            )

            # Segunda query (deve reutilizar conexão se houver cache)
            result2 = self.executor.execute_query(
                "INSERT INTO test (id) VALUES (1)", connection=conn
            )

            assert result1.success is True
            assert result2.success is True
        finally:
            import os

            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_execute_query_success(self):
        """Testa execução de query com sucesso."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = DatabaseConnection(db_type="sqlite", database=db_path)

            # Criar tabela e inserir dados
            self.executor.execute_query(
                "CREATE TABLE IF NOT EXISTS users_test (id INTEGER, name TEXT)",
                connection=conn,
            )

            # Limpar dados existentes
            self.executor.execute_query("DELETE FROM users_test", connection=conn)

            self.executor.execute_query(
                "INSERT INTO users_test (id, name) VALUES (1, 'Alice'), (2, 'Bob')",
                connection=conn,
            )

            # Executar SELECT
            result = self.executor.execute_query(
                "SELECT * FROM users_test", connection=conn
            )

            assert result.success is True
            assert len(result.rows) == 2
            assert result.rows[0]["id"] == 1
            assert result.rows[0]["name"] == "Alice"
            assert "id" in result.columns
            assert "name" in result.columns
            assert result.row_count == 2
        finally:
            import os

            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_execute_query_failure(self):
        """Testa execução de query com falha."""
        conn = DatabaseConnection(db_type="sqlite", database=":memory:")

        # Executar query inválida
        result = self.executor.execute_query(
            "SELECT * FROM nonexistent_table", connection=conn
        )

        assert result.success is False
        assert result.error is not None
        assert (
            "error" in result.error.lower()
            or "doesn't exist" in result.error.lower()
            or "no such table" in result.error.lower()
        )
        assert result.rows == []

    def test_execute_query_with_parameters(self):
        """Testa execução de query com parâmetros."""
        # Usar database único para evitar conflitos
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = DatabaseConnection(db_type="sqlite", database=db_path)

            # Criar tabela
            self.executor.execute_query(
                "CREATE TABLE users (id INTEGER, name TEXT)", connection=conn
            )

            # Inserir dados
            self.executor.execute_query(
                "INSERT INTO users (id, name) VALUES (1, 'Alice'), (2, 'Bob')",
                connection=conn,
            )

            # Executar SELECT com parâmetros
            result = self.executor.execute_query(
                "SELECT * FROM users WHERE id = :id",
                connection=conn,
                parameters={"id": 1},
            )

            assert result.success is True
            assert len(result.rows) == 1
            assert result.rows[0]["id"] == 1
            assert result.rows[0]["name"] == "Alice"
        finally:
            import os

            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_connection_url_caching_key(self):
        """Testa chave de cache baseada na URL de conexão."""
        conn1 = DatabaseConnection(db_type="sqlite", database="/tmp/db1.db")
        conn2 = DatabaseConnection(db_type="sqlite", database="/tmp/db2.db")
        conn3 = DatabaseConnection(db_type="sqlite", database="/tmp/db1.db")

        url1 = conn1.get_connection_url()
        url2 = conn2.get_connection_url()
        url3 = conn3.get_connection_url()

        # URLs diferentes para bancos diferentes
        assert url1 != url2
        # URLs iguais para mesma configuração
        assert url1 == url3

    def test_sql_injection_protection(self):
        """Testa proteção contra SQL injection usando parâmetros."""
        # Usar database único para este teste
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            conn = DatabaseConnection(db_type="sqlite", database=db_path)

            # Criar tabela
            self.executor.execute_query(
                "CREATE TABLE IF NOT EXISTS users (id INTEGER, name TEXT)",
                connection=conn,
            )

            self.executor.execute_query(
                "INSERT INTO users (id, name) VALUES (1, 'Alice')", connection=conn
            )

            # SQL com parâmetros nomeados (seguro) - SQLAlchemy escapa automaticamente
            safe_sql = "SELECT * FROM users WHERE name = :name"
            parameters = {"name": "'; DROP TABLE users; --"}

            # Executar query com parâmetro potencialmente perigoso
            result = self.executor.execute_query(
                safe_sql, connection=conn, parameters=parameters
            )

            # Deve executar sem erro (parâmetro é escapado)
            # Não deve encontrar nenhum resultado (nome não existe)
            assert result.success is True
            assert len(result.rows) == 0  # Nenhum resultado encontrado

            # Tabela ainda deve existir (não foi dropada)
            check_result = self.executor.execute_query(
                "SELECT COUNT(*) as count FROM users", connection=conn
            )
            assert check_result.success is True
            assert check_result.rows[0]["count"] == 1
        finally:
            # Limpar arquivo temporário
            import os

            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_database_types_coverage(self):
        """Testa cobertura de tipos de banco suportados."""
        supported_types = ["sqlite", "postgresql", "mysql", "oracle", "mssql"]

        for db_type in supported_types:
            conn = DatabaseConnection(db_type=db_type, database="test")

            # Não deve levantar exceção para tipos suportados
            try:
                url = conn.get_connection_url()
                assert isinstance(url, str)
                assert len(url) > 0
            except ValueError:
                # Apenas para tipos não suportados
                assert db_type not in supported_types
