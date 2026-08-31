"""Internal processing window for agents.

Allows agents to work silently in background, showing only status updates
and final results.

Features:
    - Silent background processing
    - Status update streaming
    - Tool usage tracking
    - Message consolidation
    - Performance monitoring

Classes:
    - InternalProcessingWindow: Main processing window manager

Example:
    >>> from aura_cli.cli.ui.internal_window import InternalProcessingWindow
    >>> window = InternalProcessingWindow(status_queue, "AGI")
    >>> window.start()
"""

from queue import Queue
import re
import time
from typing import Any, Dict, List, Optional

from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console

from .responsive import ResponsiveLayout


class InternalProcessingWindow:
    """Internal processing window for agents.

    Captures internal agent conversations and processes them silently,
    showing only status updates.

    Attributes:
        status_queue: Queue for sending status updates
        agent_name: Agent name (for status messages)
        verbose: If True, keeps more context in consolidated messages
        chat_history: List of chat messages
        tools_used: List of tools used
        is_active: Whether window is active
        start_time: Processing start time
        message_count: Number of messages processed
    """

    def __init__(
        self, status_queue: Queue, agent_name: str = "Agent", verbose: bool = False
    ):
        """Initialize processing window.

        Args:
            status_queue: Queue for sending status updates
            agent_name: Agent name (for status messages)
            verbose: If True, keeps more context in consolidated messages
        """
        self.status_queue = status_queue
        self.agent_name = agent_name
        self.verbose = verbose
        self.chat_history: List[Dict[str, Any]] = []
        self.tools_used: List[str] = []
        self.generated_files: List[str] = []
        self.edited_files: List[str] = []
        self.analyzed_files: List[str] = []
        self.is_active = False
        self.start_time = None
        self.message_count = 0
        self._last_status_update: float = 0.0
        self._status_update_interval = 0.5  # Maximum 1 update every 0.5s
        self.important_messages: List[Dict[str, Any]] = []

    def start(self):
        """Inicia modo de processamento interno."""
        self.is_active = True
        self.chat_history = []
        self.tools_used = []
        self.generated_files = []
        self.edited_files = []
        self.analyzed_files = []
        self.important_messages = []
        self.start_time = time.time()
        self.message_count = 0
        self._last_status_update: float = 0.0

    def stop(self):
        """Stop the internal window and clean up."""
        self.is_active = False

    def capture_message(
        self, sender_name: str, recipient_name: str, message: Dict[str, Any]
    ):
        """Capture a message for internal display."""
        if not self.is_active:
            return

        self.message_count += 1

        message_data = {
            "from": sender_name,
            "to": recipient_name,
            "content": message.get("content", ""),
            "timestamp": time.time(),
            "index": self.message_count,
        }
        self.chat_history.append(message_data)

        content = message.get("content", "")
        if self._is_important_message(content):
            self.important_messages.append(message_data)

        self._update_status_from_message(message)
        self._extract_tools(message)
        self._extract_file_artifacts(message)

    def _throttled_status_update(self, message: str):
        """Apply throttled status updates to avoid flooding."""
        current_time = time.time()
        if current_time - self._last_status_update >= self._status_update_interval:
            self.status_queue.put(message)
            self._last_status_update = current_time

    def _update_status_from_message(self, message: Dict[str, Any]):
        """Update internal status from a message payload."""
        content = message.get("content", "").lower()

        if "terminate" in content:
            duration = time.time() - self.start_time if self.start_time else 0
            self.status_queue.put(
                f"› [{self.agent_name}] {UIIcons.SUCCESS} Processing completed in {duration:.1f}s!"
            )
            return

        # keyword → (icon, label) pairs evaluated in order
        _KEYWORD_STATUS = [
            (
                ("list_directory", "listando"),
                UIIcons.DIR,
                "Explorando estrutura de diretórios...",
            ),
            (("read_file", "lendo"), UIIcons.FILE, "Lendo arquivos do projeto..."),
            (
                ("write_file", "escrevendo", "criando"),
                UIIcons.CREATE,
                "Criando/editando arquivos...",
            ),
            (("edit_file", "editando"), UIIcons.EDIT, "Editando arquivos..."),
            (
                ("search", "grep", "buscando"),
                UIIcons.SEARCH,
                "Buscando padrões no código...",
            ),
            (("analis", "analyz"), UIIcons.STATS, "Analisando código e arquitetura..."),
            (("git",), UIIcons.OPS, "Verificando repositório Git..."),
            (("docker",), UIIcons.OPS, "Analisando containers Docker..."),
            (("run_shell", "executando"), UIIcons.RUN, "Executando comando..."),
        ]
        for keywords, icon, label in _KEYWORD_STATUS:
            if any(kw in content for kw in keywords):
                self._throttled_status_update(f"› [{self.agent_name}] {icon} {label}")
                return

    def _extract_tools(self, message: Dict[str, Any]):
        """Extract tool call records from a message."""
        content = message.get("content", "")

        known_tools = [
            "list_directory",
            "read_file",
            "write_file",
            "edit_file",
            "run_shell_command",
            "search_in_files",
            "tree_view",
            "git_status",
            "git_diff",
            "git_log",
            "git_commit",
            "docker_ps",
            "docker_logs",
            "docker_build",
            "analyze_code",
            "validate_syntax",
            "format_code",
        ]

        for tool in known_tools:
            if tool in content and tool not in self.tools_used:
                self.tools_used.append(tool)

    def _extract_file_artifacts(self, message: Dict[str, Any]) -> None:
        """Extract file artifacts from tool-call-like message content."""
        content = message.get("content", "")
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
            if "write_file" in lowered and file_path not in self.generated_files:
                self.generated_files.append(file_path)
            if "edit_file" in lowered and file_path not in self.edited_files:
                self.edited_files.append(file_path)
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
                and file_path not in self.analyzed_files
            ):
                self.analyzed_files.append(file_path)

    def _is_important_message(self, content: str) -> bool:
        """Return True if the message should be preserved."""
        if not content:
            return False

        important_keywords = [
            "encontrei",
            "descobri",
            "identifiquei",
            "concluí",
            "resultado",
            "encontrado",
            "detectado",
            "analisado",
            "completo",
            "sucesso",
            "erro",
            "problema",
            "issue",
            "bug",
            "vulnerabilidade",
        ]

        content_lower = content.lower()
        return (
            any(keyword in content_lower for keyword in important_keywords)
            and len(content) > 50
        )

    def should_suppress_message(self, sender_name: str, content: str) -> bool:
        """Return True if this message should be suppressed."""
        if "TERMINATE" in content:
            return False

        if "proxy" in sender_name.lower():
            return True

        if len(content.strip()) < 20:
            return True

        return bool(content.strip().startswith("***** "))

    def _select_final_message(self, agent_messages: list) -> str:
        """Pick the best final message from the agent message list."""
        final_message = agent_messages[-1]["content"]
        final_message = final_message.replace("TERMINATE", "").strip()
        final_message = re.sub(
            r"\*{5,}.*?\*{5,}", "", final_message, flags=re.DOTALL
        ).strip()

        if len(final_message) < 50 and len(agent_messages) > 1:
            if self.important_messages and self.verbose:
                important_content = "\n\n".join(
                    msg["content"].replace("TERMINATE", "").strip()
                    for msg in self.important_messages[-5:]
                    if len(msg["content"].strip()) > 20
                )
                if important_content:
                    return important_content
            else:
                return "\n\n".join(
                    msg["content"].replace("TERMINATE", "").strip()
                    for msg in agent_messages[-5:]
                    if len(msg["content"].strip()) > 20
                )

        if self.verbose and self.important_messages and len(final_message) < 500:
            context_parts = [
                f"• {c[:200]}{'...' if len(c) > 200 else ''}"
                for msg in self.important_messages[-3:]
                if len(c := msg["content"].replace("TERMINATE", "").strip()) > 30
                and c not in final_message
            ]
            if context_parts:
                final_message += "\n\n**Contexto adicional:**\n" + "\n".join(
                    context_parts
                )

        return final_message

    def get_consolidated_response(self) -> Panel:
        """Return the consolidated response text."""
        agent_messages = [
            msg
            for msg in self.chat_history
            if self.agent_name.lower() in msg["from"].lower()
            or "agi" in msg["from"].lower()
            or "ops" in msg["from"].lower()
        ]

        if not agent_messages:
            from aura_cli.cli.ui.constants import UIIcons, UIStyles
            from aura_cli.cli.ui.terminal_display import create_status_badge

            badge = create_status_badge("warning", "Nenhuma resposta foi gerada")
            return Panel(
                badge,
                title=f"[{UIStyles.TITLE}]{UIIcons.AGENT} {self.agent_name}[/{UIStyles.TITLE}]",
                border_style=UIStyles.BORDER_WARNING,
                padding=(1, 2),
                expand=False,
                width=ResponsiveLayout(get_console()).get_panel_width(),
            )

        final_message = self._select_final_message(agent_messages)

        from aura_cli.cli.ui.constants import UIIcons, UIStyles

        duration = time.time() - self.start_time if self.start_time else 0
        timeline = self._render_timeline()
        metrics_panel = self._render_metrics_panel(duration)

        from rich.markdown import Markdown

        content_parts: List[Any] = [Markdown(final_message)]
        content_parts.append(Text())
        if timeline:
            content_parts.append(timeline)
            content_parts.append(Text())
        content_parts.append(metrics_panel)

        return Panel(
            Group(*content_parts),
            title=f"[{UIStyles.TITLE}]{UIIcons.AGENT} {self.agent_name}[/{UIStyles.TITLE}]",
            subtitle=f"[dim]{len(self.chat_history)} mensagens · {len(self.tools_used)} ferramentas[/dim]"
            if (self.chat_history or self.tools_used)
            else None,
            border_style=UIStyles.BORDER_PRIMARY,
            padding=(1, 2),
            expand=False,
            width=ResponsiveLayout(get_console()).get_panel_width(),
        )

    def _render_timeline(self) -> Optional[Table]:
        """Renderiza timeline visual de processamento (estilo Cursor-Agent)."""
        if not self.chat_history or len(self.chat_history) < 2:
            return None

        table = Table(
            show_header=True,
            header_style=UIStyles.SUBTITLE,
            border_style=UIStyles.BORDER_MUTED,
            box=None,
            padding=(0, 1),
            title="[dim]Atividade[/dim]",
            expand=True,
        )

        table.add_column("Tempo", style=UIStyles.MUTED, ratio=1)
        table.add_column("Evento", ratio=4, overflow="fold")

        recent_events = self.chat_history[-5:]
        for msg in recent_events:
            elapsed = msg["timestamp"] - self.start_time if self.start_time else 0
            time_str = f"{elapsed:.1f}s"

            content = msg.get("content", "").lower()
            if "tool" in content or any(tool in content for tool in self.tools_used):
                event_icon = UIIcons.TOOL
                event_text = f"{event_icon} Execução de ferramenta"
            elif "error" in content or "failed" in content:
                event_icon = UIIcons.ERROR
                event_text = f"{event_icon} Erro"
            elif "complete" in content or "done" in content:
                event_icon = UIIcons.SUCCESS
                event_text = f"{event_icon} Concluído"
            else:
                event_icon = UIIcons.BULLET
                event_text = f"{event_icon} Processando"

            table.add_row(
                f"[{UIStyles.MUTED}]{time_str}[/]",
                f"[{UIStyles.BODY}]{event_text}[/]",
            )

        return table

    def _render_metrics_panel(self, duration: float) -> Panel:
        """Render the metrics panel with Cursor-Agent style cards."""
        metrics_cards = []

        msg_card = Text()
        msg_card.append(f"{UIIcons.STATS} ", style=UIStyles.INFO)
        msg_card.append(f"{len(self.chat_history)}", style=UIStyles.PRIMARY + " bold")
        msg_card.append(" mensagens", style=UIStyles.MUTED)
        metrics_cards.append(
            Panel(msg_card, border_style=UIStyles.BORDER_ACCENT, padding=(1, 1))
        )

        tool_card = Text()
        tool_card.append(f"{UIIcons.TOOL} ", style=UIStyles.ACCENT)
        tool_card.append(f"{len(self.tools_used)}", style=UIStyles.PRIMARY + " bold")
        tool_card.append(" ferramentas", style=UIStyles.MUTED)
        metrics_cards.append(
            Panel(tool_card, border_style=UIStyles.BORDER_ACCENT, padding=(1, 1))
        )

        time_card = Text()
        time_card.append(f"{UIIcons.TIMER} ", style=UIStyles.WARNING)
        time_card.append(f"{duration:.1f}s", style=UIStyles.PRIMARY + " bold")
        metrics_cards.append(
            Panel(time_card, border_style=UIStyles.BORDER_ACCENT, padding=(1, 1))
        )

        return Panel(
            Columns(metrics_cards, equal=True, expand=True),
            title="[dim]Resumo[/dim]",
            title_align="left",
            border_style=UIStyles.BORDER_MUTED,
            padding=(0, 1),
        )

    def get_full_history(self) -> str:
        """Return the full message history."""
        lines = []
        lines.append(f"\n{'=' * 80}")
        lines.append(f"HISTÓRICO COMPLETO - {self.agent_name}")
        lines.append(f"{'=' * 80}\n")

        for i, msg in enumerate(self.chat_history, 1):
            elapsed = msg["timestamp"] - self.start_time if self.start_time else 0
            lines.append(f"[{i}] ({elapsed:.1f}s) {msg['from']} -> {msg['to']}")
            lines.append(f"    {msg['content'][:200]}...")
            lines.append("")

        lines.append(f"\n{'=' * 80}")
        lines.append(
            f"FERRAMENTAS USADAS: {', '.join(self.tools_used) if self.tools_used else 'Nenhuma'}"
        )
        lines.append(f"{'=' * 80}\n")

        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of internal window state."""
        duration = time.time() - self.start_time if self.start_time else 0
        files_touched = []
        for file_path in self.generated_files + self.edited_files + self.analyzed_files:
            if file_path not in files_touched:
                files_touched.append(file_path)

        return {
            "total_messages": len(self.chat_history),
            "tools_used": self.tools_used,
            "tool_count": len(self.tools_used),
            "generated_files": self.generated_files,
            "edited_files": self.edited_files,
            "analyzed_files": self.analyzed_files,
            "files_touched": files_touched,
            "duration": duration,
            "message_count": self.message_count,
        }
