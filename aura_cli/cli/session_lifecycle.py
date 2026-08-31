"""Concrete lifecycle adapter for an interactive ``AppLoop`` session.

Owns startup, shutdown, queue draining, timeouts, persistence notifications and
conversation compression at the CLI boundary.
"""

from pathlib import Path
import threading
import time
from typing import Any

from aura_cli.application.sessions import (
    build_snapshot_history,
    plan_snapshot,
    truncate_history,
)
from aura_cli.cli.helpers import handle_status_updates
from aura_cli.cli.ui.display_facade import register_ui, unregister_ui
from aura_cli.cli.utils.exceptions import RateLimitError
from aura_cli.cli.utils.thread_manager import get_thread_manager
from aura_cli.core.config import config_manager
from aura_cli.core.constants import COMPRESSION_THRESHOLD
from aura_cli.core.context.base import (
    compress_conversation_history,
    compression_threshold_for_model,
)
from aura_cli.core.logger import get_logger
from aura_cli.core.memory.notebook_service import notebook_service
from aura_cli.core.todo.todo_notifications import check_and_notify_task_completion
from aura_cli.core.todo.todo_tracker import refresh_todo_tracker
from aura_cli.core.utils.background_process import get_background_process_supervisor

logger = get_logger(__name__)


class SessionLifecycleMixin:
    """Mixin providing session lifecycle methods for AppLoop."""

    shutdown_event: threading.Event | None
    logger: Any
    _thread_lock: Any
    agi_thread: Any
    ops_thread: Any
    conversation_history: list[dict[str, Any]]
    _base_system_messages: list[dict[str, Any]]
    stats: Any

    def set_shutdown_event(self, event: threading.Event) -> None:
        """Set event that signals when TUI should shut down.

        Args:
            event: Threading event to signal shutdown
        """
        self.shutdown_event = event

    def shutdown(self, timeout: float = 10.0) -> bool:
        """Gracefully shutdown all threads and resources.

        Uses ThreadManager.stop_all() to ensure all registered threads
        are stopped gracefully. This includes workers, background threads,
        and any other threads registered with the ThreadManager.

        Args:
            timeout: Maximum time to wait for shutdown (in seconds)

        Returns:
            True if shutdown successful, False otherwise
        """
        self.logger.info("Iniciando graceful shutdown...")

        # Signal shutdown and capture thread references atomically to avoid
        # race conditions where threads could be replaced between checks.
        with self._thread_lock:
            if self.shutdown_event:
                self.shutdown_event.set()
                self.logger.debug("Shutdown event definido")
            agi_thread = (
                self.agi_thread
                if (self.agi_thread and self.agi_thread.is_alive())
                else None
            )
            ops_thread = (
                self.ops_thread
                if (self.ops_thread and self.ops_thread.is_alive())
                else None
            )

        # Stop all registered threads via ThreadManager first
        thread_manager = get_thread_manager()
        results = thread_manager.stop_all(timeout=timeout)
        all_success = True
        for thread_name, success in results.items():
            if success:
                self.logger.info(f"Thread '{thread_name}' parou com sucesso")
            else:
                self.logger.warning(
                    f"Thread '{thread_name}' não parou dentro do timeout"
                )
                all_success = False

        # Join AGI/Ops threads that may not be registered with ThreadManager
        remaining_timeout = max(timeout / 4, 1.0)
        if agi_thread:
            self.logger.info(
                f"Parando thread AGI: {getattr(agi_thread, 'name', 'agi_worker')}"
            )
            agi_thread.join(timeout=remaining_timeout)
            if agi_thread.is_alive():
                self.logger.warning("Thread AGI não parou dentro do timeout")
                all_success = False

        if ops_thread:
            self.logger.info(
                f"Parando thread Ops: {getattr(ops_thread, 'name', 'ops_worker')}"
            )
            ops_thread.join(timeout=remaining_timeout)
            if ops_thread.is_alive():
                self.logger.warning("Thread Ops não parou dentro do timeout")
                all_success = False

        try:
            background_records = get_background_process_supervisor().cancel_all()
            for record in background_records:
                self.logger.info(
                    f"Background PID {record.pid} encerrado: {record.status}"
                )
                if record.status in {"running", "cancelling"}:
                    all_success = False
        except Exception:
            self.logger.exception("Failed to shut down background processes")
            all_success = False

        if all_success:
            self.logger.info("Graceful shutdown bem-sucedido")
        else:
            self.logger.warning(
                "Graceful shutdown completed with warnings (some threads did not stop)"
            )

        runtime_services = getattr(self, "_runtime_services", None)
        if runtime_services is not None:
            try:
                runtime_services.shutdown()
            except Exception:
                self.logger.exception("Failed to shut down the service container")
                all_success = False

        return all_success

    def _truncate_conversation_history(self):
        """Truncate conversation history to prevent memory leaks."""
        with self._thread_lock:
            truncated = truncate_history(
                self.conversation_history, self._max_conversation_history
            )
            if len(truncated) != len(self.conversation_history):
                self.conversation_history[:] = truncated
                self.logger.debug(
                    f"Conversation history truncated to {len(truncated)} messages"
                )

    def _save_context_to_notebook(self) -> None:
        """Save current conversation context to notebook and reset history.

        Creates a snapshot of the conversation history in the notebook memory
        system with cognitive refinement, then clears the history and adds a
        reference to the saved page. This prevents token overflow while maintaining
        accessible context.

        The snapshot uses cognitive refinement to extract essential information
        and create intelligent summaries when the context is large.
        """

        snapshot_plan = plan_snapshot(self.conversation_history)

        self.logger.debug(
            f"Saving context snapshot (estimated {snapshot_plan.estimated_tokens} tokens, "
            f"threshold: 16000, refinement: {snapshot_plan.use_cognitive_refinement})"
        )

        try:
            snapshot_history = list(self.conversation_history)
            turn = getattr(self, "_active_turn_execution", None)
            if turn is not None and turn.operations:
                facts = [
                    f"{item.label}: {item.status.value}; alvo={item.target or '—'}; "
                    f"resultado={item.result_summary or '—'}"
                    for item in turn.operations
                ]
                snapshot_history.append(
                    {
                        "role": "system",
                        "content": "Fatos do ledger:\n" + "\n".join(facts),
                    }
                )
            if not any(
                str(item.get("content", "")).strip() for item in snapshot_history
            ):
                return
            page_path = notebook_service.create_snapshot(
                snapshot_history,
                use_cognitive_refinement=snapshot_plan.use_cognitive_refinement,
                refinement_threshold_tokens=COMPRESSION_THRESHOLD * 20,
            )
            page = Path(page_path)
            if not page.is_file() or not page.read_text(encoding="utf-8").strip():
                raise OSError(f"Invalid snapshot: {page_path}")
            self.logger.debug(f"Context snapshot saved to: {page_path}")
            self.conversation_history = build_snapshot_history(
                self._base_system_messages,
                page_path=str(page_path),
                saved_message_count=len(self.conversation_history),
                refined=snapshot_plan.use_cognitive_refinement,
            )
            self.stats.increment_notebook_snapshots()

        except (OSError, PermissionError) as e:
            self.logger.warning(f"Error saving to notebook (IO): {e}")
            self.conversation_history = compress_conversation_history(
                self.conversation_history,
                max_tokens=compression_threshold_for_model(
                    getattr(self, "final_model", "")
                ),
            )
        except Exception as e:
            self.logger.warning(f"Error saving to notebook: {e}", exc_info=True)
            self.conversation_history = compress_conversation_history(
                self.conversation_history,
                max_tokens=compression_threshold_for_model(
                    getattr(self, "final_model", "")
                ),
            )

    def run(self):
        """Start and execute main interaction loop.

        Each iteration: (1) drain and show status updates from background workers
        (AGI/Ops), (2) prompt the user. The chat stays free — the user can type
        new commands or press Enter to refresh and see more worker updates.
        """
        _ITERATION_TIMEOUT = float(config_manager.get("loop_iteration_timeout", 300))
        register_ui(self.ui)
        try:
            while True:
                _iter_start = time.monotonic()
                try:
                    if self.shutdown_event and self.shutdown_event.is_set():
                        break

                    handle_status_updates(self.ui.status_queue, ui=self.ui)
                    refresh_todo_tracker()
                    self._todo_done_count = check_and_notify_task_completion(
                        self.ui.status_queue, self._todo_done_count
                    )

                    tangent_indicator = self.tangent_manager.get_indicator()
                    self.ui.display_status_bar()
                    command = self.ui.prompt(tangent_indicator=tangent_indicator)

                    if not command or not command.strip():
                        continue

                    command = command.strip()

                    if self._handle_auto_run_command(command):
                        continue

                    if self._handle_exit_command(command):
                        break

                    if self._handle_tui_command(command):
                        continue

                    command, should_continue = self._handle_multiline_command(command)
                    if not should_continue:
                        continue

                    should_continue = self.process_command_single_shot(command)
                    if not should_continue:
                        break

                    _elapsed = time.monotonic() - _iter_start
                    if _elapsed > _ITERATION_TIMEOUT:
                        self.logger.warning(
                            f"Loop iteration exceeded timeout ({_elapsed:.1f}s > {_ITERATION_TIMEOUT}s)"
                        )
                        self.ui.display_warning(
                            f"Operação demorou {_elapsed:.0f}s — verifique se há travamento."
                        )

                except (KeyboardInterrupt, EOFError):
                    self.ui.display_warning("Operação cancelada pelo usuário.")
                    break
                except RateLimitError as e:
                    error_msg = self._handle_rate_limit_error(
                        e, getattr(e, "retry_after", None)
                    )
                    self.ui.display_error(error_msg)
                    self.logger.debug(
                        f"Rate limit exceeded: {getattr(e, 'model', None)} (retry_after: {getattr(e, 'retry_after', None)})"
                    )
                    continue
                except Exception as e:
                    self._handle_generic_exception(e)

            self.ui.display_success("Sessão encerrada.")
        finally:
            try:
                self.shutdown()
            except Exception:
                self.logger.exception("Failed to release session resources")
            finally:
                unregister_ui()
