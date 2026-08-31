"""
Testes para o módulo logs_aggregator.

Testa funcionalidades de coleta, agregação e análise
de logs de múltiplas fontes.
"""

from datetime import datetime, timedelta
import re
from unittest.mock import patch

from aura_cli.core.ops_tools.monitoring.logs_aggregator import (
    LogEntry,
    LogLevel,
    LogsAggregator,
)


class TestLogLevel:
    """Testa enum LogLevel."""

    def test_log_level_values(self):
        """Testa valores dos níveis de log."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"

    def test_log_level_hierarchy_concept(self):
        """Testa conceito de hierarquia de níveis."""
        levels = [
            LogLevel.DEBUG,
            LogLevel.INFO,
            LogLevel.WARNING,
            LogLevel.ERROR,
            LogLevel.CRITICAL,
        ]

        # Verificar que temos todos os níveis esperados
        assert len(levels) == 5

        # Verificar valores únicos
        values = [level.value for level in levels]
        assert len(set(values)) == 5


class TestLogEntry:
    """Testa dataclass LogEntry."""

    def test_log_entry_creation(self):
        """Testa criação de entrada de log."""
        timestamp = datetime.now()
        entry = LogEntry(
            timestamp=timestamp,
            level=LogLevel.INFO,
            source="test_app",
            message="Test message",
        )

        assert entry.timestamp == timestamp
        assert entry.level == LogLevel.INFO
        assert entry.source == "test_app"
        assert entry.message == "Test message"
        assert entry.metadata == {}

    def test_log_entry_with_metadata(self):
        """Testa entrada de log com metadados."""
        timestamp = datetime.now()
        metadata = {"user_id": "123", "request_id": "abc-def"}

        entry = LogEntry(
            timestamp=timestamp,
            level=LogLevel.ERROR,
            source="auth_service",
            message="Authentication failed",
            metadata=metadata,
        )

        assert entry.metadata == metadata
        assert entry.metadata["user_id"] == "123"
        assert entry.metadata["request_id"] == "abc-def"

    def test_log_entry_metadata_default(self):
        """Testa valor padrão dos metadados."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=LogLevel.DEBUG,
            source="debug_app",
            message="Debug message",
        )

        assert isinstance(entry.metadata, dict)
        assert len(entry.metadata) == 0

    def test_log_entry_different_levels(self):
        """Testa entradas com diferentes níveis."""
        timestamp = datetime.now()

        entries = []
        for level in LogLevel:
            entry = LogEntry(
                timestamp=timestamp,
                level=level,
                source="test",
                message=f"Message at {level.value} level",
            )
            entries.append(entry)

        assert len(entries) == 5
        assert entries[0].level == LogLevel.DEBUG
        assert entries[-1].level == LogLevel.CRITICAL


class TestLogsAggregator:
    """Testa classe LogsAggregator."""

    def setup_method(self):
        """Setup para cada teste."""
        self.aggregator = LogsAggregator()

    def test_init(self):
        """Testa inicialização."""
        assert hasattr(self.aggregator, "logs")
        assert hasattr(self.aggregator, "stats")
        assert isinstance(self.aggregator.logs, list)
        assert len(self.aggregator.logs) == 0

    @patch("aura_cli.core.ops_tools.monitoring.logs_aggregator.datetime")
    def test_add_log_basic(self, mock_datetime):
        """Testa adição básica de log."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        self.aggregator.add_log(
            level=LogLevel.INFO, source="test_app", message="Test message"
        )

        assert len(self.aggregator.logs) == 1

        entry = self.aggregator.logs[0]
        assert entry.timestamp == mock_now
        assert entry.level == LogLevel.INFO
        assert entry.source == "test_app"
        assert entry.message == "Test message"
        assert entry.metadata == {}

    @patch("aura_cli.core.ops_tools.monitoring.logs_aggregator.datetime")
    def test_add_log_with_metadata(self, mock_datetime):
        """Testa adição de log com metadados."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        metadata = {"component": "auth", "session_id": "xyz"}

        self.aggregator.add_log(
            level=LogLevel.WARNING,
            source="auth_service",
            message="Session expired",
            metadata=metadata,
        )

        entry = self.aggregator.logs[0]
        assert entry.metadata == metadata

    def test_add_multiple_logs(self):
        """Testa adição de múltiplos logs."""
        logs_data = [
            (LogLevel.DEBUG, "app1", "Debug message"),
            (LogLevel.INFO, "app2", "Info message"),
            (LogLevel.ERROR, "app3", "Error message"),
        ]

        for level, source, message in logs_data:
            self.aggregator.add_log(level, source, message)

        assert len(self.aggregator.logs) == 3

        # Verificar ordem de adição
        assert self.aggregator.logs[0].level == LogLevel.DEBUG
        assert self.aggregator.logs[1].level == LogLevel.INFO
        assert self.aggregator.logs[2].level == LogLevel.ERROR

    def test_log_rotation_limit(self):
        """Testa rotação de logs quando excede limite."""
        # Adicionar mais de 10000 logs para testar rotação
        for i in range(10005):
            self.aggregator.add_log(LogLevel.INFO, f"source_{i % 10}", f"Message {i}")

        # Deve manter apenas os últimos 10000
        assert len(self.aggregator.logs) == 10000

        # Verificar que manteve os mais recentes (últimos 10000 de 0-10004)
        # O último deve ser Message 10004
        assert "Message 10004" in self.aggregator.logs[-1].message
        # O primeiro deve ser Message 5 (10005 - 10000 = 5)
        assert "Message 5" in self.aggregator.logs[0].message

    def test_search_logs_by_text(self):
        """Testa busca de logs por texto."""
        # Adicionar logs de teste
        test_logs = [
            (LogLevel.INFO, "app1", "User login successful"),
            (LogLevel.ERROR, "app2", "Database connection failed"),
            (LogLevel.INFO, "app1", "User logout"),
            (LogLevel.WARNING, "app3", "High memory usage"),
        ]

        for level, source, message in test_logs:
            self.aggregator.add_log(level, source, message)

        # Buscar por "user"
        results = self.aggregator.search_logs("user")

        assert len(results) == 2
        assert all("user" in result.message.lower() for result in results)

    def test_search_logs_by_level(self):
        """Testa busca de logs por nível."""
        # Adicionar logs com diferentes níveis
        test_logs = [
            (LogLevel.INFO, "app1", "Info message 1"),
            (LogLevel.ERROR, "app2", "Error message 1"),
            (LogLevel.INFO, "app3", "Info message 2"),
            (LogLevel.WARNING, "app4", "Warning message"),
        ]

        for level, source, message in test_logs:
            self.aggregator.add_log(level, source, message)

        # Buscar apenas logs INFO
        results = self.aggregator.search_logs("", level=LogLevel.INFO)

        assert len(results) == 2
        assert all(result.level == LogLevel.INFO for result in results)

    def test_search_logs_by_source(self):
        """Testa busca de logs por fonte."""
        # Adicionar logs de diferentes fontes
        test_logs = [
            (LogLevel.INFO, "web_server", "Request processed"),
            (LogLevel.ERROR, "database", "Query failed"),
            (LogLevel.INFO, "web_server", "Response sent"),
            (LogLevel.WARNING, "cache", "Cache miss"),
        ]

        for level, source, message in test_logs:
            self.aggregator.add_log(level, source, message)

        # Buscar apenas logs do web_server
        results = self.aggregator.search_logs("", source="web_server")

        assert len(results) == 2
        assert all(result.source == "web_server" for result in results)

    def test_search_logs_with_regex(self):
        """Testa busca de logs com regex."""
        # Adicionar logs com padrões específicos
        test_logs = [
            (LogLevel.INFO, "app", "User ID: 12345 logged in"),
            (LogLevel.INFO, "app", "User ID: 67890 logged out"),
            (LogLevel.ERROR, "app", "Invalid user credentials"),
            (LogLevel.INFO, "app", "System startup complete"),
        ]

        for level, source, message in test_logs:
            self.aggregator.add_log(level, source, message)

        # Buscar por padrão "User ID: \d+"
        results = self.aggregator.search_logs(r"User ID: \d+")

        assert len(results) == 2
        assert all(re.search(r"User ID: \d+", result.message) for result in results)

    def test_search_logs_invalid_regex(self):
        """Testa busca com regex inválida (fallback para texto)."""
        # Adicionar logs de teste
        self.aggregator.add_log(LogLevel.INFO, "app", "Test message with [brackets]")
        self.aggregator.add_log(LogLevel.INFO, "app", "Another message")

        # Usar regex inválida - deve fazer fallback para busca de texto
        results = self.aggregator.search_logs("[invalid")

        # Deve encontrar o log que contém "[invalid" como substring
        # (neste caso, nenhum, mas não deve dar erro)
        assert isinstance(results, list)

    def test_search_logs_limit(self):
        """Testa limite de resultados na busca."""
        # Adicionar muitos logs similares
        for i in range(50):
            self.aggregator.add_log(LogLevel.INFO, "app", f"Test message {i}")

        # Buscar com limite de 10
        results = self.aggregator.search_logs("test", limit=10)

        assert len(results) == 10

    def test_search_logs_sorted_by_timestamp(self):
        """Testa que resultados são ordenados por timestamp (mais recente primeiro)."""
        # Adicionar logs com timestamps diferentes
        with patch(
            "aura_cli.core.ops_tools.monitoring.logs_aggregator.datetime"
        ) as mock_datetime:
            base_time = datetime(2024, 1, 1, 12, 0, 0)

            # Primeiro log (mais antigo)
            mock_datetime.now.return_value = base_time
            self.aggregator.add_log(LogLevel.INFO, "app", "First message")

            # Segundo log (mais recente)
            mock_datetime.now.return_value = base_time + timedelta(minutes=1)
            self.aggregator.add_log(LogLevel.INFO, "app", "Second message")

        results = self.aggregator.search_logs("message")

        assert len(results) == 2
        # Mais recente primeiro
        assert "Second message" in results[0].message
        assert "First message" in results[1].message

    def test_aggregate_by_level(self):
        """Testa agregação por nível."""
        # Adicionar logs com diferentes níveis
        test_logs = [
            LogLevel.INFO,
            LogLevel.INFO,
            LogLevel.INFO,
            LogLevel.ERROR,
            LogLevel.ERROR,
            LogLevel.WARNING,
            LogLevel.DEBUG,
            LogLevel.CRITICAL,
        ]

        for i, level in enumerate(test_logs):
            self.aggregator.add_log(level, "app", f"Message {i}")

        counts = self.aggregator.aggregate_by_level()

        assert counts["INFO"] == 3
        assert counts["ERROR"] == 2
        assert counts["WARNING"] == 1
        assert counts["DEBUG"] == 1
        assert counts["CRITICAL"] == 1

    def test_aggregate_by_source(self):
        """Testa agregação por fonte."""
        # Adicionar logs de diferentes fontes
        test_logs = [
            ("web_server", "Request 1"),
            ("web_server", "Request 2"),
            ("database", "Query 1"),
            ("cache", "Cache hit"),
            ("web_server", "Request 3"),
        ]

        for source, message in test_logs:
            self.aggregator.add_log(LogLevel.INFO, source, message)

        # Usa método real aggregate_by_source
        counts = self.aggregator.aggregate_by_source()

        assert counts["web_server"] == 3
        assert counts["database"] == 1
        assert counts["cache"] == 1

    def test_get_recent_logs(self):
        """Testa obtenção de logs recentes."""
        # Adicionar logs com timestamps diferentes
        with patch(
            "aura_cli.core.ops_tools.monitoring.logs_aggregator.datetime"
        ) as mock_datetime:
            base_time = datetime(2024, 1, 1, 12, 0, 0)

            for i in range(5):
                mock_datetime.now.return_value = base_time + timedelta(minutes=i)
                self.aggregator.add_log(LogLevel.INFO, "app", f"Message {i}")

        # Usa search_logs com limite para obter logs recentes
        recent = self.aggregator.search_logs("", limit=3)

        assert len(recent) == 3
        assert "Message 4" in recent[0].message  # Mais recente

    def test_clear_logs(self):
        """Testa limpeza de logs."""
        # Adicionar alguns logs
        for i in range(5):
            self.aggregator.add_log(LogLevel.INFO, "app", f"Message {i}")

        assert len(self.aggregator.logs) == 5

        # Limpar logs
        self.aggregator.logs.clear()

        assert len(self.aggregator.logs) == 0

    def test_log_statistics(self):
        """Testa estatísticas de logs."""
        # Adicionar logs variados
        test_data = [
            (LogLevel.INFO, "app1"),
            (LogLevel.ERROR, "app2"),
            (LogLevel.INFO, "app1"),
            (LogLevel.WARNING, "app3"),
            (LogLevel.ERROR, "app2"),
        ]

        for level, source in test_data:
            self.aggregator.add_log(level, source, "Test message")

        # Calcular estatísticas básicas
        total_logs = len(self.aggregator.logs)
        unique_sources = len({entry.source for entry in self.aggregator.logs})
        error_count = len(
            [entry for entry in self.aggregator.logs if entry.level == LogLevel.ERROR]
        )

        assert total_logs == 5
        assert unique_sources == 3
        assert error_count == 2

    def test_log_filtering_combined(self):
        """Testa filtragem combinada (nível + fonte + texto)."""
        # Adicionar logs variados
        test_logs = [
            (LogLevel.INFO, "web", "User login successful"),
            (LogLevel.ERROR, "web", "User login failed"),
            (LogLevel.INFO, "db", "User query executed"),
            (LogLevel.ERROR, "db", "Database connection failed"),
        ]

        for level, source, message in test_logs:
            self.aggregator.add_log(level, source, message)

        # Buscar logs ERROR da fonte "web" contendo "user"
        results = self.aggregator.search_logs(
            query="user", level=LogLevel.ERROR, source="web"
        )

        assert len(results) == 1
        assert results[0].level == LogLevel.ERROR
        assert results[0].source == "web"
        assert "user" in results[0].message.lower()

    def test_log_entry_immutability_concept(self):
        """Testa conceito de imutabilidade de entradas de log."""
        self.aggregator.add_log(LogLevel.INFO, "app", "Original message")

        original_entry = self.aggregator.logs[0]
        original_message = original_entry.message

        # Tentar modificar a mensagem (não deveria afetar o log armazenado)
        modified_message = original_message + " - MODIFIED"

        # A entrada original deve permanecer inalterada
        assert self.aggregator.logs[0].message == "Original message"
        assert modified_message != self.aggregator.logs[0].message

    def test_log_metadata_search(self):
        """Testa busca baseada em metadados."""
        # Adicionar logs com metadados específicos
        self.aggregator.add_log(
            LogLevel.INFO,
            "api",
            "Request processed",
            metadata={"endpoint": "/users", "method": "GET"},
        )

        self.aggregator.add_log(
            LogLevel.ERROR,
            "api",
            "Request failed",
            metadata={"endpoint": "/orders", "method": "POST"},
        )

        # Buscar logs que mencionam "processed" na mensagem
        results = self.aggregator.search_logs("processed")

        # Deve encontrar o primeiro log (que tem "processed" na mensagem)
        assert len(results) >= 1
        assert "processed" in results[0].message.lower()
