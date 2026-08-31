"""Alerting system for Aura CLI.

Provides alert rule creation, condition evaluation and notifications.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Severidade de alerta."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AlertRule:
    """Alert rule (id, name, condition, severity, cooldown)."""

    id: str
    name: str
    condition: Callable[[Dict[str, Any]], bool]
    severity: AlertSeverity
    message: str
    enabled: bool = True


@dataclass
class Alert:
    """Generated alert (id, rule_id, severity, message, timestamp)."""

    id: str
    rule_id: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertingSystem:
    """Alerting system with rule management and resolution."""

    def __init__(self):
        """Initialise the alerting system."""
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: List[Alert] = []
        self.stats = get_stats()

        logger.info("AlertingSystem initialized")

    def add_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self.rules[rule.id] = rule
        logger.info(f"Regra de alerta '{rule.name}' ({rule.id}) adicionada")

    def evaluate_rules(self, context: Dict[str, Any]) -> List[Alert]:
        """Evaluate all rules against current metrics."""
        new_alerts = []

        for rule in self.rules.values():
            if not rule.enabled:
                continue

            try:
                if rule.condition(context):
                    import uuid

                    alert = Alert(
                        id=str(uuid.uuid4())[:8],
                        rule_id=rule.id,
                        severity=rule.severity,
                        message=rule.message,
                        timestamp=datetime.now(),
                        metadata={"context": context},
                    )

                    self.alerts.append(alert)
                    new_alerts.append(alert)

                    logger.warning(
                        f"Alerta gerado: {rule.name} ({rule.severity.value})"
                    )
            except Exception as e:
                logger.error(f"Error evaluating rule '{rule.name}': {e}", exc_info=True)

        if new_alerts:
            self.stats.track_tool_usage("alerting_system")

        return new_alerts

    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve um alerta.

        Args:
            alert_id: ID do alerta

        Returns:
            True se resolvido
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                logger.info(f"Alerta {alert_id} resolvido")
                return True

        return False

    def get_active_alerts(
        self, severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """Return currently active alerts."""
        alerts = [a for a in self.alerts if not a.resolved]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.ERROR: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 3,
        }

        alerts.sort(
            key=lambda a: (severity_order[a.severity], a.timestamp), reverse=True
        )

        return alerts

    def get_statistics(self) -> Dict[str, Any]:
        """Return alerting statistics as a dict."""
        total = len(self.alerts)
        active = len([a for a in self.alerts if not a.resolved])
        resolved = total - active

        by_severity = {}
        for severity in AlertSeverity:
            by_severity[severity.value] = len(
                [a for a in self.alerts if a.severity == severity and not a.resolved]
            )

        return {
            "total_alerts": total,
            "active_alerts": active,
            "resolved_alerts": resolved,
            "by_severity": by_severity,
            "total_rules": len(self.rules),
        }


# Factory function for singleton pattern
_alerting_instance: Optional[AlertingSystem] = None


def get_alerting_system() -> AlertingSystem:
    """
    Get or create AlertingSystem instance (singleton).

    Returns:
        AlertingSystem instance
    """
    global _alerting_instance
    if _alerting_instance is None:
        _alerting_instance = AlertingSystem()
    return _alerting_instance
