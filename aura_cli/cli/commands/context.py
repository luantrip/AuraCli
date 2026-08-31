"""Context command handlers for Aura CLI.

Handles commands:
- /tangent: Manage tangent conversations
- /checkpoint: Manage git checkpoints (init, create, list, restore)
"""

from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.formatters import (
    format_error_message,
    format_info_message,
    format_success_message,
    format_warning_message,
)
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def handle_tangent(
    command: str, conversation_messages: List[Dict[str, Any]], tangent_manager: Any
) -> Tuple[List[Dict[str, Any]], str]:
    """Handle /tangent command for conversation checkpointing."""

    cmd_parts = command.strip().split()
    subcmd = cmd_parts[0].lower() if cmd_parts else ""

    if subcmd == "tail":
        if not tangent_manager.in_tangent:
            return conversation_messages, format_warning_message(
                "Não está no modo tangent."
            )

        restored_messages, status = tangent_manager.exit(
            conversation_messages, keep_tail=True
        )
        return restored_messages, format_success_message(status)

    elif not subcmd:
        if tangent_manager.in_tangent:
            restored_messages, status = tangent_manager.exit(conversation_messages)
            return restored_messages, format_success_message(status)
        else:
            status = tangent_manager.enter(conversation_messages)
            return [], format_info_message(status)

    return conversation_messages, format_error_message(
        f"Comando tangent desconhecido: {subcmd}"
    )


def handle_checkpoint(
    command: str,
    checkpoint_manager: Any,
    conversation_state: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Handle /checkpoint command for Git-based checkpointing."""
    cmd_parts = command.strip().split(maxsplit=1)
    subcmd = cmd_parts[0].lower() if cmd_parts else ""
    args = cmd_parts[1] if len(cmd_parts) > 1 else ""

    if subcmd == "init":
        checkpoint_manager.init()
        return True, None, format_success_message("Checkpoint system initialized.")

    elif subcmd == "create":
        if not args:
            return (
                True,
                None,
                format_error_message("Descrição do checkpoint obrigatória."),
            )
        checkpoint_manager.create(args, conversation_state=conversation_state)
        return True, None, format_success_message(f"Checkpoint created: {args}")

    elif subcmd == "list":
        try:
            limit = 10
            if args.strip():
                limit = min(int(args.strip()), 50)
        except ValueError:
            limit = 10
        checkpoints = checkpoint_manager.list(limit=limit)
        if not checkpoints:
            return (
                True,
                None,
                format_warning_message(
                    "Nenhum checkpoint encontrado. Use /checkpoint create <desc> para criar."
                ),
            )

        table = Table(title="Checkpoints", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=10)
        table.add_column("Descrição", style="white")
        table.add_column("Data", style="dim", width=20)
        for cp in checkpoints:
            table.add_row(
                cp.id, cp.description, cp.timestamp.strftime("%Y-%m-%d %H:%M")
            )
        Console().print(table)
        return True, None, None  # type: ignore[return-value]

    elif subcmd == "restore":
        if not args:
            return (
                True,
                None,
                format_error_message(
                    "Uso: /checkpoint restore <id> ou /checkpoint restore hard <id>"
                ),
            )
        parts = args.strip().split(maxsplit=1)
        hard = False
        checkpoint_id = args.strip()
        if parts[0].lower() == "hard" and len(parts) > 1:
            hard = True
            checkpoint_id = parts[1].strip()
        if not checkpoint_id:
            return True, None, format_error_message("ID do checkpoint obrigatório.")
        success, state = checkpoint_manager.restore(checkpoint_id, hard=hard)
        if not success:
            return (
                True,
                None,
                format_error_message(
                    f"Failed to restore checkpoint '{checkpoint_id}'. Check that the ID exists (/checkpoint list)."
                ),
            )
        return (
            True,
            state,
            format_success_message(
                f"Checkpoint '{checkpoint_id}' restaurado."
                + (" (restauração hard)" if hard else "")
            ),
        )

    return (
        True,
        None,
        format_error_message(f"Comando checkpoint desconhecido: {subcmd}"),
    )


def handle_memory(args: str) -> None:
    """Handle /memory [search <query> | list] command."""

    console = get_console()
    parts = args.strip().split(maxsplit=1)
    subcmd = parts[0].lower() if parts else "list"
    query = parts[1] if len(parts) > 1 else ""

    try:
        from aura_cli.core.memory.notebook_service import get_notebook_service

        svc = get_notebook_service()

        if subcmd == "search" and query:
            results = svc.search_pages(query)  # type: ignore[attr-defined]
            if not results:
                console.print(
                    f"[{UIStyles.MUTED}]Nenhuma memória encontrada para '{query}'.[/]"
                )
                return
            table = Table(show_header=True, box=None, padding=(0, 2))
            table.add_column("Página", style=UIStyles.ACCENT)
            table.add_column("Trecho", style=UIStyles.BODY)
            for r in results[:10]:
                title = getattr(r, "title", str(r)[:40])
                snippet = getattr(r, "snippet", "")[:80]
                table.add_row(title, snippet)
            console.print(
                Panel(
                    table,
                    title=f"[{UIStyles.TITLE}]{UIIcons.SEARCH} Memórias: {query}[/]",
                    border_style=UIStyles.BORDER_PRIMARY,
                )
            )
        else:
            pages = svc.list_pages()
            if not pages:
                console.print(f"[{UIStyles.MUTED}]Nenhuma memória persistida ainda.[/]")
                return
            table = Table(show_header=True, box=None, padding=(0, 2))
            table.add_column("#", style=UIStyles.MUTED, width=4)
            table.add_column("Título", style=UIStyles.ACCENT)
            table.add_column("Data", style=UIStyles.MUTED, width=20)
            for i, p in enumerate(pages[:20], 1):
                title = getattr(p, "title", str(p))
                date = getattr(p, "created_at", "")
                if hasattr(date, "strftime"):
                    date = date.strftime("%Y-%m-%d %H:%M")
                table.add_row(str(i), title, str(date)[:19])
            console.print(
                Panel(
                    table,
                    title=f"[{UIStyles.TITLE}]{UIIcons.STATS} Memórias Persistidas[/]",
                    border_style=UIStyles.BORDER_PRIMARY,
                )
            )
    except Exception as e:
        logger.warning(f"Error accessing memories: {e}")
        console.print(f"[{UIStyles.ERROR}]Error accessing memories: {e}[/]")


def handle_constitution(args: str) -> None:
    """Handle /constitution [show | edit] command."""

    console = get_console()
    subcmd = args.strip().lower() or "show"

    try:
        from aura_cli.core.memory.notebook_service import get_notebook_service

        svc = get_notebook_service()
        content = svc.read_constitution()  # type: ignore[attr-defined]

        if subcmd == "show":
            if not content:
                console.print(
                    f"[{UIStyles.MUTED}]Nenhuma constituição definida. Use /agi para criar uma.[/]"
                )
                return
            console.print(
                Panel(
                    Markdown(content),
                    title=f"[{UIStyles.TITLE}]{UIIcons.SPARKLES} Constituição do Projeto[/]",
                    border_style=UIStyles.BORDER_PRIMARY,
                    padding=(1, 2),
                )
            )
        elif subcmd == "edit":
            console.print(
                f"[{UIStyles.INFO}]Use /agi para regenerar a constituição interativamente.[/]"
            )
        else:
            console.print(f"[{UIStyles.MUTED}]Uso: /constitution [show|edit][/]")
    except Exception as e:
        logger.warning(f"Error accessing constitution: {e}")
        console.print(f"[{UIStyles.ERROR}]Error accessing constitution: {e}[/]")
