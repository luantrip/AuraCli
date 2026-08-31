"""CLI composition adapter for worker checkpoint coordination."""

from __future__ import annotations

import importlib.util
import logging
import sys
from typing import Any, Literal, MutableMapping, Optional

from aura_cli.application.workspace.checkpoint_coordinator import (
    WorkerCheckpointCoordinator,
)
from aura_cli.cli.ui.composition import publish_agent_status
from aura_cli.core.hooks import HookEvent

logger = logging.getLogger(__name__)


class WorkerCheckpointHelper(WorkerCheckpointCoordinator):
    """Discover CLI adapters and delegate checkpoint policy to application."""

    def __init__(
        self, worker_name: str = "worker", status_queue: Optional[Any] = None
    ) -> None:
        self.status_queue = status_queue
        self._hook_manager: Optional[Any] = None
        super().__init__(worker_name, status_publisher=self._publish_status)

    def initialize(self) -> bool:
        checkpoint_manager = None
        try:
            import aura_cli.core.tools.checkpoint_tools as checkpoint_tools

            checkpoint_manager = checkpoint_tools._checkpoint_manager
        except Exception as exc:
            logger.debug("Ferramentas de checkpoint não disponíveis: %s", exc)

        try:
            if importlib.util.find_spec("aura_cli.core.hooks") is not None:
                main_module = sys.modules.get("aura_cli.cli.main")
                self._hook_manager = getattr(main_module, "hook_manager", None)
        except Exception as exc:
            logger.debug("Hook manager não disponível: %s", exc)

        self.configure(
            checkpoint_manager=checkpoint_manager,
            status_publisher=self._publish_status,
            hook_publisher=self._publish_hook,
        )
        return super().initialize()

    def _publish_hook(self, event_type: str, context: MutableMapping[str, Any]) -> None:
        if self._hook_manager is None:
            return
        hook_event = getattr(HookEvent, event_type.upper().replace("-", "_"), None)
        if hook_event is not None:
            self._hook_manager.trigger(hook_event, context)

    def _publish_status(self, message: str) -> None:
        name = self.worker_name.lower()
        agent_type: Literal["agi", "ops", "tester"] = (
            "ops"
            if "ops" in name
            else "tester"
            if "test" in name or "tester" in name
            else "agi"
        )
        publish_agent_status(self.status_queue, agent_type, message)


def get_checkpoint_helper(
    worker_name: str = "worker", status_queue: Optional[Any] = None
) -> WorkerCheckpointHelper:
    """Create and initialize a CLI-configured checkpoint helper."""
    helper = WorkerCheckpointHelper(worker_name=worker_name, status_queue=status_queue)
    helper.initialize()
    return helper


__all__ = ["WorkerCheckpointHelper", "get_checkpoint_helper"]
