"""Testes para monitoring tools."""


class TestAlertingSystem:
    """Testes para alerting_system."""

    def test_alerting_system_import(self):
        """Testa importação do módulo alerting_system."""
        from aura_cli.core.ops_tools.monitoring import alerting_system

        assert alerting_system is not None


class TestDashboard:
    """Testes para dashboard."""

    def test_dashboard_import(self):
        """Testa importação do módulo dashboard."""
        from aura_cli.core.ops_tools.monitoring import dashboard

        assert dashboard is not None


class TestLogsAggregator:
    """Testes para logs_aggregator."""

    def test_logs_aggregator_import(self):
        """Testa importação do módulo logs_aggregator."""
        from aura_cli.core.ops_tools.monitoring import logs_aggregator

        assert logs_aggregator is not None


class TestMetricsCollector:
    """Testes para metrics_collector."""

    def test_metrics_collector_import(self):
        """Testa importação do módulo metrics_collector."""
        from aura_cli.core.ops_tools.monitoring import metrics_collector

        assert metrics_collector is not None


class TestPerformanceMonitor:
    """Testes para performance_monitor."""

    def test_performance_monitor_import(self):
        """Testa importação do módulo performance_monitor."""
        from aura_cli.core.ops_tools.monitoring import performance_monitor

        assert performance_monitor is not None
