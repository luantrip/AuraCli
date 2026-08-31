"""Loading states — visual feedback system for all Aura CLI operations.

Canonical loading module (loading.py was removed as a production orphan).
All callers should import from here.

Covers all as operation categories:
    - LLM: query, streaming, model fallback
    - Tool: tool execution and validation
    - File: reading, writing, code analysis
    - Agent: thinking, planning, execution
    - Background: indexation, cache, dependency analysis

Typical usage:
    >>> from aura_cli.cli.ui.loading_states import show_tool_loading, LoadingState
    >>> loading = show_tool_loading(console, "write_file", {"path": "foo.py"})
    >>> loading.update(LoadingState.EXECUTING, "Escrevendo...")
    >>> loading.complete()
"""

import time
from typing import Any, Dict, Optional

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

from aura_cli.application.execution_feedback import (
    LoadingCategory,
    LoadingState,
    configure_loading_feedback,
    resolve_agent_loading,
    resolve_file_loading,
)
from aura_cli.cli.ui.constants import UIIcons
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.theme_manager import get_theme_manager


class AdvancedLoadingManager:
    """Advanced loading state manager.

    Manages loading states for all operations with visual feedback,
    time tracking, and category-based styling.

    Attributes:
        console: Rich Console instance
        current_state: Current loading state
        current_category: Current operation category
        start_time: Operation start time
        live: Rich Live instance for updates
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize the loading state manager in idle state."""
        self.console = console if console is not None else get_console()
        self.current_state = LoadingState.IDLE
        self.current_category: Optional[LoadingCategory] = None
        self.start_time: Optional[float] = None
        self.live: Optional[Live] = None
        self._stopped: bool = False  # guard against double-stop

    def start(
        self, category: LoadingCategory, operation: str, details: Optional[str] = None
    ):
        """Start loading state.

        Args:
            category: Operation category
            operation: Operation description
            details: Optional additional details
        """
        self._stopped = False
        self.current_category = category
        self.current_state = LoadingState.PREPARING
        self.start_time = time.time()

        message = self._create_loading_message(operation, details)
        theme = get_theme_manager()

        spinner = Spinner(
            "dots",
            text=message,
            style=theme.get_color("loading_primary") or theme.get_color("primary"),
        )
        self.live = Live(spinner, console=self.console, refresh_per_second=4)
        self.live.start()

    def update(self, state: LoadingState, details: Optional[str] = None):
        """Atualiza o estado de loading."""
        if self._stopped:
            return
        self.current_state = state

        if self.live:
            elapsed = time.time() - self.start_time if self.start_time else 0
            message = self._create_state_message(state, details, elapsed)
            spinner = Spinner("dots", text=message, style=self._get_state_color(state))
            self.live.update(spinner)

    def complete(self, result: Optional[str] = None):
        """Completa o loading com sucesso."""
        if self._stopped:
            return
        self._stopped = True
        if self.live:
            self.live.stop()
        self.current_state = LoadingState.COMPLETE

    def error(self, error_msg: str):
        """Completa o loading com erro."""
        if self._stopped:
            return
        self._stopped = True
        if self.live:
            self.live.stop()

        theme = get_theme_manager()
        self.console.print(
            f"[{theme.get_color('error')}]{UIIcons.ERROR}[/] Erro: {error_msg}"
        )

        self.current_state = LoadingState.ERROR

    def _create_loading_message(self, operation: str, details: Optional[str]) -> str:
        """Create a loading message string."""
        icon = self._get_category_icon()
        msg = f"{icon} {operation}"
        if details:
            msg += f" - {details}"
        return msg

    def _create_state_message(
        self, state: LoadingState, details: Optional[str], elapsed: float
    ) -> str:
        """Create a state message string."""
        icon = self._get_state_icon(state)

        if details:
            msg = f"{icon} {details}"
        else:
            state_labels = {
                LoadingState.IDLE: "Aguardando",
                LoadingState.PREPARING: "Preparando",
                LoadingState.EXECUTING: "Executando",
                LoadingState.PROCESSING: "Processando",
                LoadingState.ANALYZING: "Analisando",
                LoadingState.THINKING: "Pensando",
                LoadingState.STREAMING: "Recebendo resposta",
                LoadingState.FINALIZING: "Finalizando",
                LoadingState.COMPLETE: "Concluído",
                LoadingState.ERROR: "Erro",
            }
            state_name = state_labels.get(state, state.value)
            msg = f"{icon} {state_name}"

        if elapsed >= 1.0:
            msg += f" ({elapsed:.0f}s)"
        return msg

    def _get_category_icon(self) -> str:
        """Return the icon for a loading category."""
        icons = {
            LoadingCategory.LLM: UIIcons.AURA,
            LoadingCategory.TOOL: UIIcons.TOOL,
            LoadingCategory.FILE: UIIcons.FILE,
            LoadingCategory.AGENT: UIIcons.AGENT,
            LoadingCategory.BACKGROUND: UIIcons.WORKING,
            LoadingCategory.SYSTEM: UIIcons.SYSTEM,
        }
        return (
            icons.get(self.current_category, UIIcons.LOADING)
            if self.current_category
            else UIIcons.LOADING
        )

    def _get_state_icon(self, state: LoadingState) -> str:
        """Return the icon for a loading state."""
        icons = {
            LoadingState.IDLE: UIIcons.IDLE,
            LoadingState.PREPARING: UIIcons.LOADING,
            LoadingState.EXECUTING: UIIcons.RUN,
            LoadingState.PROCESSING: UIIcons.WORKING,
            LoadingState.ANALYZING: UIIcons.SEARCH,
            LoadingState.THINKING: UIIcons.THINKING,
            LoadingState.STREAMING: UIIcons.ARROW_DOWN,
            LoadingState.FINALIZING: UIIcons.AURA,
            LoadingState.COMPLETE: UIIcons.SUCCESS,
            LoadingState.ERROR: UIIcons.ERROR,
        }
        return icons.get(state, "")

    def _get_state_color(self, state: LoadingState) -> str:
        """Return the Rich colour string for a loading state."""
        theme = get_theme_manager()
        colors = {
            LoadingState.PREPARING: theme.get_color("info"),
            LoadingState.EXECUTING: theme.get_color("primary"),
            LoadingState.PROCESSING: theme.get_color("secondary"),
            LoadingState.ANALYZING: theme.get_color("accent"),
            LoadingState.THINKING: theme.get_color("warning"),
            LoadingState.STREAMING: theme.get_color("success"),
            LoadingState.FINALIZING: theme.get_color("accent_alt"),
            LoadingState.COMPLETE: theme.get_color("success"),
            LoadingState.ERROR: theme.get_color("error"),
        }
        return colors.get(state, theme.get_color("loading_primary"))


class LLMLoadingStates:
    """Loading state factories for LLM operations."""

    @staticmethod
    def query_llm(console: Console, model: str):
        """Start an LLM query loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(LoadingCategory.LLM, f"Consultando {model}", "Preparando prompt")
        return manager

    @staticmethod
    def streaming_response(console: Console):
        """Start a streaming-response loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(LoadingCategory.LLM, "Recebendo resposta", "Streaming ativo")
        manager.update(LoadingState.STREAMING, "Processando tokens")
        return manager

    @staticmethod
    def fallback_model(console: Console, from_model: str, to_model: str):
        """Start a model-fallback loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(
            LoadingCategory.LLM, "Fallback de modelo", f"{from_model} -> {to_model}"
        )
        return manager


class ToolLoadingStates:
    """Loading state factories for tool execution."""

    @staticmethod
    def execute_tool(console: Console, tool_name: str, args: Dict[str, Any]):
        """Start a tool-execution loading state."""
        manager = AdvancedLoadingManager(console)
        args_str = ", ".join(f"{k}={v}" for k, v in list(args.items())[:2])
        manager.start(LoadingCategory.TOOL, f"Executando {tool_name}", args_str)
        return manager

    @staticmethod
    def validate_tool(console: Console, tool_name: str):
        """Start a tool-validation loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(
            LoadingCategory.TOOL, f"Validando {tool_name}", "Verificando parâmetros"
        )
        return manager


class FileLoadingStates:
    """Loading state factories for file operations."""

    @staticmethod
    def read_file(console: Console, filepath: str):
        """Start a file-read loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(LoadingCategory.FILE, "Lendo arquivo", filepath)
        return manager

    @staticmethod
    def write_file(console: Console, filepath: str):
        """Start a file-write loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(LoadingCategory.FILE, "Escrevendo arquivo", filepath)
        return manager

    @staticmethod
    def analyze_code(console: Console, filepath: str):
        """Start a code-analysis loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(LoadingCategory.FILE, "Analisando código", filepath)
        manager.update(LoadingState.ANALYZING, "Analisando AST")
        return manager


class AgentLoadingStates:
    """Loading state factories for agent operations."""

    @staticmethod
    def agent_thinking(console: Console, agent_name: str, task: str):
        """Start an agent-thinking loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(LoadingCategory.AGENT, f"{agent_name} pensando", task)
        manager.update(LoadingState.THINKING, "Analisando contexto")
        return manager

    @staticmethod
    def agent_planning(console: Console, agent_name: str):
        """Start an agent-planning loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(
            LoadingCategory.AGENT, f"{agent_name} planejando", "Criando estratégia"
        )
        return manager

    @staticmethod
    def agent_executing(console: Console, agent_name: str, action: str):
        """Start an agent-execution loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(LoadingCategory.AGENT, f"{agent_name} executando", action)
        manager.update(LoadingState.EXECUTING, "Em progresso")
        return manager


class BackgroundLoadingStates:
    """Loading state factories for background tasks."""

    @staticmethod
    def indexing_codebase(console: Console):
        """Start a codebase-indexing loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(
            LoadingCategory.BACKGROUND, "Indexando codebase", "Analisando arquivos"
        )
        return manager

    @staticmethod
    def building_cache(console: Console):
        """Start a cache-build loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(
            LoadingCategory.BACKGROUND, "Construindo cache", "Otimizando acesso"
        )
        return manager

    @staticmethod
    def analyzing_dependencies(console: Console):
        """Start a dependency-analysis loading state."""
        manager = AdvancedLoadingManager(console)
        manager.start(
            LoadingCategory.BACKGROUND, "Analisando dependências", "Construindo grafo"
        )
        return manager


def show_llm_loading(console: Console, model: str) -> AdvancedLoadingManager:
    """Display a loading state for an LLM operation."""
    return LLMLoadingStates.query_llm(console, model)


def show_tool_loading(
    console: Console, tool_name: str, args: Dict[str, Any]
) -> AdvancedLoadingManager:
    """Display a loading state for tool execution."""
    return ToolLoadingStates.execute_tool(console, tool_name, args)


def show_file_loading(
    console: Console, operation: str, filepath: str
) -> AdvancedLoadingManager:
    """Display a loading state for a file operation."""
    intent = resolve_file_loading(operation)
    if intent == "read":
        return FileLoadingStates.read_file(console, filepath)
    if intent == "write":
        return FileLoadingStates.write_file(console, filepath)
    if intent == "analyze":
        return FileLoadingStates.analyze_code(console, filepath)
    manager = AdvancedLoadingManager(console)
    manager.start(LoadingCategory.FILE, operation, filepath)
    return manager


def show_agent_loading(
    console: Console, agent_name: str, action: str, details: str
) -> AdvancedLoadingManager:
    """Display a loading state for an agent action."""
    intent = resolve_agent_loading(action)
    if intent == "thinking":
        return AgentLoadingStates.agent_thinking(console, agent_name, details)
    if intent == "planning":
        return AgentLoadingStates.agent_planning(console, agent_name)
    return AgentLoadingStates.agent_executing(console, agent_name, details)


configure_loading_feedback(
    llm_factory=lambda console, model: show_llm_loading(console, model),
    tool_factory=lambda console, tool_name, params: show_tool_loading(
        console, tool_name, params
    ),
)
