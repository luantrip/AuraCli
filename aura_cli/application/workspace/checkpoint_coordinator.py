"""Application coordination for worker checkpoints and lifecycle hooks."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Mapping, MutableMapping, Optional

logger = logging.getLogger(__name__)

StatusPublisher = Callable[[str], None]
HookPublisher = Callable[[str, MutableMapping[str, Any]], None]


class WorkerCheckpointCoordinator:
    """Coordinate worker checkpoints without discovering infrastructure globally."""

    def __init__(
        self,
        worker_name: str = "worker",
        *,
        checkpoint_manager: Any = None,
        status_publisher: Optional[StatusPublisher] = None,
        hook_publisher: Optional[HookPublisher] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.worker_name = worker_name
        self._checkpoint_manager = checkpoint_manager
        self._status_publisher = status_publisher
        self._hook_publisher = hook_publisher
        self._clock = clock
        self._initial_checkpoint_id: Optional[str] = None
        self._initialized = False

    def configure(
        self,
        *,
        checkpoint_manager: Any = None,
        status_publisher: Optional[StatusPublisher] = None,
        hook_publisher: Optional[HookPublisher] = None,
    ) -> None:
        """Supply host adapters before marking the coordinator ready."""
        self._checkpoint_manager = checkpoint_manager
        self._status_publisher = status_publisher
        self._hook_publisher = hook_publisher

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def create_initial_checkpoint(self, description: str = "start") -> Optional[str]:
        if not self._checkpoint_manager or not self._initialized:
            return None
        try:
            if not getattr(self._checkpoint_manager, "initialized", False):
                self._checkpoint_manager.init()
            checkpoint = self._checkpoint_manager.create(
                f"{self.worker_name} {description}"
            )
            if checkpoint is not None:
                self._initial_checkpoint_id = getattr(checkpoint, "commit_hash", None)
                self._send_status(
                    f"📸 Checkpoint created: {self._initial_checkpoint_id}"
                )
                return self._initial_checkpoint_id
        except Exception as exc:
            logger.warning("Failed to create initial checkpoint: %s", exc)
        return None

    def create_checkpoint_before_task(self, task_description: str) -> Optional[str]:
        if not self._checkpoint_manager or not self._initialized:
            return None
        try:
            checkpoint = self._checkpoint_manager.create(f"Before: {task_description}")
            if checkpoint is not None:
                return getattr(checkpoint, "commit_hash", None)
        except Exception as exc:
            logger.warning("Failed to create task checkpoint: %s", exc)
        return None

    def restore_on_failure(self) -> bool:
        if (
            not self._checkpoint_manager
            or not self._initialized
            or not self._initial_checkpoint_id
        ):
            return False
        try:
            result = self._checkpoint_manager.restore(self._initial_checkpoint_id)
            if result:
                files_count = len(result) if hasattr(result, "__len__") else 0
                self._send_status(
                    f"▲ Restored to checkpoint {self._initial_checkpoint_id} "
                    f"({files_count} files)"
                )
                return True
        except Exception as exc:
            logger.error("Failed to restore checkpoint: %s", exc)
        return False

    def trigger_hook(
        self, event_type: str, context: Optional[Mapping[str, Any]] = None
    ) -> None:
        if self._hook_publisher is None:
            return
        payload = dict(context or {})
        payload.setdefault("worker_name", self.worker_name)
        payload.setdefault("timestamp", self._clock())
        try:
            self._hook_publisher(event_type, payload)
        except Exception as exc:
            logger.debug("Failed to trigger hook: %s", exc)

    def _send_status(self, message: str) -> None:
        if not message or self._status_publisher is None:
            return
        try:
            self._status_publisher(message)
        except Exception as exc:
            logger.debug("Failed to publish worker status: %s", exc)
