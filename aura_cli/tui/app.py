"""Aura TUI Application.

Main Textual application providing IDE-grade terminal interface with:
- Multi-pane CSS Grid layout (sidebar, chat, analysis/events)
- Event-driven architecture with AgiEvents integration
- Plugin system for extensibility
- Command palette and keybind management
- Tool integration (AuraPaint, Monitor, File Manager)
- Theme support with Nebula Void styling
- Real-time task tree visualization
- Focus mode for task-specific chat filtering
"""

import contextlib
import logging
import os
import shutil
import threading
from typing import Any, ClassVar, Literal, Optional
import uuid

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Vertical
from textual.css.query import NoMatches
from textual.events import Resize
from textual.widgets import DirectoryTree, Static, TabbedContent, TabPane, Tree

from aura_cli.application.agents.events import AgiEvent
from aura_cli.application.artifacts import ArtifactLayout
from aura_cli.application.presentation.activity_feed import ActivityFeed
from aura_cli.application.presentation.attention_delivery import (
    AttentionDeliveryState,
    AttentionPreferences,
)
from aura_cli.application.presentation.attention_inbox import AttentionInbox
from aura_cli.application.presentation.codebase_analysis import (
    build_codebase_analysis_view,
    codebase_investigation_objective,
)
from aura_cli.application.presentation.command_routing import (
    PresentationCommandRouter as AuraTUIController,
)
from aura_cli.application.presentation.external_tools import (
    ExternalToolPhase,
    ExternalToolSession,
    begin_external_tool,
    transition_external_tool,
)
from aura_cli.application.presentation.input_routing import (
    PresentationInputRoute,
    route_presentation_input,
)
from aura_cli.application.presentation.tui_layout import (
    DrawerMode,
    TuiDrawer,
    TuiLayoutState,
    decide_tui_layout,
)
from aura_cli.application.presentation.tui_runtime_state import (
    RuntimeAction,
    RuntimePhase,
    TuiRuntimeState,
    transition_runtime_state,
)
from aura_cli.application.presentation.tui_surface_state import (
    ActivitySection,
    TuiSurfaceState,
    clear_focus,
    dismiss_navigation_layer,
    select_activity,
    set_spatial_focus,
    set_task_filter,
    toggle_drawer,
)
from aura_cli.application.presentation.tui_surfaces import SurfaceRequest
from aura_cli.application.workspace.consolidation import (
    ConsolidationStatus,
    consolidate_notebook_rules,
)
from aura_cli.tui.commands.dispatch import resolve_command_action
from aura_cli.tui.commands.local_commands import handle_local_command
from aura_cli.tui.commands.palette_catalog import register_default_palette_commands
from aura_cli.tui.controllers import ConversationController
from aura_cli.tui.core.error_handler import (
    TUIErrorHandler,
    get_error_handler,
    set_error_handler,
)
from aura_cli.tui.core.event_bus import TUIEvents
from aura_cli.tui.core.sync_store import get_store
from aura_cli.tui.event_subscriptions import bind_tui_events, release_subscriptions
from aura_cli.tui.keybinds import KeybindManager, load_keybinds
from aura_cli.tui.mount_runtime import mount_runtime, stop_autosave_timer
from aura_cli.tui.plugin_manager import PluginManager
from aura_cli.tui.shell.screen_registry import ScreenId, open_screen
from aura_cli.tui.surface_materializer import materialize_surface
from aura_cli.tui.theme_loader import apply_nebula_theme
from aura_cli.tui.utils.clipboard_utils import ClipboardManager
from aura_cli.tui.utils.terminal_detector import get_optimal_theme
from aura_cli.tui.widgets.chat import AuraChatLog
from aura_cli.tui.widgets.code_analysis_panel import CodeAnalysisPanel
from aura_cli.tui.widgets.command_palette import CommandPalette, get_command_registry
from aura_cli.tui.widgets.event_stream_panel import EventStreamPanel
from aura_cli.tui.widgets.footer import AuraFooter
from aura_cli.tui.widgets.ide_panel import RefactoringAction
from aura_cli.tui.widgets.input import AuraInputBar
from aura_cli.tui.widgets.loading import AuraLoadingIndicator
from aura_cli.tui.widgets.memory_browser import MemoryBrowser
from aura_cli.tui.widgets.status import AuraStatusSidebar
from aura_cli.tui.widgets.todo_panel import AuraTodoPanel
from aura_cli.tui.widgets.workflow_monitor import WorkflowMonitor

logger = logging.getLogger(__name__)


class AuraTUI(App):
    """Main TUI Application for Aura CLI.

    Provides comprehensive terminal interface with multi-pane layout,
    event-driven architecture, plugin system, and integrated tools.
    """

    CSS_PATH = None

    # Theme to CSS file mapping
    THEME_CSS_FILES: ClassVar[dict] = {
        "nebula-dark": "theme.tcss",
        "nebula-light": "theme.tcss",  # Uses same file with light mode
        "midnight": "theme.tcss",
        "solar-light": "theme.tcss",
        "dracula": "theme.tcss",
        "macos-light": "macos_light.tcss",  # Dedicated macOS theme file
    }

    @classmethod
    def _get_css_path(cls, theme_name: Optional[str] = None) -> str:
        """Get CSS path for the specified theme using importlib.resources.

        Args:
            theme_name: Optional theme name. If None, uses default or detected theme.

        Returns:
            Path to the appropriate CSS file.

        Raises:
            FileNotFoundError: If the CSS file cannot be found.
        """
        from importlib import resources

        # Determine which CSS file to use based on theme
        if theme_name and theme_name in cls.THEME_CSS_FILES:
            css_filename = cls.THEME_CSS_FILES[theme_name]
        else:
            try:
                from aura_cli.tui.styles.themes import get_theme_manager

                manager = get_theme_manager()
                current_theme_name = manager.current_theme.name.lower().replace(
                    " ", "-"
                )
                css_filename = cls.THEME_CSS_FILES.get(current_theme_name, "theme.tcss")
            except Exception:
                css_filename = "theme.tcss"

        try:
            package = resources.files("aura_cli.tui.styles")
            css_file = package / css_filename
            if css_file.is_file():
                return str(css_file)
            else:
                raise FileNotFoundError(
                    f"CSS file '{css_filename}' not found in package."
                )
        except (ModuleNotFoundError, FileNotFoundError) as e:
            logger.error(
                f"Could not locate CSS file '{css_filename}' via importlib.resources: {e}"
            )
            # As a last resort for local development, create a relative path
            fallback_path = os.path.join(
                os.path.dirname(__file__), "styles", css_filename
            )
            if os.path.exists(fallback_path):
                return fallback_path
            raise FileNotFoundError(
                f"Could not find CSS file '{css_filename}' using any method."
            ) from e

    @classmethod
    def _get_css_paths(cls, theme_name: Optional[str] = None) -> list[str]:
        """Load theme appearance first and shared structural rules last."""
        theme_path = cls._get_css_path(theme_name)
        from importlib import resources

        layout_file = resources.files("aura_cli.tui.styles") / "layout.tcss"
        if not layout_file.is_file():
            raise FileNotFoundError("Shared TUI layout stylesheet not found")
        return [theme_path, str(layout_file)]

    def get_css_variables(self) -> dict[str, str]:
        """Inject the active Aura theme colors as ``$theme-*`` CSS variables.

        The TCSS stylesheets reference custom variables (``$theme-background``,
        ``$theme-primary``, ``$spacing-1`` ...). Textual only knows its own native
        variables, so we bridge here: on every CSS (re)evaluation we add the current
        Aura theme's colors. Combined with ``refresh_css()`` on theme switch, this makes
        all registered themes change appearance live without per-theme TCSS files.
        """
        variables = super().get_css_variables()
        try:
            from aura_cli.tui.styles.themes import get_theme_manager

            theme = get_theme_manager(self).current_theme
            for field_name in theme.colors.__dataclass_fields__:
                value = getattr(theme.colors, field_name)
                variables[f"theme-{field_name.replace('_', '-')}"] = value
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Could not inject theme CSS variables: %s", exc)
        return variables

    BINDINGS: ClassVar[list] = [
        Binding("ctrl+c", "quit", "Sair"),
        Binding("ctrl+l", "clear_chat", "Limpar Chat"),
        Binding("f", "toggle_focus_mode", "Modo Foco", show=True),
        Binding("ctrl+s", "show_code_analysis", "Análise de Código", show=True),
        Binding("ctrl+e", "toggle_analysis_event_panel", "Análise/Eventos", show=True),
        Binding("ctrl+b", "toggle_workspace_panel", "Workspace", show=True),
        Binding("ctrl+p", "toggle_command_palette", "Paleta de Comandos", show=True),
        Binding("ctrl+g", "push_paint_screen", "Paint", show=True),
        Binding("ctrl+f", "push_file_manager_screen", "Arquivos", show=True),
        Binding("ctrl+m", "push_monitor_screen", "Monitor", show=True),
        Binding("ctrl+shift+t", "show_token_usage", "Tokens", show=True),
        Binding("ctrl+space", "leader_key", "Tecla Líder", show=False),
    ]

    REFACTORINGS: ClassVar[list] = [
        RefactoringAction(
            "rename",
            "Renomear símbolo",
            "Renomear um símbolo em todo o codebase",
            "rename",
            parameters={"new_name": "string"},
        ),
        RefactoringAction(
            "extract_method",
            "Extrair método",
            "Extrair seleção em um novo método",
            "extract",
            requires_selection=True,
        ),
        RefactoringAction(
            "extract_variable",
            "Extrair variável",
            "Extrair expressão em uma variável",
            "extract",
            requires_selection=True,
        ),
        RefactoringAction(
            "inline_variable",
            "Inline variável",
            "Substituir variável pelo valor",
            "inline",
        ),
        RefactoringAction(
            "move_function",
            "Mover função",
            "Mover função para outro módulo",
            "move",
            parameters={"target": "string"},
        ),
        RefactoringAction(
            "convert_to_async",
            "Converter para async",
            "Converter função para async",
            "convert",
        ),
        RefactoringAction(
            "add_type_hints",
            "Adicionar type hints",
            "Adicionar type hints à função",
            "enhance",
        ),
        RefactoringAction(
            "optimize_imports",
            "Otimizar imports",
            "Remover não usados e ordenar imports",
            "optimize",
        ),
    ]

    def __init__(self, app_loop=None, **kwargs):
        """Initialize TUI application with core systems.

        Args:
            app_loop: Optional AppLoop instance for command processing
            **kwargs: Additional arguments passed to Textual App
        """
        if self.CSS_PATH is None:
            self.CSS_PATH = self._get_css_paths()
        super().__init__(**kwargs)
        self.controller = AuraTUIController()
        self.app_loop = app_loop
        self.task_states = {}
        self.shutdown_event = threading.Event()
        self.conversation = ConversationController(self)
        self.surface_state = TuiSurfaceState()
        self.runtime_state = TuiRuntimeState(phase=RuntimePhase.BOOTING)
        self.attention_inbox = AttentionInbox()
        self.attention_delivery_state = AttentionDeliveryState()
        self.attention_preferences = AttentionPreferences()
        self.activity_feed = ActivityFeed()
        self.external_tool_session: ExternalToolSession | None = None
        self._active_tui_worker: Any | None = None
        self._last_saved_message_count = 0
        self._last_autosave_at: float | None = None
        self._autosave_timer: Any | None = None
        self.plugin_manager = PluginManager(
            app=self,
            plugin_dirs=[os.path.join(os.path.dirname(__file__), "plugins")],
        )

        self.store = get_store()
        self.error_handler = TUIErrorHandler(self)
        set_error_handler(self.error_handler)
        self.keybind_config = load_keybinds()
        self.keybind_manager: KeybindManager = None
        self.dialog_provider = None
        self.windows = None  # WindowStack — set in on_mount

        self._event_unsubscribers = self._setup_event_subscriptions()

    def _setup_event_subscriptions(self) -> list[Any]:
        """Subscribe to TUI event bus channels."""
        return bind_tui_events(TUIEvents.bus, self)

    def _teardown_event_subscriptions(self) -> None:
        """Release only subscriptions owned by this application instance."""
        release_subscriptions(self._event_unsubscribers)

    def _on_toast_event(self, payload):
        """Handle toast notification events."""
        if not isinstance(payload, dict):
            logger.warning("Invalid TUI toast payload: %r", payload)
            return
        self.notify(
            payload.get("message", ""),
            title=payload.get("title"),
            severity=payload.get("severity", "information"),
            timeout=payload.get("timeout", 5),
        )

    def _on_command_event(self, payload):
        """Handle command execution events."""
        if not isinstance(payload, dict):
            logger.warning("Invalid TUI command payload: %r", payload)
            return
        command = payload.get("command", "")
        self._execute_command(command, payload.get("args", {}))

    def _on_navigate_event(self, payload):
        """Handle navigation events."""
        if not isinstance(payload, dict):
            logger.warning("Invalid TUI navigation payload: %r", payload)
            return
        route_type = payload.get("route_type", "home")
        params = payload.get("params", {})
        from aura_cli.tui.shell.screen_registry import navigate_route

        try:
            navigate_route(self, route_type, **params)
        except (TypeError, ValueError) as error:
            logger.warning("Invalid TUI navigation route %r: %s", route_type, error)

    def _execute_command(self, command: str, args: Optional[dict] = None):
        """Execute command by name with error handling.

        Args:
            command: Command name to execute
            args: Optional command arguments
        """
        action = resolve_command_action(self, command)
        if action:
            try:
                action()
            except KeyboardInterrupt:
                # User cancellation - don't log as error
                raise
            except SystemExit:
                # System exit — don't log as error
                raise
            except Exception as e:
                # Use centralized error handler for better error reporting
                error_handler = get_error_handler()
                if error_handler is not None:
                    error_handler.handle_error(
                        e,
                        context=f"command:{command}",
                        log=True,
                        notify=True,
                        notify_callback=lambda msg, severity="error": self.notify(
                            msg, severity=severity
                        ),
                    )
                else:
                    logger.error("TUI command failed (%s): %s", command, e)
        else:
            logger.warning(f"Comando desconhecido: {command}")

    def compose(self) -> ComposeResult:
        """Compose TUI layout with 3-column grid and tabbed content."""
        with Grid(id="main_grid"):
            with Container(id="left_panel", classes="panel-container"):
                yield Static("Contexto", classes="panel-title")
                yield AuraStatusSidebar(id="status_sidebar")
                yield DirectoryTree(".", id="directory_tree", classes="directory-tree")

            with Container(id="center_panel", classes="panel-container"):
                yield Static("Conversa", classes="panel-title")
                with Vertical(id="main_content"):
                    yield AuraTodoPanel(id="todo_panel")
                    yield AuraChatLog(id="chat_log")
                    yield AuraInputBar()

            with Container(id="right_panel", classes="panel-container"):
                yield Static("Atividade", classes="panel-title")
                with TabbedContent(id="right_tabs"):
                    with TabPane("Eventos", id="events_tab"):
                        yield EventStreamPanel(id="event_stream_panel")
                    with TabPane("Análise", id="analysis_tab"):
                        yield Container(id="analysis_panel_slot")
                    with TabPane("Memória", id="memory_tab"):
                        yield Container(id="memory_panel_slot")
                    with TabPane("Workflows", id="workflows_tab"):
                        yield WorkflowMonitor(id="workflow_monitor")

        yield AuraLoadingIndicator(id="loading_indicator")
        yield AuraFooter(id="footer")
        yield CommandPalette(id="command_palette", registry=get_command_registry())

    def _register_palette_commands(self) -> None:
        """Register all default commands for the command palette."""
        register_default_palette_commands(get_command_registry())

    def on_mount(self) -> None:
        """Initialize systems, apply theme, and display welcome message."""
        detected_theme = get_optimal_theme()
        apply_nebula_theme(self)
        self._apply_layout_plan()
        logger.debug(f"Applied theme: {detected_theme}")

        self._register_palette_commands()

        mount_runtime(self)
        self._transition_runtime(RuntimeAction.READY)

        self.call_after_refresh(self.plugin_manager.notify_app_ready)
        self.call_after_refresh(self._print_welcome)

    def _on_autosave_interval(self) -> None:
        from aura_cli.tui.services.tui_session_service import maybe_autosave

        maybe_autosave(self)

    def _print_welcome(self):
        """Display welcome message in chat."""
        try:
            chat = self.query_one(AuraChatLog)
            if not chat.is_attached:
                return
            chat.write_assistant_message(
                content=(
                    "# Bem-vindo ao Aura CLI (Modo TUI)\n\n"
                    "Sistema pronto para comandos.\n\n"
                    "Comece digitando uma pergunta, use `/help` para orientação "
                    "ou `Ctrl+P` para abrir a paleta de comandos."
                ),
                sender="Aura",
            )
        except Exception as error:
            logger.debug("TUI welcome message not rendered: %s", error)

    def on_input_submitted(self, event) -> None:
        """Handle user input submission and process command.

        Args:
            event: Input submission event containing user input
        """
        user_input = event.value.strip()
        if not user_input:
            return

        event.input.value = ""

        if user_input.startswith("/"):
            handled = self._handle_tui_command(user_input)
            if handled:
                return

        self.post_message_to_chat("User", user_input)

        route = route_presentation_input(
            user_input,
            router=self.controller,
            runtime_available=self.app_loop is not None,
        )
        if route is PresentationInputRoute.CODEBASE_INVESTIGATION:
            self._run_codebase_investigation(user_input)
        elif route is PresentationInputRoute.AGI_WORKER:
            self._activate_agi_worker_automatically(user_input)
        elif route is PresentationInputRoute.DIRECT:
            self._transition_runtime(RuntimeAction.LOADING, "Processando comando...")
            self._active_tui_worker = self.run_worker(
                self._process_command_worker(user_input), exclusive=True
            )
        else:
            self.post_message_to_chat("Sistema", "Erro: AppLoop não conectado.")

    def _handle_tui_command(self, command: str) -> bool:
        """Handle TUI-specific commands that should be processed locally.

        Returns True if command was handled locally, False to pass to app_loop.
        """
        return handle_local_command(self, command)

    def _open_constitution_screen(self) -> None:
        """Open the ConstitutionBuilder TUI screen."""

        def _on_result(constitution: str | None) -> None:
            """Handle result from ConstitutionScreen and persist to disk."""
            if constitution:
                path = ArtifactLayout().project("constitution.md")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(constitution, encoding="utf-8")
                self.post_message_to_chat(
                    "Sistema",
                    f"✔ Constituição criada e salva em `{path}`.",
                )
            else:
                self.post_message_to_chat(
                    "Sistema", "Criação da constituição cancelada."
                )

        open_screen(self, ScreenId.CONSTITUTION, _on_result)

    def _open_settings_screen(self) -> None:
        """Open native settings (API keys + LLM configuration)."""

        open_screen(self, ScreenId.SETTINGS)

    def _activate_agi_worker_automatically(self, command: str) -> None:
        """Activate AgiWorker automatically for complex tasks.

        Args:
            command: User command to process with AgiWorker
        """
        if not self.app_loop:
            self.post_message_to_chat("Sistema", "Erro: AppLoop não conectado.")
            return

        # Check if AgiWorker is already running
        if self.app_loop.agi_thread and self.app_loop.agi_thread.is_alive():
            self.post_message_to_chat(
                "Sistema",
                "Aura AGI já está ativa. Aguarde a conclusão da tarefa atual ou use /agi explicitamente para nova tarefa.",
            )
            return

        chat = self.query_one(AuraChatLog)
        chat.show_thinking("Aura")

        self.post_message_to_chat(
            "Sistema",
            "◈ Detectando tarefa complexa. Ativando Aura AGI automaticamente...",
        )

        agi_command = f"/agi {command}"

        self._transition_runtime(RuntimeAction.THINKING, "Pensando...")
        self._active_tui_worker = self.run_worker(
            self._process_command_worker(agi_command), exclusive=True
        )

    def _run_codebase_investigation(self, command: str) -> None:
        """Run codebase investigation automatically.

        Args:
            command: User command to process
        """
        if not self.app_loop:
            self.post_message_to_chat("Sistema", "Erro: AppLoop não conectado.")
            return

        chat = self.query_one(AuraChatLog)
        chat.show_thinking("Aura")

        self.post_message_to_chat(
            "Sistema",
            "⚲ Detectando análise de código. Iniciando investigação do codebase...",
        )

        objective = codebase_investigation_objective(command)

        self._transition_runtime(RuntimeAction.LOADING, "Analisando codebase...")
        self._active_tui_worker = self.run_worker(
            self._investigate_codebase_worker(objective), exclusive=True
        )

    async def _investigate_codebase_worker(self, objective: str) -> None:
        """Worker to run codebase investigation in background.

        Args:
            objective: Objective for the investigation
        """
        try:
            from pathlib import Path

            from aura_cli.core.tools.codebase_analysis import investigate_codebase

            # Get project root
            project_root = Path.cwd()
            if self.app_loop and hasattr(self.app_loop, "project_root"):
                project_root = self.app_loop.project_root or project_root

            self.post_message_to_chat(
                "Sistema", f"▥ Iniciando análise do codebase em: {project_root}"
            )

            results = investigate_codebase(
                root_path=str(project_root),
                objective=objective,
                max_files=100,
                verbose=True,
                respect_gitignore=True,
                use_imagination=True,
            )

            chat = self.query_one(AuraChatLog)
            chat.hide_thinking()

            self._display_codebase_investigation_results(results)
            self._transition_runtime(RuntimeAction.COMPLETED, "Análise concluída")
        except KeyboardInterrupt:
            self._transition_runtime(RuntimeAction.CANCELLED, "Análise cancelada")
        except Exception as error:
            self._transition_runtime(RuntimeAction.ERROR, f"Erro: {error}")
            logger.exception("Codebase investigation failed")
        finally:
            if self.runtime_state.loading_visible:
                self._transition_runtime(RuntimeAction.READY)
            else:
                self._sync_runtime_ui()

    def _display_codebase_investigation_results(self, results: dict) -> None:
        """Display codebase investigation results in TUI.

        Args:
            results: Results dictionary from investigate_codebase
        """
        try:
            view = build_codebase_analysis_view(results)
            self.post_message_to_chat("Aura", view.chat_markdown)
            self._ensure_activity_panel(ActivitySection.ANALYSIS)
            self._activate_activity_tab(ActivitySection.ANALYSIS, "analysis_tab")

            code_analysis_panel = self.query_one(
                "#code_analysis_panel", CodeAnalysisPanel
            )

            code_analysis_panel.update_analysis_results(view.as_panel_payload())

        except Exception as e:
            error_handler = get_error_handler() or self.error_handler
            error_handler.handle_error(
                e,
                context="tui:display_codebase_investigation_results",
                log=True,
                notify=True,
                notify_callback=lambda msg, severity="error": self.post_message_to_chat(
                    "Erro", msg
                ),
            )

    def _handle_consolidate_command(self) -> None:
        """Handle /consolidate command in TUI.

        Consolidates learned rules from scratchpad into constitution.
        """
        if not self.app_loop:
            self.post_message_to_chat("Sistema", "Erro: AppLoop não conectado.")
            return

        try:
            from pathlib import Path

            from aura_cli.core.memory.memory_service import get_memory_service

            # Get project root
            project_root = Path.cwd()
            if hasattr(self.app_loop, "project_root") and self.app_loop.project_root:
                project_root = self.app_loop.project_root

            # Use memory service (singleton pattern avoids SIGSEGV)
            memory_service = get_memory_service(project_root)
            notebook_manager = memory_service.notebook_manager

            outcome = consolidate_notebook_rules(notebook_manager)
            if outcome.status is ConsolidationStatus.NO_CONSTITUTION:
                self.post_message_to_chat(
                    "Sistema",
                    "✖ Nenhuma Constituição encontrada. Use /agi para criar uma.",
                )
                return
            if outcome.status is ConsolidationStatus.NO_PENDING_PAGES:
                self.post_message_to_chat(
                    "Sistema", "ℹ️ Nenhuma consolidação pendente no Rascunho."
                )
                return
            if outcome.status is ConsolidationStatus.NO_RULES:
                self.post_message_to_chat(
                    "Sistema", "⚠️ Nenhuma regra encontrada nas consolidações."
                )
                return
            if outcome.status is ConsolidationStatus.CONSOLIDATED:
                updated_constitution = outcome.updated_constitution or ""
                if hasattr(self.app_loop, "constitution"):
                    self.app_loop.constitution = updated_constitution
                    if hasattr(self.app_loop, "constitution_validator"):
                        from aura_cli.core.memory.constitution_validator import (
                            ConstitutionValidator,
                        )

                        self.app_loop.constitution_validator = ConstitutionValidator(
                            updated_constitution
                        )

                self.post_message_to_chat(
                    "Sistema",
                    f"✔ Constituição atualizada com {outcome.rule_count} regra(s) consolidadas!",
                )
            else:
                self.post_message_to_chat(
                    "Error", "✖ Error saving updated constitution."
                )

        except Exception as e:
            error_handler = get_error_handler() or self.error_handler
            error_handler.handle_error(
                e,
                context="tui:consolidate_rules",
                log=True,
                notify=True,
                notify_callback=lambda msg, severity="error": self.post_message_to_chat(
                    "Erro", f"✖ {msg}"
                ),
            )

    async def _process_command_worker(self, command: str):
        """Process command in background worker without blocking UI.

        Args:
            command: User command to process
        """
        if self.shutdown_event.is_set():
            return
        try:
            should_continue = await self.app_loop.process_command_single_shot_async(
                command
            )
            if not should_continue:
                self._transition_runtime(RuntimeAction.STOPPED, "Encerrando")
                self.exit()
            elif self.runtime_state.loading_visible:
                self._transition_runtime(RuntimeAction.COMPLETED, "Concluído")
        except KeyboardInterrupt:
            # User cancellation - don't log as error
            self._transition_runtime(RuntimeAction.CANCELLED, "Operação cancelada")
            return
        except Exception as error:
            self._transition_runtime(RuntimeAction.ERROR, f"Erro: {error}")
            error_handler = get_error_handler() or self.error_handler
            error_handler.handle_error(
                error,
                context="tui:process_command",
                log=True,
                notify=True,
                notify_callback=lambda msg, severity="error": self.notify(
                    f"Error: {msg}", severity=severity
                ),
            )
        finally:
            if self.runtime_state.loading_visible:
                self._transition_runtime(RuntimeAction.READY)
            else:
                self._sync_runtime_ui()

    def post_message_to_chat(
        self, sender: str, content: str, task_id: str = "global_chat"
    ):
        """Post message to chat log with appropriate styling.

        Args:
            sender: Message sender name
            content: Message content
            task_id: Associated task ID for filtering
        """
        if not isinstance(content, str):
            try:
                content = str(content)
            except Exception:
                content = repr(content)

        self.conversation.append(sender, content, task_id)
        if sender in ("Aura", "Tool"):
            from aura_cli.tui.services.tui_session_service import maybe_autosave

            maybe_autosave(self)

    def _sync_runtime_footer(self) -> None:
        """Render the semantic runtime state in the mounted footer."""
        with contextlib.suppress(Exception):
            self.query_one("#footer", AuraFooter).set_runtime_state(self.runtime_state)

    def _sync_runtime_ui(self) -> None:
        """Synchronize footer and loading from one semantic state."""
        self._sync_runtime_footer()
        with contextlib.suppress(Exception):
            loading = self.query_one("#loading_indicator", AuraLoadingIndicator)
            if self.runtime_state.loading_visible:
                loading.show(self.runtime_state.footer_message)
            else:
                loading.hide()

    def _transition_runtime(
        self,
        action: RuntimeAction,
        message: str = "",
        task_id: str | None = None,
    ) -> None:
        """Apply a local lifecycle action and refresh the TUI chrome."""
        self.runtime_state = transition_runtime_state(
            self.runtime_state,
            action,
            message=message,
            task_id=task_id,
        )
        self._sync_runtime_ui()

    def present_surface(self, request: SurfaceRequest) -> None:
        """Materialize one semantic output decision in observable steps."""
        materialize_surface(self, request)

    def _render_filtered_chat_messages(self):
        """Filter and display chat messages based on focused task."""
        self.conversation.render(self.surface_state.task_filter)

    @property
    def all_chat_messages(self) -> list[dict[str, Any]]:
        """Compatibility view for session and local-command adapters."""
        return self.conversation.messages

    @all_chat_messages.setter
    def all_chat_messages(self, messages: list[dict[str, Any]]) -> None:
        self.conversation.messages = messages

    def update_task_tree(self, event: AgiEvent):
        """Update task tree in sidebar based on AgiEvents.

        Args:
            event: AgiEvent containing task state changes
        """
        from aura_cli.application.presentation import reduce_task_tree

        self.task_states = reduce_task_tree(self.task_states, event)

        with contextlib.suppress(Exception):
            sidebar = self.query_one(AuraStatusSidebar)
            sidebar.update_task_tree(self.task_states)
        with contextlib.suppress(Exception):
            self.query_one(WorkflowMonitor).consume_agi_event(event)
        self._render_filtered_chat_messages()

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        """Handle task tree node selection and display details.

        Args:
            event: Tree node selection event
        """
        node_data = event.node.data

        if not node_data:
            self.surface_state = clear_focus(self.surface_state)
            self._render_filtered_chat_messages()
            self._apply_layout_plan()
            self._restore_composer_focus()
            return

        task_id = node_data.get("task_id")

        from aura_cli.application.presentation import find_task_entry

        event_entry = find_task_entry(self.task_states, task_id)

        if event_entry and "event" in event_entry:
            event_data = event_entry["event"]
            self._activate_activity_tab(ActivitySection.EVENTS, "events_tab")
            event_stream_panel = self.query_one("#event_stream_panel", EventStreamPanel)
            event_stream_panel.write_event_details(event_data)
            self.notify(
                f"Selected: {event_data.type.value} {event_data.task_id}",
                title="Tarefa Selecionada",
            )
        else:
            self.notify(
                "Details not found for selected item.", severity="warning"
            )

    def action_toggle_focus_mode(self):
        """Toggle focus mode for currently selected task."""
        sidebar = self.query_one(AuraStatusSidebar)
        tree = sidebar.query_one("#task_tree", Tree)
        selected_node = getattr(tree, "cursor_node", None)

        if selected_node and selected_node.data and selected_node.data.get("task_id"):
            current_task_id = selected_node.data["task_id"]
            if self.surface_state.task_filter == current_task_id:
                self.surface_state = set_task_filter(self.surface_state, None)
                self.surface_state = set_spatial_focus(self.surface_state, False)
                self.notify("Modo foco desativado.", title="Foco")
            else:
                self.surface_state = set_task_filter(
                    self.surface_state, current_task_id
                )
                self.surface_state = set_spatial_focus(self.surface_state, True)
                self.notify(f"Focando na tarefa: {current_task_id}", title="Foco")
        else:
            if self.surface_state.spatial_focus or self.surface_state.task_filter:
                self.surface_state = clear_focus(self.surface_state)
                message = "Foco limpo."
            else:
                self.surface_state = set_spatial_focus(self.surface_state, True)
                message = "Foco geral ativado."
            self.notify(message, title="Foco")

        self._render_filtered_chat_messages()
        self._apply_layout_plan()

    def action_show_code_analysis(self):
        """Show code analysis panel with guidance to index the project."""
        self._ensure_activity_panel(ActivitySection.ANALYSIS)
        self._activate_activity_tab(ActivitySection.ANALYSIS, "analysis_tab")
        self.notify(
            "Use /init to index the project for real code analysis.",
            title="Análise de Código",
            timeout=5,
        )

    def action_toggle_analysis_event_panel(self):
        """Open or close the contextual activity drawer."""
        self._toggle_drawer(TuiDrawer.ACTIVITY)

    def action_toggle_workspace_panel(self) -> None:
        """Open or close project context and file navigation."""
        self._toggle_drawer(TuiDrawer.WORKSPACE)

    def _focus_drawer_target(self, drawer: TuiDrawer) -> None:
        """Focus the primary interactive control of an opened drawer."""
        selector = "#directory_tree" if drawer is TuiDrawer.WORKSPACE else "#right_tabs"
        try:
            target = self.query_one(selector)
            if not target.can_focus and drawer is TuiDrawer.ACTIVITY:
                target = next(
                    (child for child in target.children if child.can_focus), target
                )
            if target.display and target.can_focus:
                target.focus()
                return
        except NoMatches:
            logger.debug("Drawer focus target not found: %s", selector)
        self._restore_composer_focus()

    def _toggle_drawer(self, drawer: TuiDrawer) -> None:
        self.surface_state = toggle_drawer(self.surface_state, drawer)
        self._apply_layout_plan()
        active_drawer = self.surface_state.active_drawer
        if active_drawer is None:
            self.call_after_refresh(self._restore_composer_focus)
        else:
            self.call_after_refresh(self._focus_drawer_target, active_drawer)

    def on_resize(self, event: Resize) -> None:
        """Recompute density and drawer behavior for the current viewport."""
        self._apply_layout_plan(event.size.width, event.size.height)

    def _apply_layout_plan(
        self, width: int | None = None, height: int | None = None
    ) -> None:
        """Materialize the neutral layout decision in Textual widgets."""
        viewport = self.size
        plan = decide_tui_layout(
            TuiLayoutState(
                width=width or viewport.width,
                height=height or viewport.height,
                requested_drawer=self.surface_state.active_drawer,
                focus_mode=self.surface_state.spatial_focus,
            )
        )
        grid = self.query_one("#main_grid", Grid)
        left = self.query_one("#left_panel", Container)
        right = self.query_one("#right_panel", Container)
        task_panel = self.query_one("#todo_panel", AuraTodoPanel)
        footer = self.query_one("#footer", AuraFooter)
        titles = self.query(".panel-title")

        grid.remove_class("drawer-open", "drawer-overlay", "drawer-workspace")
        grid.remove_class("density-compact", "density-comfortable", "density-spacious")
        grid.add_class(f"density-{plan.density.value}")
        left.remove_class("drawer-visible")
        right.remove_class("drawer-visible")
        if plan.drawer is not None:
            panel = left if plan.drawer is TuiDrawer.WORKSPACE else right
            panel.add_class("drawer-visible")
            grid.add_class("drawer-open")
            if plan.drawer is TuiDrawer.WORKSPACE:
                grid.add_class("drawer-workspace")
            if plan.drawer_mode is DrawerMode.OVERLAY:
                grid.add_class("drawer-overlay")
            elif plan.drawer is TuiDrawer.WORKSPACE:
                grid.styles.grid_columns = f"{plan.drawer_width} 1fr"
            else:
                grid.styles.grid_columns = f"1fr {plan.drawer_width}"
        else:
            grid.styles.grid_columns = "1fr"

        task_panel.display = plan.show_task_panel and bool(task_panel.tasks)
        footer.set_class(not plan.show_footer_details, "compact")
        for title in titles:
            title.display = plan.show_header

    def action_clear_chat(self):
        """Clear chat history and display welcome message."""
        self.all_chat_messages.clear()
        self.post_message(AuraChatLog.ClearHistory())
        self._print_welcome()

    def action_toggle_command_palette(self):
        """Toggle command palette visibility."""
        palette = self.query_one("#command_palette", CommandPalette)
        palette.toggle()

    def action_leader_key(self):
        """Activate leader key mode for keybind sequences."""
        if self.keybind_manager:
            self.keybind_manager.leader.enter_leader_mode()

    def action_show_events(self):
        """Show agent event stream panel."""
        self._activate_activity_tab(ActivitySection.EVENTS, "events_tab")
        self.notify("Painel de eventos ativado", title="Eventos")

    def action_show_memory(self):
        """Show memory/notebook browser panel."""
        self._ensure_activity_panel(ActivitySection.MEMORY)
        self._activate_activity_tab(ActivitySection.MEMORY, "memory_tab")
        self.notify("Browser de memória ativado", title="Memória")

    def _activate_activity_tab(self, section: ActivitySection, tab_id: str) -> None:
        """Keep activity state, drawer layout, and visible tab synchronized."""
        self.surface_state = select_activity(self.surface_state, section)
        self._apply_layout_plan()
        self.query_one("#right_tabs", TabbedContent).active = tab_id

    def _ensure_activity_panel(self, section: ActivitySection) -> None:
        """Mount expensive activity content only when first requested."""
        factories = {
            ActivitySection.ANALYSIS: (
                "#analysis_panel_slot",
                "#code_analysis_panel",
                lambda: CodeAnalysisPanel(id="code_analysis_panel"),
            ),
            ActivitySection.MEMORY: (
                "#memory_panel_slot",
                "#memory_browser",
                lambda: MemoryBrowser(id="memory_browser"),
            ),
        }
        spec = factories.get(section)
        if spec is None:
            return
        slot_selector, panel_selector, factory = spec
        if self.query(panel_selector):
            return
        self.query_one(slot_selector, Container).mount(factory())

    def action_push_paint_screen(self) -> None:
        """Push the native AuraPaint screen onto the stack."""

        open_screen(self, ScreenId.PAINT)

    def action_push_file_manager_screen(self) -> None:
        """Push File Manager screen onto stack."""

        open_screen(self, ScreenId.FILES)

    def action_push_monitor_screen(self) -> None:
        """Push Monitor Tool screen onto stack."""

        open_screen(self, ScreenId.MONITOR)

    def action_push_history_screen(self) -> None:
        """Push session history browser onto stack."""

        open_screen(self, ScreenId.HISTORY)

    def _action_show_help(self) -> None:
        self._handle_tui_command("/help")

    def action_save_session(self) -> None:
        from aura_cli.tui.services.tui_session_service import save_tui_session

        session = save_tui_session(self)
        if session:
            self.notify(
                f"Sessão salva: {session.name} ({session.id})",
                title="Sessão",
            )

    def action_new_session(self) -> None:
        from aura_cli.tui.services.tui_session_service import start_new_tui_session

        session = start_new_tui_session(self)
        self.notify(f"Nova sessão: {session.name}", title="Sessão")

    def action_show_token_usage(self) -> None:
        from aura_cli.core.stats import get_stats
        from aura_cli.tui.services.token_usage_snapshot import (
            build_token_usage_snapshot,
        )

        stats = get_stats()
        app_loop = self.app_loop
        if app_loop and getattr(app_loop, "stats", None):
            stats = app_loop.stats
        snapshot = build_token_usage_snapshot(
            stats,
            app_loop=app_loop,
            message_count=len(self.all_chat_messages),
        )
        open_screen(self, ScreenId.TOKEN_USAGE, snapshot=snapshot)

    def action_show_workflows(self) -> None:
        """Switch to the workflows tab with safe fallback to events."""
        try:
            self._activate_activity_tab(ActivitySection.WORKFLOWS, "workflows_tab")
            self.notify("Painel de workflows ativo", title="Workflows")
        except Exception as error:
            logger.warning("Workflow tab switch failed: %s", error)
            # Fallback to events if workflows tab is missing or broken
            with contextlib.suppress(Exception):
                self.action_show_events()

    def _action_clipboard_stub(self) -> None:
        """Handle copy/paste actions by delegating to ClipboardManager.

        Copy: reads selected text from the focused widget and copies to system clipboard.
        Paste: reads system clipboard and inserts into the composer input.
        """
        # Determine intent from the action name stored on the dispatch table.
        # This single method handles copy, copy_selection, paste, and paste_smart.
        focused = self.focused
        clipboard = ClipboardManager()

        # --- COPY path ---
        # Try to get selected text from the focused widget.
        selected_text: Optional[str] = None
        if focused is not None:
            # Textual's Input / TextArea both expose .selected_text
            selected_text = getattr(focused, "selected_text", None)
            # RichLog / Static may expose .renderable as plain string fallback
            if not selected_text:
                value = getattr(focused, "value", None)
                if isinstance(value, str) and value:
                    selected_text = value

        if selected_text:
            ok = clipboard.copy(selected_text)
            if ok:
                preview = selected_text[:60].replace("\n", "↵")
                suffix = "..." if len(selected_text) > 60 else ""
                self.notify(
                    f"Copiado: '{preview}{suffix}'",
                    title="Área de transferência",
                )
            else:
                self.notify(
                    "Failed to copy — system clipboard unavailable.",
                    title="Área de transferência",
                    severity="error",
                )
            return

        # --- PASTE path ---
        # No selected text → treat as paste into the composer.
        content = clipboard.paste_smart()
        if content is None:
            self.notify(
                "Clipboard vazio ou inacessível.",
                title="Área de transferência",
                severity="warning",
            )
            return

        # Try to insert into the composer input widget (RichPromptInput / Input).
        try:
            from aura_cli.tui.widgets.rich_input import RichPromptInput

            composer: Optional[RichPromptInput] = self.query_one(RichPromptInput)
        except (NoMatches, Exception):
            composer = None

        if composer is not None:
            # Reuse the existing smart_paste action on the composer widget
            self.call_after_refresh(composer.action_smart_paste)
            return

        # Last resort: try inserting into any focused Input
        if focused is not None:
            insert = getattr(focused, "insert_text_at_cursor", None)
            if callable(insert):
                insert(content.content)
                return

        self.notify(
            "Nenhum campo de entrada ativo para colar o conteúdo.",
            title="Área de transferência",
            severity="warning",
        )

    def _action_cancel(self) -> None:
        """Dismiss the nearest UI layer before cancelling active work."""
        if getattr(self, "windows", None) and self.windows.has_overlay:
            self.windows.close_overlays()
            self._restore_composer_focus()
            return
        screen_stack = getattr(self, "screen_stack", [])
        if len(screen_stack) > 1:
            self.pop_screen()
            self._restore_composer_focus()
            return

        navigation_state = dismiss_navigation_layer(self.surface_state)
        if navigation_state != self.surface_state:
            self.surface_state = navigation_state
            self._render_filtered_chat_messages()
            self._apply_layout_plan()
            self._restore_composer_focus()
            return

        runtime_state = getattr(self, "runtime_state", None)
        if getattr(runtime_state, "phase", None) is RuntimePhase.CANCELLED:
            return

        worker = getattr(self, "_active_tui_worker", None)
        is_finished = bool(getattr(worker, "is_finished", False))
        is_cancelled = bool(getattr(worker, "is_cancelled", False))
        cancel = getattr(worker, "cancel", None)
        if (
            worker is not None
            and not is_finished
            and not is_cancelled
            and callable(cancel)
        ):
            cancel()
            self._transition_runtime(RuntimeAction.CANCELLED, "Operação cancelada")
            self._restore_composer_focus()
            self.notify("Operação cancelada.", title="Execução", severity="warning")

    def action_toggle_theme_mode(self) -> None:
        from aura_cli.tui.styles.themes import get_theme_manager, toggle_theme

        get_theme_manager(self)
        theme = toggle_theme()
        self.notify(f"Tema: {theme.name}", title="Aparência")

    def action_cycle_theme(self) -> None:
        from aura_cli.tui.styles.themes import THEMES, get_theme_manager

        manager = get_theme_manager(self)
        names = sorted(THEMES.keys())
        if not names:
            return
        current = manager.current_theme.name.lower().replace(" ", "-")
        try:
            idx = names.index(current)
        except ValueError:
            idx = -1
        next_name = names[(idx + 1) % len(names)]
        manager.set_theme(next_name)
        self.notify(f"Tema: {next_name}", title="Aparência")

    def action_push_tools_menu_screen(self) -> None:
        """Push optional tool launcher menu onto stack."""

        open_screen(self, ScreenId.TOOLS_MENU)

    def action_launch_paint(self) -> None:
        """Launch the bundled AuraPaint editor in its own terminal process."""
        from aura_cli.tui.tools import launch_paint

        self._begin_external_session("AuraPaint")
        try:
            self._advance_external_session(ExternalToolPhase.LAUNCHING)
            with self.suspend():
                self._advance_external_session(ExternalToolPhase.ATTACHED)
                exit_code = launch_paint()
            self._advance_external_session(ExternalToolPhase.RETURNING, cwd=os.getcwd())
            self._finish_external_session(exit_code)
        except KeyboardInterrupt:
            self._interrupt_external_session()
        except FileNotFoundError as e:
            self._fail_external_session(str(e))
            self.notify(f"AuraPaint não encontrado: {e}", severity="error")
        except Exception as e:
            self._fail_external_session(str(e))
            error_handler = get_error_handler() or self.error_handler
            error_handler.handle_error(
                e,
                context="tui:launch_aurapaint",
                log=True,
                notify=True,
                notify_callback=lambda msg, severity="error": self.notify(
                    f"Erro ao abrir AuraPaint: {msg}", severity=severity
                ),
            )

    def action_launch_files(self) -> None:
        """Launch the optional file manager through the external return protocol."""
        from aura_cli.tui.tools import launch_files

        self._begin_external_session("Files")
        try:
            self._advance_external_session(ExternalToolPhase.LAUNCHING)
            with self.suspend():
                self._advance_external_session(ExternalToolPhase.ATTACHED)
                exit_code = launch_files(os.getcwd())
            self._advance_external_session(ExternalToolPhase.RETURNING, cwd=os.getcwd())
            self._finish_external_session(exit_code)
        except KeyboardInterrupt:
            self._interrupt_external_session()
        except Exception as error:
            self._fail_external_session(str(error))

    def action_launch_monitor(self) -> None:
        """Launch Monitor Tool (Chawan) as external subprocess."""
        from aura_cli.tui.tools import get_monitor_binary

        monitor_binary = get_monitor_binary()
        if monitor_binary:
            self._launch_external_tui(monitor_binary, "Monitor")
        else:
            self._launch_external_tui("cha", "Monitor")

    def on_key(self, event) -> None:
        """Handle key events for leader key sequences.

        Args:
            event: Key event to process
        """
        if self.keybind_manager and self.keybind_manager.leader.state.active:
            handled = self.keybind_manager.leader.handle_key(event.key)
            if handled:
                event.prevent_default()
                event.stop()

    def _launch_external_tui(
        self, command: str, tool_name: str = "External Tool"
    ) -> None:
        """Suspend TUI, run external command, then resume.

        Args:
            command: Shell command to execute
            tool_name: Display name for notifications

        Raises:
            SecurityError: If command fails security validation
        """
        from aura_cli.core.logger import get_logger
        from aura_cli.core.tools.shell import _is_safe_command

        logger = get_logger(__name__)

        if not _is_safe_command(command):
            reason = "Command contains dangerous patterns or blocked commands"
            logger.warning(f"Unsafe command blocked in TUI: {command[:50]}...")
            self.notify(
                f"Command blocked for security: {reason}",
                title="Segurança",
                severity="error",
            )
            return

        cmd_name = command.split()[0] if command.split() else command
        if not shutil.which(cmd_name):
            self.notify(
                f"Command '{cmd_name}' not found. Please install {tool_name}.",
                severity="error",
            )
            return

        self._begin_external_session(tool_name)
        try:
            self._advance_external_session(ExternalToolPhase.LAUNCHING)
            with self.suspend():
                self._advance_external_session(ExternalToolPhase.ATTACHED)
                from aura_cli.core.utils.safe_subprocess import SafeSubprocess

                executor = SafeSubprocess(timeout_seconds=300)
                result = executor.run_shell(command)
                exit_code = result.exit_code

            self._advance_external_session(ExternalToolPhase.RETURNING, cwd=os.getcwd())
            self._finish_external_session(exit_code)
        except KeyboardInterrupt:
            self._interrupt_external_session()
        except FileNotFoundError:
            self._fail_external_session(f"Command not found: {cmd_name}")
            logger.error(f"Command not found: {command}", exc_info=True)
            self.notify(f"Command not found: {cmd_name}", severity="error")
        except PermissionError:
            self._fail_external_session(f"Permission denied for {tool_name}")
            logger.error(f"Permission denied for command: {command}", exc_info=True)
            self.notify(f"Permission denied for {tool_name}", severity="error")
        except OSError as e:
            self._fail_external_session(str(e))
            logger.error(f"OS error launching {tool_name}: {e}", exc_info=True)
            self.notify(f"System error launching {tool_name}: {e}", severity="error")

    def _sync_external_tool_footer(self) -> None:
        """Project the external tool session into the persistent footer."""
        try:
            self.query_one("#footer", AuraFooter).set_external_tool_session(
                self.external_tool_session
            )
        except NoMatches:
            return

    def _begin_external_session(self, tool_name: str) -> None:
        self.external_tool_session = begin_external_tool(
            f"external-{uuid.uuid4().hex[:8]}", tool_name, os.getcwd()
        )
        self._sync_external_tool_footer()
        self.notify(f"Preparando {tool_name}…", title="Ferramenta externa")

    def _advance_external_session(
        self, phase: ExternalToolPhase, **changes: Any
    ) -> None:
        if self.external_tool_session is not None:
            self.external_tool_session = transition_external_tool(
                self.external_tool_session, phase, **changes
            )
            self._sync_external_tool_footer()

    def _finish_external_session(self, exit_code: int) -> None:
        session = self.external_tool_session
        if session is None:
            return
        focus_returned = self._restore_composer_focus()
        phase = (
            ExternalToolPhase.COMPLETED if exit_code == 0 else ExternalToolPhase.FAILED
        )
        self._advance_external_session(
            phase,
            exit_code=exit_code,
            error=None if exit_code == 0 else f"exit code {exit_code}",
            focus_returned=focus_returned,
        )
        severity: Literal["information", "warning"] = (
            "information" if exit_code == 0 else "warning"
        )
        self.notify(
            f"{session.tool_name} devolveu o controle · exit {exit_code}",
            title="Ferramenta externa",
            severity=severity,
        )

    def _fail_external_session(self, error: str) -> None:
        if self.external_tool_session is not None:
            with contextlib.suppress(ValueError):
                self._advance_external_session(
                    ExternalToolPhase.FAILED,
                    error=error,
                    focus_returned=self._restore_composer_focus(),
                )

    def _interrupt_external_session(self) -> None:
        if self.external_tool_session is not None:
            with contextlib.suppress(ValueError):
                self._advance_external_session(
                    ExternalToolPhase.INTERRUPTED,
                    cwd=os.getcwd(),
                    focus_returned=self._restore_composer_focus(),
                )
            self.notify(
                f"{self.external_tool_session.tool_name} interrompido pelo usuário.",
                title="Ferramenta externa",
                severity="warning",
            )

    def _restore_composer_focus(self) -> bool:
        try:
            composer = self.query_one(AuraInputBar)
            composer.query_one("#main_input").focus()
            return True
        except NoMatches:
            return False

    async def action_quit(self) -> None:
        """Clean shutdown with event bus cleanup."""
        from aura_cli.tui.services.tui_session_service import maybe_autosave

        transition_runtime = getattr(self, "_transition_runtime", None)
        if callable(transition_runtime) and hasattr(self, "runtime_state"):
            transition_runtime(RuntimeAction.STOPPED, "Interrompido")
        maybe_autosave(self, force=True)
        stop_autosave_timer(self)
        self.shutdown_event.set()
        keybind_manager = getattr(self, "keybind_manager", None)
        if keybind_manager is not None:
            with contextlib.suppress(Exception):
                keybind_manager.stop()
        self._teardown_event_subscriptions()
        with contextlib.suppress(Exception):
            self.plugin_manager.unload_plugins()
        if self.app_loop and getattr(self.app_loop, "ui", None):
            stop = getattr(self.app_loop.ui, "stop", None)
            if callable(stop):
                stop()
        await super().action_quit()
