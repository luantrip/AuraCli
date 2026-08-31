"""Provider and tool-schema adapter for conversational CLI turns.

Prompt sanitation, tool filtering and context estimates are Application policies;
this mixin binds them to configured providers and the active ``AppLoop`` session.
"""

from collections.abc import Callable, Sequence
from datetime import datetime, timezone
import time
from typing import Any, ClassVar, Dict, List
from uuid import uuid4

from aura_cli.application.conversation import (
    BudgetDecision,
    TokenBudget,
    estimate_context_tokens,
    filter_tool_schemas,
    prepare_prompt,
    sanitize_prompt_text,
)
from aura_cli.application.conversation.claims import validate_completion_claims
from aura_cli.application.execution import TurnExecution, TurnPhase
from aura_cli.cli.function_call_handler import process_function_calls_loop
from aura_cli.cli.ui.constants import UIIcons
from aura_cli.core.config import config_manager
from aura_cli.core.constants import (
    FALLBACK_CHARS_PER_TOKEN,
    MAX_FUNCTION_CALLS,
)
from aura_cli.core.llm.tool_schemas import create_tool_schemas
from aura_cli.core.service_registry import get_tools_dict


class LLMQueryMixin:
    """Bind conversational LLM queries to an ``AppLoop`` session."""

    conversation_history: list[dict[str, Any]]
    stats: Any
    logger: Any
    constitution: Any
    ui: Any
    available_tools: Any
    shutdown_event: Any
    context_manager: Any
    final_model: str
    console: Any
    _turn_repository: Any
    project_root: Any
    presenter: Any
    _save_context_to_notebook: Callable[..., Any]
    _do_delegate_to_agi: Callable[..., Any]
    _do_delegate_to_ops: Callable[..., Any]
    _do_delegate_to_subagent: Callable[..., Any]
    get_delegated_task_status: Callable[..., Any]
    list_delegated_tasks: Callable[..., Any]
    get_latest_delegated_task: Callable[..., Any]
    summarize_delegated_tasks: Callable[..., Any]
    summarize_delegated_task: Callable[..., Any]
    get_delegated_task_artifacts: Callable[..., Any]
    read_delegated_task_snapshot: Callable[..., Any]
    reattach_delegated_task_context: Callable[..., Any]
    _truncate_conversation_history: Callable[..., Any]
    _handle_llm_errors: Callable[..., Any]

    _ESSENTIAL_TOOLS: ClassVar[frozenset] = frozenset(
        {
            "run_shell_command",
            "list_directory",
            "read_file",
            "write_file",
            "tree_view",
            "find_in_files",
            "glob_search",
            "advanced_grep_search",
            "view_repo_map",
            "view_subdirectory",
            "codebase_search",
            "scan_project",
            "analyze_code",
            "analyze_project_structure",
            "analyze_project_quality",
            "analyze_project_security",
            "analyze_dependencies",
            "dep_find_dependencies",
            "dep_get_impact_analysis",
            "summarize_code",
            "validate_syntax",
            "classify_code",
            "find_duplicate_code",
            "check_file_changes",
            "investigate_codebase",
            "inspect_code_structure",
            "edit_file",
            "sanitize_code",
            "format_file",
            "git_status",
            "git_commit",
            "git_diff",
            "git_log",
            "git_branch",
            "suggest_commit_message",
            "generate_tests_ml",
            "run_tests_advanced",
            "notebook_write",
            "notebook_read",
            "notebook_search",
            "docker_ps",
            "docker_logs",
            "system_resources",
            "web_search",
            "delegate_to_agi",
            "delegate_to_ops",
            "delegate_to_subagent",
            "plan_refactoring",
        }
    )

    _PURE_QUESTION_PATTERNS: ClassVar[tuple] = (
        "o que é ",
        "what is ",
        "o que são ",
        "what are ",
        "como funciona ",
        "how does ",
        "explique ",
        "explain ",
        "qual a diferença",
        "what's the difference",
        "me fale sobre",
        "tell me about",
    )

    def _estimate_context_tokens(self, extra_text: str | None = None) -> int:
        """Estimate current context size in tokens (approximate)."""
        return estimate_context_tokens(
            self.conversation_history,
            extra_text,
            chars_per_token=FALLBACK_CHARS_PER_TOKEN,
        )

    def _maybe_compact_context(self, upcoming_user_message: str | None = None) -> None:
        """Proactively compact context before LLM calls to avoid token overflow."""
        try:
            estimated_tokens = self._estimate_context_tokens(upcoming_user_message)
            self.stats.context_tokens = estimated_tokens
            message_count = len(self.conversation_history)
            context_hard = int(config_manager.get("context_max_tokens") or 32_000)
            context_soft = max(int(context_hard * 0.8), 1)
            session_soft = int(config_manager.get("token_budget_warning") or 100_000)
            session_hard = int(config_manager.get("token_budget_hard") or 250_000)
            session_tokens = getattr(self.stats, "session_tokens", 0)
            if not isinstance(session_tokens, int):
                session_tokens = int(getattr(self.stats, "tokens_used", 0) or 0)
            decision = TokenBudget(
                context_soft_limit=context_soft,
                context_hard_limit=context_hard,
                session_soft_limit=session_soft,
                session_hard_limit=session_hard,
            ).decide(context_tokens=estimated_tokens, session_tokens=session_tokens)
            if decision is BudgetDecision.STOP:
                raise RuntimeError(
                    f"Limite rígido atingido: contexto={estimated_tokens:,}, "
                    f"sessão={session_tokens:,} tokens"
                )
            threshold_messages = 100
            if (
                decision is BudgetDecision.CONTINUE
                and message_count < threshold_messages
            ):
                return
            if message_count < 20:
                self.logger.debug(
                    f"Skipping compaction: only {message_count} messages "
                    f"(estimated {estimated_tokens} tokens)"
                )
                return

            self.logger.info(
                f"Context compaction triggered: {estimated_tokens} tokens, "
                f"{message_count} messages (soft limit: {context_soft} tokens, "
                f"{threshold_messages} messages)"
            )
            self._save_context_to_notebook()
        except RuntimeError:
            raise
        except Exception as e:
            self.logger.warning(
                f"Failed to compact context proactively: {e}", exc_info=True
            )

    def _sanitize_for_prompt(self, text: str) -> str:
        """Sanitize text to prevent prompt injection via XML tag manipulation."""
        return sanitize_prompt_text(text)

    def _prepare_llm_command(self, command: str) -> tuple:
        """Apply constitution and pending context to command.

        Returns `(original_command, llm_command, used_pending_context)`.
        """
        pending_context = getattr(self.stats, "_pending_context", "") or ""

        def reduce_prompt(text: str) -> str:
            from aura_cli.core.autocomplete.preprocessing import ContextPreprocessor

            return ContextPreprocessor().reduce_context_pollution(text, max_tokens=2000)

        try:
            prepared = prepare_prompt(
                command,
                constitution=self.constitution or "",
                pending_context=pending_context,
                reducer=reduce_prompt,
            )
        except Exception as exc:
            self.logger.debug(f"ContextPreprocessor indisponível: {exc}")
            prepared = prepare_prompt(
                command,
                constitution=self.constitution or "",
                pending_context=pending_context,
            )

        if prepared.used_constitution:
            self.ui.display_info(
                f"{UIIcons.INFO} Prompt sanitizado com a Constituição do Projeto."
            )
        if prepared.used_pending_context:
            num_files = self.stats._pending_context_files
            self.ui.display_info(f"Injetando contexto de {num_files} arquivo(s)...")
        return prepared.original, prepared.rendered, prepared.used_pending_context

    def _filter_tool_schemas(self, tool_schemas: list, llm_command: str) -> list:
        """Filter tool schemas by task type classification and pure-question detection.

        Uses the TaskRouter to classify the user query and sends only relevant
        tool schemas to the LLM, reducing token usage from ~7500 to ~1500-2500.
        """

        def task_filter(
            schemas: Sequence[dict[str, Any]], prompt: str
        ) -> Sequence[dict[str, Any]]:
            from aura_cli.core.llm.task_router import get_task_router
            from aura_cli.core.llm.tool_schemas import filter_tool_schemas_for_task

            task_type = get_task_router().detect_task_type(prompt).value
            return filter_tool_schemas_for_task(list(schemas), task_type)

        try:
            return filter_tool_schemas(
                tool_schemas,
                llm_command,
                essential_tools=self._ESSENTIAL_TOOLS,
                task_filter=task_filter,
            )
        except Exception:
            return filter_tool_schemas(
                tool_schemas,
                llm_command,
                essential_tools=self._ESSENTIAL_TOOLS,
            )

    def _build_augmented_tools_dict(self) -> dict:
        """Build tools dict with delegation methods registered under their canonical names."""
        tools_dict = dict(
            self.available_tools
            if isinstance(self.available_tools, dict)
            else get_tools_dict()
        )
        _delegation_tools = [
            ("delegate_to_agi", self._do_delegate_to_agi),
            ("delegate_to_ops", self._do_delegate_to_ops),
            ("delegate_to_subagent", self._do_delegate_to_subagent),
            ("get_delegated_task_status", self.get_delegated_task_status),
            ("list_delegated_tasks", self.list_delegated_tasks),
            ("get_latest_delegated_task", self.get_latest_delegated_task),
            ("summarize_delegated_tasks", self.summarize_delegated_tasks),
            ("summarize_delegated_task", self.summarize_delegated_task),
            ("get_delegated_task_artifacts", self.get_delegated_task_artifacts),
            ("read_delegated_task_snapshot", self.read_delegated_task_snapshot),
            ("reattach_delegated_task_context", self.reattach_delegated_task_context),
        ]
        for name, method in _delegation_tools:
            method.__func__.__name__ = name  # type: ignore[attr-defined]
            tools_dict[name] = method
        return tools_dict

    def _conversation_with_consciousness_skills(
        self, user_query: str
    ) -> List[Dict[str, Any]]:
        """Return conversation history with relevant consciousness skills injected."""
        try:
            out = list(self.conversation_history)
            from aura_cli.core.personas.integrations import get_consciousness_manager

            manager = get_consciousness_manager()
            section = manager.get_skills_section(
                user_query, max_skills=2, threshold=0.35
            )
            if not section:
                return out
            out.insert(-1, {"role": "system", "content": section})
            return out
        except Exception as e:
            self.logger.debug("Consciousness skills injection skipped: %s", e)
            return list(self.conversation_history)

    async def _process_llm_query(self, command: str):
        """Process query destined for language model."""
        if self.shutdown_event and self.shutdown_event.is_set():
            return

        original_command, llm_command, used_pending_context = self._prepare_llm_command(
            command
        )

        self._maybe_compact_context(upcoming_user_message=llm_command)

        self.conversation_history.append({"role": "user", "content": original_command})
        self._truncate_conversation_history()
        self.context_manager.add_message("user", original_command)

        self.stats.set_status("thinking", "Pensando...")

        raw_model = config_manager.get("default_model") or self.final_model

        from aura_cli.core.llm.model_utils import (
            DEFAULT_MODEL,
            normalize_model_name,
            resolve_model_option,
        )

        raw_model = resolve_model_option(raw_model)

        # Use task router for automatic model selection when on default model
        if raw_model in (DEFAULT_MODEL, "auto"):
            try:
                from aura_cli.core.llm.task_router import get_task_router

                raw_model = get_task_router().select_model(command)
            except Exception as _e:
                self.logger.debug("TaskRouter unavailable, using default model: %s", _e)
                raw_model = DEFAULT_MODEL

        current_model = normalize_model_name(raw_model)
        if current_model != raw_model:
            self.logger.debug(
                f"Modelo normalizado em app_loop: {raw_model} -> {current_model}"
            )

        if not config_manager.get("default_model"):
            try:
                from aura_cli.core.llm.task_router import get_task_router

                router = get_task_router()
                task_type = router.detect_task_type(command)
                self.logger.debug(
                    f"TaskRouter.select_model: task_type={task_type.value} "
                    f"-> model='{current_model}'"
                )
            except Exception as _e:
                self.logger.debug(f"TaskRouter debug info unavailable: {_e}")

        tools_dict = self._build_augmented_tools_dict()
        tool_schemas = self._filter_tool_schemas(
            create_tool_schemas(tools_dict), llm_command
        )

        messages_for_llm = self._conversation_with_consciousness_skills(llm_command)
        for idx in range(len(messages_for_llm) - 1, -1, -1):
            if messages_for_llm[idx].get("role") == "user":
                messages_for_llm[idx] = {
                    **messages_for_llm[idx],
                    "content": llm_command,
                }
                break

        start_time = time.time()
        session_id = getattr(self, "_execution_session_id", None)
        if session_id is None:
            session_id = uuid4().hex
            self._execution_session_id = session_id
        turn_execution = TurnExecution(session_id=session_id)
        self._active_turn_execution = turn_execution
        if hasattr(self.stats, "bind_turn_execution"):
            self.stats.bind_turn_execution(turn_execution)

        try:
            response_content, response = await process_function_calls_loop(
                model=current_model or "",
                conversation_history=messages_for_llm,
                tool_schemas=tool_schemas,
                available_tools=tools_dict,
                stats=self.stats,
                ui=self.ui,
                console=self.console,
                max_calls=MAX_FUNCTION_CALLS,
                shutdown_event=self.shutdown_event,
                suppress_tool_loading=True,
                turn_execution=turn_execution,
                user_request=original_command,
                checkpoint_callback=lambda _turn: self._save_context_to_notebook(),
            )
        except Exception as e:
            self._handle_llm_errors(e, current_model or "")
            self.stats.reset_to_idle()
            return

        turn_execution.phase = TurnPhase.RESPONDING

        if used_pending_context and response is not None:
            self.stats._pending_context = None
            self.stats._pending_context_files = 0

        self._process_llm_response(
            response_content, response, command, current_model, start_time
        )
        turn_execution.phase = TurnPhase.COMPLETED
        turn_execution.finished_at = datetime.now(timezone.utc)
        turn_execution.token_usage = {
            key: value if isinstance(value, int) else 0
            for key, value in {
                "turn_tokens": getattr(self.stats, "turn_tokens", 0),
                "context_tokens": getattr(self.stats, "context_tokens", 0),
                "session_tokens": getattr(self.stats, "session_tokens", 0),
            }.items()
        }
        try:
            self._turn_repository.persist_turn(
                turn_execution,
                self.conversation_history,
                current_directory=str(self.project_root),
            )
        except OSError as error:
            self.logger.error(
                "Failed to persist turn %s: %s", turn_execution.turn_id, error
            )
        try:
            from aura_cli.core.llm.multi_model_advanced import ModelPreferenceLearner
            from aura_cli.core.llm.task_router import get_task_router

            supported = validate_completion_claims(
                original_command, str(response_content or ""), turn_execution
            ).supported
            ModelPreferenceLearner().record_outcome(
                get_task_router().detect_task_type(original_command).value,
                current_model or "",
                supported=supported,
            )
        except Exception as error:
            self.logger.debug("Outcome learning unavailable: %s", error)

    def _process_llm_response(
        self,
        response_content: Any,
        response: Any,
        command: str,
        current_model: Any,
        start_time: float,
    ) -> None:
        """Record token usage, update history, display response, and update status."""
        if (
            response
            and hasattr(response, "usage")
            and response.usage
            and hasattr(response.usage, "total_tokens")
        ):
            self.stats.add_tokens(
                {
                    "total_tokens": response.usage.total_tokens,
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(
                        response.usage, "completion_tokens", 0
                    ),
                },
                model=current_model,
            )
            budget_warning = self.stats.check_budget()
            if budget_warning:
                self.ui.display_warning(budget_warning)

        if response_content == "__SUPPRESSED__":
            pass
        elif response_content:
            self.conversation_history.append(
                {"role": "assistant", "content": response_content}
            )
            self._truncate_conversation_history()
            self.context_manager.add_message("assistant", response_content)
            try:
                from aura_cli.core.llm.multi_model_advanced import (
                    ModelPreferenceLearner,
                )
                from aura_cli.core.llm.task_router import get_task_router

                _task_type = get_task_router().detect_task_type(command).value
                ModelPreferenceLearner().record_decision(
                    task_type=_task_type,
                    models_used=[current_model or ""],
                    selected_model=current_model or "",
                )
            except Exception as _le:
                self.logger.debug(f"ModelPreferenceLearner record ignorado: {_le}")
            self.presenter.display_llm_response(
                response_content,
                start_time,
                response_tokens=getattr(response.usage, "total_tokens", 0)
                if response and hasattr(response, "usage") and response.usage
                else 0,
                model=current_model or "",
            )
        else:
            self.ui.display_error("Não foi possível obter resposta do modelo.")

        self.stats.set_status("idle")
        self.presenter.display_status_footer(
            exec_time=time.time() - start_time, model=current_model or ""
        )
