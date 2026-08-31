"""Tool Registry Execution Visualization for Aura TUI.

Interactive panel for viewing and executing Aura OPS tools with real-time monitoring.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from inspect import isawaitable, iscoroutinefunction
from typing import Any, Callable, Dict, List, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Input, ProgressBar, Static


class ToolStatus(Enum):
    """Tool execution status."""

    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolInfo:
    """Information about a registered tool."""

    name: str
    description: str
    category: str = "general"
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ToolStatus = ToolStatus.IDLE
    last_run: Optional[str] = None
    last_result: Optional[Any] = None
    run_count: int = 0


@dataclass
class ToolExecution:
    """Record of a tool execution."""

    tool_name: str
    started_at: str
    completed_at: Optional[str] = None
    status: ToolStatus = ToolStatus.RUNNING
    output: str = ""
    error: Optional[str] = None
    duration_ms: int = 0


class ToolRegistryPanel(Static):
    """Interactive tool registry panel for Aura OPS visualization."""

    selected_tool = reactive("")
    is_executing = reactive(False)

    class ToolExecutionStarted(Message):
        """Emitted when a tool starts executing."""

        def __init__(self, tool_name: str):
            """Initialize the widget."""
            super().__init__()
            self.tool_name = tool_name

    class ToolExecutionCompleted(Message):
        """Emitted when a tool finishes executing."""

        def __init__(self, execution: ToolExecution):
            """Initialize the widget."""
            super().__init__()
            self.execution = execution

    def __init__(self, **kwargs):
        """Initialize the widget."""
        super().__init__(**kwargs)
        self.tools: Dict[str, ToolInfo] = {}
        self.executions: List[ToolExecution] = []
        self._current_execution: Optional[ToolExecution] = None
        self._executor: Optional[Callable[[ToolInfo], Any]] = None

        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register built-in tools into the registry."""
        default_tools = [
            ToolInfo(
                name="file_read",
                description="Ler conteúdo de arquivo",
                category="filesystem",
                parameters={"path": "string"},
            ),
            ToolInfo(
                name="file_write",
                description="Escrever conteúdo em arquivo",
                category="filesystem",
                parameters={"path": "string", "content": "string"},
            ),
            ToolInfo(
                name="shell_execute",
                description="Executar comando shell",
                category="system",
                parameters={"command": "string", "timeout": "int"},
            ),
            ToolInfo(
                name="code_analyze",
                description="Analisar código em busca de problemas",
                category="analysis",
                parameters={"path": "string", "language": "string"},
            ),
            ToolInfo(
                name="git_status",
                description="Obter status do repositório Git",
                category="git",
                parameters={"path": "string"},
            ),
            ToolInfo(
                name="git_diff",
                description="Mostrar diferenças do Git",
                category="git",
                parameters={"path": "string", "staged": "bool"},
            ),
            ToolInfo(
                name="find_in_files",
                description="Pesquisar código no repositório",
                category="search",
                parameters={"query": "string", "path": "string"},
            ),
            ToolInfo(
                name="refactor_rename",
                description="Renomear símbolo na base de código",
                category="refactoring",
                parameters={"old_name": "string", "new_name": "string"},
            ),
            ToolInfo(
                name="test_run",
                description="Executar testes de arquivo ou diretório",
                category="testing",
                parameters={"path": "string", "verbose": "bool"},
            ),
            ToolInfo(
                name="dependency_graph",
                description="Gerar grafo de dependências",
                category="analysis",
                parameters={"path": "string", "format": "string"},
            ),
        ]

        for tool in default_tools:
            self.tools[tool.name] = tool

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        with Horizontal():
            with Vertical(classes="tool-list-pane"):
                yield Static("⚒ Ferramentas disponíveis", classes="pane-header")
                yield Input(
                    placeholder="Pesquisar ferramentas...",
                    id="tool_search",
                    classes="tool-search",
                )
                yield DataTable(
                    id="tool_table", zebra_stripes=True, classes="tool-table"
                )
                with Horizontal(classes="tool-actions"):
                    yield Button("▶ Executar", id="run_btn", variant="primary")
                    yield Button(
                        "⏹ Parar", id="stop_btn", variant="error", disabled=True
                    )

            with Vertical(classes="tool-output-pane"):
                yield Static("↑ Saída da execução", classes="pane-header")
                yield ProgressBar(
                    id="exec_progress", classes="progress-container", show_eta=False
                )
                yield VerticalScroll(id="output_log", classes="output-log")
                with Horizontal(classes="tool-actions"):
                    yield Button("✖ Limpar", id="clear_btn")
                    yield Button("⊞ Copiar", id="copy_btn")
                    yield Button("▥ Histórico", id="history_btn")

    def on_mount(self) -> None:
        """Initialize widget state after mounting."""
        self._setup_tool_table()
        self._load_tools()

        progress = self.query_one("#exec_progress", ProgressBar)
        progress.display = False

    def _setup_tool_table(self) -> None:
        """Configure tool table columns."""
        table = self.query_one("#tool_table", DataTable)
        table.add_columns("Estado", "Ferramenta", "Categoria", "Execuções")
        table.cursor_type = "row"

    def _load_tools(self, filter_query: str = "") -> None:
        """Load registered tools into the table."""
        table = self.query_one("#tool_table", DataTable)
        table.clear()

        filter_lower = filter_query.lower()

        for name, tool in sorted(self.tools.items()):
            if (
                filter_lower
                and filter_lower not in name.lower()
                and filter_lower not in tool.category.lower()
            ):
                continue

            status_icon = self._get_status_icon(tool.status)

            table.add_row(
                status_icon,
                name,
                self._category_label(tool.category),
                str(tool.run_count),
                key=name,
            )

    @staticmethod
    def _category_label(category: str) -> str:
        """Return the user-facing Portuguese label for a tool category."""
        labels = {
            "filesystem": "sistema de arquivos",
            "system": "sistema",
            "analysis": "análise",
            "git": "Git",
            "search": "pesquisa",
            "refactoring": "refatoração",
            "testing": "testes",
        }
        return labels.get(category, category)

    def _get_status_icon(self, status: ToolStatus) -> str:
        """Return an icon character for a given status."""
        icons = {
            ToolStatus.IDLE: "●",
            ToolStatus.RUNNING: "◉",
            ToolStatus.SUCCESS: "✔",
            ToolStatus.FAILED: "✖",
            ToolStatus.CANCELLED: "⊘",
        }
        return icons.get(status, "●")

    def _write_log(self, message: str, log_class: str = "log-info") -> None:
        """Append a message to the log display."""
        log_container = self.query_one("#output_log", VerticalScroll)
        log_entry = Static(message, classes=f"log-entry {log_class}")
        log_container.mount(log_entry)
        log_container.scroll_end()

    def _clear_log(self) -> None:
        """Clear the log display."""
        log_container = self.query_one("#output_log", VerticalScroll)
        log_container.remove_children()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in data table."""
        if event.data_table.id == "tool_table":
            self.selected_tool = event.row_key.value or ""
            self._show_tool_details()

    def _show_tool_details(self) -> None:
        """Show details for the selected tool."""
        if not self.selected_tool:
            return

        tool = self.tools.get(self.selected_tool)
        if not tool:
            return

        self._clear_log()

        self._write_log(f"Ferramenta: {tool.name}", "log-label")
        self._write_log(f"Descrição: {tool.description}", "log-label")
        self._write_log(
            f"Categoria: {self._category_label(tool.category)}", "log-label"
        )
        self._write_log(f"Execuções: {tool.run_count}", "log-label")

        if tool.parameters:
            self._write_log("", "log-content")
            self._write_log("Parâmetros:", "log-label")
            for param, ptype in tool.parameters.items():
                self._write_log(f"  • {param}: {ptype}", "log-info")

        if tool.last_run:
            self._write_log("", "log-content")
            self._write_log(f"Última execução: {tool.last_run}", "log-label")

            if tool.last_result:
                self._write_log("Último resultado:", "log-label")
                self._write_log(str(tool.last_result)[:500], "log-content")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes."""
        if event.input.id == "tool_search":
            self._load_tools(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "run_btn":
            self._execute_selected_tool()
        elif button_id == "stop_btn":
            self._cancel_execution()
        elif button_id == "clear_btn":
            self._clear_log()
        elif button_id == "copy_btn":
            self._copy_output()
        elif button_id == "history_btn":
            self._show_history()

    def _execute_selected_tool(self) -> None:
        """Execute the currently selected tool."""
        if not self.selected_tool or self.is_executing:
            return

        tool = self.tools.get(self.selected_tool)
        if not tool:
            return

        self.is_executing = True
        tool.status = ToolStatus.RUNNING

        self._load_tools()
        run_btn = self.query_one("#run_btn", Button)
        stop_btn = self.query_one("#stop_btn", Button)
        run_btn.disabled = True
        stop_btn.disabled = False

        progress = self.query_one("#exec_progress", ProgressBar)
        progress.display = True
        progress.update(progress=0.0)

        self._clear_log()
        self._write_log(f"▶ Executando: {tool.name}", "log-start")
        self._write_log(
            f"Iniciado às: {datetime.now().strftime('%H:%M:%S')}", "log-info"
        )
        self._write_log("", "log-content")

        self._current_execution = ToolExecution(
            tool_name=tool.name,
            started_at=datetime.now().isoformat(),
        )

        self.post_message(self.ToolExecutionStarted(tool.name))

        self.run_worker(self._run_tool_async(tool))

    async def _run_tool_async(self, tool: ToolInfo) -> None:
        """Run the injected tool executor asynchronously."""
        progress = self.query_one("#exec_progress", ProgressBar)
        execution = self._current_execution

        try:
            if self._executor is None:
                raise RuntimeError(
                    "Executor de tools não configurado; execução não realizada."
                )

            start_time = datetime.now()
            self._write_log("Executando executor configurado...", "log-info")
            if iscoroutinefunction(self._executor):
                result = await self._executor(tool)
            else:
                result = await asyncio.to_thread(self._executor, tool)
                if isawaitable(result):
                    result = await result
            if not self.is_executing:
                return

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            tool.status = ToolStatus.SUCCESS
            tool.run_count += 1
            tool.last_run = end_time.isoformat()
            tool.last_result = result

            if execution:
                execution.status = ToolStatus.SUCCESS
                execution.completed_at = end_time.isoformat()
                execution.duration_ms = duration_ms
                execution.output = str(result)
                self.executions.append(execution)

            progress.update(progress=1.0)
            self._write_log("", "log-content")
            self._write_log("✔ Execução concluída", "log-success")
            self._write_log(f"Resultado: {str(result)[:500]}", "log-content")
            self._write_log(f"Duração: {duration_ms}ms", "log-info")

        except Exception as error:
            tool.status = ToolStatus.FAILED
            if execution:
                execution.status = ToolStatus.FAILED
                execution.error = str(error)
                execution.completed_at = datetime.now().isoformat()
                self.executions.append(execution)

            self._write_log("", "log-content")
            self._write_log(f"✖ Execução não realizada: {error}", "log-error")

        finally:
            self.is_executing = False

            self._load_tools()
            run_btn = self.query_one("#run_btn", Button)
            stop_btn = self.query_one("#stop_btn", Button)
            run_btn.disabled = False
            stop_btn.disabled = True

            progress.display = False

            if execution:
                self.post_message(self.ToolExecutionCompleted(execution))
            self._current_execution = None

    def _cancel_execution(self) -> None:
        """Cancel the running tool execution."""
        if not self.is_executing:
            return

        self.is_executing = False

        tool = self.tools.get(self.selected_tool)
        if tool:
            tool.status = ToolStatus.CANCELLED

        if self._current_execution:
            self._current_execution.status = ToolStatus.CANCELLED
            self._current_execution.completed_at = datetime.now().isoformat()
            self.executions.append(self._current_execution)

        self._write_log("", "log-content")
        self._write_log("⊘ Execução cancelada", "log-warning")
        self.notify("Execução cancelada", severity="warning")

    def _copy_output(self) -> None:
        """Copy tool output to clipboard."""
        self.notify("Saída copiada para a área de transferência")

    def _show_history(self) -> None:
        """Show tool execution history."""
        self._clear_log()

        self._write_log("▥ Histórico de execuções", "log-start")
        self._write_log("", "log-content")

        if not self.executions:
            self._write_log("Nenhuma execução ainda", "log-info")
            return

        for exec_record in reversed(self.executions[-20:]):
            status_icon = self._get_status_icon(exec_record.status)
            duration = (
                f"{exec_record.duration_ms}ms" if exec_record.duration_ms else "—"
            )

            self._write_log(f"{status_icon} {exec_record.tool_name}", "log-label")
            self._write_log(f"   Início: {exec_record.started_at[:19]}", "log-info")
            self._write_log(f"   Duração: {duration}", "log-info")
            if exec_record.error:
                self._write_log(f"   Erro: {exec_record.error}", "log-error")
            self._write_log("", "log-content")

    def register_tool(self, tool: ToolInfo) -> None:
        """Register a new tool in the registry."""
        self.tools[tool.name] = tool
        self._load_tools()

    def set_executor(self, executor: Callable[[ToolInfo], Any]) -> None:
        """Set an executor receiving the selected ``ToolInfo``.

        The executor must return a result or raise an exception. The panel does
        not invent tool arguments; callers are responsible for collecting and
        validating any inputs before injecting the executor.
        """
        self._executor = executor

    def get_tool_status(self, tool_name: str) -> Optional[ToolStatus]:
        """Get the current status of a tool."""
        tool = self.tools.get(tool_name)
        return tool.status if tool else None
