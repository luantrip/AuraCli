"""Execute commands owned by the Textual adapter."""

from __future__ import annotations

from typing import Any, Protocol

from aura_cli.application.presentation.command_routing import PresentationCommandAction
from aura_cli.tui.widgets.chat import AuraChatLog

HELP_TEXT = """# Aura CLI TUI — Available Commands

## Interface:
- `/clear` or `/cls` — Clear chat history
- `/help` or `/?` — Show this help
- `/welcome` — Welcome screen and quick commands
- `/keyboard` `/keys` `/shortcuts` — Keyboard shortcuts
- `/back` — Return to legacy CLI interface
- `/exit` or `/quit` — Exit Aura CLI

## Tools and screens:
- `/tools` or `/tools-menu` — Open optional tools menu
- `/context` — Open project workspace and context
- `/files` — Open external file manager
- `/settings` — Settings (API keys, models)
- `/sessions` — Saved session history
- `/constitution` — Project constitution assistant
- `/history` — Input command history (↑/↓)

## Agents and context:
- `/agi <task>` — Start AGI agent with task
- `/ops <task>` — Start DevOps agent
- `/todo [add|done|list]` — Task list
- `/memory` — Memory explorer
- `/notebook` — Notebook status (persistent memory)
- `/consolidate` — Consolidate learned rules
- `/init` — Initialize project context
- `/extensions` — List loaded extensions

## Models and configuration:
- `/model [list|set|info]` — Manage AI models
- `/dev [status]` — Check local LLM availability
- `/config [show|set|reset]` — System configuration
- `/auto-run` — Toggle execution without confirmation
- `/theme <name>` — Switch visual theme

## Session:
- `/checkpoint [create|list|restore]` — Restore points
- `/tangent` — Parallel conversations
- `/cost` — Estimated token cost
- `/dashboard` — Dashboards
- `/workflow` — Automated workflows

## Tips:
- Type normally to chat with the AI
- Use `Ctrl+P` for the full command palette
- Press `↑/↓` in the input to navigate history"""

SHORTCUTS_TEXT = """# Keyboard Shortcuts

- `Ctrl+C` — Exit application
- `Ctrl+L` — Clear chat
- `ESC` — Cancel operation
- `Ctrl+E` — Toggle analysis/events panel
- `Ctrl+S` — Show code analysis
- `F` — Focus mode
- `Ctrl+P` — Command palette
- `Ctrl+G` — Paint
- `Ctrl+F` — File manager
- `Ctrl+M` — Embedded monitor
- `Ctrl+Shift+T` — Token/context usage
- `<leader> l` — Session history"""

WELCOME_TEXT = """# ✦ Welcome to Aura CLI

## Quick commands:
- `/help` — List all commands
- `/keyboard` — Keyboard shortcuts
- `/tools` — Available tools
- `/model` — Switch AI model
- `/settings` — Settings and API keys
- `/sessions` — Saved session history

## Tips:
- Type normally to chat with the AI
- Use `/` to access commands
- `Ctrl+P` abre a paleta de comandos
- `Ctrl+G` abre o editor de arte ANSI (Paint)

_Digite uma pergunta ou use um comando acima._"""

HISTORY_TEXT = (
    "No TUI, `/history` refere-se ao histórico de **comandos** do input (↑/↓). "
    "Para conversas salvas em disco, use **`/sessions`** (~/.aura/sessions)."
)


class LocalCommandHost(Protocol):
    controller: Any
    all_chat_messages: list[Any]

    def post_message(self, message: Any) -> bool: ...
    def post_message_to_chat(self, sender: str, content: str) -> None: ...
    def exit(self) -> None: ...
    def set_timer(self, delay: float, callback: Any) -> Any: ...
    def query_one(self, selector: str) -> Any: ...
    def action_push_tools_menu_screen(self) -> None: ...
    def action_push_history_screen(self) -> None: ...
    def action_push_file_manager_screen(self) -> None: ...
    def action_toggle_workspace_panel(self) -> None: ...
    def _open_constitution_screen(self) -> None: ...
    def _open_settings_screen(self) -> None: ...
    def _handle_consolidate_command(self) -> None: ...


def handle_local_command(host: LocalCommandHost, command: str) -> bool:
    """Classify and execute a slash command owned by the TUI."""
    action = host.controller.classify_command(command)
    if action in (
        PresentationCommandAction.PASSTHROUGH,
        PresentationCommandAction.UNHANDLED,
    ):
        return False
    if action is PresentationCommandAction.MODEL:
        host.post_message_to_chat("Sistema", "⟳ Processando comando de modelo...")
        return False

    handlers = {
        PresentationCommandAction.CONSOLIDATE: host._handle_consolidate_command,
        PresentationCommandAction.TOOLS: host.action_push_tools_menu_screen,
        PresentationCommandAction.CONSTITUTION: host._open_constitution_screen,
        PresentationCommandAction.SETTINGS: host._open_settings_screen,
        PresentationCommandAction.SESSIONS: host.action_push_history_screen,
    }
    handler = handlers.get(action)
    if handler is not None:
        handler()
    elif action is PresentationCommandAction.CLEAR:
        host.post_message(AuraChatLog.ClearHistory())
        host.all_chat_messages.clear()
        host.post_message_to_chat("Sistema", "Chat limpo.")
    elif action is PresentationCommandAction.HELP:
        host.post_message_to_chat("Sistema", HELP_TEXT)
    elif action is PresentationCommandAction.SHORTCUTS:
        host.post_message_to_chat("Sistema", SHORTCUTS_TEXT)
    elif action is PresentationCommandAction.WELCOME:
        host.post_message_to_chat("Sistema", WELCOME_TEXT)
    elif action is PresentationCommandAction.HISTORY:
        host.post_message_to_chat("Sistema", HISTORY_TEXT)
    elif action is PresentationCommandAction.BACK:
        host.post_message_to_chat("Sistema", "Retornando à interface CLI legada...")
        host.exit()
    elif action is PresentationCommandAction.EXIT:
        host.post_message_to_chat("Sistema", "Até logo! Encerrando Aura CLI...")
        host.set_timer(0.5, host.exit)
    elif action is PresentationCommandAction.CONTEXT:
        host.action_toggle_workspace_panel()
    elif action is PresentationCommandAction.FILES:
        host.action_push_file_manager_screen()
    elif action is PresentationCommandAction.TODO:
        _reveal_todo(host)
    return True


def _reveal_todo(host: LocalCommandHost) -> None:
    try:
        panel = host.query_one("#todo_panel")
        panel.display = bool(panel.tasks)
        panel.scroll_visible()
        message = (
            "✔ Tarefas visíveis no fluxo da conversa."
            if panel.tasks
            else "A lista está vazia. Use `/todo add <tarefa>` para adicionar."
        )
    except Exception:
        message = "Lista de tarefas: use `/todo add <tarefa>` para adicionar itens."
    host.post_message_to_chat("Sistema", message)


__all__ = ["handle_local_command"]
