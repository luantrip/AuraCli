"""Long-term memory tools for the Aura CLI agent.

Exposes the notebook memory system (ler_pagina_caderno, ver_indice_caderno,
listar_paginas_caderno, informacoes_sessao) so the agent can retrieve context
from previous interactions across context-window boundaries.
"""

from aura_cli.core.logger import get_logger
from aura_cli.core.memory.notebook_service import notebook_service
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


def ler_pagina_caderno(caminho_pagina: str) -> str:
    """Read the content of a specific notebook page.

    Retrieves context snapshots saved when the context limit was reached.
    The path is provided in the system message when a snapshot is created.
    Use ver_indice_caderno() to browse summaries before reading full pages.

    Args:
        caminho_pagina: Full path to the page
            (e.g. ".aura/notebooks/20231201_143052/pagina_001.txt").

    Returns:
        Page content in Markdown (date, message count, USER/ASSISTANT history),
        or a descriptive error message.
    """
    from aura_cli.core.ui import display_tool_call

    display_tool_call("ler_pagina_caderno", {"caminho_pagina": caminho_pagina})

    stats = get_stats()
    stats.track_tool_usage("ler_pagina_caderno")

    try:
        content = notebook_service.read_page(caminho_pagina)

        if content.startswith("ERRO:"):
            logger.warning(f"Error reading page: {content}")
            return content

        logger.info(f"Page read: {caminho_pagina} ({len(content)} chars)")
        return content

    except Exception as e:
        error_msg = f"Error reading notebook page: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def listar_paginas_caderno() -> str:
    """List all available pages in the current session's notebook.

    Returns a formatted list with the session ID, total page count and
    file names. Use ver_indice_caderno() for summaries or
    ler_pagina_caderno() to read a full page.

    Returns:
        Formatted string with session info and page list, or an
        informative message if no pages exist yet.
    """
    from aura_cli.core.ui import display_tool_call

    display_tool_call("listar_paginas_caderno", {})

    stats = get_stats()
    stats.track_tool_usage("listar_paginas_caderno")

    try:
        pages = notebook_service.list_pages()
        session_info = notebook_service.get_session_info()

        if not pages:
            return (
                "📓 No pages found in the current session notebook.\n\n"
                f"Session: {notebook_service.session_id}\n"
                "Pages are created automatically when context exceeds 30 messages."
            )

        result = f"📓 Session Notebook: {notebook_service.session_id}\n"
        result += f"Directory: {notebook_service.session_path}\n"
        result += f"Total pages: {len(pages)}\n"

        if session_info.get("total_size_bytes"):
            size_kb = session_info["total_size_bytes"] / 1024
            result += f"Tamanho total: {size_kb:.1f} KB\n"

        result += "\n**Available pages:**\n"

        for page in sorted(pages):
            full_path = notebook_service.session_path / page
            result += f"- `{page}`"

            try:
                size = full_path.stat().st_size
                if size < 1024:
                    result += f" ({size} B)"
                else:
                    result += f" ({size / 1024:.1f} KB)"
            except Exception as _e:
                logger.debug(f"Ignorado: {_e}")

            result += "\n"

        result += "\n💡 Use `ler_pagina_caderno(path)` to view the content."
        result += "\n💡 Use `notebook_index()` to see page summaries."

        logger.info(f"Listed {len(pages)} notebook pages")
        return result

    except Exception as e:
        error_msg = f"Error listing pages: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def ver_indice_caderno() -> str:
    """Show the notebook index with summaries of all saved pages.

    Use before reading full pages to decide which one to consult.
    The index is updated automatically when new pages are created.

    Returns:
        Markdown index with number, filename, date and summary for each
        page, or an informative message if the notebook is empty.
    """
    from aura_cli.core.ui import display_tool_call

    display_tool_call("ver_indice_caderno", {})

    stats = get_stats()
    stats.track_tool_usage("ver_indice_caderno")

    try:
        index = notebook_service.read_index()

        if not index or index.strip() == "# Notebook Index":
            return (
                "# Notebook Index\n\n"
                "📓 No pages registered yet.\n\n"
                f"Session: {notebook_service.session_id}\n"
                "Pages will be created automatically when context "
                "exceeds 30 messages."
            )

        header = f"# 📓 Notebook - Session {notebook_service.session_id}\n\n"
        header += f"Directory: `{notebook_service.session_path}`\n\n"
        header += "---\n\n"

        if index.startswith("# Notebook Index"):
            index = index.replace("# Notebook Index", "", 1).strip()

        logger.info("Notebook index viewed")
        return header + index

    except Exception as e:
        error_msg = f"Error reading index: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def info_sessao_caderno() -> str:
    """Return metadata about the current notebook session.

    Useful for debugging or understanding available memory context.
    Reports session ID, directory, page count, total size and backend
    (Nim or Python fallback).

    Returns:
        Formatted string with session information.
    """
    from aura_cli.core.ui import display_tool_call

    display_tool_call("info_sessao_caderno", {})

    stats = get_stats()
    stats.track_tool_usage("info_sessao_caderno")

    try:
        info = notebook_service.get_session_info()

        result = "📊 **Notebook Session Information**\n\n"
        result += f"- **Session:** {notebook_service.session_id}\n"
        result += f"- **Directory:** `{notebook_service.session_path}`\n"
        result += f"- **Pages:** {info.get('page_count', 0)}\n"

        size_bytes = info.get("total_size_bytes", 0)
        if size_bytes < 1024:
            result += f"- **Tamanho:** {size_bytes} B\n"
        elif size_bytes < 1024 * 1024:
            result += f"- **Tamanho:** {size_bytes / 1024:.1f} KB\n"
        else:
            result += f"- **Tamanho:** {size_bytes / (1024 * 1024):.1f} MB\n"

        if notebook_service._lib is not None:
            result += "- **Backend:** Nim (alto desempenho)\n"
        else:
            result += "- **Backend:** Python (fallback)\n"

        result += f"- **Page counter:** {notebook_service.page_counter}\n"

        logger.info("Notebook session info retrieved")
        return result

    except Exception as e:
        error_msg = f"Error fetching session info: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def save_constitution(content: str, project_root: str = ".") -> str:
    """Save or update the project constitution file.

    Should be called by an agent at the end of a setup interview to
    persist agreed project rules. The constitution guides all future
    agent actions in this project.

    Args:
        content: Full formatted constitution content to save.
        project_root: Project root directory (default ".").

    Returns:
        Confirmation message indicating success or failure.
    """
    from pathlib import Path

    from aura_cli.core.memory.memory_service import get_memory_service
    from aura_cli.core.ui import display_tool_call

    display_tool_call("save_constitution", {"content": content[:100] + "..."})
    stats = get_stats()
    stats.track_tool_usage("save_constitution")

    try:
        memory = get_memory_service(Path(project_root))
        if memory.save_constitution(content):
            logger.info("Constitution saved successfully via tool.")
            return "Constitution saved successfully."
        else:
            logger.error("Failed to save constitution via tool.")
            return "Error: Failed to save the constitution."
    except Exception as e:
        logger.error(f"Error in save_constitution tool: {e}", exc_info=True)
        return f"Ocorreu um erro inesperado: {e}"
