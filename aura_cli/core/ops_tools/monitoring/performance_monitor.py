"""Performance monitor for Aura CLI.

Provides system, application and operation performance monitoring.
"""

from dataclasses import dataclass
from datetime import datetime
import time
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)

import psutil

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric (name, value, unit, timestamp)."""

    name: str
    value: float
    unit: str
    timestamp: datetime
    threshold: Optional[float] = None


class PerformanceMonitor:
    """Performance monitor with CPU, memory, disk and bottleneck detection."""

    def __init__(self):
        """Initialise the performance monitor."""
        self.metrics: List[PerformanceMetric] = []
        self.stats = get_stats()

        logger.info("PerformanceMonitor initialized")

    def collect_system_metrics(self, *, cpu_interval: float = 1.0) -> Dict[str, Any]:
        """Collect current system-level metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=cpu_interval)
            cpu_count = psutil.cpu_count()

            memory = psutil.virtual_memory()

            disk = psutil.disk_usage("/")

            net_io = psutil.net_io_counters()

            metrics = {
                "cpu": {"percent": cpu_percent, "count": cpu_count},
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100,
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                },
            }

            self._record_metric("cpu_percent", cpu_percent, "%", 80.0)
            self._record_metric("memory_percent", memory.percent, "%", 90.0)
            self._record_metric(
                "disk_percent", (disk.used / disk.total) * 100, "%", 90.0
            )

            logger.debug("Métricas do sistema coletadas")

            return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics do sistema: {e}", exc_info=True)
            return {}

    def monitor_operation(
        self,
        operation_name: str,
        operation_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[Any, Dict[str, Any]]:
        """Context manager to monitor a named operation."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss

        try:
            result = operation_func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss

        duration = end_time - start_time
        memory_delta = end_memory - start_memory

        metrics = {
            "operation": operation_name,
            "duration": duration,
            "memory_delta": memory_delta,
            "success": success,
            "error": error,
        }

        self._record_metric(f"{operation_name}_duration", duration, "seconds")
        self._record_metric(f"{operation_name}_memory", memory_delta, "bytes")

        logger.debug(
            f"Operação '{operation_name}' monitorada: "
            f"{duration:.2f}s, {memory_delta / 1024 / 1024:.2f}MB"
        )

        return result, metrics

    def _record_metric(
        self, name: str, value: float, unit: str, threshold: Optional[float] = None
    ) -> None:
        """Record a single metric data point internally."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=datetime.now(),
            threshold=threshold,
        )

        self.metrics.append(metric)

        if len(self.metrics) > 1000:
            self.metrics = self.metrics[-1000:]

        if threshold and value > threshold:
            logger.warning(
                f"Métrica {name} excedeu threshold: {value}{unit} > {threshold}{unit}"
            )

    def get_performance_summary(self, *, cpu_interval: float = 1.0) -> Dict[str, Any]:
        """Return a performance summary as a dict."""
        system_metrics = self.collect_system_metrics(cpu_interval=cpu_interval)

        operation_metrics = {}
        for metric in self.metrics:
            if "_duration" in metric.name:
                op_name = metric.name.replace("_duration", "")
                if op_name not in operation_metrics:
                    operation_metrics[op_name] = {
                        "count": 0,
                        "total_duration": 0.0,
                        "avg_duration": 0.0,
                    }
                operation_metrics[op_name]["count"] += 1
                operation_metrics[op_name]["total_duration"] += metric.value

        for data in operation_metrics.values():
            if data["count"] > 0:
                data["avg_duration"] = data["total_duration"] / data["count"]

        return {
            "system": system_metrics,
            "operations": operation_metrics,
            "total_metrics": len(self.metrics),
        }
