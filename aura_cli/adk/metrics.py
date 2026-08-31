"""ADK Metrics API — agent observability and performance tracking.

This module is the **public** metrics API for AuraCli plugins and ADK agents.
The underlying implementation lives in ``aura_cli.application.observability``.

Quick start
-----------
Record a custom metric::

    from aura_cli.adk.metrics import record_metric, get_metrics_collector

    record_metric("my_plugin.items_processed", 42.0)

    collector = get_metrics_collector()
    summary = collector.get_summary()
    print(summary["total_executions"])

Track execution time with a context manager::

    from aura_cli.adk.metrics import track_performance

    with track_performance("my_operation") as tracker:
        tracker.add_metadata("input_size", len(data))
        result = do_work(data)
        tracker.add_metric("output_size", len(result))

    print(f"Took {tracker.duration:.2f}s")

Track an agent execution::

    from aura_cli.adk.metrics import get_metrics_collector

    collector = get_metrics_collector()
    collector.record_agent_execution(
        agent_name="my_agent",
        success=True,
        time_seconds=1.23,
        tokens=512,
    )

    agent_metrics = collector.get_agent_metrics("my_agent")
    print(f"Success rate: {agent_metrics.success_rate:.1f}%")
    print(f"p95 latency:  {agent_metrics.p95_time:.2f}s")
"""

from aura_cli.application.observability import (
    AgentMetrics,
    MetricPoint,
    MetricsCollector,
    PerformanceTracker,
    get_metrics_collector,
    record_metric,
    track_performance,
)

__all__ = [
    "AgentMetrics",
    "MetricPoint",
    "MetricsCollector",
    "PerformanceTracker",
    "get_metrics_collector",
    "record_metric",
    "track_performance",
]
