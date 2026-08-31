"""CLI command controller mixed into ``AppLoop``.

It adapts shell, slash, multiline and interface-switching commands to the active
Rich session while delegating reusable routing decisions to Application.
"""

import asyncio
from collections.abc import Callable
from typing import Any

from aura_cli.cli.command_router import route_command
from aura_cli.cli.helpers import handle_multiline_input
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class CommandHandlerMixin:
    """Bind CLI command handling to an ``AppLoop`` session."""

    stats: Any
    ui: Any
    logger: Any
    shutdown_event: Any
    agi_thread: Any
    ops_thread: Any
    final_model: str
    console: Any
    project_root: Any
    is_constitution_setup_active: bool
    conversation_history: list[dict[str, Any]]
    _get_thread_refs: Callable[..., Any]
    _set_thread_refs: Callable[..., Any]
    _process_llm_query: Callable[..., Any]
    _truncate_conversation_history: Callable[..., Any]

    def _handle_auto_run_command(self, command: str) -> bool:
        """Handle /auto-run command toggle.

        Args:
            command: User command string

        Returns:
            True if command was handled, False otherwise
        """
        if command.lower() not in ["/auto-run", "/autorun"]:
            return False

        self.stats.skip_confirmations = not self.stats.skip_confirmations
        status = "ativado" if self.stats.skip_confirmations else "desativado"
        self.ui.display_info(
            f"Execução sem confirmação {status}. Use Shift+Tab ou /auto-run para alternar."
        )
        return True

    def _handle_exit_command(self, command: str) -> bool:
        """Handle /exit command.

        Args:
            command: User command string

        Returns:
            True if command was exit, False otherwise
        """
        return command.lower() in ["/exit", "exit"]

    def _handle_tui_command(self, command: str) -> bool:
        """Handle /interface or /tui command to launch TUI.

        Args:
            command: User command string

        Returns:
            True if command was handled, False otherwise
        """
        if command.lower() not in ["/interface", "/tui"]:
            return False

        self.ui.display_info("Iniciando Nebula TUI...")
        try:
            from aura_cli.interface_runtime import launch_textual_interface

            launch_textual_interface(self)
            self.ui.display_success("Retorno da interface Nebula.")
            return True

        except ImportError as e:
            self.ui.display_error(f"Failed to load TUI components: {e}")
            return True
        except (AttributeError, RuntimeError) as e:
            self.ui.display_error(f"Erro na TUI: {e}")
            self.logger.error(f"TUI launch error: {e}", exc_info=True)
            return True
        except Exception as e:
            self.ui.display_error(f"Erro inesperado na TUI: {e}")
            self.logger.error(f"Unexpected TUI error: {e}", exc_info=True)
            return True

    def _handle_multiline_command(self, command: str) -> tuple:
        """Handle multiline input command.

        Args:
            command: User command string

        Returns:
            Tuple of (processed_command, should_continue)
        """
        if command != '"""':
            return command, True

        processed = handle_multiline_input(ui=self.ui)
        if processed is None:
            return command, False
        return processed, True

    def process_command_single_shot(self, command: str) -> bool:
        """Process single user command (CLI or TUI).

        Routes command to appropriate handler and updates worker threads
        and model state as needed.

        Args:
            command: User command string

        Returns:
            False if application should terminate, True otherwise
        """
        if self.shutdown_event and self.shutdown_event.is_set():
            return False

        should_continue, result_type, new_agi, new_ops, new_model = route_command(
            command,
            self.agi_thread,
            self.ops_thread,
            self.final_model,
            self.stats,
            self.ui,
            self.console,
            project_root=self.project_root,
            app_loop=self,
        )

        self.agi_thread = new_agi if new_agi is not None else self.agi_thread
        self.ops_thread = new_ops if new_ops is not None else self.ops_thread
        self.final_model = new_model if new_model is not None else self.final_model

        if not should_continue:
            return False

        if result_type == "llm_query":
            if self.is_constitution_setup_active:
                self.conversation_history.append({"role": "user", "content": command})
                self._truncate_conversation_history()
                agi_thread_ref, _ = self._get_thread_refs()
                if agi_thread_ref and agi_thread_ref.is_alive():
                    pass
                else:
                    self.ui.display_warning(
                        "Agente de constituição não está ativo ou não respondeu. Tente /agi novamente para iniciar a configuração da constituição."
                    )
                return True
            else:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop is None:
                    asyncio.run(self._process_llm_query(command))
                else:
                    # Already inside an async context – run in a separate
                    # thread to avoid nested event loop deadlock.
                    self.logger.warning(
                        "process_command_single_shot called from async context; "
                        "dispatching to thread."
                    )
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(1) as pool:
                        pool.submit(
                            asyncio.run, self._process_llm_query(command)
                        ).result()

        return True

    async def process_command_single_shot_async(self, command: str) -> bool:
        """Async version of process_command_single_shot for TUI use.

        Args:
            command: User command string

        Returns:
            False if application should terminate, True otherwise
        """
        if self.shutdown_event and self.shutdown_event.is_set():
            return False

        agi_thread_ref, ops_thread_ref = self._get_thread_refs()

        should_continue, result_type, new_agi, new_ops, new_model = route_command(
            command,
            agi_thread_ref,
            ops_thread_ref,
            self.final_model,
            self.stats,
            self.ui,
            self.console,
            project_root=self.project_root,
            app_loop=self,
        )

        self._set_thread_refs(agi_thread=new_agi, ops_thread=new_ops)
        self.final_model = new_model if new_model is not None else self.final_model

        if not should_continue:
            return False

        if result_type == "llm_query":
            if self.is_constitution_setup_active:
                self.conversation_history.append({"role": "user", "content": command})
                self._truncate_conversation_history()
                agi_thread_ref, _ = self._get_thread_refs()
                if agi_thread_ref and agi_thread_ref.is_alive():
                    pass
                else:
                    self.ui.display_warning(
                        "Agente de constituição não está ativo ou não respondeu. Tente /agi novamente para iniciar a configuração da constituição."
                    )
                return True
            else:
                await self._process_llm_query(command)

        return True
