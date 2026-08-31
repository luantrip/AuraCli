"""
AgiExecutionEngine Module.

This module handles the core execution logic for the AGI Worker, including:
- Environment configuration (API keys)
- Agent creation (UserProxy, AuraAGI)
- Workflow execution
- Chat execution
- Event capturing
"""

from contextlib import nullcontext
import logging
from pathlib import Path
import re
import time
from typing import Any, Callable, ContextManager, Dict, Literal

from aura_cli.application.execution_feedback import LoadingState
from aura_cli.core.agents import AgentBackendFactory, AgentConfig
from aura_cli.core.agents.conversation_instrumentation import (
    instrument_agent_conversation,
)
from aura_cli.core.llm.tool_schemas import create_llm_config_with_tools
from aura_cli.core.ui_bridge import UIIcons

logger = logging.getLogger(__name__)

# Tools exposed to the AGI agent. Kept intentionally broad (AGI needs deep access)
# but capped to avoid Nemotron schema degradation (content=None above ~50 tools).
_AGI_ESSENTIAL_TOOLS = {
    # Filesystem
    "read_file",
    "write_file",
    "list_directory",
    "tree_view",
    "find_in_files",
    "glob_search",
    "advanced_grep_search",
    # Codebase analysis
    "scan_project",
    "analyze_code",
    "analyze_project_structure",
    "analyze_project_quality",
    "analyze_project_security",
    "analyze_dependencies",
    "dep_find_dependencies",
    "dep_find_dependents",
    "dep_analyze_import_graph",
    "summarize_code",
    "validate_syntax",
    "classify_code",
    "find_duplicate_code",
    "check_file_changes",
    "investigate_codebase",
    "inspect_code_structure",
    "deep_project_analysis",
    "discover_patterns",
    "view_repo_map",
    "view_subdirectory",
    "codebase_search",
    # Editing
    "edit_file",
    "sanitize_code",
    "format_file",
    "backup_file",
    "restore_backup",
    # Shell & system
    "run_shell_command",
    "process_info",
    "check_port",
    "system_resources",
    # Git
    "git_status",
    "git_commit",
    "git_diff",
    "git_log",
    "git_branch",
    "suggest_commit_message",
    # Testing & refactoring
    "generate_tests_ml",
    "run_tests_advanced",
    "plan_refactoring",
    # Memory & context
    "notebook_write",
    "notebook_read",
    "notebook_search",
    "notebook_list",
    "get_context_usage",
    "forget_messages",
    # Checkpoints
    "create_checkpoint",
    "restore_checkpoint",
    "list_checkpoints",
    # Web & delegation
    "web_search",
    "browse_content",
    # Vision
    "view_image",
    "take_screenshot",
    "describe_url_visual",
    "delegate_to_ops",
}


# Task-type → param-normalization tables

# Tasks that need project_path resolved from path fallback
_PROJECT_PATH_TASKS = frozenset(
    {
        "analyze_project_structure",
        "analyze_project_quality",
        "analyze_project_security",
        "analyze_project_documentation",
        "compare_project_fronts",
    }
)

# Tasks that need a plain path resolved
_FILE_PATH_TASKS = frozenset(
    {
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "tree_view",
    }
)

# Tasks that need path + pattern
_SEARCH_TASKS = frozenset({"codebase_search", "find_in_files"})

# Tasks that need file_path resolved from file_path|path (optional)
_REVIEW_TASKS = frozenset({"review_file", "find_related_tests", "generate_tests"})

# Tasks that need test_path resolved
_TEST_RUN_TASKS = frozenset({"run_tests", "validate_tests_pass"})


def _normalize_task_params(task_type: str, params: dict) -> None:
    """Normalize task parameters in-place based on task type."""
    if task_type in _PROJECT_PATH_TASKS:
        params["project_path"] = str(
            params.get("project_path") or params.get("path") or "."
        )

    elif task_type in _FILE_PATH_TASKS:
        params["path"] = str(params.get("path") or ".")

    elif task_type in _SEARCH_TASKS:
        params["path"] = str(params.get("path") or ".")
        params["pattern"] = str(params.get("pattern") or "")

    elif task_type in _REVIEW_TASKS:
        fp = params.get("file_path") or params.get("path")
        if fp:
            params["file_path"] = str(fp)

    elif task_type in _TEST_RUN_TASKS:
        params["test_path"] = str(params.get("test_path") or params.get("path") or ".")

    elif task_type == "plan_refactoring":
        params["pattern"] = str(params.get("pattern") or "")
        params["replacement"] = str(params.get("replacement") or "")
        params["scope"] = str(params.get("scope") or params.get("path") or ".")

    elif task_type in {"analyze_impact", "suggest_strategy"}:
        _normalize_analysis_params(task_type, params)


def _normalize_analysis_params(task_type: str, params: dict) -> None:
    """Normalize params for analyze_impact and suggest_strategy tasks."""
    if task_type == "analyze_impact":
        fp = params.get("file_path") or params.get("path")
        if fp:
            params["file_path"] = str(fp)
        params["scope"] = str(params.get("scope") or ".")
    else:  # suggest_strategy
        params["pattern"] = str(params.get("pattern") or "")
        params["scope"] = str(params.get("scope") or params.get("path") or ".")


class AgiExecutionEngine:
    """
    Encapsulates the execution logic for the AGI Agent.
    """

    def __init__(
        self,
        agi_worker: Any,  # Reference back to worker for shared state access (temporarily tight coupling)
        planner: Any,
        context_manager: Any,
        validator: Any,
        workflow_executor: Any,
        orchestrator: Any,
        git_manager: Any,
        communication_manager: Any = None,
        agent_memory: Any = None,
        progress_factory: Callable[[str], Any] | None = None,
        publish_progress: Callable[[Any, Any], None] | None = None,
        publish_status: Callable[[Any, Literal["agi", "ops", "tester"], str], None]
        | None = None,
        tool_panel_context_factory: Callable[..., ContextManager[Any]] | None = None,
    ):
        """Initialize the instance."""
        self.worker = agi_worker
        self.planner = planner
        self.context_manager = context_manager
        self.validator = validator
        self.workflow_executor = workflow_executor
        self.orchestrator = orchestrator
        self.git_manager = git_manager
        self.communication_manager = communication_manager
        self.agent_memory = agent_memory
        self.progress_factory = progress_factory
        self.publish_progress = publish_progress
        self.publish_status = publish_status
        self.tool_panel_context_factory = tool_panel_context_factory or (
            lambda **_: nullcontext()
        )
        self.event_adapter = agi_worker.agi_event_adapter
        self.api_keys = agi_worker.api_keys
        self.model = agi_worker.model
        self.available_tools = agi_worker.available_tools
        self.headless = agi_worker.headless
        self.task_id = agi_worker.task_id
        self.result_queue = agi_worker.result_queue

    def run(self, prompt: str, loading: Any = None) -> None:
        """
        Main execution entry point.
        """
        try:
            api_key, actual_model = self._configure_environment()
            if not api_key:
                error = "Credencial ausente ou provider não configurado."
                self.worker._record_final_error(error, error_code="configuration")
                if self.headless:
                    self.worker._publish_terminal_result(
                        self.worker.final_error
                        or {
                            "status": "error",
                            "error": error,
                            "error_code": "configuration",
                            "prompt": prompt,
                        }
                    )
                return

            if loading:
                loading.update(LoadingState.PREPARING, "Configurando ambiente...")
            if self.context_manager and hasattr(self.context_manager, "prepare_evidence"):
                self.context_manager.prepare_evidence(prompt)
            user_proxy, aura_agi_agent = self._create_agents(
                actual_model, api_key, prompt
            )
            task_plan = None
            use_workflow = False

            if self.worker.use_advanced_features and self.planner:
                if loading:
                    loading.update(
                        LoadingState.ANALYZING, "Planejando tarefas com LLM..."
                    )

                task_plan = self.planner.decompose_and_plan(prompt)

                if task_plan and len(task_plan.tasks) > 1:
                    valid_tasks = self._validate_tasks(task_plan.tasks)

                    if len(valid_tasks) > 1:
                        task_plan.tasks = valid_tasks
                        use_workflow = True
                        self.event_adapter.emit_chat_message(
                            sender="agent",
                            content=f"› [Aura AGI] {UIIcons.INFO} Using workflow for {len(valid_tasks)} valid tasksdas",
                        )
                        self.planner.sync_plan_to_todo(task_plan, prompt)
                    else:
                        self.event_adapter.emit_chat_message(
                            sender="agent",
                            content=f"› [Aura AGI] {UIIcons.WARNING} Plan created but too few valid tasks, using default execution",
                        )
                        task_plan = None
            if loading:
                loading.update(
                    LoadingState.ANALYZING, "Iniciando análise de contexto..."
                )
            else:
                self.event_adapter.emit_chat_message(
                    sender="agent",
                    content=f"› [Aura AGI] {UIIcons.SUCCESS} Contexto analisado. Iniciando análise...",
                )
            if use_workflow and self.workflow_executor and task_plan:
                self._execute_workflow(
                    workflow_executor=self.workflow_executor,
                    task_plan=task_plan,
                    loading=loading,
                    prompt=prompt,
                )
            else:
                self._execute_chat(user_proxy, aura_agi_agent, prompt, loading)

            if hasattr(self.worker, "_check_and_save_periodic_snapshot"):
                self.worker._check_and_save_periodic_snapshot()
            self._handle_post_execution()
            self._save_final_notebook_snapshot()

            from aura_cli.core.stats import get_stats

            get_stats().set_status("idle", "")

            if loading:
                loading.complete()

        except Exception as e:
            self._handle_error(e, prompt)
            raise

    def _configure_environment(self):
        """Resolves the API key and model for the current provider.

        Does NOT write to os.environ — api_key is passed directly to
        litellm via llm_config to avoid race conditions in multi-thread scenarios.
        """
        actual_model = self.model

        from aura_cli.core.llm.model_utils import (
            get_provider_from_model,
            normalize_model_name,
        )

        actual_model = normalize_model_name(actual_model)
        provider = get_provider_from_model(actual_model) or ""

        credential_names = {
            "gemini": "GOOGLE_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "gpt": "OPENAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "nvidia": "NVIDIA_API_KEY",
            "cerebras": "CEREBRAS_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        credential_name = credential_names.get(provider, "GOOGLE_API_KEY")
        api_key = self.api_keys.get(credential_name)
        if not api_key:
            if provider in credential_names:
                message = f"{credential_name} não configurada. Configure com /settings"
            else:
                message = "Nenhuma API key configurada. Configure com /settings"
            self._emit_warning(message)
            return None, None

        if provider == "gemini":
            import litellm

            litellm.drop_params = True

        return api_key, actual_model

    def _create_agents(self, model, api_key, prompt):
        """Creates UserProxy and AuraAGI agents."""
        tools = {
            k: v for k, v in self.available_tools.items() if k in _AGI_ESSENTIAL_TOOLS
        }
        instrumented_tools = self._build_instrumented_tools(tools)
        llm_config = create_llm_config_with_tools(
            model=model,
            api_key=api_key,
            tools=instrumented_tools,
            temperature=0.7,
            max_tokens=4096,
        )

        base_system_message = self._get_base_system_message()
        if self.context_manager:
            system_message = self.context_manager.build_conscious_system_message(
                base_system_message, prompt
            )
        else:
            system_message = base_system_message

        backend = AgentBackendFactory.create()

        agi_config = AgentConfig(
            name="aura_agi",
            role="assistant",
            system_message=system_message,
            llm_config=llm_config,
        )
        aura_agi_agent = backend.create_assistant(agi_config)

        proxy_config = AgentConfig(
            name="user_proxy",
            role="proxy",
            system_message="",
            llm_config={},
            max_consecutive_auto_reply=30,
            human_input_mode="NEVER",
        )
        user_proxy = backend.create_user_proxy(proxy_config)

        user_proxy.is_termination_msg = lambda x: (
            x.get("content", "").rstrip().endswith("TERMINATE")
        )
        user_proxy.code_execution_config = False
        user_proxy.function_map = instrumented_tools

        # Wire shutdown check so watchdog can halt the agent loop
        user_proxy.shutdown_check = lambda: self.worker._shutdown_event.is_set()

        # Wire real-time event emission for user visibility during execution
        def _on_agent_message(role, content):
            self.worker.agi_event_adapter.emit_chat_message(
                sender=role, content=content[:500]
            )

        user_proxy.on_message = _on_agent_message

        return user_proxy, aura_agi_agent

    def _execute_workflow(self, workflow_executor, task_plan, loading, prompt):
        """Executes a planned workflow."""
        try:
            workflow, panel = self._build_agi_workflow(task_plan, prompt)

            if panel and self.publish_progress:
                self.publish_progress(self.worker.status_queue, panel)

            if loading:
                loading.update(LoadingState.EXECUTING, "Executando workflow...")

            if panel:
                self._setup_agi_panel_tracking(workflow_executor, panel)

            task_description = prompt[:80] + "..." if len(prompt) > 80 else prompt

            try:
                with self.tool_panel_context_factory(
                    task_id=None, task_description=task_description
                ):
                    workflow_result = workflow_executor.execute_workflow(
                        workflow, max_iterations=1000
                    )
            finally:
                if panel:
                    workflow_executor.step_wrapper = None

            self.worker.dashboard_active = False
            if self.worker.dashboard_thread:
                self.worker.dashboard_thread.join(timeout=1.0)

            if workflow_result.get("status") == "completed":
                self.event_adapter.emit_chat_message(
                    sender="agent",
                    content=f"› [Aura AGI] {UIIcons.SUCCESS} Workflow completed! ({workflow_result.get('iterations', 0)} iterations)",
                )
            else:
                self.event_adapter.emit_chat_message(
                    sender="agent",
                    content=f"› [Aura AGI] {UIIcons.WARNING} Workflow finished with status: {workflow_result.get('status', 'unknown')}",
                )

            workflow_status = str(workflow_result.get("status") or "error").lower()
            terminal_status = (
                workflow_status
                if workflow_status
                in {
                    "completed",
                    "failed",
                    "cancelled",
                    "timeout",
                    "timed_out",
                    "blocked",
                }
                else "error"
            )
            result_payload: Dict[str, Any] = {
                "status": terminal_status,
                "prompt": prompt,
                "model": self.model,
                "workflow_result": workflow_result,
                "context_summary": self.context_manager.get_context_summary(),
            }
            if terminal_status != "completed":
                result_payload["error_code"] = "workflow_not_completed"
                result_payload["fallback_reason"] = workflow_status
            result = self._build_final_result_payload(result_payload)
            if hasattr(self.worker, "_record_final_result"):
                self.worker._record_final_result(result)

        except Exception as e:
            logger.error(f"Error executing workflow: {e}", exc_info=True)
            self.event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura AGI] {UIIcons.WARNING} Erro no workflow, continuando com execução padrão",
            )
            raise e

    def _build_agi_workflow(self, task_plan, prompt) -> tuple:
        """Build Workflow and optional SubAgentPanel. Returns (workflow, panel)."""
        from aura_cli.core.agents.agent_workflow import Workflow

        workflow = Workflow(
            workflow_id=f"agi_{int(time.time())}",
            name=f"AGI Workflow: {prompt[:50]}...",
            description=prompt,
        )
        panel = (
            self.progress_factory(f"Delegando {len(task_plan.tasks)}")
            if self.progress_factory
            else None
        )

        for task in task_plan.tasks:
            agent_id = self.planner.select_agent_for_task(task, self.orchestrator)
            if agent_id not in self.orchestrator.agents:
                logger.warning(
                    f"Agent {agent_id} not found, using code_agent as fallback"
                )
                agent_id = "code_agent"
            params = task.parameters.copy()
            params = self.planner.normalize_task_params(params, agent_id)
            self._record_structured_task_artifacts(params)
            workflow.add_step(
                step_id=task.id,
                name=task.description[:50],
                agent_id=agent_id,
                task_description=task.description,
                parameters=params,
                dependencies=task.dependencies,
                retry_count=1,
            )
            if panel:
                panel.add_task(task.id, task.description[:50])

        return workflow, panel

    def _setup_agi_panel_tracking(self, workflow_executor, panel) -> None:
        """Install step_wrapper to track SubAgentPanel state during workflow."""
        step_start_times: Dict[str, float] = {}

        def _tracked_step_wrapper(wf, step, execute_fn):
            step_start_times[step.id] = time.time()
            panel.update_task(step.id, tool_count=0)
            if self.publish_progress:
                self.publish_progress(self.worker.status_queue, panel)
            try:
                execute_fn()
            finally:
                duration = time.time() - step_start_times.get(step.id, time.time())
                if step.status.value == "completed":
                    panel.complete_task(step.id, tool_count=1, duration=duration)
                elif step.status.value == "failed":
                    panel.fail_task(step.id, error=step.error or "unknown")
                if self.publish_progress:
                    self.publish_progress(self.worker.status_queue, panel)

        workflow_executor.step_wrapper = _tracked_step_wrapper

    def _execute_chat(self, user_proxy, aura_agi_agent, prompt, loading):
        """Executes the standard chat loop."""
        self._wrap_agent_methods(user_proxy, aura_agi_agent)
        if not self._check_git_safety(prompt) and self.publish_status:
            self.publish_status(
                self.worker.status_queue,
                "agi",
                f"{UIIcons.WARNING} Repositório Git em estado inseguro - prosseguindo com cuidado",
            )
        if self.validator:
            user_prompt = self.validator.validate_and_sanitize_prompt(prompt)
        else:
            user_prompt = prompt

        task_description = prompt[:80] + "..." if len(prompt) > 80 else prompt

        with self.tool_panel_context_factory(
            task_id=None, task_description=task_description
        ):
            user_proxy.initiate_chat(aura_agi_agent, message=user_prompt)

        self.worker.dashboard_active = False
        if self.worker.dashboard_thread:
            self.worker.dashboard_thread.join(timeout=1.0)

        result = self._build_final_result_payload(
            {
                "status": "completed",
                "prompt": prompt,
                "model": self.model,
                "validation_result": None,
            }
        )
        if hasattr(self.worker, "_record_final_result"):
            self.worker._record_final_result(result)

        self.event_adapter.emit_chat_message(
            sender="agent",
            content=f"› [Aura AGI] {UIIcons.SUCCESS} Análise concluída!",
        )

    def _check_git_safety(self, prompt):
        """Checks git safety before execution."""
        is_safe, warning = self.git_manager.validate_before_write()
        if not is_safe and not self.headless:
            self.event_adapter.emit_chat_message(
                sender="system",
                content=f"› [Aura AGI] {UIIcons.WARNING} {warning}",
            )
            checkpoint_hash = self.git_manager.create_checkpoint(
                f"aura-wip: Pre-AGI checkpoint for: {prompt[:50]}"
            )
            if checkpoint_hash:
                self.event_adapter.emit_chat_message(
                    sender="system",
                    content=f"› [Aura AGI] {UIIcons.INFO} Checkpoint created automatically: {checkpoint_hash[:8]}",
                )
            return False
        elif is_safe and self.git_manager.is_git_repository():
            self.git_manager.create_checkpoint(
                f"aura-wip: Pre-AGI checkpoint for: {prompt[:50]}"
            )
        return True

    def _handle_post_execution(self):
        """Handles post-execution validation and consolidation."""
        generated_files = self.worker.generated_files

        if self.validator:
            if generated_files:
                self.validator.auto_validate_generated_files(generated_files)
            if self.worker.enable_adversarial_validation and generated_files:
                self.validator.run_adversarial_validation(
                    files_to_validate=generated_files,
                    model=self.model,
                    api_keys=self.api_keys,
                    available_tools=self.available_tools,
                    status_queue=self.worker.status_queue,
                )
            from aura_cli.core.config import config_manager

            self.validator.consolidate_learned_rules(config_manager)

    def _save_final_notebook_snapshot(self) -> None:
        """Save the final AGI execution snapshot to the Notebook."""
        try:
            if not hasattr(self.worker, "_notebook_service"):
                return

            history = (
                self.context_manager.conversation_history
                if hasattr(self.context_manager, "conversation_history")
                else []
            )

            if not history or len(history) < 2:
                return
            page_path = self.worker._notebook_service.create_snapshot(
                history, use_cognitive_refinement=True, refinement_threshold_tokens=8000
            )
            self.worker.last_snapshot_path = str(page_path)

            logger.info(f"Snapshot final AGI salvo no Notebook: {page_path}")

            if not self.headless:
                self.event_adapter.emit_chat_message(
                    sender="system",
                    content=f"› [Aura AGI] {UIIcons.SUCCESS} Análise salva no caderno: {Path(page_path).name}",
                )
        except Exception as e:
            logger.warning(f"Error saving final AGI snapshot: {e}")

    def _handle_error(self, e, prompt):
        """Handles execution errors."""
        if hasattr(self.worker, "_record_final_error"):
            self.worker._record_final_error(e)
        # NOTE: skip_confirmations restoration is deferred — tracked via session state
        logger.debug(f"Error handling workflow result: {e}")
        error_result = {"status": "error", "error": str(e), "prompt": prompt}
        if self.headless:
            self.worker._publish_terminal_result(
                getattr(self.worker, "final_error", None) or error_result
            )

    def _build_final_result_payload(
        self, base_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Attach reusable execution artifacts to a final AGI result."""
        result = dict(base_result)
        tools_used = []
        if self.context_manager and hasattr(self.context_manager, "tools_used"):
            tools_used = list(getattr(self.context_manager, "tools_used", []) or [])
        generated_files = list(getattr(self.worker, "generated_files", []) or [])
        edited_files = list(getattr(self.worker, "edited_files", []) or [])
        analyzed_files = list(getattr(self.worker, "analyzed_files", []) or [])
        files_touched = []
        for file_path in generated_files + edited_files + analyzed_files:
            if file_path not in files_touched:
                files_touched.append(file_path)
        result.setdefault("tools_used", tools_used)
        result.setdefault("generated_files", generated_files)
        result.setdefault("edited_files", edited_files)
        result.setdefault("analyzed_files", analyzed_files)
        result.setdefault("files_touched", files_touched)
        return result

    def _extract_file_artifacts(self, content: str) -> None:
        """Extract file artifacts from tool-call-like message content."""
        if not content:
            return

        path_matches = re.findall(
            r"""path["']?\s*[:=]\s*["']([^"']+)["']""",
            content,
            flags=re.IGNORECASE,
        )
        file_paths = [path for path in path_matches if "/" in path or "." in path]
        if not file_paths:
            return

        lowered = content.lower()
        for file_path in file_paths:
            if "write_file" in lowered and file_path not in self.worker.generated_files:
                self.worker.generated_files.append(file_path)
            if "edit_file" in lowered and file_path not in self.worker.edited_files:
                self.worker.edited_files.append(file_path)
            if (
                any(
                    tool in lowered
                    for tool in [
                        "read_file",
                        "find_in_files",
                        "analyze_code",
                        "validate_syntax",
                    ]
                )
                and file_path not in self.worker.analyzed_files
            ):
                self.worker.analyzed_files.append(file_path)

    def _record_structured_task_artifacts(self, params: Dict[str, Any]) -> None:
        """Record file artifacts from structured workflow task parameters."""
        task_type = str(params.get("type", "")).lower()
        candidate_paths = [
            params.get("path"),
            params.get("file_path"),
            params.get("test_path"),
        ]
        for path in candidate_paths:
            if not isinstance(path, str) or not path.strip():
                continue
            normalized = path.strip()
            if normalized in {".", "/"}:
                continue
            if task_type in {"write_file"}:
                if normalized not in self.worker.generated_files:
                    self.worker.generated_files.append(normalized)
            elif task_type in {"edit_file", "apply_refactoring"}:
                if normalized not in self.worker.edited_files:
                    self.worker.edited_files.append(normalized)
            elif (
                task_type
                in {
                    "read_file",
                    "find_in_files",
                    "analyze_code",
                    "validate_syntax",
                    "review_file",
                    "analyze_impact",
                    "run_tests",
                    "find_related_tests",
                    "validate_tests_pass",
                }
                and normalized not in self.worker.analyzed_files
            ):
                self.worker.analyzed_files.append(normalized)

    def _record_tool_artifacts(
        self, tool_name: str, tool_kwargs: Dict[str, Any]
    ) -> None:
        """Record file artifacts from a structured tool invocation."""
        path_value = None
        for key in ("path", "file_path", "test_path"):
            value = tool_kwargs.get(key)
            if isinstance(value, str) and value.strip():
                path_value = value.strip()
                break
        if not path_value or path_value in {".", "/"}:
            return

        if tool_name == "write_file":
            if path_value not in self.worker.generated_files:
                self.worker.generated_files.append(path_value)
        elif tool_name == "edit_file":
            if path_value not in self.worker.edited_files:
                self.worker.edited_files.append(path_value)
        elif (
            tool_name
            in {
                "read_file",
                "find_in_files",
                "analyze_code",
                "validate_syntax",
                "review_file",
            }
            and path_value not in self.worker.analyzed_files
        ):
            self.worker.analyzed_files.append(path_value)

    def _build_instrumented_tools(self, tools: Dict[str, Any]) -> Dict[str, Any]:
        """Wrap tools so artifact classification uses real tool-call arguments."""
        instrumented_tools: Dict[str, Any] = {}
        for tool_name, tool_func in tools.items():
            if not callable(tool_func):
                instrumented_tools[tool_name] = tool_func
                continue

            def wrapped_tool(
                *args, __tool_name=tool_name, __tool_func=tool_func, **kwargs
            ):
                self._record_tool_artifacts(__tool_name, kwargs)
                return __tool_func(*args, **kwargs)

            wrapped_tool.__name__ = tool_name
            instrumented_tools[tool_name] = wrapped_tool
        return instrumented_tools

    def _emit_warning(self, message):
        """Emit a warning event to the status queue."""
        self.event_adapter.emit_chat_message(
            sender="agent",
            content=f"› [Aura AGI] {UIIcons.WARNING} {message}",
        )

    def _validate_tasks(self, tasks):
        """Validate tasks before executing workflow."""
        valid_tasks = []
        allowed_types = set(getattr(self.planner, "allowed_task_types", []) or [])

        for task in tasks:
            params = getattr(task, "parameters", None)
            if not isinstance(params, dict):
                logger.warning("Ignoring task without valid parameters")
                continue

            task_type = params.get("type", "").lower()
            if not task_type:
                logger.warning("Ignoring task without type")
                continue

            if allowed_types and task_type not in allowed_types:
                logger.warning("Ignoring task with unsupported type '%s'", task_type)
                continue

            _normalize_task_params(task_type, params)

            try:
                if hasattr(self.planner, "select_agent_for_task") and self.orchestrator:
                    self.planner.select_agent_for_task(task, self.orchestrator)
            except Exception as exc:
                logger.warning("Ignoring task due to agent selection error: %s", exc)
                continue

            valid_tasks.append(task)

        return valid_tasks

    def _wrap_agent_methods(self, user_proxy, aura_agi_agent):
        """Attach the shared backend observer to the AGI conversation."""
        instrument_agent_conversation(
            user_proxy=user_proxy,
            assistant=aura_agi_agent,
            observer=self._observe_agent_message,
        )

    def _observe_agent_message(
        self, message: Any, sender: str, _recipient: str, direction: str
    ) -> None:
        """Publish one message and retain meaningful assistant discoveries."""
        content = message if isinstance(message, str) else message.get("content", "")
        self._extract_file_artifacts(content)
        self.event_adapter.emit_chat_message(
            sender=sender, content=content, task_id=self.task_id
        )
        if direction != "receive" or not isinstance(message, dict):
            return
        if self.communication_manager and self.agent_memory:
            normalized = content.casefold()
            if len(content) > 50 and any(
                keyword in normalized
                for keyword in (
                    "encontrei",
                    "descobri",
                    "identifiquei",
                    "analisei",
                    "concluí",
                )
            ):
                timestamp = time.time()
                self.agent_memory.store(
                    agent_id="aura_agi",
                    key=f"discovery_{int(timestamp)}",
                    value=content[:500],
                    context={"sender": sender, "timestamp": timestamp},
                    ttl=3600,
                )
        if content and self.validator:
            self.validator.extract_learned_rules_from_response(content)

    def _get_base_system_message(self):
        """Build the base system prompt for the AGI agent."""
        base_message = """Você é a Aura AGI, uma gerente de projetos de software autônoma e experiente, operando dentro do ecossistema Aura CLI.

**SEU OBJETIVO**: Analisar, planejar e executar tarefas complexas de desenvolvimento de software com precisão e autonomia.

**ENGINES NIM (ALTA PERFORMANCE — USE PRIMEIRO):**
- `scan_project(path=".")` — escaneia o projeto ultrarrápido via Imagination Engine. Use no início de qualquer análise.
- `analyze_dependencies(path=".")` — grafo de imports/dependências via Nexus Engine.
- `check_file_changes(path=".")` — detecta arquivos alterados via Sentinel.
- `sanitize_code(code, fix=True)` — linta e formata código via Forge.

**FERRAMENTAS DE ARQUIVOS E CÓDIGO:**
- `list_directory(path)`, `tree_view(path)`, `read_file(path)`, `write_file(path, content)`
- `find_in_files(pattern, path)`, `glob_search(pattern)`, `codebase_search(query)`
- `analyze_code(path)`, `validate_syntax(path)`, `summarize_code(path)`
- `run_shell_command(command)` — executa comandos shell

**MEMÓRIA PERSISTENTE (NOTEBOOK):**
- `notebook_write(content, summary)` — salva decisões e planos importantes
- `notebook_read(page_path)`, `notebook_list()`, `notebook_search(query)`

**PROCESSO DE TRABALHO (CHAIN OF THOUGHT):**
1. **ANÁLISE**: Use `scan_project(".")` para visão rápida do projeto.
2. **EXPLORAÇÃO**: Use `list_directory` e `read_file` para entender o código relevante.
3. **PLANEJAMENTO**: Formule um plano claro antes de agir.
4. **EXECUÇÃO**: Execute ferramentas passo-a-passo, verificando cada resultado.
5. **VERIFICAÇÃO**: Confirme que o objetivo foi atingido. Valide sintaxe ou rode testes quando aplicável.

**REGRAS DE OURO:**
- **NÃO ALUCINE**: Só cite arquivos que você confirmou que existem.
- **USE FERRAMENTAS**: Não peça para o usuário fazer coisas que você pode fazer com suas ferramentas.
- **CONTEXT FIRST**: Sempre entenda o contexto antes de agir.
- **SEJA PROFISSIONAL**: Tom técnico, objetivo e colaborativo.

**FINALIZAÇÃO:**
Quando concluir a tarefa com sucesso, termine sua mensagem com "TERMINATE".
"""
        delegation_payload = getattr(self.worker, "delegation_payload", None) or {}
        if not delegation_payload:
            return base_message

        recent_excerpt = delegation_payload.get("recent_chat_excerpt", "")
        supporting_context = delegation_payload.get("supporting_context", "")
        lines = [
            base_message.rstrip(),
            "",
            "**CHAT DELEGATION PAYLOAD:**",
            f"- source: {delegation_payload.get('source', 'unknown')}",
            f"- primary_request: {delegation_payload.get('primary_request', '')}",
            f"- project_root: {delegation_payload.get('project_root', '')}",
            f"- current_chat_model: {delegation_payload.get('current_chat_model', '')}",
            f"- constitution_active: {delegation_payload.get('constitution_active', False)}",
        ]
        if delegation_payload.get("delegation_mode"):
            lines.append(
                f"- delegation_mode: {delegation_payload.get('delegation_mode')}"
            )
        if supporting_context:
            lines.extend(
                [
                    "- supporting_context:",
                    str(supporting_context)[:1200],
                ]
            )
        if recent_excerpt:
            lines.extend(
                [
                    "- recent_chat_excerpt:",
                    str(recent_excerpt)[:1200],
                ]
            )
        lines.extend(
            [
                "- Treat the payload as structured context from the general chat.",
                "- Prefer the primary_request as the canonical objective.",
            ]
        )
        return "\n".join(lines)
