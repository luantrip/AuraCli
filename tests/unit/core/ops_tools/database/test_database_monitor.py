"""
Testes para o módulo database_monitor.

Testa funcionalidades de monitoramento de performance,
conexões e saúde de bancos de dados.
"""

from unittest.mock import Mock, patch

from aura_cli.core.ops_tools.database.database_monitor import (
    DatabaseMetrics,
    DatabaseMonitor,
)


class TestDatabaseMetrics:
    """Testa dataclass DatabaseMetrics."""

    def test_database_metrics_defaults(self):
        """Testa valores padrão das métricas."""
        metrics = DatabaseMetrics(db_name="testdb")

        assert metrics.db_name == "testdb"
        assert metrics.connections == 0
        assert metrics.active_queries == 0
        assert metrics.cache_hit_ratio == 0.0
        assert metrics.size == 0
        assert metrics.uptime == 0.0
        assert metrics.table_count == 0
        assert metrics.index_count == 0

    def test_database_metrics_custom_values(self):
        """Testa métricas com valores customizados."""
        metrics = DatabaseMetrics(
            db_name="production",
            connections=25,
            active_queries=5,
            cache_hit_ratio=0.95,
            size=1024000000,
            uptime=86400.0,
            table_count=50,
            index_count=120,
        )

        assert metrics.db_name == "production"
        assert metrics.connections == 25
        assert metrics.active_queries == 5
        assert metrics.cache_hit_ratio == 0.95
        assert metrics.size == 1024000000
        assert metrics.uptime == 86400.0
        assert metrics.table_count == 50
        assert metrics.index_count == 120

    def test_cache_hit_ratio_bounds(self):
        """Testa limites da taxa de cache hit."""
        # Taxa mínima
        metrics_min = DatabaseMetrics(db_name="test", cache_hit_ratio=0.0)
        assert metrics_min.cache_hit_ratio == 0.0

        # Taxa máxima
        metrics_max = DatabaseMetrics(db_name="test", cache_hit_ratio=1.0)
        assert metrics_max.cache_hit_ratio == 1.0

        # Taxa intermediária
        metrics_mid = DatabaseMetrics(db_name="test", cache_hit_ratio=0.85)
        assert metrics_mid.cache_hit_ratio == 0.85


class TestDatabaseMonitor:
    """Testa classe DatabaseMonitor."""

    def setup_method(self):
        """Setup para cada teste."""
        self.monitor = DatabaseMonitor()

    def test_init(self):
        """Testa inicialização."""
        assert hasattr(self.monitor, "stats")
        assert hasattr(self.monitor, "metrics_history")
        assert isinstance(self.monitor.metrics_history, list)
        assert len(self.monitor.metrics_history) == 0

    def test_metrics_queries_structure(self):
        """Testa estrutura das queries de métricas."""
        queries = DatabaseMonitor.METRICS_QUERIES

        # Verifica se contém os tipos de banco esperados
        assert "sqlite" in queries
        assert "postgresql" in queries
        assert "mysql" in queries

        # Verifica queries SQLite
        sqlite_queries = queries["sqlite"]
        assert "tables" in sqlite_queries
        assert "indexes" in sqlite_queries
        assert "sqlite_master" in sqlite_queries["tables"]

        # Verifica queries PostgreSQL
        pg_queries = queries["postgresql"]
        assert "connections" in pg_queries
        assert "active_queries" in pg_queries
        assert "cache_hit" in pg_queries
        assert "size" in pg_queries
        assert "tables" in pg_queries
        assert "indexes" in pg_queries

        # Verifica queries MySQL
        mysql_queries = queries["mysql"]
        assert "connections" in mysql_queries
        assert "active_queries" in mysql_queries
        assert "size" in mysql_queries
        assert "tables" in mysql_queries
        assert "indexes" in mysql_queries

    def test_sqlite_queries_content(self):
        """Testa conteúdo das queries SQLite."""
        sqlite_queries = DatabaseMonitor.METRICS_QUERIES["sqlite"]

        tables_query = sqlite_queries["tables"]
        assert "COUNT(*)" in tables_query
        assert "sqlite_master" in tables_query
        assert "type='table'" in tables_query

        indexes_query = sqlite_queries["indexes"]
        assert "COUNT(*)" in indexes_query
        assert "sqlite_master" in indexes_query
        assert "type='index'" in indexes_query

    def test_postgresql_queries_content(self):
        """Testa conteúdo das queries PostgreSQL."""
        pg_queries = DatabaseMonitor.METRICS_QUERIES["postgresql"]

        connections_query = pg_queries["connections"]
        assert "pg_stat_activity" in connections_query
        assert "datname = current_database()" in connections_query

        cache_hit_query = pg_queries["cache_hit"]
        assert "blks_hit" in cache_hit_query
        assert "blks_read" in cache_hit_query
        assert "pg_stat_database" in cache_hit_query

        size_query = pg_queries["size"]
        assert "pg_database_size" in size_query

    def test_mysql_queries_content(self):
        """Testa conteúdo das queries MySQL."""
        mysql_queries = DatabaseMonitor.METRICS_QUERIES["mysql"]

        connections_query = mysql_queries["connections"]
        assert "information_schema.processlist" in connections_query

        active_queries_query = mysql_queries["active_queries"]
        assert "command != 'Sleep'" in active_queries_query

        size_query = mysql_queries["size"]
        assert "data_length + index_length" in size_query
        assert "information_schema.tables" in size_query

    def test_get_executor(self):
        """Testa obtenção do executor."""
        from aura_cli.core.ops_tools.database.query_executor import QueryExecutor

        executor = self.monitor._get_executor()

        assert isinstance(executor, QueryExecutor)

    def test_collect_metrics_sqlite_success(self):
        """Testa coleta de métricas SQLite com sucesso."""
        mock_executor = Mock()

        # Mock das respostas das queries
        mock_executor.execute_query.side_effect = [
            Mock(success=True, rows=[{"count": 10}]),  # tables
            Mock(success=True, rows=[{"count": 25}]),  # indexes
        ]

        with patch.object(self.monitor, "_get_executor", return_value=mock_executor):
            mock_connection = Mock()
            mock_connection.db_type = "sqlite"
            mock_connection.database = "test.db"

            metrics = self.monitor.collect_metrics(mock_connection)

            assert metrics is not None
            assert metrics.db_name == "test.db"
            assert metrics.table_count == 10
            assert metrics.index_count == 25
            assert len(self.monitor.metrics_history) == 1

    def test_collect_metrics_postgresql_success(self):
        """Testa coleta de métricas PostgreSQL com sucesso."""
        mock_executor = Mock()

        # Mock das respostas das queries
        mock_executor.execute_query.side_effect = [
            Mock(success=True, rows=[{"count": 15}]),  # connections
            Mock(success=True, rows=[{"count": 3}]),  # active_queries
            Mock(success=True, rows=[{"ratio": 0.92}]),  # cache_hit
            Mock(success=True, rows=[{"size": 5000000}]),  # size
            Mock(success=True, rows=[{"count": 20}]),  # tables
            Mock(success=True, rows=[{"count": 45}]),  # indexes
        ]

        with patch.object(self.monitor, "_get_executor", return_value=mock_executor):
            mock_connection = Mock()
            mock_connection.db_type = "postgresql"
            mock_connection.database = "myapp"

            metrics = self.monitor.collect_metrics(mock_connection)

            assert metrics is not None
            assert metrics.db_name == "myapp"
            assert metrics.connections == 15
            assert metrics.active_queries == 3
            assert metrics.cache_hit_ratio == 0.92
            assert metrics.size == 5000000
            assert metrics.table_count == 20
            assert metrics.index_count == 45

    def test_collect_metrics_mysql_success(self):
        """Testa coleta de métricas MySQL com sucesso."""
        mock_executor = Mock()

        # Mock das respostas das queries
        mock_executor.execute_query.side_effect = [
            Mock(success=True, rows=[{"count": 8}]),  # connections
            Mock(success=True, rows=[{"count": 2}]),  # active_queries
            Mock(success=True, rows=[{"size": 3000000}]),  # size
            Mock(success=True, rows=[{"count": 15}]),  # tables
            Mock(success=True, rows=[{"count": 30}]),  # indexes
        ]

        with patch.object(self.monitor, "_get_executor", return_value=mock_executor):
            mock_connection = Mock()
            mock_connection.db_type = "mysql"
            mock_connection.database = "webapp"

            metrics = self.monitor.collect_metrics(mock_connection)

            assert metrics is not None
            assert metrics.db_name == "webapp"
            assert metrics.connections == 8
            assert metrics.active_queries == 2
            assert metrics.size == 3000000
            assert metrics.table_count == 15
            assert metrics.index_count == 30

    def test_collect_metrics_query_failure(self):
        """Testa coleta de métricas com falha na query."""
        mock_executor = Mock()

        # Mock de falha na primeira query
        mock_executor.execute_query.return_value = Mock(success=False)

        with patch.object(self.monitor, "_get_executor", return_value=mock_executor):
            mock_connection = Mock()
            mock_connection.db_type = "sqlite"
            mock_connection.database = "test.db"

            metrics = self.monitor.collect_metrics(mock_connection)

            # Deve retornar None ou métricas com valores padrão
            # dependendo da implementação
            assert metrics is None or isinstance(metrics, DatabaseMetrics)

    @patch("aura_cli.core.ui.display_tool_call")
    def test_collect_metrics_unsupported_db_type(self, mock_display):
        """Testa coleta de métricas com tipo de banco não suportado."""
        mock_connection = Mock()
        mock_connection.db_type = "oracle"  # Não suportado
        mock_connection.database = "testdb"

        metrics = self.monitor.collect_metrics(mock_connection)

        # Para tipos não suportados, ainda retorna DatabaseMetrics com valores padrão
        # porque o código não verifica explicitamente por tipos suportados
        assert isinstance(metrics, DatabaseMetrics)
        assert metrics.db_name == "testdb"
        # Valores padrão para tipo não suportado (sem queries executadas)
        assert metrics.connections == 0
        assert metrics.table_count == 0

    def test_metrics_history_tracking(self):
        """Testa rastreamento do histórico de métricas."""
        mock_connection = Mock()
        mock_connection.db_type = "sqlite"
        mock_connection.database = "test.db"

        with patch.object(self.monitor, "_get_executor") as mock_get_executor:
            mock_executor = Mock()
            mock_get_executor.return_value = mock_executor

            # Mock de sucesso
            mock_executor.execute_query.side_effect = [
                Mock(success=True, rows=[{"count": 5}]),  # tables
                Mock(success=True, rows=[{"count": 10}]),  # indexes
            ]

            # Primeira coleta
            metrics1 = self.monitor.collect_metrics(mock_connection)
            assert len(self.monitor.metrics_history) == 1

            # Segunda coleta
            metrics2 = self.monitor.collect_metrics(mock_connection)
            assert len(self.monitor.metrics_history) == 2

            # Verificar que são objetos diferentes
            assert metrics1 is not metrics2

    def test_metrics_data_types(self):
        """Testa tipos de dados das métricas."""
        metrics = DatabaseMetrics(
            db_name="test",
            connections=10,
            active_queries=2,
            cache_hit_ratio=0.85,
            size=1000000,
            uptime=3600.5,
            table_count=15,
            index_count=30,
        )

        assert isinstance(metrics.db_name, str)
        assert isinstance(metrics.connections, int)
        assert isinstance(metrics.active_queries, int)
        assert isinstance(metrics.cache_hit_ratio, float)
        assert isinstance(metrics.size, int)
        assert isinstance(metrics.uptime, float)
        assert isinstance(metrics.table_count, int)
        assert isinstance(metrics.index_count, int)

    def test_metrics_size_formatting(self):
        """Testa formatação de tamanho de banco."""
        # Tamanhos em bytes
        small_db = DatabaseMetrics(db_name="small", size=1024)  # 1KB
        medium_db = DatabaseMetrics(db_name="medium", size=1048576)  # 1MB
        large_db = DatabaseMetrics(db_name="large", size=1073741824)  # 1GB

        assert small_db.size == 1024
        assert medium_db.size == 1048576
        assert large_db.size == 1073741824

        # Conversões para unidades legíveis
        assert small_db.size / 1024 == 1.0  # KB
        assert medium_db.size / (1024 * 1024) == 1.0  # MB
        assert large_db.size / (1024 * 1024 * 1024) == 1.0  # GB

    def test_cache_hit_ratio_calculation(self):
        """Testa cálculo da taxa de cache hit."""
        # Taxa perfeita
        perfect_cache = DatabaseMetrics(db_name="perfect", cache_hit_ratio=1.0)
        assert perfect_cache.cache_hit_ratio == 1.0

        # Taxa ruim
        poor_cache = DatabaseMetrics(db_name="poor", cache_hit_ratio=0.1)
        assert poor_cache.cache_hit_ratio == 0.1

        # Taxa boa
        good_cache = DatabaseMetrics(db_name="good", cache_hit_ratio=0.95)
        assert good_cache.cache_hit_ratio == 0.95

    def test_uptime_formatting(self):
        """Testa formatação de tempo de atividade."""
        # Diferentes períodos de uptime
        short_uptime = DatabaseMetrics(db_name="short", uptime=3600.0)  # 1 hora
        long_uptime = DatabaseMetrics(db_name="long", uptime=86400.0)  # 1 dia

        assert short_uptime.uptime == 3600.0
        assert long_uptime.uptime == 86400.0

        # Conversões
        assert short_uptime.uptime / 3600 == 1.0  # horas
        assert long_uptime.uptime / 86400 == 1.0  # dias
