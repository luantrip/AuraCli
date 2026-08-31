"""Monitoring dashboard for Aura CLI.

Provides visualisation of metrics, logs and alerts in an interactive dashboard format.
"""

from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from rich.console import Console
from rich.table import Table

from aura_cli.core.logger import get_logger
from aura_cli.core.ops_tools.monitoring.alerting_system import AlertingSystem
from aura_cli.core.ops_tools.monitoring.logs_aggregator import LogsAggregator
from aura_cli.core.ops_tools.monitoring.metrics_collector import MetricsCollector
from aura_cli.core.ops_tools.monitoring.performance_monitor import PerformanceMonitor

logger = get_logger(__name__)
console = Console()


@dataclass
class DashboardWidget:
    """Dashboard widget (id, title, widget_type, data)."""

    id: str
    title: str
    widget_type: str
    data: Dict[str, Any]
    position: Tuple[int, int] = (0, 0)


class MonitoringDashboard:
    """Aggregates monitoring metrics into a dashboard view."""

    def __init__(
        self,
        logs_aggregator: Optional[LogsAggregator] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        alerting_system: Optional[AlertingSystem] = None,
        performance_monitor: Optional[PerformanceMonitor] = None,
    ):
        """Initialise the monitoring dashboard."""
        self.logs_aggregator = logs_aggregator
        self.metrics_collector = metrics_collector
        self.alerting_system = alerting_system
        self.performance_monitor = performance_monitor

        self.widgets: List[DashboardWidget] = []

        logger.info("MonitoringDashboard initialized")

    def display_overview(self) -> None:
        """Display a monitoring overview to the console."""
        from aura_cli.core.ui_bridge import UIStyles

        console.print("\n[bold][S] Dashboard de Monitoramento[/bold]\n")

        if self.performance_monitor:
            summary = self.performance_monitor.get_performance_summary(cpu_interval=0.0)
            system = summary.get("system", {})

            table = Table(title="Métricas do Sistema", show_header=True)
            table.add_column("Métrica", style=UIStyles.PRIMARY)
            table.add_column("Valor", style=UIStyles.SECONDARY)

            if "cpu" in system:
                table.add_row("CPU", f"{system['cpu']['percent']:.1f}%")
            if "memory" in system:
                table.add_row("Memória", f"{system['memory']['percent']:.1f}%")
            if "disk" in system:
                table.add_row("Disco", f"{system['disk']['percent']:.1f}%")

            console.print(table)

        if self.alerting_system:
            alerts = self.alerting_system.get_active_alerts()

            if alerts:
                alert_table = Table(title="Alertas Ativos", show_header=True)
                alert_table.add_column("Severidade", style=UIStyles.PRIMARY)
                alert_table.add_column("Mensagem", style=UIStyles.BODY)
                alert_table.add_column("Data", style=UIStyles.MUTED)

                for alert in alerts[:10]:  # Top 10
                    severity_style = {
                        "critical": UIStyles.ERROR,
                        "error": UIStyles.ERROR,
                        "warning": UIStyles.WARNING,
                        "info": UIStyles.INFO,
                    }.get(alert.severity.value, UIStyles.BODY)

                    alert_table.add_row(
                        f"[{severity_style}]{alert.severity.value.upper()}[/{severity_style}]",
                        alert.message[:50],
                        alert.timestamp.strftime("%H:%M:%S"),
                    )

                console.print(alert_table)

        if self.logs_aggregator:
            recent_logs = self.logs_aggregator.logs[-10:]

            if recent_logs:
                log_table = Table(title="Logs Recentes", show_header=True)
                log_table.add_column("Nível", style=UIStyles.PRIMARY)
                log_table.add_column("Fonte", style=UIStyles.SECONDARY)
                log_table.add_column("Mensagem", style=UIStyles.BODY)

                for log in reversed(recent_logs):
                    log_table.add_row(log.level.value, log.source, log.message[:60])

                console.print(log_table)

    def add_widget(self, widget: DashboardWidget) -> None:
        """
        Adiciona widget ao dashboard.

        Args:
            widget: Widget a adicionar
        """
        self.widgets.append(widget)
        logger.debug(f"Widget '{widget.title}' adicionado ao dashboard")

    def get_statistics(self) -> Dict[str, Any]:
        """Return dashboard statistics as a dict."""
        stats: Dict[str, Any] = {"widgets_count": len(self.widgets)}

        if self.logs_aggregator:
            stats["logs"] = self.logs_aggregator.get_statistics()

        if self.metrics_collector:
            stats["metrics"] = self.metrics_collector.get_statistics()

        if self.alerting_system:
            stats["alerts"] = self.alerting_system.get_statistics()

        return stats


# Factory function for singleton pattern
_dashboard_instance: Optional[MonitoringDashboard] = None


def get_dashboard() -> MonitoringDashboard:
    """
    Get or create MonitoringDashboard instance (singleton).

    Returns:
        MonitoringDashboard instance
    """
    global _dashboard_instance
    if _dashboard_instance is None:
        _dashboard_instance = MonitoringDashboard()
    return _dashboard_instance
