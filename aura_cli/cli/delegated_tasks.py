"""CLI adapters for observing and presenting delegated AGI/Ops tasks."""

import os
from typing import Any, Dict, Optional

from aura_cli.application.agents.delegated_ports import (
    ObserveThread,
    ReadSnapshot,
    SnapshotExists,
    ThreadObservation,
)
from aura_cli.application.agents.delegated_reporting import (
    build_delegated_task_context,
    format_delegated_task_artifacts,
    format_delegated_task_status,
    format_delegated_task_summary,
)
from aura_cli.application.agents.delegated_tasks import (
    DelegatedTaskRegistry,
    DelegatedTaskStatus,
)
from aura_cli.cli.utils.thread_manager import get_thread_manager
from aura_cli.core.logger import get_logger
from aura_cli.core.memory.notebook_service import notebook_service

logger = get_logger(__name__)


class DelegatedTaskManager:
    """Manages delegated AGI/Ops tasks lifecycle."""

    def __init__(
        self,
        persist_callback=None,
        *,
        observe_thread: ObserveThread | None = None,
        read_snapshot: ReadSnapshot | None = None,
        snapshot_exists: SnapshotExists | None = None,
    ):
        """Initialize with empty task registry.

        Args:
            persist_callback: Optional callback(task_id, **kwargs) for persistence.
        """
        self._registry = DelegatedTaskRegistry(persist_callback)
        self._observe_thread = observe_thread or self._observe_thread_default
        self._read_snapshot = read_snapshot or (
            lambda path: notebook_service.read_page(path)
        )
        self._snapshot_exists = snapshot_exists or (lambda path: os.path.exists(path))

    @staticmethod
    def _observe_thread_default(thread_name: str) -> ThreadObservation | None:
        thread_info = get_thread_manager().get_thread_info(thread_name)
        if thread_info is None:
            return None
        return ThreadObservation(
            status=str(thread_info.status.value),
            alive=bool(thread_info.thread.is_alive()),
        )

    @property
    def tasks(self) -> Dict[str, Dict[str, Any]]:
        """Legacy mutable task map kept for CLI fixture/integration compatibility."""
        return self._registry.live_tasks

    def register_task(
        self,
        *,
        agent_type: str,
        task_id: str,
        thread_name: str,
        prompt: str,
        delegation_payload: Dict[str, Any],
        mode: Optional[str] = None,
        worker_ref: Optional[Any] = None,
    ) -> None:
        """Store delegated-task metadata for follow-up queries from chat."""
        self._registry.register_task(
            agent_type=agent_type,
            task_id=task_id,
            thread_name=thread_name,
            prompt=prompt,
            mode=mode,
            delegation_payload=delegation_payload,
            worker_ref=worker_ref,
        )

    def reconcile_state(self, task_info: Dict[str, Any]) -> None:
        """Pull final outcome metadata from the live worker into local/persistent state."""
        self._registry.reconcile_state(task_info)

    def cancel_task(self, task_id: str, reason: str = "cancelled by user") -> str:
        """Record cancellation; request worker cancellation when supported."""
        task = self.resolve_task(task_id=task_id)
        if task is None:
            return f"Nenhuma tarefa delegada encontrada para task_id='{task_id}'."
        worker = task.get("worker_ref")
        cancel = getattr(worker, "cancel", None)
        if callable(cancel):
            cancel()
        self._registry.mark_terminal(task, DelegatedTaskStatus.CANCELLED, reason=reason)
        return self.get_task_status(task_id=task_id)

    def mark_timed_out(self, task_id: str, timeout_seconds: float) -> str:
        """Record a verified observation timeout without claiming worker failure."""
        task = self.resolve_task(task_id=task_id)
        if task is None:
            return f"Nenhuma tarefa delegada encontrada para task_id='{task_id}'."
        self._registry.mark_terminal(
            task,
            DelegatedTaskStatus.TIMED_OUT,
            reason=f"observation timeout after {timeout_seconds:.1f}s",
        )
        return self.get_task_status(task_id=task_id)

    def resolve_task(
        self, task_id: str = "", agent_type: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Resolve delegated-task metadata by task_id, agent type, or latest task."""
        return self._registry.resolve_task(task_id=task_id, agent_type=agent_type)

    def add_rehydrated_task(self, task_info: Dict[str, Any]) -> bool:
        """Restore persisted metadata without triggering another persistence write."""
        return self._registry.add_rehydrated_task(task_info)

    def list_tasks(self) -> str:
        """List known delegated AGI/Ops tasks for follow-up."""
        if not self._registry.tasks:
            return "Nenhuma tarefa delegada foi registrada nesta sessão."

        lines = []
        for info in self._registry.sorted_tasks():
            task_id = str(info["task_id"])
            status_text = self.get_task_status(task_id)
            short_prompt = str(info.get("prompt", ""))[:120]
            lines.append(
                f"- {task_id} | {info.get('agent_type')} | {status_text} | prompt={short_prompt}"
            )
        return "\n".join(lines)

    def get_latest_task(self, agent_type: str = "") -> str:
        """Return the latest delegated task, optionally filtered by agent type."""
        if not self._registry.tasks:
            return "Nenhuma tarefa delegada foi registrada nesta sessão."

        candidates = self._registry.sorted_tasks(agent_type)

        if not candidates:
            return f"Nenhuma tarefa delegada encontrada para agent_type='{agent_type}'."

        latest = candidates[0]
        return self.get_task_status(task_id=str(latest["task_id"]))

    def summarize_tasks(self) -> str:
        """Return a compact summary of delegated-task counts and latest entries."""
        if not self._registry.tasks:
            return "Nenhuma tarefa delegada foi registrada nesta sessão."

        counts = self._registry.counts()
        latest_any = self.get_latest_task()
        latest_agi = self.get_latest_task("agi") if counts.agi else "n/a"
        latest_ops = self.get_latest_task("ops") if counts.ops else "n/a"
        return (
            f"delegated_total={counts.total}; agi={counts.agi}; ops={counts.ops}\n"
            f"latest_any={latest_any}\n"
            f"latest_agi={latest_agi}\n"
            f"latest_ops={latest_ops}"
        )

    def get_task_status(self, task_id: str = "", agent_type: str = "") -> str:
        """Return status for a delegated task in this session."""
        task_info = self.resolve_task(task_id=task_id, agent_type=agent_type)
        if not task_info:
            if not self._registry.tasks:
                return "Nenhuma tarefa delegada foi registrada nesta sessão."
            return f"Nenhuma tarefa delegada encontrada para task_id='{task_id}' agent_type='{agent_type}'."

        self.reconcile_state(task_info)

        thread_name = str(task_info.get("thread_name", ""))
        observation = self._observe_thread(thread_name) if thread_name else None
        if observation is not None:
            status = observation.status
            alive = observation.alive
        else:
            status = str(task_info.get("persisted_status") or "unknown")
            alive = False

        if status != task_info.get("persisted_status"):
            self._registry.update_status(task_info, status)

        return format_delegated_task_status(task_info, status=status, alive=alive)

    def summarize_task(self, task_id: str = "", agent_type: str = "") -> str:
        """Return a detailed summary for a delegated task."""
        task_info = self.resolve_task(task_id=task_id, agent_type=agent_type)
        if not task_info:
            if not self._registry.tasks:
                return "Nenhuma tarefa delegada foi registrada nesta sessão."
            return f"Nenhuma tarefa delegada encontrada para task_id='{task_id}' agent_type='{agent_type}'."

        status_line = self.get_task_status(task_id=str(task_info["task_id"]))
        return format_delegated_task_summary(task_info, status_line)

    def get_task_artifacts(self, task_id: str = "", agent_type: str = "") -> str:
        """Return concrete artifacts associated with a delegated task."""
        task_info = self.resolve_task(task_id=task_id, agent_type=agent_type)
        if not task_info:
            if not self._registry.tasks:
                return "Nenhuma tarefa delegada foi registrada nesta sessão."
            return f"Nenhuma tarefa delegada encontrada para task_id='{task_id}' agent_type='{agent_type}'."

        self.reconcile_state(task_info)
        final_result = task_info.get("final_result") or {}
        final_error = task_info.get("final_error") or {}
        snapshot_path = (
            task_info.get("snapshot_path")
            or final_result.get("snapshot_path")
            or final_error.get("snapshot_path")
        )
        snapshot_exists = bool(
            snapshot_path and self._snapshot_exists(str(snapshot_path))
        )
        return format_delegated_task_artifacts(
            task_info, snapshot_exists=snapshot_exists
        )

    def read_task_snapshot(
        self, task_id: str = "", agent_type: str = "", max_chars: int = 4000
    ) -> str:
        """Read the notebook snapshot associated with a delegated task."""
        task_info = self.resolve_task(task_id=task_id, agent_type=agent_type)
        if not task_info:
            if not self._registry.tasks:
                return "Nenhuma tarefa delegada foi registrada nesta sessão."
            return f"Nenhuma tarefa delegada encontrada para task_id='{task_id}' agent_type='{agent_type}'."

        self.reconcile_state(task_info)
        final_result = task_info.get("final_result") or {}
        final_error = task_info.get("final_error") or {}
        snapshot_path = (
            task_info.get("snapshot_path")
            or final_result.get("snapshot_path")
            or final_error.get("snapshot_path")
        )
        if not snapshot_path:
            return "A tarefa delegada não possui snapshot associado no notebook."

        try:
            content = self._read_snapshot(str(snapshot_path))
        except Exception as e:
            return f"Failed to read delegated task snapshot: {e}"

        if not content:
            return f"Snapshot vazio ou indisponível: {snapshot_path}"

        truncated = content[:max_chars]
        if len(content) > max_chars:
            truncated += "\n\n[... snapshot truncado ...]"
        return (
            f"[DELEGATED TASK SNAPSHOT]\n"
            f"task_id: {task_info['task_id']}\n"
            f"snapshot_path: {snapshot_path}\n\n"
            f"{truncated}\n"
            f"[/DELEGATED TASK SNAPSHOT]"
        )

    def reattach_task_context(
        self, task_id: str = "", agent_type: str = "", stats: Any = None
    ) -> str:
        """Prepare delegated-task context for the next chat turn and return it."""
        task_info = self.resolve_task(task_id=task_id, agent_type=agent_type)
        if not task_info:
            if not self._registry.tasks:
                return "Nenhuma tarefa delegada foi registrada nesta sessão."
            return f"Nenhuma tarefa delegada encontrada para task_id='{task_id}' agent_type='{agent_type}'."

        context_block = build_delegated_task_context(task_info)

        if stats:
            existing_context = getattr(stats, "_pending_context", None)
            existing_count = getattr(stats, "_pending_context_files", 0)
            if not isinstance(existing_count, int):
                existing_count = 0
            if existing_context:
                stats._pending_context = f"{existing_context}\n\n{context_block}"
                stats._pending_context_files = existing_count + 1
            else:
                stats._pending_context = context_block
                stats._pending_context_files = 1

        return (
            f"Contexto da tarefa delegada preparado para o próximo turno do chat.\n"
            f"{context_block}"
        )
