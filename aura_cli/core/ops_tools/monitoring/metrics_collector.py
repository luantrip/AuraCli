"""Metrics collector for Aura CLI.

Provides collection, storage and analysis of system and application metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class MetricType(Enum):
    """Metric type enum."""

    COUNTER = "counter"  # Contador (sempre cresce)
    GAUGE = "gauge"  # Instantaneous measurement
    HISTOGRAM = "histogram"  # Distribution
    SUMMARY = "summary"  # Statistical summary


@dataclass
class Metric:
    """Collected metric (name, value, metric_type, timestamp, labels)."""

    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None


class MetricsCollector:
    """Metrics collector with aggregation, analysis and export."""

    def __init__(self, retention_hours: int = 24):
        """Initialise the collector."""
        self.retention_hours = retention_hours
        self.metrics: List[Metric] = []
        self.stats = get_stats()

        logger.info(f"MetricsCollector initialized (retention: {retention_hours}h)")

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None,
        unit: Optional[str] = None,
    ) -> None:
        """Record a metric data point."""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            timestamp=datetime.now(),
            labels=labels or {},
            unit=unit,
        )

        self.metrics.append(metric)

        self._cleanup_old_metrics()

        logger.debug(f"Métrica registrada: {name}={value}")

    def get_metric(
        self, name: str, labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """Get the latest value for a metric."""
        matching = self._filter_metrics(name, labels)

        if not matching:
            return None

        latest = max(matching, key=lambda m: m.timestamp)
        return latest.value

    def get_metric_history(
        self, name: str, labels: Optional[Dict[str, str]] = None, limit: int = 100
    ) -> List[Metric]:
        """Return historical values for a metric."""
        matching = self._filter_metrics(name, labels)

        matching.sort(key=lambda m: m.timestamp, reverse=True)

        return matching[:limit]

    def aggregate_metrics(
        self,
        name: str,
        aggregation: str = "avg",
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[float]:
        """Return aggregated statistics for a metric."""
        matching = self._filter_metrics(name, labels)

        if not matching:
            return None

        values = [m.value for m in matching]

        if aggregation == "avg":
            return sum(values) / len(values)
        elif aggregation == "sum":
            return sum(values)
        elif aggregation == "min":
            return min(values)
        elif aggregation == "max":
            return max(values)

        return None

    def _filter_metrics(
        self, name: str, labels: Optional[Dict[str, str]]
    ) -> List[Metric]:
        """Filter metrics by name and labels."""
        matching = [m for m in self.metrics if m.name == name]

        if labels:
            filtered = []
            for metric in matching:
                match = True
                for key, value in labels.items():
                    if metric.labels.get(key) != value:
                        match = False
                        break
                if match:
                    filtered.append(metric)
            matching = filtered

        return matching

    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than the retention period."""
        cutoff = datetime.now().timestamp() - (self.retention_hours * 3600)

        original_count = len(self.metrics)
        self.metrics = [m for m in self.metrics if m.timestamp.timestamp() > cutoff]

        removed = original_count - len(self.metrics)
        if removed > 0:
            logger.debug(f"{removed} métricas antigas removidas")

    def get_statistics(self) -> Dict[str, Any]:
        """Return collector statistics as a dict."""
        metrics_by_name: Dict[str, List[Metric]] = {}
        for metric in self.metrics:
            if metric.name not in metrics_by_name:
                metrics_by_name[metric.name] = []
            metrics_by_name[metric.name].append(metric)

        return {
            "total_metrics": len(self.metrics),
            "unique_metric_names": len(metrics_by_name),
            "retention_hours": self.retention_hours,
        }


# Factory function for singleton pattern
_collector_instance: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get or create MetricsCollector instance (singleton).

    Returns:
        MetricsCollector instance
    """
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = MetricsCollector()
    return _collector_instance
