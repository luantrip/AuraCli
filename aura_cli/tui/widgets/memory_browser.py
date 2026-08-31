"""Memory Browser Interface for Aura TUI.

Interactive browser for inspecting AI context, conversation memory, and session state.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, ClassVar, Dict, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)

from aura_cli.application.artifacts import ArtifactLayout
from aura_cli.core.memory import (
    ConversationMemory,
    PersistentStore,
    get_persistent_store,
)
from aura_cli.core.memory import (
    InMemoryState as SessionState,
)
from aura_cli.tui.widgets.dialogs.confirm_dialog import ConfirmDialog


class MemoryBrowser(Static):
    """Interactive memory browser for inspecting AI context and memory."""

    search_query = reactive("")

    class MemoryEntrySelected(Message):
        """Emitted when a memory entry is selected."""

        def __init__(self, entry_type: str, entry_data: Any):
            """Initialize the widget."""
            super().__init__()
            self.entry_type = entry_type
            self.entry_data = entry_data

    class MemoryCleared(Message):
        """Emitted when memory is cleared."""

        def __init__(self, memory_type: str):
            """Initialize the widget."""
            super().__init__()
            self.memory_type = memory_type

    def __init__(
        self,
        conversation_memory: Optional[ConversationMemory] = None,
        session_state: Optional[SessionState] = None,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.conversation_memory = conversation_memory or ConversationMemory()
        self.session_state = session_state or SessionState()
        self._persistent_store: Optional[PersistentStore] = None
        self._last_export_path: Optional[Path] = None

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        yield Static("◉ Navegador de memória", classes="memory-header")

        with Horizontal(classes="search-bar"):
            yield Input(
                placeholder="Pesquisar na memória...",
                id="memory_search",
                classes="search-input",
            )
            yield Button("⚲", id="search_btn", classes="search-button")
            yield Button("⟳", id="refresh_btn", classes="search-button")

        with TabbedContent(id="memory_tabs"):
            with TabPane("▣ Conversa", id="conv_tab"):
                yield DataTable(id="conversation_table", zebra_stripes=True)
                yield Static(
                    "Nenhuma mensagem nesta conversa.",
                    id="conversation-empty-state",
                    classes="empty-state",
                )
                yield VerticalScroll(id="message_detail", classes="message-detail")

            with TabPane("⊞ Estado da sessão", id="state_tab"):
                yield Tree("Estado da sessão", id="state_tree", classes="state-tree")

            with TabPane("▾ Persistência", id="persistent_tab"):
                yield DataTable(id="persistent_table", zebra_stripes=True)
                yield Static(
                    "Nenhum registro persistente disponível.",
                    id="persistent-empty-state",
                    classes="empty-state",
                )

            with TabPane("▥ Estatísticas", id="stats_tab"):
                yield Static(id="memory_stats")

        with Horizontal(classes="action-bar"):
            yield Button("✖ Limpar conversa", id="clear_conv_btn", variant="error")
            yield Button("✖ Limpar estado", id="clear_state_btn", variant="error")
            yield Button("↑ Exportar", id="export_btn", variant="primary")

    def on_mount(self) -> None:
        """Initialize widget state after mounting."""
        self._setup_conversation_table()
        self._setup_persistent_table()
        self._load_conversation_data()
        self._load_session_state()
        self._load_persistent_data()
        self._update_statistics()

    def _setup_conversation_table(self) -> None:
        """Configure conversation history table columns."""
        table = self.query_one("#conversation_table", DataTable)
        table.add_columns("ID", "Papel", "Prévia do conteúdo", "Horário")
        table.cursor_type = "row"

    def _setup_persistent_table(self) -> None:
        """Configure persistent memory table columns."""
        table = self.query_one("#persistent_table", DataTable)
        table.add_columns("Chave", "Tipo", "Prévia do valor", "Atualizado")
        table.cursor_type = "row"

    def _load_conversation_data(self) -> None:
        """Load conversation history into the table."""
        table = self.query_one("#conversation_table", DataTable)
        table.clear()

        for i, msg in enumerate(self.conversation_memory.messages):
            content_preview = (
                msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            )
            content_preview = content_preview.replace("\n", " ")

            timestamp = datetime.fromtimestamp(msg.timestamp).strftime("%H:%M:%S")

            role_styled = self._style_role(msg.role)

            table.add_row(
                str(i),
                role_styled,
                content_preview,
                timestamp,
                key=str(i),
            )

        self._set_conversation_empty_state()

    def _set_conversation_empty_state(self, message: Optional[str] = None) -> None:
        """Keep conversation guidance synchronized with the table contents."""
        table = self.query_one("#conversation_table", DataTable)
        empty_state = self.query_one("#conversation-empty-state", Static)
        if message:
            empty_state.update(message)
        empty_state.display = table.row_count == 0

    def _set_persistent_empty_state(self, message: Optional[str] = None) -> None:
        """Keep persistent-memory guidance synchronized with table contents."""
        table = self.query_one("#persistent_table", DataTable)
        empty_state = self.query_one("#persistent-empty-state", Static)
        if message:
            empty_state.update(message)
        empty_state.display = table.row_count == 0

    _ROLE_STYLES: ClassVar[dict] = {
        "user": "user",
        "assistant": "assistant",
        "system": "system",
    }

    def _style_role(self, role: str) -> str:
        """Return a Rich style string for a message role."""
        return self._ROLE_STYLES.get(role, role)

    def _load_session_state(self) -> None:
        """Load session state into the tree view."""
        tree = self.query_one("#state_tree", Tree)
        tree.clear()

        state_data = self.session_state.all()

        if not state_data:
            tree.root.add_leaf("Nenhum estado de sessão")
            return

        self._add_dict_to_tree(tree.root, state_data)
        tree.root.expand()

    def _add_dict_to_tree(self, parent, data: Dict, depth: int = 0) -> None:
        """Recursively add dictionary entries to a tree node."""
        if depth > 5:
            parent.add_leaf("...")
            return

        for key, value in data.items():
            if isinstance(value, dict):
                branch = parent.add(key)
                self._add_dict_to_tree(branch, value, depth + 1)
            elif isinstance(value, list):
                branch = parent.add(f"{key} ({len(value)} itens)")
                for i, item in enumerate(value[:10]):
                    if isinstance(item, dict):
                        item_branch = branch.add(f"[{i}]")
                        self._add_dict_to_tree(item_branch, item, depth + 1)
                    else:
                        branch.add_leaf(f"[{i}] {self._truncate(str(item))}")
                if len(value) > 10:
                    branch.add_leaf(f"... e mais {len(value) - 10}")
            else:
                value_str = self._truncate(str(value))
                parent.add_leaf(f"{key}: {value_str}")

    def _truncate(self, text: str, max_len: int = 50) -> str:
        """Truncate a string to a maximum length."""
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text

    def _load_persistent_data(self) -> None:
        """Load persistent memory entries into the table."""
        table = self.query_one("#persistent_table", DataTable)
        table.clear()

        try:
            store = get_persistent_store()
            self._persistent_store = store

            tasks = store.get_recent_tasks(20)
            for task in tasks:
                table.add_row(
                    f"task:{task['task_id']}",
                    "task",
                    self._truncate(task.get("name", "N/D")),
                    task.get("created_at", "N/D")[:19],
                    key=f"task:{task['task_id']}",
                )

            for key in ["theme", "llm_settings", "user_preferences"]:
                value = store.get_setting(key)
                if value is not None:
                    table.add_row(
                        f"setting:{key}",
                        "setting",
                        self._truncate(str(self._safe_setting_value(key, value))),
                        "",
                        key=f"setting:{key}",
                    )
            self._set_persistent_empty_state()
        except Exception as e:
            self._set_persistent_empty_state(
                "Não foi possível carregar a memória persistente. Tente Atualizar."
            )
            self.notify(f"Failed to load persistent data: {e}", severity="error")

    def _update_statistics(self) -> None:
        """Refresh memory statistics display."""
        stats_widget = self.query_one("#memory_stats", Static)

        conv_count = len(self.conversation_memory.messages)
        conv_chars = sum(len(m.content) for m in self.conversation_memory.messages)
        state_count = len(self.session_state.all())

        stats_text = f"""
▥ Estatísticas da memória

Memória da conversa:
  • Mensagens: {conv_count}
  • Caracteres totais: {conv_chars:,}
  • Resumo: {"Sim" if self.conversation_memory.summary else "Não"}
  • Máximo de mensagens: {self.conversation_memory.max_messages}

Estado da sessão:
  • Chaves: {state_count}
  • Alterado: {"Sim" if self.session_state.is_dirty else "Não"}

Armazenamento persistente:
  • Banco de dados: ~/.aura/tui_data.db
"""
        stats_widget.update(stats_text)

    def _write_log(self, message: str, log_class: str = "log-content") -> None:
        """Append a message to the log display."""
        log_container = self.query_one("#message_detail", VerticalScroll)
        log_entry = Static(message, classes=f"log-entry {log_class}")
        log_container.mount(log_entry)
        log_container.scroll_end()

    def _clear_log(self) -> None:
        """Clear the log display."""
        log_container = self.query_one("#message_detail", VerticalScroll)
        log_container.remove_children()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in data table."""
        table_id = event.data_table.id

        if table_id == "conversation_table":
            self._show_message_detail(event.row_key.value or "")
        elif table_id == "persistent_table":
            self._show_persistent_detail(event.row_key.value or "")

    def _show_message_detail(self, row_key: str) -> None:
        """Show full detail of a selected message."""
        try:
            idx = int(row_key)
            if 0 <= idx < len(self.conversation_memory.messages):
                msg = self.conversation_memory.messages[idx]

                self._clear_log()
                self._write_log(f"Papel: {msg.role}", "log-label")
                self._write_log(
                    f"Horário: {datetime.fromtimestamp(msg.timestamp)}", "log-label"
                )

                if msg.metadata:
                    self._write_log(
                        f"Metadados: {json.dumps(msg.metadata, indent=2)}", "log-label"
                    )

                self._write_log("", "log-content")
                self._write_log("Conteúdo:", "log-label")
                self._write_log(msg.content, "log-content")

                self.post_message(self.MemoryEntrySelected("conversation", msg))
        except (ValueError, IndexError) as error:
            self.log.debug("Conversation row is no longer available: %s", error)

    def _show_persistent_detail(self, row_key: str) -> None:
        """Show full detail of a selected persistent entry."""
        if self._persistent_store is None:
            return

        if row_key.startswith("task:"):
            task_id = row_key[5:]
            task = self._persistent_store.get_task(task_id)
            if task:
                self.notify(
                    f"Tarefa: {task.get('name', 'N/D')}\nEstado: {task.get('status', 'N/D')}"
                )
                self.post_message(self.MemoryEntrySelected("task", task))

        elif row_key.startswith("setting:"):
            setting_key = row_key[8:]
            value = self._persistent_store.get_setting(setting_key)
            if value is not None:
                safe_value = self._safe_setting_value(setting_key, value)
                self.notify(
                    f"Configuração: {setting_key}\nValor: {json.dumps(safe_value, indent=2)[:200]}"
                )
                self.post_message(
                    self.MemoryEntrySelected("setting", {setting_key: safe_value})
                )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "memory_search":
            self._perform_search(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "search_btn":
            search_input = self.query_one("#memory_search", Input)
            self._perform_search(search_input.value)

        elif button_id == "refresh_btn":
            self._refresh_all()

        elif button_id == "clear_conv_btn":
            self._request_clear("conversation")

        elif button_id == "clear_state_btn":
            self._request_clear("session")

        elif button_id == "export_btn":
            self._export_memory()

    def _perform_search(self, query: str) -> None:
        """Execute search across memory entries."""
        if not query:
            self._load_conversation_data()
            return

        query_lower = query.lower()
        table = self.query_one("#conversation_table", DataTable)
        table.clear()

        for i, msg in enumerate(self.conversation_memory.messages):
            if query_lower in msg.content.lower() or query_lower in msg.role.lower():
                content_preview = (
                    msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
                )
                content_preview = content_preview.replace("\n", " ")
                timestamp = datetime.fromtimestamp(msg.timestamp).strftime("%H:%M:%S")

                table.add_row(
                    str(i),
                    self._style_role(msg.role),
                    content_preview,
                    timestamp,
                    key=str(i),
                )

        self._set_conversation_empty_state(
            "Nenhuma mensagem corresponde à busca."
            if table.row_count == 0
            else "Nenhuma mensagem nesta conversa."
        )
        self.notify(f"{table.row_count} mensagens encontradas")

    def _refresh_all(self) -> None:
        """Reload all data panels."""
        self._load_conversation_data()
        self._load_session_state()
        self._load_persistent_data()
        self._update_statistics()
        self.notify("Navegador de memória atualizado")

    def _request_clear(self, memory_type: str) -> None:
        """Ask for confirmation before clearing a memory surface."""
        label = "a conversa" if memory_type == "conversation" else "o estado da sessão"
        dialog = ConfirmDialog(
            message=f"Tem certeza que deseja limpar {label}? Esta ação não pode ser desfeita.",
            title="Confirmar limpeza",
            on_confirm=(
                self._clear_conversation
                if memory_type == "conversation"
                else self._clear_session_state
            ),
            confirm_label="Limpar",
            cancel_label="Cancelar",
        )
        self.app.mount(dialog)

    def _clear_conversation(self) -> None:
        """Clear conversation history after confirmation."""
        self.conversation_memory.clear()
        self._load_conversation_data()
        self._update_statistics()
        self.post_message(self.MemoryCleared("conversation"))
        self.notify("Memória de conversa limpa")

    def _clear_session_state(self) -> None:
        """Clear session state after confirmation."""
        self.session_state.clear()
        self._load_session_state()
        self._update_statistics()
        self.post_message(self.MemoryCleared("session"))
        self.notify("Estado da sessão limpo")

    def _export_memory(self) -> None:
        """Export memory data to a timestamped JSON file."""
        export_data = {
            "conversation": self.conversation_memory.to_dict(),
            "session_state": self.session_state.to_dict(),
            "exported_at": datetime.now().isoformat(),
        }
        export_dir = ArtifactLayout().project("exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / (
            f"aura-memory-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        temporary_path = export_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(export_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_path.replace(export_path)
        self._last_export_path = export_path
        self.notify(f"Memória exportada: {export_path.name}")

    def _safe_setting_value(self, key: str, value: Any) -> Any:
        """Mask credential-like fields before persistent data reaches the UI."""
        if key != "llm_settings" or not isinstance(value, dict):
            return value
        sensitive_tokens = ("key", "token", "secret", "password")
        return {
            field: "[oculto]"
            if any(token in field.lower() for token in sensitive_tokens)
            else field_value
            for field, field_value in value.items()
        }

    def update_conversation(self, memory: ConversationMemory) -> None:
        """Update the conversation history display."""
        self.conversation_memory = memory
        self._load_conversation_data()
        self._update_statistics()

    def update_session_state(self, state: SessionState) -> None:
        """Update the session state display."""
        self.session_state = state
        self._load_session_state()
        self._update_statistics()

    def add_message(
        self, role: str, content: str, metadata: Optional[Dict] = None
    ) -> None:
        """Add a new message to the conversation view."""
        self.conversation_memory.add_message(role, content, metadata)
        self._load_conversation_data()
        self._update_statistics()
