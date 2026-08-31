"""
ADK Metrics System.

Provides performance tracking and analytics for agents.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import logging
import statistics
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class AgentMetrics:
    """Metrics for a single agent."""

    agent_name: str
    executions: int = 0
    successes: int = 0
    failures: int = 0
    total_tokens: int = 0
    total_time: float = 0.0
    execution_times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.executions == 0:
            return 0.0
        return (self.successes / self.executions) * 100

    @property
    def average_time(self) -> float:
        """Get average execution time."""
        if not self.execution_times:
            return 0.0
        return statistics.mean(self.execution_times)

    @property
    def median_time(self) -> float:
        """Get median execution time."""
        if not self.execution_times:
            return 0.0
        return statistics.median(self.execution_times)

    @property
    def p95_time(self) -> float:
        """Get 95th percentile execution time."""
        if len(self.execution_times) < 20:
            return max(self.execution_times) if self.execution_times else 0.0
        sorted_times = sorted(self.execution_times)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[idx]

    @property
    def tokens_per_execution(self) -> float:
        """Get average tokens per execution."""
        if self.executions == 0:
            return 0.0
        return self.total_tokens / self.executions

    def record_execution(
        self,
        success: bool,
        time_seconds: float,
        tokens: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """Record an execution."""
        self.executions += 1
        self.execution_times.append(time_seconds)
        self.total_time += time_seconds
        self.total_tokens += tokens

        if success:
            self.successes += 1
        else:
            self.failures += 1
            if error:
                self.errors.append(error)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_name": self.agent_name,
            "executions": self.executions,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": self.success_rate,
            "total_tokens": self.total_tokens,
            "tokens_per_execution": self.tokens_per_execution,
            "average_time": self.average_time,
            "median_time": self.median_time,
            "p95_time": self.p95_time,
            "total_time": self.total_time,
            "recent_errors": self.errors[-5:],
        }


class PerformanceTracker:
    """
    Tracks performance metrics for a specific operation.

    Can be used as a context manager:
        ```python
        with PerformanceTracker("my_operation") as tracker:
            # do work
            tracker.add_metric("items_processed", 100)

        print(tracker.duration)
        ```
    """

    def __init__(self, operation_name: str):
        """Initialize the instance."""
        self.operation_name = operation_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.metrics: Dict[str, float] = {}
        self.metadata: Dict[str, Any] = {}

    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time

    def start(self) -> PerformanceTracker:
        """Start tracking."""
        self.start_time = time.time()
        return self

    def stop(self) -> PerformanceTracker:
        """Stop tracking."""
        self.end_time = time.time()
        return self

    def add_metric(self, name: str, value: float) -> None:
        """Add a metric."""
        self.metrics[name] = value

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata."""
        self.metadata[key] = value

    def __enter__(self) -> PerformanceTracker:
        """Enter the context manager."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager and clean up."""
        self.stop()
        if exc_type:
            self.add_metadata("error", str(exc_val))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation_name,
            "duration": self.duration,
            "metrics": self.metrics,
            "metadata": self.metadata,
        }


class MetricsCollector:
    """
    Central collector for all metrics.

    Aggregates metrics from multiple agents and operations.
    """

    def __init__(self):
        """Initialize the instance."""
        self._agent_metrics: Dict[str, AgentMetrics] = {}
        self._custom_metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._callbacks: List[Callable[[MetricPoint], None]] = []
        self._start_time = time.time()

    def get_agent_metrics(self, agent_name: str) -> AgentMetrics:
        """Get or create metrics for an agent."""
        if agent_name not in self._agent_metrics:
            self._agent_metrics[agent_name] = AgentMetrics(agent_name=agent_name)
        return self._agent_metrics[agent_name]

    def record_agent_execution(
        self,
        agent_name: str,
        success: bool,
        time_seconds: float,
        tokens: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """Record an agent execution."""
        metrics = self.get_agent_metrics(agent_name)
        metrics.record_execution(success, time_seconds, tokens, error)

        # Emit metric point
        self._emit(
            MetricPoint(
                name=f"agent.{agent_name}.execution",
                value=time_seconds,
                labels={"success": str(success)},
            )
        )

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a custom metric."""
        point = MetricPoint(name=name, value=value, labels=labels or {})
        self._custom_metrics[name].append(point)
        self._emit(point)

    def _emit(self, point: MetricPoint) -> None:
        """Emit metric to callbacks."""
        for callback in self._callbacks:
            try:
                callback(point)
            except Exception as e:
                logger.error(f"Metric callback error: {e}")

    def on_metric(self, callback: Callable[[MetricPoint], None]) -> None:
        """Register a metric callback."""
        self._callbacks.append(callback)

    def get_all_agent_metrics(self) -> Dict[str, AgentMetrics]:
        """Get all agent metrics."""
        return dict(self._agent_metrics)

    def get_metric_series(
        self,
        name: str,
        since: Optional[float] = None,
    ) -> List[MetricPoint]:
        """Get metric time series."""
        points = self._custom_metrics.get(name, [])
        if since:
            points = [p for p in points if p.timestamp >= since]
        return points

    def get_summary(self) -> Dict[str, Any]:
        """Get overall metrics summary."""
        total_executions = sum(m.executions for m in self._agent_metrics.values())
        total_successes = sum(m.successes for m in self._agent_metrics.values())
        total_tokens = sum(m.total_tokens for m in self._agent_metrics.values())

        return {
            "uptime_seconds": time.time() - self._start_time,
            "total_agents": len(self._agent_metrics),
            "total_executions": total_executions,
            "total_successes": total_successes,
            "total_failures": total_executions - total_successes,
            "overall_success_rate": (
                (total_successes / total_executions * 100)
                if total_executions > 0
                else 0
            ),
            "total_tokens": total_tokens,
            "custom_metrics_count": sum(len(v) for v in self._custom_metrics.values()),
            "agents": {
                name: metrics.to_dict() for name, metrics in self._agent_metrics.items()
            },
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._agent_metrics.clear()
        self._custom_metrics.clear()
        self._start_time = time.time()


# Global metrics collector
_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def record_metric(name: str, value: float, **labels) -> None:
    """Convenience function to record a metric."""
    get_metrics_collector().record_metric(name, value, labels)


def track_performance(operation_name: str) -> PerformanceTracker:
    """Create a performance tracker."""
    return PerformanceTracker(operation_name)
