"""
Testes para módulos de monitoring do Aura CLI.

Este pacote contém testes para:
- logs_aggregator: Coleta, agregação e análise de logs de múltiplas fontes
- metrics_collector: Coleta, armazenamento e análise de métricas de sistema e aplicação
- alerting_system: Criação, gerenciamento e notificação de alertas baseados em condições
- performance_monitor: Monitoramento de performance de sistema, aplicação e operações
- dashboard: Visualização de métricas, logs e alertas em formato de dashboard interativo
- health: Verificação de saúde de serviços
- monitoring: Monitoramento geral do sistema
"""

__all__ = [
    "test_alerting_system",
    "test_dashboard",
    "test_health",
    "test_logs_aggregator",
    "test_metrics_collector",
    "test_monitoring",
    "test_performance_monitor",
]
