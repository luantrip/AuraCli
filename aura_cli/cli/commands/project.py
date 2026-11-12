"""Project command handlers for Aura CLI.

Handles commands:
- /init: Initialize project
- /todo: View task board
- /notebook: Manage notebook memory
"""

from rich.panel import Panel

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.core.logger import get_logger
from aura_cli.core.memory.notebook_service import notebook_service
from aura_cli.core.sessions.session_state import get_session_state

logger = get_logger(__name__)


def handle_init() -> None:
    """Handle /init command to index the current project."""

    import asyncio

    console = get_console()

    try:
        from aura_cli.core.context.project_indexer import handle_init_command

        with console.status(
            f"[{UIStyles.STATUS_WORKING}]{UIIcons.WORKING} Inicializando projeto...[/]"
        ) as status:

            def ui_callback(msg: str) -> None:
                """Drive the live status line from indexer progress."""
                status.update(
                    f"[{UIStyles.STATUS_WORKING}]{UIIcons.WORKING} {msg}[/]"
                )

            results = asyncio.run(handle_init_command(ui_callback=ui_callback))

            # Optional semantic indexing with embeddings (requires fastembed).
            semantic_indexed = 0
            try:
                from aura_cli.core.embeddings.embeddings_advanced import (
                    CodebaseEmbeddings,
                )

                status.update(
                    f"[{UIStyles.STATUS_WORKING}]{UIIcons.WORKING} "
                    "Indexing semantic embeddings...[/]"
                )
                embeddings = CodebaseEmbeddings(scope=".")
                emb_result = embeddings.index_codebase()
                semantic_indexed = emb_result.get("total_documents", 0)
            except ImportError:
                logger.debug("project: fastembed not installed, skipping embedding initialization")
            except Exception as emb_err:
                logger.debug(f"Semantic indexing skipped: {emb_err}")

        if results.get("status") != "success":
            console.print(
                f"[{UIStyles.ERROR}]{UIIcons.ERROR} Falha ao inicializar o projeto.[/]\n"
                f"[{UIStyles.MUTED}]▪ {results.get('error', 'unknown error')}[/{UIStyles.MUTED}]"
            )
            return

        analyzed = results.get("files_analyzed", 0)
        skipped = results.get("files_skipped", 0)
        console.print(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Projeto inicializado com sucesso![/]"
        )
        console.print(
            f"[{UIStyles.MUTED}]  ↳ {analyzed} arquivos analisados, "
            f"{skipped} em cache[/{UIStyles.MUTED}]"
        )
        if semantic_indexed > 0:
            console.print(
                f"[{UIStyles.MUTED}]  ↳ {semantic_indexed} trechos indexados "
                f"semanticamente[/{UIStyles.MUTED}]"
            )

    except Exception as e:
        logger.error(f"Error initializing project: {e}", exc_info=True)
        console.print(
            f"[{UIStyles.ERROR}]{UIIcons.ERROR} Falha ao inicializar o projeto.[/]\n"
            f"[{UIStyles.MUTED}]▪ Tente: verificar logs em ~/.aura/logs/[/{UIStyles.MUTED}]"
        )


def handle_todo() -> None:
    """Display visual task board from to-do.md file."""

    from aura_cli.cli.ui.todo_display import create_todo_panel
    from aura_cli.core.todo.todo_tracker import TodoTracker

    console = get_console()

    try:
        tracker = TodoTracker()
        panel = create_todo_panel(tracker, max_tasks=20)
        console.print()
        console.print(panel)
        console.print()
    except FileNotFoundError:
        console.print(
            f"[{UIStyles.WARNING}]{UIIcons.WARNING} Nenhum arquivo .aura/to-do.md encontrado.[/]\n"
            f"[{UIStyles.MUTED}]▪ Crie tarefas pedindo para o Aura: 'crie um to-do para o projeto'[/{UIStyles.MUTED}]"
        )
    except Exception as e:
        logger.error(f"Error displaying todo board: {e}", exc_info=True)
        console.print(
            f"[{UIStyles.ERROR}]{UIIcons.ERROR} Failed to display task board: {e}[/]"
        )


def handle_notebook() -> None:
    """Display notebook memory status and information."""

    console = get_console()
    session_state = get_session_state().get_current_state()
    pages = notebook_service.list_pages()
    total_pages = len(pages)

    info = (
        f"[{UIStyles.TITLE}]Status do Notebook[/]\n\n"
        f"Total pages: {total_pages}\n"
        f"Caminho: {notebook_service.notebook_dir}\n"
    )

    if session_state:
        info += f"Current session: {session_state.session_id}\n"

    panel = Panel(
        info,
        title=f"[{UIStyles.TITLE}]{UIIcons.AURA} Notebook[/]",
        border_style=UIStyles.BORDER_PRIMARY,
    )
    console.print(panel)
