"""Composition controller for an interactive Rich CLI session.

``AppLoop`` binds command, LLM and session-lifecycle mixins to workspace services,
delegated-worker adapters and the Rich UI. Reusable policies live in Application;
this module owns mutable session wiring and concrete interface effects.
"""

from pathlib import Path
import threading
import time
from typing import TYPE_CHECKING, Any, Dict, List, Mapping, Optional

if TYPE_CHECKING:
    from rich.console import Console

    from aura_cli.cli.runtime import RuntimeServices

# --- Functional imports ---
from aura_cli.application.agents.delegation_launcher import DelegationLaunchCoordinator
from aura_cli.cli.command_handler import CommandHandlerMixin
from aura_cli.cli.delegated_tasks import (
    DelegatedTaskManager,
)
from aura_cli.cli.delegation_service import DelegationService
from aura_cli.cli.error_handling import (
    detect_provider_from_error as _detect_provider_from_error_fn,
)
from aura_cli.cli.error_handling import (
    handle_api_key_error as _handle_api_key_error_fn,
)
from aura_cli.cli.error_handling import (
    handle_generic_exception as _handle_generic_exception_fn,
)
from aura_cli.cli.error_handling import (
    handle_llm_errors as _handle_llm_errors_fn,
)
from aura_cli.cli.error_handling import (
    handle_rate_limit_error as _handle_rate_limit_error_fn,
)
from aura_cli.cli.error_handling import (
    handle_rate_limit_in_exception as _handle_rate_limit_in_exception_fn,
)
from aura_cli.cli.llm_handler import LLMQueryMixin
from aura_cli.cli.session_lifecycle import SessionLifecycleMixin
from aura_cli.cli.ui.manager import UIManager
from aura_cli.cli.ui.presenter import AppPresenter
from aura_cli.core.config import config_manager
from aura_cli.core.context.base import ContextManager
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import StatsTracker
from aura_cli.core.tools.file_system import set_allowed_base_dir

__all__ = ["AppLoop"]


class _UnavailableTurnRepository:
    """Compatibility adapter for externally constructed legacy runtimes."""

    def persist_turn(self, *args: Any, **kwargs: Any) -> None:
        return None

    def restore_latest(self, *, current_directory: str) -> None:
        return None


class AppLoop(CommandHandlerMixin, SessionLifecycleMixin, LLMQueryMixin):
    """Encapsulates the main interactive application loop."""

    def __init__(
        self,
        ui: UIManager,
        stats: StatsTracker,
        console: "Console",
        conversation_history: List[Dict[str, Any]],
        context_manager: ContextManager,
        available_tools: Dict[str, Any],
        initial_model: str,
        project_root: Path,
        runtime_services: "RuntimeServices",
    ):
        """Initialize the application loop with all required services and state."""
        self.ui = ui
        self.stats = stats
        self.logger = get_logger(__name__)
        self.console = console
        self.conversation_history = conversation_history
        self._base_system_messages = [
            dict(message)
            for message in conversation_history
            if message.get("role") == "system"
        ]
        resolved_project_root = Path(project_root).expanduser().resolve()
        if runtime_services.project_root != resolved_project_root:
            raise ValueError("RuntimeServices belongs to a different project root")
        set_allowed_base_dir(str(resolved_project_root))

        self.workspace_state = runtime_services.workspace
        self.context_manager = self.workspace_state.context
        self.available_tools = available_tools
        self.final_model = initial_model
        self.project_root = resolved_project_root
        self._runtime_services = runtime_services
        self._turn_repository = (
            getattr(runtime_services, "turn_repository", None)
            or _UnavailableTurnRepository()
        )
        self.agi_thread: Optional[Any] = None
        self.ops_thread: Optional[Any] = None
        self.shutdown_event: Optional[threading.Event] = None
        self.constitution: Optional[str] = None
        self.is_constitution_setup_active = False

        self._thread_lock = threading.RLock()
        self._max_conversation_history = config_manager.get(
            "context_max_history_size", 1000
        )

        self._memory_service = self.workspace_state.memory
        self._session_state = self.workspace_state.session
        self.imagination_manager = self.workspace_state.imagination
        self.tangent_manager = runtime_services.tangent_manager
        self.checkpoint_manager = self.workspace_state.checkpoint
        self.hook_manager = runtime_services.hook_manager
        self.notebook_manager = self._memory_service.notebook_manager
        self.presenter = AppPresenter(self.console, self.ui, self.stats)
        try:
            from aura_cli.cli.tool_execution import set_hook_manager
            from aura_cli.core.tools.checkpoint_tools import (
                set_checkpoint_manager,
                set_tangent_manager,
            )

            set_checkpoint_manager(self.checkpoint_manager)
            set_tangent_manager(self.tangent_manager)
            set_hook_manager(self.hook_manager)
        except ImportError:
            self.logger.debug("Ferramentas de checkpoint não disponíveis")
        from aura_cli.core.paths import ArtifactLayout

        hooks_config = ArtifactLayout(self.project_root).project("hooks.json")
        if hooks_config.exists():
            self.hook_manager.load_from_file(hooks_config)
        self._todo_done_count = 0  # track completed tasks for notifications
        self._task_manager = DelegatedTaskManager(
            persist_callback=self._persist_delegated_task
        )
        self._delegation_launcher = DelegationLaunchCoordinator(
            self._task_manager.register_task
        )

        def get_api_keys():
            from aura_cli.cli.helpers import get_api_keys_dict

            return get_api_keys_dict()

        self._delegation_service = DelegationService(
            launcher=self._delegation_launcher,
            conversation_history=self.conversation_history,
            project_root=self.project_root,
            model=self.final_model,
            constitution=self.constitution,
            api_keys_provider=get_api_keys,
            has_credentials=self._has_any_llm_api_key,
            logger=self.logger,
        )
        self._persistent_store: Optional[Any] = None
        self._load_persisted_delegated_tasks()

    def restore_latest_turn(self) -> bool:
        """Restore the latest complete conversation and ledger for this workspace."""
        restored = self._turn_repository.restore_latest(
            current_directory=str(self.project_root)
        )
        if restored is None:
            return False
        self._execution_session_id = restored.session_id
        self.conversation_history[:] = restored.conversation_history
        if restored.last_turn is not None:
            self._active_turn_execution = restored.last_turn
            if hasattr(self.stats, "bind_turn_execution"):
                self.stats.bind_turn_execution(restored.last_turn)
        return True

    def _get_persistent_store(self) -> Optional[Any]:
        """Return the shared persistent store when available."""
        if self._persistent_store is not None:
            return self._persistent_store
        try:
            from aura_cli.core.memory import get_persistent_store

            self._persistent_store = get_persistent_store()
        except Exception as e:
            self.logger.debug("Persistent store unavailable for delegated tasks: %s", e)
            self._persistent_store = None
        return self._persistent_store

    def _load_persisted_delegated_tasks(self, limit: int = 50) -> None:
        """Rehydrate delegated-task metadata persisted for this project."""
        store = self._get_persistent_store()
        if store is None:
            return
        try:
            recent_tasks = store.get_recent_tasks(limit)
        except Exception as e:
            self.logger.debug("Failed to load persisted delegated tasks: %s", e)
            return

        project_root_str = str(self.project_root)
        for task in recent_tasks:
            data = task.get("data") or {}
            if data.get("kind") != "delegated_chat_task":
                continue
            if data.get("project_root") != project_root_str:
                continue
            task_id = str(task.get("task_id") or "")
            if not task_id or task_id in self._task_manager.tasks:
                continue
            self._task_manager.add_rehydrated_task(
                {
                    "task_id": task_id,
                    "agent_type": data.get("agent_type"),
                    "thread_name": data.get("thread_name", ""),
                    "prompt": data.get("prompt", ""),
                    "mode": data.get("mode"),
                    "delegation_payload": data.get("delegation_payload", {}) or {},
                    "created_at": data.get("created_at_ts", 0) or time.time(),
                    "persisted_status": task.get("status", "unknown"),
                    "persisted_created_at": task.get("created_at"),
                    "persisted_completed_at": task.get("completed_at"),
                    "final_result": data.get("final_result"),
                    "final_error": data.get("final_error"),
                    "snapshot_path": data.get("snapshot_path"),
                    "fallback_reason": data.get("fallback_reason"),
                    "worker_ref": None,
                }
            )

    def _persist_delegated_task(
        self,
        *,
        task_id: str,
        agent_type: str,
        thread_name: str,
        prompt: str,
        mode: Optional[str],
        delegation_payload: Dict[str, Any],
        status: str,
        created_at: float,
        final_result: Optional[Dict[str, Any]] = None,
        final_error: Optional[Dict[str, Any]] = None,
        snapshot_path: Optional[str] = None,
        fallback_reason: Optional[str] = None,
    ) -> None:
        """Persist delegated-task metadata for recovery across sessions."""
        store = self._get_persistent_store()
        if store is None:
            return
        try:
            store.save_task(
                task_id,
                f"delegated_{agent_type}",
                status,
                {
                    "kind": "delegated_chat_task",
                    "project_root": str(self.project_root),
                    "agent_type": agent_type,
                    "thread_name": thread_name,
                    "prompt": prompt,
                    "mode": mode,
                    "delegation_payload": delegation_payload,
                    "created_at_ts": created_at,
                    "final_result": final_result,
                    "final_error": final_error,
                    "snapshot_path": snapshot_path,
                    "fallback_reason": fallback_reason,
                },
            )
        except Exception as e:
            self.logger.debug("Failed to persist delegated task '%s': %s", task_id, e)

    def _handle_rate_limit_error(
        self, error: Exception, retry_after: Optional[int] = None
    ) -> str:
        """Handle rate limit errors and return user-friendly message."""
        return _handle_rate_limit_error_fn(error, retry_after, model=self.final_model)

    def _detect_provider_from_error(self, error_str: str) -> str:
        """Detect provider from error message."""
        return _detect_provider_from_error_fn(error_str)

    def _handle_llm_errors(self, error: Exception, current_model: str) -> None:
        """Handle LLM-related errors during query processing."""
        _handle_llm_errors_fn(error, current_model, ui=self.ui)

    def _handle_api_key_error(
        self, error: Exception, error_str: str, is_leaked: bool = False
    ) -> tuple:
        """Handle API key errors and return user-friendly message."""
        return _handle_api_key_error_fn(error, error_str, is_leaked, ui=self.ui)

    def _get_thread_refs(self):
        """Get thread references safely (with lock)."""
        with self._thread_lock:
            return self.agi_thread, self.ops_thread

    def _set_thread_refs(self, agi_thread=None, ops_thread=None):
        """Set thread references safely (with lock)."""
        with self._thread_lock:
            if agi_thread is not None:
                self.agi_thread = agi_thread
            if ops_thread is not None:
                self.ops_thread = ops_thread

    @staticmethod
    def _has_any_llm_api_key(api_keys: Mapping[str, str]) -> bool:
        """Return True when any supported remote-provider key is configured."""
        return any(
            api_keys.get(key)
            for key in [
                "GOOGLE_API_KEY",
                "GEMINI_API_KEY",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "OPENROUTER_API_KEY",
                "NVIDIA_API_KEY",
                "GROQ_API_KEY",
            ]
        )

    def _load_and_display_constitution(self) -> bool:
        """Load and display the constitution in chat when /agi is activated."""
        session_state = self._session_state.get_current_state()
        if session_state and session_state.constitution:
            constitution_content = session_state.constitution
        else:
            constitution_content = self._memory_service.get_constitution() or ""
            if constitution_content and session_state:
                self._session_state.update_constitution(constitution_content)

        if constitution_content:
            self.constitution = constitution_content
            self._session_state.set_active_mode("agi")
            self.presenter.display_constitution(constitution_content)
            return True
        else:
            self.presenter.display_constitution_missing()

            self.is_constitution_setup_active = True

            constitution_worker_task = "Defina a constituição para este novo projeto através de uma conversa guiada. Use a ferramenta `save_constitution` quando o usuário confirmar o resumo final."

            from aura_cli.cli.helpers import get_api_keys_dict

            api_keys = get_api_keys_dict()

            from aura_cli.cli.utils.worker_factory import create_agi_worker_thread
            from aura_cli.cli.utils.worker_readiness import WorkerReadinessError

            try:
                _constitution_agi_worker, constitution_thread = (
                    create_agi_worker_thread(
                        objective=constitution_worker_task,
                        model=self.final_model,
                        api_keys=api_keys,
                        headless=False,
                        project_root=self.project_root,
                        shutdown_timeout=300.0,
                    )
                )
            except WorkerReadinessError as readiness_error:
                self.is_constitution_setup_active = False
                self.ui.display_warning(readiness_error.report.message)
                return False
            self._set_thread_refs(agi_thread=constitution_thread)
            if constitution_thread and constitution_thread.is_alive():
                constitution_thread.join(timeout=300)

            self.is_constitution_setup_active = False

            session_state = self._session_state.get_current_state()
            if session_state and session_state.constitution:
                constitution_content = session_state.constitution
            else:
                constitution_content = self._memory_service.get_constitution() or ""
                if constitution_content and session_state:
                    self._session_state.update_constitution(constitution_content)

            if constitution_content:
                self.constitution = constitution_content
                self._session_state.set_active_mode("agi")
                self.ui.display_info("◇ Constituição do Projeto criada:")
                self.ui.print(f"\n[dim]{'=' * 60}[/dim]")
                self.ui.print("[bold cyan]◇ CONSTITUIÇÃO DO PROJETO[/bold cyan]")
                self.ui.print(f"[dim]{'=' * 60}[/dim]")
                self.ui.print(f"[white]{constitution_content}[/white]")
                self.ui.print(f"[dim]{'=' * 60}[/dim]\n")
                return True
            else:
                self.ui.display_warning(
                    "Constituição não foi criada. Tente novamente com /agi."
                )
                return False

    def _handle_rate_limit_in_exception(self, error: Exception) -> bool:
        """Handle rate limit errors detected in generic exception handler."""
        return _handle_rate_limit_in_exception_fn(error, self.final_model, ui=self.ui)

    def _handle_generic_exception(self, error: Exception) -> None:
        """Handle generic exceptions in main loop."""
        _handle_generic_exception_fn(error, self.final_model, ui=self.ui)

    def _prepare_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Prepare tool schemas for LLM function calling.

        Returns:
            List of tool schemas
        """
        if hasattr(self, "available_tools") and self.available_tools:
            tools_dict = self.available_tools
        else:
            from aura_cli.core.service_registry import get_tools_dict

            tools_dict = get_tools_dict()

        from aura_cli.core.llm.tool_schemas import create_tool_schemas

        return create_tool_schemas(tools_dict)

    def _register_delegated_task(self, **kwargs) -> None:
        """Store delegated-task metadata for follow-up queries from chat."""
        self._task_manager.register_task(**kwargs)

    def _reconcile_delegated_task_state(self, task_info: Dict[str, Any]) -> None:
        """Pull final outcome metadata from the live worker into local/persistent state."""
        self._task_manager.reconcile_state(task_info)

    def _resolve_delegated_task(
        self, task_id: str = "", agent_type: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Resolve delegated-task metadata by task_id, agent type, or latest task."""
        return self._task_manager.resolve_task(task_id, agent_type)

    def list_delegated_tasks(self) -> str:
        """List known delegated AGI/Ops tasks for follow-up."""
        return self._task_manager.list_tasks()

    def get_latest_delegated_task(self, agent_type: str = "") -> str:
        """Return the latest delegated task, optionally filtered by agent type."""
        return self._task_manager.get_latest_task(agent_type)

    def summarize_delegated_tasks(self) -> str:
        """Return a compact summary of delegated-task counts and latest entries."""
        return self._task_manager.summarize_tasks()

    def get_delegated_task_status(self, task_id: str = "", agent_type: str = "") -> str:
        """Return status for a delegated task in this session."""
        return self._task_manager.get_task_status(task_id, agent_type)

    def summarize_delegated_task(self, task_id: str = "", agent_type: str = "") -> str:
        """Return a detailed summary for a delegated task."""
        return self._task_manager.summarize_task(task_id, agent_type)

    def get_delegated_task_artifacts(
        self, task_id: str = "", agent_type: str = ""
    ) -> str:
        """Return concrete artifacts associated with a delegated task."""
        return self._task_manager.get_task_artifacts(task_id, agent_type)

    def read_delegated_task_snapshot(
        self, task_id: str = "", agent_type: str = "", max_chars: int = 4000
    ) -> str:
        """Read the notebook snapshot associated with a delegated task."""
        return self._task_manager.read_task_snapshot(task_id, agent_type, max_chars)

    def reattach_delegated_task_context(
        self, task_id: str = "", agent_type: str = ""
    ) -> str:
        """Prepare delegated-task context for the next chat turn and return it."""
        return self._task_manager.reattach_task_context(
            task_id, agent_type, stats=self.stats
        )

    def _do_delegate_to_agi(self, objective: str, handoff_context: str = "") -> str:
        """Launch AGI through the dedicated CLI delegation adapter."""
        self._sync_delegation_service_context()
        message, thread = self._delegation_service.launch_agi(
            objective,
            active=bool(self.agi_thread and self.agi_thread.is_alive()),
            handoff_context=handoff_context,
        )
        if thread is not None:
            self.agi_thread = thread
        return message

    def _do_delegate_to_subagent(self, task: str, context: str = "") -> str:
        """
        Delegate a focused task to a lightweight autonomous subagent.
        The subagent runs synchronously with basic tools (read, write, edit, search, shell)
        and returns the result directly. Use for tasks that need 2-5 tool calls.

        Args:
            task: Focused task description for the subagent.
            context: Optional supporting context or file paths.

        Returns:
            The subagent's execution result.
        """
        try:
            from aura_cli.cli.subagent import run_subagent

            # Show inline progress
            if hasattr(self, "ui") and self.ui:
                self.ui.print("  [dim]⟳ Subagent executando...[/dim]", end="")

            tool_calls_made = [0]
            last_tool = [""]

            def _on_tool_call(tool_name: str, count: int):
                tool_calls_made[0] = count
                last_tool[0] = tool_name

            result = run_subagent(
                task=task,
                context=context,
                model=getattr(self, "final_model", ""),
                project_root=getattr(self, "project_root", None),
                tools_dict=self.available_tools
                if isinstance(self.available_tools, dict)
                else None,
                on_tool_call=_on_tool_call,
            )

            # Update progress line
            if hasattr(self, "ui") and self.ui:
                import sys

                sys.stdout.write("\r" + " " * 60 + "\r")
                sys.stdout.flush()
                if tool_calls_made[0] > 0:
                    self.ui.print(
                        f"  [dim green]✔ Subagent concluiu ({tool_calls_made[0]} tools)[/dim green]"
                    )
                else:
                    self.ui.print("  [dim green]✔ Subagent concluiu[/dim green]")

            return result

        except Exception as e:
            self.logger.warning(f"Subagent delegation failed: {e}")
            return f"Error executing subagent: {e}"

    def _do_delegate_to_ops(
        self, task: str, mode: str = "general", handoff_context: str = ""
    ) -> str:
        """Launch Ops through the dedicated CLI delegation adapter."""
        self._sync_delegation_service_context()
        message, thread = self._delegation_service.launch_ops(
            task,
            active=bool(self.ops_thread and self.ops_thread.is_alive()),
            mode=mode,
            handoff_context=handoff_context,
        )
        if thread is not None:
            self.ops_thread = thread
        return message

    def _sync_delegation_service_context(self) -> None:
        """Refresh mutable session values before a delegated launch."""
        self._delegation_service.model = self.final_model
        self._delegation_service.constitution = self.constitution
        self._delegation_service.project_root = self.project_root
