"""
Testes de Integração para Ferramentas OPS do Aura CLI.

Este módulo contém testes de integração que verificam o funcionamento completo
do sistema de monitoramento OPS, incluindo integração entre logs, métricas e
sistema de alertas. Testa fluxos end-to-end de coleta, processamento e alertas.

Componentes Testados:
    - LogsAggregator: Agregação e processamento de logs
    - MetricsCollector: Coleta e armazenamento de métricas
    - AlertingSystem: Sistema de alertas baseado em regras
    - Integração entre componentes: Fluxo completo de monitoramento

Cenários de Teste:
    - Integração Logs-Métricas: Conversão de logs em métricas
    - Alertas com Métricas: Geração de alertas baseados em métricas
    - Regras de Alerta: Criação e avaliação de regras customizadas

Validações:
    - Verifica que logs são convertidos em métricas corretamente
    - Valida que métricas acionam alertas quando necessário
    - Confirma que regras de alerta são avaliadas corretamente
    - Testa severidade e mensagens de alertas

Estrutura de Testes:
    - TestMonitoringIntegration: Classe principal de testes
    - test_logs_and_metrics_integration: Testa fluxo logs → métricas
    - test_alerting_with_metrics: Testa fluxo métricas → alertas

Exemplo de Uso:
    ```python
    def test_integration():
        logs_agg = LogsAggregator()
        metrics = MetricsCollector()

        logs_agg.add_log(LogLevel.ERROR, "app", "Error occurred")
        error_count = len(logs_agg.get_recent_errors())
        metrics.record_metric("error_count", error_count, MetricType.GAUGE)

        assert metrics.get_metric("error_count") == 1
    ```

Dependências:
    - pytest: Framework de testes
    - LogsAggregator: Sistema de agregação de logs
    - MetricsCollector: Sistema de coleta de métricas
    - AlertingSystem: Sistema de alertas
"""

from aura_cli.core.ops_tools.monitoring.alerting_system import (
    AlertingSystem,
    AlertSeverity,
)
from aura_cli.core.ops_tools.monitoring.logs_aggregator import LogLevel, LogsAggregator
from aura_cli.core.ops_tools.monitoring.metrics_collector import (
    MetricsCollector,
    MetricType,
)


class TestMonitoringIntegration:
    """Testes de integração para monitoramento."""

    def test_logs_and_metrics_integration(self):
        """Testa integração entre logs e métricas."""
        logs_agg = LogsAggregator()
        metrics = MetricsCollector()

        # Adiciona logs
        logs_agg.add_log(LogLevel.INFO, "app", "Application started")
        logs_agg.add_log(LogLevel.ERROR, "app", "Error occurred")

        # Registra métricas baseadas em logs
        error_count = len(logs_agg.get_recent_errors())
        metrics.record_metric("error_count", error_count, MetricType.GAUGE)

        assert metrics.get_metric("error_count") == 1

    def test_alerting_with_metrics(self):
        """Testa sistema de alertas com métricas."""
        metrics = MetricsCollector()
        alerting = AlertingSystem()

        # Registra métrica alta
        metrics.record_metric("cpu_usage", 95.0, MetricType.GAUGE)

        # Cria regra de alerta
        import uuid

        from aura_cli.core.ops_tools.monitoring.alerting_system import AlertRule

        def check_cpu(context):
            cpu = context.get("metrics", {}).get("cpu_usage")
            return cpu and cpu > 90.0

        rule = AlertRule(
            id=str(uuid.uuid4())[:8],
            name="High CPU",
            condition=check_cpu,
            severity=AlertSeverity.WARNING,
            message="CPU usage is above 90%",
        )

        alerting.add_rule(rule)

        # Avalia regras
        context = {"metrics": {"cpu_usage": metrics.get_metric("cpu_usage")}}
        alerts = alerting.evaluate_rules(context)

        assert len(alerts) > 0
        assert alerts[0].severity == AlertSeverity.WARNING
