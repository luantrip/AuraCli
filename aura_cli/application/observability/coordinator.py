"""Coordinate application metrics with the active session statistics sink."""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Protocol

if TYPE_CHECKING:
    from aura_cli.application.observability import AgentMetrics, MetricsCollector

logger = logging.getLogger(__name__)


class StatsSink(Protocol):
    """Minimum session-statistics surface consumed by telemetry coordination."""

    @property
    def total_tokens(self) -> int: ...

    prompt_tokens: int
    completion_tokens: int
    files_read: int
    files_edited: int
    files_created: int
    shell_commands_run: int
    current_status: str
    tools_used: Mapping[str, int]
    session_start: Any

    def add_tokens(self, usage: Dict[str, int]) -> None: ...

    def track_tool_usage(self, tool_name: str) -> None: ...

    def set_status(self, status: str, message: str) -> None: ...

    def update_last_activity(self) -> None: ...


class TelemetryCoordinator:
    """Coordinate agent metrics with the active session statistics sink."""

    _instance: Optional[TelemetryCoordinator] = None
    _lock = threading.Lock()

    def __new__(cls) -> TelemetryCoordinator:
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the metrics bridge."""
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._stats_tracker: Optional[StatsSink] = None
        self._adk_metrics_collector: Optional[MetricsCollector] = None
        self._sync_enabled = True
        self._sync_lock = threading.Lock()
        self._last_sync_time: float = 0.0
        self._sync_interval: float = 5.0  # Sync every 5 seconds

        self._initialized = True
        logger.info("TelemetryCoordinator initialized")

    def set_stats_tracker(self, stats_tracker: StatsSink) -> None:
        """Set the active session statistics sink."""
        self._stats_tracker = stats_tracker
        logger.debug("StatsTracker set in MetricsBridge")

    def set_adk_metrics_collector(self, metrics_collector: MetricsCollector) -> None:
        """Set the ADK MetricsCollector instance."""
        self._adk_metrics_collector = metrics_collector
        logger.debug("MetricsCollector set in MetricsBridge")

    def enable_sync(self) -> None:
        """Enable automatic synchronization."""
        self._sync_enabled = True
        logger.debug("MetricsBridge sync enabled")

    def disable_sync(self) -> None:
        """Disable automatic synchronization."""
        self._sync_enabled = False
        logger.debug("MetricsBridge sync disabled")

    def sync_adk_metrics(self, agent_id: str, metrics: AgentMetrics) -> None:
        """
        Synchronize agent metrics into the active session statistics.

        Args:
            agent_id: Agent ID
            metrics: ADK AgentMetrics instance
        """
        if not self._sync_enabled or not self._stats_tracker:
            return

        try:
            with self._sync_lock:
                # Sync tokens
                if metrics.total_tokens > 0:
                    self._stats_tracker.add_tokens(
                        {
                            "total_tokens": metrics.total_tokens,
                            "prompt_tokens": int(
                                metrics.total_tokens * 0.6
                            ),  # Estimate
                            "completion_tokens": int(
                                metrics.total_tokens * 0.4
                            ),  # Estimate
                        }
                    )

                # Track tool usage (agent executions as tool usage)
                if metrics.executions > 0:
                    tool_name = f"adk_agent_{agent_id}"
                    for _ in range(metrics.executions):
                        self._stats_tracker.track_tool_usage(tool_name)

                # Update status based on success rate
                if metrics.executions > 0:
                    if metrics.success_rate >= 90:
                        status = "idle"
                    elif metrics.success_rate >= 50:
                        status = "running"
                    else:
                        status = "error"

                    self._stats_tracker.set_status(
                        status,
                        f"ADK Agent {agent_id}: {metrics.success_rate:.1f}% success rate",
                    )

                logger.debug(f"Synced ADK metrics for {agent_id} to Stats")

        except Exception as e:
            logger.warning(f"Error syncing ADK metrics for {agent_id}: {e}")

    def track_adk_execution(
        self,
        agent_id: str,
        execution_time: float,
        tokens: int = 0,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """
        Track an ADK agent execution in the Stats system.

        Args:
            agent_id: Agent ID
            execution_time: Execution time in seconds
            tokens: Tokens used (optional)
            success: Whether execution was successful
            error: Error message if failed
        """
        if not self._sync_enabled or not self._stats_tracker:
            return

        try:
            # Track tokens
            if tokens > 0:
                self._stats_tracker.add_tokens(
                    {
                        "total_tokens": tokens,
                        "prompt_tokens": int(tokens * 0.6),
                        "completion_tokens": int(tokens * 0.4),
                    }
                )

            # Track tool usage
            self._stats_tracker.track_tool_usage(f"adk_agent_{agent_id}")

            # Update last activity
            self._stats_tracker.update_last_activity()

            logger.debug(
                f"Tracked ADK execution for {agent_id}: {execution_time:.2f}s, {tokens} tokens"
            )

        except Exception as e:
            logger.warning(f"Error tracking ADK execution for {agent_id}: {e}")

    def get_unified_metrics(self) -> Dict[str, Any]:
        """
        Get unified metrics from both systems.

        Returns:
            Dict with consolidated metrics
        """
        unified: Dict[str, Any] = {"legacy_stats": {}, "adk_metrics": {}, "summary": {}}

        if self._stats_tracker:
            unified["legacy_stats"] = {
                "total_tokens": self._stats_tracker.total_tokens,
                "prompt_tokens": self._stats_tracker.prompt_tokens,
                "completion_tokens": self._stats_tracker.completion_tokens,
                "files_read": self._stats_tracker.files_read,
                "files_edited": self._stats_tracker.files_edited,
                "files_created": self._stats_tracker.files_created,
                "shell_commands": self._stats_tracker.shell_commands_run,
                "current_status": self._stats_tracker.current_status,
                "tools_used": dict(self._stats_tracker.tools_used),
            }

        if self._adk_metrics_collector:
            adk_metrics_dict = {}
            all_agent_metrics = self._adk_metrics_collector.get_all_agent_metrics()

            for agent_name, metrics in all_agent_metrics.items():
                adk_metrics_dict[agent_name] = metrics.to_dict()

            unified["adk_metrics"] = adk_metrics_dict

        # Calculate summary
        total_tokens = unified["legacy_stats"].get("total_tokens", 0)
        adk_total_tokens = sum(
            m.get("total_tokens", 0) for m in unified["adk_metrics"].values()
        )

        unified["summary"] = {
            "total_tokens_all": total_tokens + adk_total_tokens,
            "total_agents": len(unified["adk_metrics"]),
            "total_tools_used": len(unified["legacy_stats"].get("tools_used", {})),
            "session_duration": time.time()
            - (
                self._stats_tracker.session_start.timestamp()
                if self._stats_tracker
                else time.time()
            ),
        }

        return unified

    def get_agent_performance(self, agent_id: str) -> Dict[str, Any]:
        """
        Get performance metrics for a specific agent.

        Args:
            agent_id: Agent ID

        Returns:
            Dict with agent performance metrics
        """
        performance: Dict[str, Any] = {
            "agent_id": agent_id,
            "adk_metrics": None,
            "legacy_stats": {},
        }

        if self._adk_metrics_collector:
            adk_metrics = self._adk_metrics_collector.get_agent_metrics(agent_id)
            performance["adk_metrics"] = adk_metrics.to_dict()

        if self._stats_tracker:
            tool_name = f"adk_agent_{agent_id}"
            performance["legacy_stats"] = {
                "tool_usage_count": self._stats_tracker.tools_used.get(tool_name, 0)
            }

        return performance

    def auto_sync(self) -> None:
        """Perform automatic synchronization if interval has passed."""
        current_time = time.time()
        if current_time - self._last_sync_time < self._sync_interval:
            return

        if not self._sync_enabled:
            return

        try:
            if self._adk_metrics_collector and self._stats_tracker:
                # Sync all agent metrics
                all_agent_metrics = self._adk_metrics_collector.get_all_agent_metrics()
                for agent_name, metrics in all_agent_metrics.items():
                    self.sync_adk_metrics(agent_name, metrics)

                self._last_sync_time = current_time
                logger.debug("Auto-synced ADK metrics to Stats")
        except Exception as e:
            logger.warning(f"Error in auto-sync: {e}")


def get_telemetry_coordinator() -> TelemetryCoordinator:
    """Get the process-wide telemetry coordinator."""
    return TelemetryCoordinator()
