"""Parallel task executor.

Provides efficient parallel execution of task groups with concurrency control.
"""

from dataclasses import dataclass, field
import queue
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aura_cli.core.agents.agent_base import AgentTask
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


@dataclass
class TaskGroup:
    """A group of tasks to execute in parallel."""

    group_id: str
    tasks: List[AgentTask] = field(default_factory=list)
    max_workers: int = 3
    timeout: Optional[float] = None


class ParallelExecutor:
    """Parallel task executor with concurrency control and pooling."""

    def __init__(self, max_workers: int = 3):
        """Initialise the parallel executor."""
        self.max_workers = max_workers
        self.stats = get_stats()

        self.worker_pool: List[threading.Thread] = []
        self.task_queue: queue.Queue = queue.Queue()
        self.result_queue: queue.Queue = queue.Queue()

        self.running = False
        self.lock = threading.Lock()

        logger.info(f"ParallelExecutor initialized (max_workers: {max_workers})")

    def execute_group(
        self, group: TaskGroup, executor_func: Callable[[AgentTask], Any]
    ) -> Dict[str, Any]:
        """Execute a task group and return results."""
        logger.info(
            f"Executando grupo {group.group_id} "
            f"({len(group.tasks)} tarefas, max_workers: {group.max_workers})"
        )

        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except queue.Empty:
                break

        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break

        for task in group.tasks:
            self.task_queue.put((task, executor_func))

        num_workers = min(group.max_workers, len(group.tasks), self.max_workers)
        self.running = True

        workers = []
        for i in range(num_workers):
            # Use daemon threads for worker pool
            # Workers are managed and joined explicitly, so daemon is safe
            worker = threading.Thread(
                target=self._worker,
                args=(i,),
                daemon=True,
            )
            worker.start()
            workers.append(worker)

        results = {}
        start_time = time.time()

        completed = 0
        total = len(group.tasks)

        while completed < total:
            if group.timeout and (time.time() - start_time) > group.timeout:
                logger.warning(f"Timeout do grupo {group.group_id}")
                self.running = False
                break

            try:
                task_id, result, error = self.result_queue.get(timeout=min(1.0, 60.0))
                results[task_id] = {
                    "result": result,
                    "error": error,
                    "success": error is None,
                }
                completed += 1
            except queue.Empty:
                continue

        self.running = False

        for worker in workers:
            worker.join(timeout=1.0)

        duration = time.time() - start_time

        logger.info(
            f"Group {group.group_id} completed: "
            f"{completed}/{total} tasks ({duration:.2f}s)"
        )

        return {
            "group_id": group.group_id,
            "completed": completed,
            "total": total,
            "duration": duration,
            "results": results,
        }

    def _worker(self, worker_id: int) -> None:
        """Worker thread function for parallel task execution."""
        logger.debug(f"Worker {worker_id} iniciado")

        while self.running:
            try:
                task, executor_func = self.task_queue.get(timeout=min(0.5, 30.0))

                try:
                    result = executor_func(task)
                    error = None
                except Exception as e:
                    result = None
                    error = str(e)
                    logger.error(
                        f"Worker {worker_id} erro na tarefa {task.id}: {e}",
                        exc_info=True,
                    )

                self.result_queue.put((task.id, result, error))

                self.task_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} erro: {e}", exc_info=True)

        logger.debug(f"Worker {worker_id} finished")

    def execute_tasks_parallel(
        self,
        tasks: List[AgentTask],
        executor_func: Callable[[AgentTask], Any],
        max_workers: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a list of tasks in parallel."""
        import uuid

        group = TaskGroup(
            group_id=str(uuid.uuid4())[:8],
            tasks=tasks,
            max_workers=max_workers or self.max_workers,
        )

        return self.execute_group(group, executor_func)
