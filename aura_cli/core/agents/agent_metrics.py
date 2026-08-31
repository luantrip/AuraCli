"""Per-agent performance metrics for Aura CLI.

MetricsCollector (singleton via get_metrics_collector()) aggregates
TaskExecution and ToolExecution records across all agents. AgentMetrics
tracks task counts, execution times, token usage, errors and tool patterns
for a single agent. Exportable to JSON.
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TaskExecution:
    """
    Record of a single task execution.

    Attributes:
        task_id: Unique task identifier
        started_at: Start timestamp (Unix time)
        ended_at: End timestamp (None if still running)
        success: Whether task completed successfully
        tokens_used: Number of LLM tokens consumed
        tools_called: List of tool names called during execution
        error: Error message if task failed
    """

    task_id: str
    started_at: float
    ended_at: Optional[float] = None
    success: bool = False
    tokens_used: int = 0
    tools_called: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def duration(self) -> float:
        """
        Calculate task duration in seconds.

        Returns:
            Duration in seconds (ongoing tasks return elapsed time)
        """
        if self.ended_at:
            return self.ended_at - self.started_at
        return time.time() - self.started_at


@dataclass
class ToolExecution:
    """
    Record of a single tool execution.

    Attributes:
        tool_name: Name of the tool executed
        started_at: Start timestamp (Unix time)
        ended_at: End timestamp (None if still running)
        success: Whether tool execution succeeded
        parameters: Parameters passed to the tool
        result_size: Size of result in bytes
        error: Error message if execution failed
    """

    tool_name: str
    started_at: float
    ended_at: Optional[float] = None
    success: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)
    result_size: int = 0
    error: Optional[str] = None

    @property
    def duration(self) -> float:
        """
        Calculate tool execution duration in seconds.

        Returns:
            Duration in seconds (ongoing executions return elapsed time)
        """
        if self.ended_at:
            return self.ended_at - self.started_at
        return time.time() - self.started_at


class AgentExecutionMetrics:
    """
    Performance metrics tracker for a specific agent.

    Tracks task executions, tool usage, token consumption, and errors
    for a single agent. Provides aggregated statistics and historical data.

    Attributes:
        agent_id: Unique agent identifier
        max_history: Maximum number of executions to keep in history
        total_tasks: Total number of tasks executed
        successful_tasks: Number of successfully completed tasks
        failed_tasks: Number of failed tasks
        total_tokens: Total LLM tokens consumed
        total_execution_time: Total execution time in seconds
        tools_called: Count of calls per tool
        tools_time: Total execution time per tool
        tools_errors: Error count per tool
    """

    def __init__(self, agent_id: str, max_history: int = 1000):
        """
        Initialize metrics tracker for an agent.

        Args:
            agent_id: Unique identifier for the agent
            max_history: Maximum number of executions to retain in history
        """
        self.agent_id = agent_id
        self.max_history = max_history
        self.lock = threading.RLock()

        self.total_tasks = 0
        self.successful_tasks = 0
        self.failed_tasks = 0
        self.total_tokens = 0

        self.total_execution_time = 0.0
        self.min_execution_time: Optional[float] = None
        self.max_execution_time: Optional[float] = None

        self.tools_called: Dict[str, int] = {}
        self.tools_time: Dict[str, float] = {}
        self.tools_errors: Dict[str, int] = {}

        self.task_history: List[TaskExecution] = []
        self.tool_history: List[ToolExecution] = []

        self._active_tasks: Dict[str, TaskExecution] = {}
        self._active_tools: Dict[str, ToolExecution] = {}

        self.created_at = datetime.now()
        self.last_activity: Optional[datetime] = None

    def record_task_start(self, task_id: str) -> None:
        """
        Record the start of a task execution.

        Creates a TaskExecution record and marks it as active.

        Args:
            task_id: Unique identifier for the task
        """
        with self.lock:
            execution = TaskExecution(task_id=task_id, started_at=time.time())
            self._active_tasks[task_id] = execution
            self.last_activity = datetime.now()

            logger.debug(f"Task {task_id} started for agent {self.agent_id}")

    def record_task_end(
        self,
        task_id: str,
        success: bool = True,
        tokens: int = 0,
        error: str | None = None,
    ) -> None:
        """
        Record the completion of a task execution.

        Updates counters, calculates duration, and moves task to history.

        Args:
            task_id: Unique identifier for the task
            success: Whether task completed successfully
            tokens: Number of LLM tokens consumed
            error: Error message if task failed
        """
        with self.lock:
            if task_id not in self._active_tasks:
                logger.warning(f"Task {task_id} not found in active tasks")
                return

            execution = self._active_tasks.pop(task_id)
            execution.ended_at = time.time()
            execution.success = success
            execution.tokens_used = tokens
            execution.error = error

            self.total_tasks += 1
            if success:
                self.successful_tasks += 1
            else:
                self.failed_tasks += 1

            self.total_tokens += tokens

            duration = execution.duration
            self.total_execution_time += duration

            if self.min_execution_time is None or duration < self.min_execution_time:
                self.min_execution_time = duration
            if self.max_execution_time is None or duration > self.max_execution_time:
                self.max_execution_time = duration

            self.task_history.append(execution)
            if len(self.task_history) > self.max_history:
                self.task_history.pop(0)

            self.last_activity = datetime.now()

            logger.debug(
                f"Task {task_id} ended for agent {self.agent_id}: "
                f"success={success}, duration={duration:.2f}s, tokens={tokens}"
            )

    def record_tool_start(
        self, tool_name: str, parameters: Optional[Dict] = None
    ) -> str:
        """
        Record the start of a tool execution.

        Args:
            tool_name: Name of the tool being executed
            parameters: Parameters passed to the tool

        Returns:
            Unique execution ID for this tool call
        """
        with self.lock:
            execution_id = f"{tool_name}_{int(time.time() * 1000)}"

            execution = ToolExecution(
                tool_name=tool_name, started_at=time.time(), parameters=parameters or {}
            )
            self._active_tools[execution_id] = execution

            return execution_id

    def record_tool_end(
        self,
        execution_id: str,
        success: bool = True,
        result_size: int = 0,
        error: str | None = None,
    ) -> None:
        """
        Record the completion of a tool execution.

        Updates per-tool metrics and adds execution to history.

        Args:
            execution_id: Unique execution ID from record_tool_start
            success: Whether tool execution succeeded
            result_size: Size of result in bytes
            error: Error message if execution failed
        """
        with self.lock:
            if execution_id not in self._active_tools:
                return

            execution = self._active_tools.pop(execution_id)
            execution.ended_at = time.time()
            execution.success = success
            execution.result_size = result_size
            execution.error = error

            tool_name = execution.tool_name
            duration = execution.duration

            self.tools_called[tool_name] = self.tools_called.get(tool_name, 0) + 1
            self.tools_time[tool_name] = self.tools_time.get(tool_name, 0.0) + duration

            if not success:
                self.tools_errors[tool_name] = self.tools_errors.get(tool_name, 0) + 1

            self.tool_history.append(execution)
            if len(self.tool_history) > self.max_history:
                self.tool_history.pop(0)

            for task in self._active_tasks.values():
                task.tools_called.append(tool_name)

    @property
    def avg_execution_time(self) -> float:
        """
        Calculate average task execution time.

        Returns:
            Average execution time in seconds (0.0 if no tasks)
        """
        if self.total_tasks == 0:
            return 0.0
        return self.total_execution_time / self.total_tasks

    @property
    def success_rate(self) -> float:
        """
        Calculate task success rate.

        Returns:
            Success rate as a float between 0.0 and 1.0
        """
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    @property
    def avg_tokens_per_task(self) -> float:
        """
        Calculate average tokens consumed per task.

        Returns:
            Average tokens per task (0.0 if no tasks)
        """
        if self.total_tasks == 0:
            return 0.0
        return self.total_tokens / self.total_tasks

    def get_top_tools(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most frequently used tools with statistics.

        Args:
            limit: Maximum number of tools to return

        Returns:
            List of tool statistics sorted by usage count
        """
        sorted_tools = sorted(
            self.tools_called.items(), key=lambda x: x[1], reverse=True
        )

        result = []
        for tool_name, count in sorted_tools[:limit]:
            avg_time = self.tools_time.get(tool_name, 0) / count if count > 0 else 0
            errors = self.tools_errors.get(tool_name, 0)

            result.append(
                {
                    "tool": tool_name,
                    "calls": count,
                    "avg_time": round(avg_time, 3),
                    "errors": errors,
                    "error_rate": round(errors / count * 100, 1) if count > 0 else 0,
                }
            )

        return result

    def get_recent_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recent task executions.

        Args:
            limit: Maximum number of tasks to return

        Returns:
            List of recent task execution summaries
        """
        return [
            {
                "task_id": t.task_id,
                "success": t.success,
                "duration": round(t.duration, 2),
                "tokens": t.tokens_used,
                "tools": len(t.tools_called),
                "error": t.error,
            }
            for t in self.task_history[-limit:]
        ]

    def get_summary(self) -> Dict[str, Any]:
        """
        Get complete metrics summary.

        Returns:
            Dictionary with all aggregated metrics and statistics
        """
        return {
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
            "tasks": {
                "total": self.total_tasks,
                "successful": self.successful_tasks,
                "failed": self.failed_tasks,
                "success_rate": round(self.success_rate * 100, 1),
            },
            "time": {
                "total_seconds": round(self.total_execution_time, 2),
                "avg_seconds": round(self.avg_execution_time, 2),
                "min_seconds": (
                    round(self.min_execution_time, 2)
                    if self.min_execution_time
                    else None
                ),
                "max_seconds": (
                    round(self.max_execution_time, 2)
                    if self.max_execution_time
                    else None
                ),
            },
            "tokens": {
                "total": self.total_tokens,
                "avg_per_task": round(self.avg_tokens_per_task, 1),
            },
            "tools": {
                "unique_count": len(self.tools_called),
                "total_calls": sum(self.tools_called.values()),
                "top_tools": self.get_top_tools(5),
            },
        }

    def reset(self):
        """Reset all metrics to initial state."""
        with self.lock:
            self.total_tasks = 0
            self.successful_tasks = 0
            self.failed_tasks = 0
            self.total_tokens = 0
            self.total_execution_time = 0.0
            self.min_execution_time = None
            self.max_execution_time = None
            self.tools_called.clear()
            self.tools_time.clear()
            self.tools_errors.clear()
            self.task_history.clear()
            self.tool_history.clear()
            self._active_tasks.clear()
            self._active_tools.clear()

            logger.info(f"Metrics reset for agent {self.agent_id}")


class AgentMetricsRepository:
    """
    Central metrics collector for all agents.

    Manages metrics for multiple agents and provides global statistics
    and export functionality.

    Attributes:
        storage_path: Path for metrics persistence
        agents: Dictionary of AgentMetrics by agent ID
        start_time: Collector initialization timestamp
    """

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the metrics collector.

        Args:
            storage_path: Path for persistence (None = ~/.aura/metrics)
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            from aura_cli.core.paths import aura_path

            self.storage_path = aura_path("metrics")

        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.agents: Dict[str, AgentExecutionMetrics] = {}
        self.lock = threading.RLock()

        self.start_time = datetime.now()

    def get_agent_metrics(self, agent_id: str) -> AgentExecutionMetrics:
        """
        Get or create metrics for an agent.

        Args:
            agent_id: Unique agent identifier

        Returns:
            AgentMetrics instance for the agent
        """
        with self.lock:
            if agent_id not in self.agents:
                self.agents[agent_id] = AgentExecutionMetrics(agent_id)
            return self.agents[agent_id]

    def get_all_summaries(self) -> Dict[str, Dict]:
        """
        Get metrics summaries for all agents.

        Returns:
            Dictionary mapping agent IDs to their metric summaries
        """
        with self.lock:
            return {
                agent_id: metrics.get_summary()
                for agent_id, metrics in self.agents.items()
            }

    def get_global_stats(self) -> Dict[str, Any]:
        """
        Get global statistics across all agents.

        Returns:
            Dictionary with aggregated global statistics
        """
        with self.lock:
            total_tasks = sum(m.total_tasks for m in self.agents.values())
            total_success = sum(m.successful_tasks for m in self.agents.values())
            total_tokens = sum(m.total_tokens for m in self.agents.values())
            total_time = sum(m.total_execution_time for m in self.agents.values())

            return {
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "agents": len(self.agents),
                "total_tasks": total_tasks,
                "total_successful": total_success,
                "success_rate": (
                    round(total_success / total_tasks * 100, 1)
                    if total_tasks > 0
                    else 0
                ),
                "total_tokens": total_tokens,
                "total_execution_time": round(total_time, 2),
            }

    def export_metrics(self, filepath: str | None = None) -> str:
        """
        Export all metrics to JSON file.

        Args:
            filepath: Output file path (None = auto-generate)

        Returns:
            Path to the created file
        """
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(self.storage_path / f"metrics_{timestamp}.json")

        data = {
            "exported_at": datetime.now().isoformat(),
            "global": self.get_global_stats(),
            "agents": self.get_all_summaries(),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Metrics exported to {filepath}")
        return filepath


_metrics_collector: Optional[AgentMetricsRepository] = None


def get_metrics_collector() -> AgentMetricsRepository:
    """
    Get the singleton metrics collector instance.

    Returns:
        Global MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = AgentMetricsRepository()
    return _metrics_collector


# Historical public names. Product code should use the responsibility-specific
# names above; these aliases preserve third-party imports during migration.
AgentMetrics = AgentExecutionMetrics
MetricsCollector = AgentMetricsRepository
