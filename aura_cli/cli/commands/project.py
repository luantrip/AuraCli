"""Project command handlers for Aura CLI.

Handles commands:
- /init: Initialize project
- /todo: View task board
- /notebook: Manage notebook memory
"""

from rich.console import Console
from rich.panel import Panel

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.core.logger import get_logger
from aura_cli.core.memory.notebook_service import notebook_service
from aura_cli.core.sessions.session_state import get_session_state

logger = get_logger(__name__)


def handle_init() -> None:
    """Handle /init command to index the current project."""

    console = Console()

    try:
        from aura_cli.core.indexing.project_indexer import (
            ProjectIndexer,
        )

        indexer = ProjectIndexer()

        with console.status(
            f"[{UIStyles.WORKING}]{UIIcons.WORKING} Inicializando projeto...[/]"  # type: ignore[attr-defined]
        ) as status:

            def ui_callback(msg: str):
                """Callback to display UI output from the command."""
                status.update(f"[{UIStyles.WORKING}]{UIIcons.WORKING} {msg}[/]")  # type: ignore[attr-defined]

            indexer.index_project(callback=ui_callback)

        console.print(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Project initialized successfully![/]"
        )

        # Semantic indexing with embeddings (optional — requires fastembed)
        try:
            from aura_cli.core.embeddings.embeddings_advanced import CodebaseEmbeddings

            status.update(
                f"[{UIStyles.STATUS_WORKING}]{UIIcons.WORKING} Indexando embeddings semânticos...[/]"
            )
            embeddings = CodebaseEmbeddings(scope=".")
            result = embeddings.index_codebase()
            indexed = result.get("files_indexed", 0)
            if indexed > 0:
                console.print(
                    f"[{UIStyles.MUTED}]  ↳ {indexed} arquivos indexados semanticamente[/{UIStyles.MUTED}]"
                )
        except ImportError:
            pass  # fastembed not installed — silenced
        except Exception as emb_err:
            logger.debug(f"Indexação semântica ignorada: {emb_err}")

    except Exception as e:
        logger.error(f"Error initializing project: {e}", exc_info=True)
        console.print(
            f"[{UIStyles.ERROR}]{UIIcons.ERROR} Failed to initialize project.[/]\n"
            f"[{UIStyles.MUTED}]▪ Tente: verificar logs em ~/.aura/logs/[/{UIStyles.MUTED}]"
        )


def handle_todo() -> None:
    """Display visual task board from to-do.md file."""

    from aura_cli.cli.ui.todo_display import create_todo_panel
    from aura_cli.core.todo.todo_tracker import TodoTracker

    console = Console()

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

    console = Console()
    session_state = get_session_state().get_current_state()
    pages = notebook_service.list_pages()
    total_pages = len(pages)

    info = (
        f"[{UIStyles.TITLE}]Status do Notebook[/]\n\n"
        f"Total de páginas: {total_pages}\n"
        f"Caminho: {notebook_service.notebook_dir}\n"
    )

    if session_state:
        info += f"Sessão atual: {session_state.session_id}\n"

    panel = Panel(
        info,
        title=f"[{UIStyles.TITLE}]{UIIcons.AURA} Notebook[/]",
        border_style=UIStyles.BORDER_PRIMARY,
    )
    console.print(panel)
