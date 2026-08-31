"""Background Ops worker thread for DevOps tasks (git, docker, general)."""

import os
from pathlib import Path
import queue
import time
from typing import Any, Dict, List, Optional
import uuid

from aura_cli.application.agents.artifacts import ArtifactKind, classify_artifact
from aura_cli.application.agents.ops_execution import (
    build_discovery_memory_record,
    build_ops_agent_configs,
    build_ops_chat_result,
    build_ops_system_prompt,
    build_plan_memory_record,
    format_missing_ops_credential,
    get_ops_provider_policy,
    is_ops_termination_message,
)
from aura_cli.application.agents.ops_planning import (
    build_effective_ops_prompt,
    build_ops_planning_prompt,
    build_ops_workflow_blueprint,
    build_ops_workflow_result,
    render_delegation_context,
    select_ops_agent,
    valid_workflow_tasks,
)
from aura_cli.cli.ui.constants import UIIcons

try:
    from aura_cli.cli.ui.components.subagent_panel import SubAgentPanel
except ImportError:
    SubAgentPanel = None  # type: ignore[assignment,misc]
from aura_cli.application.agents.queue_event_emitter import QueueAgiAdapter
from aura_cli.application.agents.worker_lifecycle import (
    build_worker_error_payload,
    build_worker_success_payload,
    get_worker_failure_supervisor_state,
    summarize_worker_success,
)
from aura_cli.application.diffs import WorkspaceDiff, capture_workspace_diff
from aura_cli.cli.workers.advanced_runtime import initialize_advanced_worker_runtime
from aura_cli.cli.workers.base_worker import BaseWorker
from aura_cli.cli.workers.ops_agent_registration import register_ops_agents
from aura_cli.core.agents.conversation_instrumentation import (
    instrument_agent_conversation,
)
from aura_cli.core.agents.fallbacks import classify_fallback_reason
from aura_cli.core.agi.planning import AgiPlanner
from aura_cli.core.config import config_manager
from aura_cli.core.constants import COMPRESSION_THRESHOLD, MAX_HISTORY_SIZE
from aura_cli.core.context.base import ContextManager
from aura_cli.core.logger import get_logger
from aura_cli.core.memory.notebook_service import get_notebook_service
from aura_cli.core.tools.human_intervention_adapter import (
    HumanInterventionAdapter,
    register_intervention_adapter,
)

USE_ADK_BRIDGE = os.getenv("AURA_USE_ADK_BRIDGE", "true").lower() == "true"

try:
    from aura_cli.core.personas.integrations import get_consciousness_manager

    CONSCIOUSNESS_AVAILABLE = True
except ImportError:
    CONSCIOUSNESS_AVAILABLE = False

logger = get_logger(__name__)

_DIFF_REFRESH_TOOLS = frozenset(
    {
        "write_file",
        "edit_file",
        "delete_file",
        "git_add",
        "git_commit",
        "git_checkout",
        "git_smart",
        "run_shell_command",
        "execute_command",
    }
)

try:
    from rich.console import Console as _Console

    from aura_cli.cli.ui.loading_states import AgentLoadingStates, LoadingState

    LOADING_AVAILABLE = True
    _loading_console = _Console()
except ImportError:
    LOADING_AVAILABLE = False
    _loading_console = None  # type: ignore[assignment]
    logger.debug("Loading states não disponível em OpsWorker")


class OpsWorker(BaseWorker):
    """DevOps operations worker thread."""

    max_execution_time: float = 300.0  # 5 minutes for Ops tasks
    dashboard_prefix = "Aura Ops"

    def __init__(
        self,
        prompt: str,
        model: str,
        api_keys: dict,
        mode: str = "general",
        headless: bool = False,
        status_queue: Optional[queue.Queue[Any]] = None,
        ops_tools: Optional[Dict[str, Any]] = None,
        use_advanced_features: bool = True,
        project_root: Optional[Any] = None,
        delegation_payload: Optional[Dict[str, Any]] = None,
    ):
        """Initialise the Ops worker."""
        super().__init__(
            status_queue=status_queue,
            task_id=f"ops_{mode}_{uuid.uuid4().hex[:6]}",
            headless=headless,
        )
        self.prompt = prompt
        self.model = model
        self.mode = mode
        self.api_keys = api_keys
        self.project_root = project_root
        self.context_manager = ContextManager(
            max_history_size=MAX_HISTORY_SIZE,
            compression_threshold=COMPRESSION_THRESHOLD,
        )
        self.ops_tools = ops_tools or {}
        self.use_advanced_features = use_advanced_features
        self.delegation_payload = delegation_payload or {}

        from aura_cli.core.paths import ArtifactLayout

        notebook_base = ArtifactLayout(project_root or Path.cwd()).project("notebooks")
        self._notebook_service = get_notebook_service(base_path=notebook_base)
        self._last_notebook_snapshot = 0
        self._notebook_snapshot_interval = COMPRESSION_THRESHOLD

        self.agi_event_adapter = QueueAgiAdapter(
            self.status_queue, task_id=self.task_id
        )

        if self.use_advanced_features:
            from aura_cli.core.agents.planning.problem_decomposer import (
                ProblemDecomposer,
            )
            from aura_cli.core.agents.planning.task_planner import TaskPlanner

            self.task_planner = TaskPlanner()
            self.problem_decomposer = ProblemDecomposer()

            self.human_intervention_adapter = HumanInterventionAdapter(
                status_queue=self.status_queue,
                task_id=self.task_id,
                lifecycle_emitter=self.agi_event_adapter,
            )
            register_intervention_adapter(self.task_id, self.human_intervention_adapter)

            allowed_tasks = [
                "read_file",
                "write_file",
                "list_directory",
                "tree_view",
                "analyze_code",
                "validate_syntax",
                "edit_file",
                "find_in_files",
                "git_status",
                "git_diff",
                "git_diff_context",
                "git_log",
                "git_commit",
                "git_add",
                "git_branch",
                "git_checkout",
                "docker_ps",
                "docker_logs",
                "run_shell_command",
                "execute_command",
            ]

            self.planner = AgiPlanner(
                model=self.model,
                project_root=self.project_root,
                agi_event_adapter=self.agi_event_adapter,
                human_intervention_adapter=self.human_intervention_adapter,
                task_planner=self.task_planner,
                problem_decomposer=self.problem_decomposer,
                use_advanced_features=True,
                allowed_task_types=allowed_tasks,
            )
        else:
            self.planner = None  # type: ignore[assignment]
            self.task_planner = None  # type: ignore[assignment]
            self.problem_decomposer = None  # type: ignore[assignment]

        self.orchestrator = None
        self.communication_manager = None
        self.workflow_executor = None
        self.agent_memory = None
        self.final_result: Optional[Dict[str, Any]] = None
        self.final_error: Optional[Dict[str, Any]] = None
        self.last_snapshot_path: Optional[str] = None
        self.completed_at: Optional[float] = None
        self.generated_files: List[str] = []
        self.edited_files: List[str] = []
        self.analyzed_files: List[str] = []
        self.workspace_diff: WorkspaceDiff = capture_workspace_diff(self.project_root)

    def _refresh_workspace_diff(self) -> WorkspaceDiff:
        """Refresh the authoritative workspace state used by Ops."""
        self.workspace_diff = capture_workspace_diff(self.project_root)
        return self.workspace_diff

    def _workspace_diff_prompt(self) -> str:
        """Return the current bounded diff context for an agent prompt."""
        return self._refresh_workspace_diff().render()

    def _workspace_diff_payload(self) -> dict[str, Any]:
        """Return the current diff in the worker result contract."""
        return self._refresh_workspace_diff().to_dict()

    def _record_final_result(self, result: Dict[str, Any]) -> None:
        """Persist final successful worker result for follow-up/reconciliation."""
        self.completed_at = time.time()
        payload = build_worker_success_payload(
            result,
            task_id=self.task_id,
            completed_at=self.completed_at,
            delegation_payload=self.delegation_payload,
            snapshot_path=self.last_snapshot_path,
            mode=self.mode,
            generated_files=self.generated_files,
            edited_files=self.edited_files,
            analyzed_files=self.analyzed_files,
        )
        published = self._publish_terminal_result(payload)
        self.final_result = published
        self.final_error = None
        if hasattr(self, "agi_event_adapter") and self.agi_event_adapter:
            self.agi_event_adapter.complete_task(
                True,
                result=summarize_worker_success(published),
                stats={
                    "supervisor_state": "completed",
                    "fallback_reason": None,
                },
            )

    def _workflow_has_partial_effects(self, workflow: Any) -> bool:
        """Return whether a workflow may have dispatched or completed work."""
        for step in (getattr(workflow, "steps", {}) or {}).values():
            status = getattr(getattr(step, "status", None), "value", None)
            if status in {"running", "completed"}:
                return True
            if getattr(step, "task_id", None):
                return True
        return bool(getattr(workflow, "results", {}))

    def _workflow_result_summary(self, workflow: Any) -> Dict[str, Any]:
        """Build a bounded, serializable workflow state summary."""
        steps_results: Dict[str, Dict[str, Any]] = {}
        for step_id, step in (getattr(workflow, "steps", {}) or {}).items():
            status = getattr(getattr(step, "status", None), "value", None)
            steps_results[str(step_id)] = {
                "status": status or str(getattr(step, "status", "unknown")),
                "task_id": getattr(step, "task_id", None),
                "attempts": getattr(step, "attempts", 0),
                "error": str(getattr(step, "error", "") or "")[:500] or None,
            }
        workflow_status = getattr(getattr(workflow, "status", None), "value", None)
        return {
            "workflow_id": getattr(workflow, "workflow_id", None),
            "status": workflow_status or str(getattr(workflow, "status", "unknown")),
            "steps_results": steps_results,
        }

    def _record_workflow_reconciliation_error(self, error: Any, workflow: Any) -> None:
        """Publish an error requiring reconciliation instead of chat fallback."""
        self.completed_at = time.time()
        workflow_result = self._workflow_result_summary(workflow)
        payload = build_worker_error_payload(
            error,
            task_id=self.task_id,
            prompt=self.prompt,
            completed_at=self.completed_at,
            fallback_reason="workflow_effect_uncertain",
            delegation_payload=self.delegation_payload,
            snapshot_path=self.last_snapshot_path,
            mode=self.mode,
            error_code="workflow_effect_uncertain",
        )
        payload["workflow_result"] = workflow_result
        payload["retryability"] = "reconcile_before_retry"
        self.final_error = self._publish_terminal_result(payload)
        if hasattr(self, "agi_event_adapter") and self.agi_event_adapter:
            details = {
                "supervisor_state": "reconciliation_required",
                "fallback_reason": "workflow_effect_uncertain",
                "workflow_result": workflow_result,
            }
            self.agi_event_adapter.update_task(
                "reconciliation_required",
                "Workflow interrompido; reconciliação necessária antes de repetir",
                details=details,
            )
            self.agi_event_adapter.error_task(error, details=details)

    def _record_final_error(self, error: Any, *, error_code: str | None = None) -> None:
        """Persist final worker error for follow-up/reconciliation."""
        self.completed_at = time.time()
        fallback_reason = classify_fallback_reason(error)
        error_payload = build_worker_error_payload(
            error,
            task_id=self.task_id,
            prompt=self.prompt,
            completed_at=self.completed_at,
            fallback_reason=fallback_reason,
            delegation_payload=self.delegation_payload,
            snapshot_path=self.last_snapshot_path,
            mode=self.mode,
            error_code=error_code,
        )
        self.final_error = self._publish_terminal_result(error_payload)
        if hasattr(self, "agi_event_adapter") and self.agi_event_adapter:
            supervisor_state = get_worker_failure_supervisor_state(fallback_reason)
            self.agi_event_adapter.update_task(
                supervisor_state,
                "Worker returned control to chat",
                details={
                    "supervisor_state": supervisor_state,
                    "fallback_reason": fallback_reason,
                },
            )
            self.agi_event_adapter.error_task(
                error,
                details={
                    "supervisor_state": supervisor_state,
                    "fallback_reason": fallback_reason,
                },
            )

    def _record_tool_artifacts(
        self, tool_name: str, tool_kwargs: Dict[str, Any]
    ) -> None:
        """Record file artifacts from a structured tool invocation."""
        self._record_classified_artifact(classify_artifact(tool_name, tool_kwargs))

    def _record_classified_artifact(
        self, artifact: tuple[ArtifactKind, str] | None
    ) -> None:
        """Append one classified path to its deduplicated worker collection."""
        if artifact is None:
            return
        kind, path = artifact
        target = {
            ArtifactKind.GENERATED: self.generated_files,
            ArtifactKind.EDITED: self.edited_files,
            ArtifactKind.ANALYZED: self.analyzed_files,
        }[kind]
        if path not in target:
            target.append(path)

    def _build_instrumented_ops_tools(self) -> Dict[str, Any]:
        """Wrap Ops tools so artifact classification uses real tool-call arguments."""
        instrumented_tools: Dict[str, Any] = {}
        for tool_name, tool_func in self.ops_tools.items():
            if not callable(tool_func):
                instrumented_tools[tool_name] = tool_func
                continue

            def wrapped_tool(
                *args, __tool_name=tool_name, __tool_func=tool_func, **kwargs
            ):
                self._record_tool_artifacts(__tool_name, kwargs)
                result = __tool_func(*args, **kwargs)
                if __tool_name not in _DIFF_REFRESH_TOOLS:
                    return result
                snapshot = self._refresh_workspace_diff()
                if isinstance(result, dict):
                    return {
                        **result,
                        "workspace_diff": snapshot.to_dict(),
                    }
                return f"{result}\n\n{snapshot.render(max_chars=6_000)}"

            wrapped_tool.__name__ = tool_name
            instrumented_tools[tool_name] = wrapped_tool
        return instrumented_tools

    def _record_structured_task_artifacts(self, params: Dict[str, Any]) -> None:
        """Record file artifacts from structured workflow task parameters."""
        task_type = str(params.get("type", ""))
        self._record_classified_artifact(classify_artifact(task_type, params))

    def _initialize_advanced_components(self) -> None:
        """Initialise advanced components (orchestrator, communication, etc.)."""
        if not self.use_advanced_features:
            return

        try:
            component_messages = {
                "orchestrator": "Orchestrator initialized",
                "communication": "Communication system initialized",
                "workflow": "Workflow executor initialized",
                "memory": "Memory system initialized",
            }

            def publish_component(component: str) -> None:
                self.agi_event_adapter.emit_chat_message(
                    sender="agent",
                    content=(
                        f"› [Aura Ops] {UIIcons.SUCCESS} "
                        f"{component_messages[component]}"
                    ),
                )

            runtime = initialize_advanced_worker_runtime(
                channel_id="ops_channel",
                channel_name="Canal Ops",
                on_initialized=publish_component,
            )
            self.orchestrator = runtime.orchestrator
            self.communication_manager = runtime.communication_manager
            self.workflow_executor = runtime.workflow_executor
            self.agent_memory = runtime.agent_memory

            self._create_ops_agents()

            logger.info("Advanced Ops components initialized successfully")

        except (ImportError, AttributeError, TypeError) as e:
            logger.error(
                f"Error initializing advanced components (import/type): {e}",
                exc_info=True,
            )
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura Ops] {UIIcons.WARNING} Some advanced components could not be initialized",
            )
        except Exception as e:
            logger.error(
                f"Unexpected error initializing advanced components: {e}", exc_info=True
            )
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura Ops] {UIIcons.WARNING} Some advanced components could not be initialized",
            )
            self.use_advanced_features = False

    def _create_ops_agents(self) -> None:
        """Create and return the set of ops agents."""
        if not self.orchestrator:
            return

        try:
            outcome = register_ops_agents(
                orchestrator=self.orchestrator,
                communication_manager=self.communication_manager,
                agent_memory=self.agent_memory,
                model=self.model,
                use_adk=USE_ADK_BRIDGE,
                logger=logger,
            )
            if outcome.backend == "adk":
                message = "+ Agente 'Ops Agent' registrado via ADK Bridge (wrapped)"
            else:
                message = "+ 3 agentes Ops registrados (code, git, docker)"
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura Ops] {UIIcons.SUCCESS} {message}",
            )

        except Exception as error:
            logger.error(
                f"Error creating specialized agents: {error}", exc_info=True
            )
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura Ops] {UIIcons.WARNING} Some specialized agents could not be created",
            )

    def _get_planning_prompt(self) -> str:
        """Return the planning prompt for the ops task."""
        return build_ops_planning_prompt(
            self.mode,
            self.delegation_payload,
            self._workspace_diff_prompt(),
        )

    def _get_delegation_payload_prompt_section(self) -> str:
        """Render structured delegation payload for Ops planning/chat prompts."""
        return render_delegation_context(self.delegation_payload)

    def _get_effective_prompt(self) -> str:
        """Build the actual prompt sent to Ops planning/chat paths."""
        return build_effective_ops_prompt(self.prompt, self.delegation_payload)

    def _plan_with_llm(self, prompt: str) -> Optional[List[Dict[str, Any]]]:
        """Plan the ops task using the LLM."""
        if self.planner:
            return self.planner.plan_with_llm(
                self._get_effective_prompt() if prompt == self.prompt else prompt,
                system_prompt=self._get_planning_prompt(),
            )
        return None

    def _decompose_and_plan(self, prompt: str) -> Optional[Any]:
        """Decompose the problem using AgiPlanner."""
        if self.planner:
            return self.planner.decompose_and_plan(
                self._get_effective_prompt() if prompt == self.prompt else prompt,
                system_prompt=self._get_planning_prompt(),
            )
        return None

    def _select_agent_for_task(self, task: Any) -> str:
        """Select the best agent for a given task."""
        available_agents = self.orchestrator.agents if self.orchestrator else ()
        return select_ops_agent(task, available_agents)

    def _handle_run_exception(self, error: Exception) -> None:
        """Translate an unhandled Ops execution failure."""
        self._record_final_error(error)
        logger.critical(f"OpsWorker thread crashed: {error}", exc_info=True)
        if self.headless:
            self._publish_terminal_result(
                self.final_error
                or {
                    "status": "error",
                    "error": str(error),
                    "prompt": self.prompt,
                    "mode": self.mode,
                    "delegation_payload": self.delegation_payload,
                    "error_code": "worker_error",
                }
            )
        if self.status_queue:
            try:
                self.agi_event_adapter.emit_chat_message(
                    sender="system",
                    content=f"› [Aura Ops] ❌ Erro crítico no worker: {error}",
                )
            except Exception as emit_error:
                logger.debug(f"Error queuing error message: {emit_error}")
        try:
            self.cleanup()
        except Exception as cleanup_error:
            logger.warning(f"Erro no cleanup do OpsWorker: {cleanup_error}")

    def _resolve_api_key(self, provider: str) -> Optional[str]:
        """Resolve API key for the given provider, posting error to queue if missing."""
        policy = get_ops_provider_policy(provider)
        api_key = self.api_keys.get(policy.credential_name)
        if policy.drop_unsupported_params:
            import litellm as _litellm

            _litellm.api_version = "v1"
            _litellm.drop_params = True
        if not api_key:
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=(
                    f"› [Aura Ops] {UIIcons.WARNING} "
                    f"{format_missing_ops_credential(policy)}"
                ),
            )
            return None
        return api_key

    def _validate_task_plan(self, task_plan: Any) -> tuple:
        """Validate and filter task plan. Returns (valid_plan, use_workflow)."""
        if not (task_plan and len(task_plan.tasks) > 1):
            return None, False

        valid_tasks = valid_workflow_tasks(task_plan.tasks)

        if len(valid_tasks) > 1:
            task_plan.tasks = valid_tasks
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura Ops] {UIIcons.INFO} Using workflow for {len(valid_tasks)} valid tasksdas",
            )
            return task_plan, True

        self.agi_event_adapter.emit_chat_message(
            sender="agent",
            content=f"› [Aura Ops] {UIIcons.WARNING} Plan created but too few valid tasks, using default execution",
        )
        return None, False

    def _execute_workflow_path(self, task_plan: Any, loading: Any) -> bool:
        """Execute workflow path. Returns True if workflow completed (caller should return)."""
        workflow = None
        try:
            from aura_cli.cli.workers.tool_panel_helper import tool_panel_context

            workflow, panel = self._build_ops_workflow(task_plan)
            if panel:
                from aura_cli.cli.ui.composition import publish_subagent_panel

                publish_subagent_panel(self.status_queue, panel)

            if loading:
                loading.update(LoadingState.EXECUTING, "Executando workflow...")

            if panel:
                assert self.workflow_executor is not None
                self._setup_ops_panel_tracking(panel)

            task_description = (
                f"{self.mode}: {self.prompt[:70]}"
                if len(self.prompt) > 70
                else f"{self.mode}: {self.prompt}"
            )
            try:
                with tool_panel_context(
                    task_id=None, task_description=task_description
                ):
                    assert self.workflow_executor is not None
                    workflow_result = self.workflow_executor.execute_workflow(
                        workflow, max_iterations=1000
                    )
            finally:
                if panel:
                    assert self.workflow_executor is not None
                    self.workflow_executor.step_wrapper = None

            self.dashboard_active = False
            if self.dashboard_thread:
                self.dashboard_thread.join(timeout=1.0)

            status = workflow_result.get("status", "unknown")
            icon = UIIcons.SUCCESS if status == "completed" else UIIcons.WARNING
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura Ops] {icon} Workflow {'completed' if status == 'completed' else f'finalizado com status: {status}'}! ({workflow_result.get('iterations', 0)} iterações)",
            )
            if status != "completed":
                error = RuntimeError(f"Workflow terminou com status: {status}")
                if workflow is not None and self._workflow_has_partial_effects(
                    workflow
                ):
                    self._record_workflow_reconciliation_error(error, workflow)
                else:
                    self._record_final_error(error, error_code="workflow_failed")
                self._save_worker_snapshot()
                from aura_cli.core.stats import get_stats

                get_stats().set_status("idle", "")
                if loading:
                    loading.complete()
                return True
            result = build_ops_workflow_result(
                prompt=self.prompt,
                model=self.model,
                mode=self.mode,
                workflow_result=workflow_result,
                context_summary=self.context_manager.get_context_summary(),
                tools_used=getattr(self.context_manager, "tools_used", []) or [],
                delegation_payload=self.delegation_payload,
                workspace_diff=self._workspace_diff_payload(),
            )
            self._record_final_result(result)
            if self.headless:
                self._publish_terminal_result(result)

            self._save_worker_snapshot()
            from aura_cli.core.stats import get_stats

            get_stats().set_status("idle", "")
            if loading:
                loading.complete()
            return True
        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            if workflow is not None and self._workflow_has_partial_effects(workflow):
                self._record_workflow_reconciliation_error(e, workflow)
                self._save_worker_snapshot()
                if loading:
                    loading.complete()
                self.agi_event_adapter.emit_chat_message(
                    sender="agent",
                    content=(
                        f"› [Aura Ops] {UIIcons.WARNING} Workflow interrompido com "
                        "efeito possível; reconciliação necessária antes de repetir"
                    ),
                )
                return True
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura Ops] {UIIcons.WARNING} Erro no workflow, continuando com execução padrão",
            )
            return False

    def _build_ops_workflow(self, task_plan: Any) -> tuple:
        """Build the Workflow object and optional SubAgentPanel. Returns (workflow, panel)."""
        from aura_cli.core.agents.agent_workflow import Workflow

        assert self.orchestrator is not None
        blueprint = build_ops_workflow_blueprint(
            task_plan,
            mode=self.mode,
            prompt=self.prompt,
            workflow_id=f"ops_{int(time.time())}",
            available_agents=self.orchestrator.agents,
        )
        workflow = Workflow(
            workflow_id=blueprint.workflow_id,
            name=blueprint.name,
            description=blueprint.description,
        )
        panel = (
            SubAgentPanel(title=f"Delegando {len(blueprint.steps)}")
            if SubAgentPanel
            else None
        )

        for step in blueprint.steps:
            self._record_structured_task_artifacts(dict(step.parameters))
            workflow.add_step(
                step_id=step.step_id,
                name=step.name,
                agent_id=step.agent_id,
                task_description=step.task_description,
                parameters=dict(step.parameters),
                dependencies=list(step.dependencies),
                retry_count=step.retry_count,
            )
            if panel:
                panel.add_task(step.step_id, step.name)

        return workflow, panel

    def _setup_ops_panel_tracking(self, panel: Any) -> None:
        """Install step_wrapper on workflow_executor to track panel state."""
        from aura_cli.cli.ui.composition import publish_subagent_panel

        step_start_times: Dict[str, float] = {}

        def _tracked_step_wrapper(wf, step, execute_fn):
            step_start_times[step.id] = time.time()
            panel.update_task(step.id, tool_count=0)
            publish_subagent_panel(self.status_queue, panel)
            try:
                execute_fn()
            finally:
                duration = time.time() - step_start_times.get(step.id, time.time())
                if step.status.value == "completed":
                    panel.complete_task(step.id, tool_count=1, duration=duration)
                elif step.status.value == "failed":
                    panel.fail_task(step.id, error=step.error or "unknown")
                publish_subagent_panel(self.status_queue, panel)

        assert self.workflow_executor is not None
        self.workflow_executor.step_wrapper = _tracked_step_wrapper

    def _observe_agent_message(
        self,
        message: Any,
        sender_name: str,
        recipient_name: str,
        direction: str,
        internal_window: Any,
    ) -> None:
        """Capture one backend message and persist selected assistant discoveries."""
        normalized = message if isinstance(message, dict) else {"content": str(message)}
        internal_window.capture_message(sender_name, recipient_name, normalized)
        if direction == "receive" and self.agent_memory:
            timestamp = time.time()
            record = build_discovery_memory_record(
                normalized,
                sender=sender_name,
                mode=self.mode,
                timestamp=timestamp,
            )
            if record:
                self.agent_memory.store(
                    agent_id="aura_ops",
                    key=record.key,
                    value=record.value,
                    context=dict(record.context),
                    ttl=record.ttl,
                )

    def _instrument_agent_chat(
        self, user_proxy: Any, aura_ops_agent: Any, internal_window: Any
    ) -> None:
        """Attach the shared backend observer to the concrete Ops conversation."""
        if self.communication_manager and self.agent_memory:
            self.communication_manager.register_agent("aura_ops", "ops_channel")
        instrument_agent_conversation(
            user_proxy=user_proxy,
            assistant=aura_ops_agent,
            observer=lambda message, sender, recipient, direction: (
                self._observe_agent_message(
                    message, sender, recipient, direction, internal_window
                )
            ),
        )

    def _run_agent_chat(
        self, user_proxy: Any, aura_ops_agent: Any, internal_window: Any, task_plan: Any
    ) -> None:
        """Run the agent chat loop and handle results."""
        effective_prompt = self._get_effective_prompt()
        if task_plan and self.agent_memory:
            record = build_plan_memory_record(
                task_plan, effective_prompt=effective_prompt, mode=self.mode
            )
            self.agent_memory.store(
                agent_id="aura_ops",
                key=record.key,
                value=record.value,
                context=dict(record.context),
            )

        from aura_cli.cli.workers.tool_panel_helper import tool_panel_context

        task_description = (
            f"{self.mode}: {self.prompt[:70]}"
            if len(self.prompt) > 70
            else f"{self.mode}: {self.prompt}"
        )

        with tool_panel_context(task_id=None, task_description=task_description):
            user_proxy.initiate_chat(aura_ops_agent, message=effective_prompt)

        internal_window.stop()
        self.dashboard_active = False
        if self.dashboard_thread:
            self.dashboard_thread.join(timeout=1.0)

        result_panel = internal_window.get_consolidated_response()
        self.agi_event_adapter.emit_chat_message(
            sender="agent",
            content=result_panel,
        )

        summary = internal_window.get_summary()
        result = build_ops_chat_result(
            prompt=self.prompt,
            model=self.model,
            mode=self.mode,
            summary=summary,
            context_summary=self.context_manager.get_context_summary(),
            delegation_payload=self.delegation_payload,
            workspace_diff=self._workspace_diff_payload(),
        )
        self._record_final_result(result)

        self.agi_event_adapter.emit_chat_message(
            sender="agent",
            content=f"› [Aura Ops] {UIIcons.SUCCESS} Análise DevOps concluída! ({summary['tool_count']} ferramentas, {summary['duration']:.1f}s)",
        )
        self._save_worker_snapshot()
        from aura_cli.core.stats import get_stats

        get_stats().set_status("idle", "")

    def _run_impl(self) -> None:
        """Execute the DevOps operation in the background."""
        # Autonomous confirmation is scoped to this worker's task policy.
        loading = None
        if LOADING_AVAILABLE and not self.headless:
            loading = AgentLoadingStates.agent_thinking(
                _loading_console, "Aura Ops", f"{self.mode}: {self.prompt[:50]}"
            )
        else:
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura Ops] {UIIcons.OPS} Modo {self.mode} iniciado...",
            )

        if self.use_advanced_features:
            if loading:
                loading.update(
                    LoadingState.PREPARING, "Inicializando componentes avançados..."
                )
            self._initialize_advanced_components()

            if not self.headless:
                self._start_dashboard()

        actual_model = self.model

        from aura_cli.core.llm.model_utils import (
            get_provider_from_model,
            normalize_model_name,
        )
        from aura_cli.core.llm.tool_schemas import create_llm_config_with_tools

        actual_model = normalize_model_name(actual_model) or actual_model
        provider = get_provider_from_model(actual_model) or ""
        provider_policy = get_ops_provider_policy(provider)

        api_key = self._resolve_api_key(provider)
        if api_key is None:
            error = (
                f"Credencial ausente para o provider '{provider or 'desconhecido'}'."
            )
            self._record_final_error(error, error_code="configuration")
            self._publish_terminal_result(
                {
                    "status": "error",
                    "error": error,
                    "error_code": "configuration",
                    "prompt": self.prompt,
                    "mode": self.mode,
                    "delegation_payload": self.delegation_payload,
                }
            )
            return
        instrumented_ops_tools = self._build_instrumented_ops_tools()

        llm_config = create_llm_config_with_tools(
            model=actual_model,
            api_key=api_key,
            tools=instrumented_ops_tools,
            temperature=provider_policy.temperature,
            max_tokens=provider_policy.max_tokens,
        )

        system_message = build_ops_system_prompt(
            self.mode,
            workspace_diff=self._workspace_diff_prompt(),
        )

        if CONSCIOUSNESS_AVAILABLE:
            try:
                cm = get_consciousness_manager()
                system_message = cm.build_enhanced_system_message(
                    base_prompt=system_message,
                    user_query=self.prompt,
                    agent_persona="ops-agent",
                )
                logger.info(
                    "OpsWorker system_message enhanced with consciousness persona"
                )
            except Exception as e:
                logger.debug(f"Consciousness enhancement skipped for Ops: {e}")

        from aura_cli.core.agents import AgentBackendFactory

        backend = AgentBackendFactory.create()

        ops_config, proxy_config = build_ops_agent_configs(
            system_message=system_message,
            llm_config=llm_config,
        )
        aura_ops_agent = backend.create_assistant(ops_config)

        user_proxy = backend.create_user_proxy(proxy_config)

        user_proxy.is_termination_msg = is_ops_termination_message
        user_proxy.code_execution_config = False
        user_proxy.function_map = instrumented_ops_tools

        # Wire shutdown check so watchdog can halt the agent loop
        user_proxy.shutdown_check = lambda: self._shutdown_event.is_set()

        # Wire real-time event emission for user visibility during execution
        def _on_agent_message(role, content):
            self.agi_event_adapter.emit_chat_message(sender=role, content=content[:500])

        user_proxy.on_message = _on_agent_message

        task_plan = None
        use_workflow = False

        if self.use_advanced_features and self.task_planner:
            if loading:
                loading.update(LoadingState.ANALYZING, "Planejando tarefas com LLM...")
            task_plan = self._decompose_and_plan(self.prompt)
            task_plan, use_workflow = self._validate_task_plan(task_plan)
        if loading:
            loading.update(LoadingState.ANALYZING, "Iniciando análise DevOps...")
        else:
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura Ops] {UIIcons.SUCCESS} Iniciando análise DevOps...",
            )

        if (
            use_workflow
            and self.workflow_executor
            and task_plan
            and self._execute_workflow_path(task_plan, loading)
        ):
            return

        from aura_cli.cli.ui.internal_window import InternalProcessingWindow

        verbose_mode = config_manager.get("ops_verbose_mode", False)
        internal_window = InternalProcessingWindow(
            self.status_queue, "Aura Ops", verbose=verbose_mode
        )
        internal_window.start()

        self._instrument_agent_chat(user_proxy, aura_ops_agent, internal_window)

        try:
            self._run_agent_chat(user_proxy, aura_ops_agent, internal_window, task_plan)
        except Exception as e:
            error_result = {
                "status": "error",
                "error": str(e),
                "prompt": self.prompt,
                "mode": self.mode,
            }
            self._record_final_error(e)
            if self.headless:
                self._publish_terminal_result(self.final_error or error_result)
            raise

    def _save_worker_snapshot(self) -> None:
        """Save an execution snapshot to the Notebook."""
        try:
            page_path = self._create_notebook_snapshot()
            if page_path is None:
                return

            logger.info(f"Snapshot OPS salvo no Notebook: {page_path}")

            if not self.headless:
                self.agi_event_adapter.emit_chat_message(
                    sender="agent",
                    content=f"› [Aura Ops] {UIIcons.SUCCESS} Operação salva no caderno: {Path(page_path).name}",
                )
        except Exception as e:
            logger.warning(f"Error saving OPS snapshot: {e}")
