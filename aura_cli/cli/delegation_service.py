"""CLI composition adapter for delegated AGI and Ops launches."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import logging
from pathlib import Path
from typing import Any

from aura_cli.application.agents.delegation import (
    DelegationLaunchOutcome,
    DelegationLaunchStatus,
    assess_delegation_launch,
    format_delegation_launch_outcome,
    prepare_delegation,
)
from aura_cli.application.agents.delegation_launcher import DelegationLaunchCoordinator


class DelegationService:
    """Bind application delegation policies to CLI worker factories."""

    def __init__(
        self,
        *,
        launcher: DelegationLaunchCoordinator,
        conversation_history: list[dict[str, Any]],
        project_root: Path,
        model: str,
        constitution: str | None,
        api_keys_provider: Callable[[], Mapping[str, str]],
        has_credentials: Callable[[Mapping[str, str]], bool],
        logger: logging.Logger,
    ) -> None:
        self.launcher = launcher
        self.conversation_history = conversation_history
        self.project_root = project_root
        self.model = model
        self.constitution = constitution
        self.api_keys_provider = api_keys_provider
        self.has_credentials = has_credentials
        self.logger = logger

    def launch_agi(
        self, objective: str, *, active: bool, handoff_context: str = ""
    ) -> tuple[str, Any | None]:
        return self._launch(
            objective,
            agent_type="agi",
            active=active,
            handoff_context=handoff_context,
        )

    def launch_ops(
        self,
        task: str,
        *,
        active: bool,
        mode: str = "general",
        handoff_context: str = "",
    ) -> tuple[str, Any | None]:
        return self._launch(
            task,
            agent_type="ops",
            active=active,
            mode=mode,
            handoff_context=handoff_context,
        )

    def _launch(
        self,
        request: str,
        *,
        agent_type: str,
        active: bool,
        handoff_context: str,
        mode: str | None = None,
    ) -> tuple[str, Any | None]:
        early = assess_delegation_launch(
            agent_type=agent_type, request=request, worker_active=active
        )
        if early:
            return format_delegation_launch_outcome(early), None

        credentials = dict(self.api_keys_provider())
        early = assess_delegation_launch(
            agent_type=agent_type,
            request=request,
            worker_active=False,
            has_credentials=self.has_credentials(credentials),
        )
        if early:
            return format_delegation_launch_outcome(early), None

        try:
            plan = prepare_delegation(
                request,
                agent_type=agent_type,
                conversation_history=self.conversation_history,
                project_root=self.project_root,
                final_model=self.model,
                constitution=self.constitution,
                handoff_context=handoff_context,
                mode=mode,
            )
            result = self.launcher.launch(
                plan,
                model=self.model,
                credentials=credentials,
                factory=self._factory(agent_type),
            )
        except Exception as error:
            result_outcome = DelegationLaunchOutcome(
                DelegationLaunchStatus.FAILED,
                agent_type,
                request=request,
                mode=mode,
                error=str(error),
            )
            self.logger.warning(
                "Failed to prepare %s delegation: %s", agent_type, error
            )
            return format_delegation_launch_outcome(result_outcome), None

        if result.outcome.status is DelegationLaunchStatus.FAILED:
            self.logger.warning(
                "Failed to start %s via delegation: %s",
                agent_type,
                result.outcome.error,
            )
        else:
            self.logger.info(
                "%s worker started via delegation: %s", agent_type.upper(), request[:80]
            )
        return format_delegation_launch_outcome(result.outcome), result.thread

    def _factory(self, agent_type: str):
        if agent_type == "agi":
            from aura_cli.cli.utils.worker_factory import create_agi_worker_thread

            def create_agi(prepared, model, credentials):
                return create_agi_worker_thread(
                    objective=prepared.handoff,
                    model=model,
                    api_keys=dict(credentials),
                    headless=False,
                    project_root=self.project_root,
                    delegation_payload=prepared.payload,
                )

            return create_agi

        from aura_cli.cli.utils.worker_factory import create_ops_worker_thread

        def create_ops(prepared, model, credentials):
            return create_ops_worker_thread(
                task=prepared.handoff,
                model=model,
                api_keys=dict(credentials),
                mode=prepared.mode or "general",
                headless=False,
                project_root=self.project_root,
                delegation_payload=prepared.payload,
            )

        return create_ops


__all__ = ["DelegationService"]
