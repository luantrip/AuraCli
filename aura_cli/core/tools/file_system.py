"""Basic I/O tools for file system interaction used by AGI and Ops agents."""

from __future__ import annotations

import contextlib
from datetime import datetime
from itertools import islice
import os
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING, Any, Optional

from rich.console import Console

from aura_cli.application.execution_feedback import (
    LoadingState,
    present_file_edit,
    show_tool_feedback,
)
from aura_cli.application.workspace.path_policy import resolve_workspace_path
from aura_cli.core.logger import get_logger

# NOTE: PrismManager is lazy-imported inside read_code_element
# so monkeypatch in tests can intercept it correctly.
from aura_cli.core.stats import get_stats
from aura_cli.core.tools import human_intervention_adapter
from aura_cli.core.ui import display_tool_call
from aura_cli.core.ui_bridge import UIIcons, UIStyles

if TYPE_CHECKING:
    pass  # Future type imports can go here

logger = get_logger(__name__)

AUTO_CONFIRM_TOOLS = False

_ALLOWED_BASE_DIR: Optional[Path] = None
_PATH_VALIDATION_ENABLED: bool = True


def set_allowed_base_dir(base_dir: Optional[str] = None) -> None:
    """Set the allowed base directory for file operations (None → cwd)."""
    global _ALLOWED_BASE_DIR
    if base_dir is None:
        _ALLOWED_BASE_DIR = Path.cwd().resolve()
    else:
        _ALLOWED_BASE_DIR = Path(base_dir).resolve()


def get_allowed_base_dir() -> Path:
    """Get the current allowed base directory."""
    global _ALLOWED_BASE_DIR
    if _ALLOWED_BASE_DIR is None:
        _ALLOWED_BASE_DIR = Path.cwd().resolve()
    return _ALLOWED_BASE_DIR


def enable_path_validation(enabled: bool = True) -> None:
    """Enable or disable path validation.

    This is primarily for testing purposes. In production, path validation
    should always be enabled.

    Args:
        enabled: Whether to enable path validation.
    """
    global _PATH_VALIDATION_ENABLED
    _PATH_VALIDATION_ENABLED = enabled


def _sanitize_path(path: str, base_dir: Optional[Path] = None) -> Path:
    """Sanitize and validate a file path to prevent path traversal attacks.

    This function ensures that the resolved path stays within the allowed
    base directory, preventing access to files outside the project scope.

    Args:
        path: The path to sanitize (can be relative or absolute).
        base_dir: Base directory to validate against. If None, uses allowed base dir.

    Returns:
        Resolved Path object that is guaranteed to be within base_dir.

    Raises:
        ValueError: If the path attempts to traverse outside the base directory.
        ValueError: If the path contains null bytes or other invalid characters.
    """
    if base_dir is None:
        base_dir = get_allowed_base_dir()
    return resolve_workspace_path(
        path,
        base_dir,
        validation_enabled=_PATH_VALIDATION_ENABLED,
    )


def is_path_safe(path: str, base_dir: Optional[Path] = None) -> bool:
    """Check if a path is safe (within allowed directory).

    Args:
        path: Path to check.
        base_dir: Base directory to validate against.

    Returns:
        True if path is safe, False otherwise.
    """
    try:
        _sanitize_path(path, base_dir)
        return True
    except ValueError:
        return False


def read_code_element(file_path: str, name: str, kind: Optional[str] = None) -> str:
    """Read a specific code element (function or class) using semantic analysis."""
    display_tool_call(
        "read_code_element", {"file": file_path, "name": name, "kind": kind}
    )

    try:
        safe_path = _sanitize_path(file_path)
    except ValueError as e:
        error_msg = f"Erro de segurança: {e}"
        logger.warning(
            "Path validation failed for read_code_element %s: %s", file_path, e
        )
        return error_msg

    if not safe_path.exists():
        return f"File not found: {file_path}"
    if not safe_path.is_file():
        return f"Error: '{file_path}' não é um arquivo."

    try:
        from aura_cli.core.memory.prism_bridge import PrismManager

        prism = PrismManager()
        if not prism.available:
            return "Prism não disponível. Use read_file com números de linha."

        chunks = prism.chunk_file(str(safe_path))

        matches = []
        for chunk in chunks:
            if chunk.name == name:
                if kind and chunk.kind != kind:
                    continue
                matches.append(chunk)

        if not matches:
            return f"Element '{name}' not found in '{file_path}'."

        output = []
        for m in matches:
            output.append(
                f"### {m.kind} {m.name} (Linhas {m.start_line}-{m.end_line})\n"
            )
            output.append(m.content)

        stats = get_stats()
        stats.track_tool_usage("read_code_element")

        return "\n\n".join(output)

    except Exception as e:
        logger.error(f"Error reading code element: {e}", exc_info=True)
        return f"Erro: {e}"


def read_file(path: str, offset: int = 0, limit: int = -1) -> str:
    """Read a file (or partial range) and return its content as a string.

    Args:
        path: Path to the file (relative or absolute). Not a directory —
              use list_directory for that.
        offset: Starting line (0-indexed). Default 0.
        limit: Number of lines to read from offset. -1 reads to end of file.

    Hard cap at 1 MB; content above 64 KB shows a soft hint to use
    offset/limit for large files.
    """
    display_tool_call("read_file", {"path": path, "offset": offset, "limit": limit})
    stats = get_stats()
    stats.track_tool_usage("read_file")
    stats.increment_files_read(path)

    # Hard cap: reading more than 1 MB in one shot is rarely useful and
    # silently fills the context window.  The agent gets a notice and can
    # use offset/limit to fetch specific sections.
    _MAX_READ_BYTES = 1_048_576  # 1 MB
    _READ_WARNING_BYTES = 65_536  # 64 KB — show a soft hint above this size

    try:
        safe_path = _sanitize_path(path)

        # Check size before reading to decide whether to warn or truncate
        try:
            file_size = safe_path.stat().st_size
        except OSError:
            file_size = 0

        with open(safe_path, encoding="utf-8", errors="replace") as f:
            if offset == 0 and limit == -1:
                if file_size > _MAX_READ_BYTES:
                    # Read only up to the cap and inform the agent
                    raw = f.read(_MAX_READ_BYTES)
                    notice = (
                        f"\n\n[... file truncated: read {_MAX_READ_BYTES // 1024} KB "
                        f"of {file_size // 1024} KB total. "
                        "Use offset/limit parameters to read specific sections ...]"
                    )
                    return raw + notice
                content = f.read()
                if file_size > _READ_WARNING_BYTES:
                    logger.debug(
                        "read_file: large file read (%d KB) for %s — "
                        "consider using offset/limit",
                        file_size // 1024,
                        path,
                    )
                return content

            start = max(offset, 0)
            stop = start + limit if limit != -1 else None
            return "".join(islice(f, start, stop))

    except FileNotFoundError:
        error_msg = f"Error: File '{path}' not found."
        logger.warning(f"File not found: {path}")
        error_style = UIStyles.safe_style("ERROR", "red")
        Console().print(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except PermissionError:
        error_msg = f"Erro: Sem permissão para ler o arquivo '{path}'."
        logger.warning(f"Permissão negada ao ler: {path}")
        error_style = UIStyles.safe_style("ERROR", "red")
        Console().print(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except IsADirectoryError:
        error_msg = (
            f"Error: '{path}' é um diretório, não um arquivo. "
            "Use list_directory(path) para listar o conteúdo."
        )
        logger.warning(f"Attempt to read directory as file: {path}")
        error_style = UIStyles.safe_style("ERROR", "red")
        Console().print(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except UnicodeDecodeError as e:
        error_msg = f"Error: File '{path}' não é um arquivo de texto válido (erro de encoding)."
        logger.warning(f"Erro de encoding ao ler {path}: {e}")
        error_style = UIStyles.safe_style("ERROR", "red")
        Console().print(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except ValueError as e:
        error_msg = f"Erro de segurança: {e}"
        logger.warning(f"Path validation failed for {path}: {e}")
        error_style = UIStyles.safe_style("ERROR", "red")
        Console().print(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except OSError as e:
        error_msg = f"Erro de sistema ao ler o arquivo '{path}': {e}"
        logger.error(f"System error reading file {path}: {e}", exc_info=True)
        error_style = UIStyles.safe_style("ERROR", "red")
        Console().print(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def _write_error(loading: Any, console: Any, error_msg: str) -> str:
    """Display a write error and return the error message string."""
    if loading:
        loading.error(error_msg)
    error_style = UIStyles.safe_style("ERROR", "red")
    console.print(f"[{error_style}]{error_msg}[/{error_style}]")
    return error_msg


def write_file(path: str, content: str, append: bool = False) -> str:
    """Write or append content to a file, requesting user confirmation first.

    Args:
        path: File path (relative or absolute). Parent directory must exist.
        content: Content to write (UTF-8).
        append: If True, appends to the existing file. If False (default),
                overwrites. Creates the file if it does not exist.

    Returns a success or error message string. Confirmation is skipped when
    AUTO_CONFIRM_TOOLS is enabled or skip_confirmations is active.
    """
    display_tool_call(
        "write_file", {"path": path, "content": content[:100] + "...", "append": append}
    )
    mode = "a" if append else "w"  # noqa: F841 — kept for action_desc below
    action_desc = "adicionar conteúdo ao" if append else "sobrescrever o"

    console = Console()
    warning_style = UIStyles.safe_style("WARNING", "yellow")
    console.print(
        f"\n[{warning_style}]{UIIcons.WARNING} {action_desc.capitalize()} arquivo:[/{warning_style}] [bold]{path}[/bold]"
    )
    console.print(
        f"[dim]Preview:[/dim] {content[:80]}{'...' if len(content) > 80 else ''}"
    )

    stats = get_stats()
    success_style = UIStyles.safe_style("SUCCESS", "green")
    confirmed = human_intervention_adapter.confirm_tool_execution_locally(
        "write_file",
        {"path": str(path), "content": content},
        fallback_message=f"Confirmar {action_desc} arquivo?",
        fallback_context=str(path) if path else None,
        console=console,
        force_auto_confirm=AUTO_CONFIRM_TOOLS,
        auto_confirm_message=(
            f"[{success_style}]{UIIcons.SUCCESS} "
            "Skip confirmations: Escrevendo arquivo automaticamente."
            f"[/{success_style}]"
        ),
    )

    if confirmed:
        loading = show_tool_feedback(console, "write_file", {"path": path})
        loading.update(LoadingState.EXECUTING, "Escrevendo...")

        try:
            safe_path = _sanitize_path(path)
            stats = get_stats()
            stats.track_tool_usage("write_file")

            # Create parent directories if they don't exist
            Path(safe_path).parent.mkdir(parents=True, exist_ok=True)

            file_exists = safe_path.exists()
            old_content = ""

            if file_exists:
                try:
                    with open(safe_path, encoding="utf-8") as f:
                        old_content = f.read()
                except (PermissionError, UnicodeDecodeError, OSError):
                    old_content = ""

            if append:
                # Append mode: not atomic by nature, but safe enough —
                # partial writes are recoverable since existing content is intact.
                with open(safe_path, "a", encoding="utf-8") as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
            else:
                # Overwrite: write to a temp file in the same directory, then
                # atomically rename so a crash mid-write never leaves a
                # partially-written (corrupt) file at the destination path.
                parent = safe_path.parent
                tmp_fd, tmp_name = tempfile.mkstemp(
                    prefix=f".{safe_path.name}.", suffix=".tmp", dir=parent
                )
                tmp_path = Path(tmp_name)
                try:
                    with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                        f.write(content)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp_path, safe_path)
                except Exception:
                    with contextlib.suppress(OSError):
                        tmp_path.unlink(missing_ok=True)
                    raise

            loading.update(LoadingState.FINALIZING, "Processando...")
            loading.complete()

            if file_exists:
                stats.increment_files_edited(path)
                if old_content and old_content != content:
                    present_file_edit(path, old_content, content, show_preview=True)
            else:
                stats.increment_files_created(path)

            action_desc = "adicionado a" if append else "escrito em"
            success_msg = f"Content {action_desc} '{path}' com sucesso. Arquivo {'updated' if append else 'created'}."
            success_style = UIStyles.safe_style("SUCCESS", "green")
            console.print(
                f"[{success_style}]{UIIcons.SUCCESS} Arquivo {'updated' if append else 'created'}[/{success_style}]"
            )
            return success_msg
        except PermissionError:
            error_msg = f"Erro: Sem permissão para escrever no arquivo '{path}'."
            return _write_error(loading, console, error_msg)
        except IsADirectoryError:
            error_msg = f"Error: '{path}' é um diretório, não é possível escrever."
            return _write_error(loading, console, error_msg)
        except ValueError as e:
            error_msg = f"Erro de segurança: {e}"
            return _write_error(loading, console, error_msg)
        except OSError as e:
            error_msg = f"Erro de sistema ao {'adicionar a' if append else 'escrever no'} o arquivo '{path}': {e}"
            return _write_error(loading, console, error_msg)
    else:
        console = Console()
        warning_style = UIStyles.safe_style("WARNING", "yellow")
        console.print(
            f"[{warning_style}]Operação de escrita cancelada pelo usuário.[/{warning_style}]"
        )
        return "Operação de escrita cancelada pelo usuário."


def find_directory(directory_name: str, start_path: str | None = None) -> str:
    """Intelligently find a directory by searching recursively."""
    Console()
    base_dir = get_allowed_base_dir()
    raw_start = str(base_dir) if start_path is None else start_path

    try:
        search_root = _sanitize_path(raw_start)
    except ValueError as error:
        return f"Erro de segurança ao buscar diretório: {error}"

    common_paths = (
        search_root / directory_name,
        search_root / "aura_cli" / directory_name,
    )
    for common_path in common_paths:
        if common_path.is_dir():
            return str(common_path.relative_to(search_root))

    found_paths = []
    max_depth = 3
    try:
        for root, dirs, _files in os.walk(search_root):
            root_path = Path(root)
            depth = len(root_path.relative_to(search_root).parts)
            if depth > max_depth:
                dirs[:] = []
                continue

            if directory_name in dirs:
                found_path = root_path / directory_name
                found_paths.append(str(found_path.relative_to(search_root)))
    except OSError as error:
        return f"Error searching directory: {error}"

    if found_paths:
        return found_paths[0]
    return f"Directory '{directory_name}' not found (search up to {max_depth} levels)"


_CODE_EXTS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"}
_TEXT_EXTS = {".md", ".txt", ".rst"}
_CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".xml"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}
_DOC_EXTS = {".pdf", ".doc", ".docx"}


def _get_file_type_label(ext: str) -> str:
    if ext in _CODE_EXTS:
        return "[blue]Código[/blue]"
    if ext in _TEXT_EXTS:
        return "[green]Texto[/green]"
    if ext in _CONFIG_EXTS:
        return "[yellow]Config[/yellow]"
    if ext in _IMAGE_EXTS:
        return "[magenta]Imagem[/magenta]"
    if ext in _DOC_EXTS:
        return "[cyan]Documento[/cyan]"
    return "[dim]Arquivo[/dim]"


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"


def _find_similar_dirs(path: str) -> list:
    """Search up to 2 levels deep for matching directories in the workspace."""
    found = []
    base_dir = get_allowed_base_dir()
    for root, dirs, _ in os.walk(base_dir):
        root_path = Path(root)
        if len(root_path.relative_to(base_dir).parts) >= 2:
            dirs[:] = []
            continue
        if path in dirs:
            found.append(str((root_path / path).relative_to(base_dir)))
    return found


def _build_dir_entry_row(entry: Any) -> list:
    """Build a table row for a single directory entry."""
    try:
        stat = entry.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        if entry.is_dir():
            return [
                f"[bold cyan]📁 {entry.name}/[/bold cyan]",
                "",
                "[dim]Diretório[/dim]",
                f"[dim]{mod_time.split()[0]}[/dim]",
            ]
        size_str = _format_size(stat.st_size)
        file_type = _get_file_type_label(os.path.splitext(entry.name)[1].lower())
        return [
            f"[white]📄 {entry.name}[/white]",
            f"[dim]{size_str}[/dim]",
            file_type,
            f"[dim]{mod_time.split()[0]}[/dim]",
        ]
    except OSError:
        return [f"[red]{entry.name}[/red]", "N/A", "Erro de acesso", "N/A"]


def _dir_not_found_hint(path: str) -> str:
    """Return hint text for a missing directory."""
    if os.path.isabs(path):
        return ""
    found_paths = _find_similar_dirs(path)
    if found_paths:
        suggestions = "\n".join(f"  • {p}" for p in found_paths[:3])
        extra = (
            f"\n  ... e mais {len(found_paths) - 3} ocorrências"
            if len(found_paths) > 3
            else ""
        )
        return f"\n\n💡 Diretórios similares encontrados:\n{suggestions}{extra}\n\n💡 Dica: Liste o diretório atual primeiro com list_directory('.')"
    try:
        current_items = [
            d.name for d in os.scandir(get_allowed_base_dir()) if d.is_dir()
        ]
        if current_items:
            suggestions = ", ".join(current_items[:5])
            extra = (
                f" e mais {len(current_items) - 5}" if len(current_items) > 5 else ""
            )
            return f"\n\n💡 Diretórios disponíveis no diretório atual: {suggestions}{extra}"
    except Exception as _e:
        logger.debug(f"Ignorado: {_e}")
    return ""


def _handle_dir_not_found(path: str, console: Any) -> str:
    """Build error message for missing directory with suggestions."""
    error_msg = f"Erro: Directory '{path}' not found.{_dir_not_found_hint(path)}"
    console.print(f"[bold red]{error_msg}[/bold red]")
    return error_msg


def list_directory(path: str, show_hidden: bool = False) -> str:
    """List the contents of a directory within the allowed workspace."""
    try:
        p = _sanitize_path(path)
        if not p.exists():
            return f"Error: '{path}' not found."
        if not p.is_dir():
            return f"Error: '{path}' não é um diretório."

        entries = sorted(p.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        if not show_hidden:
            entries = [e for e in entries if not e.name.startswith(".")]

        if not entries:
            return f"Directory '{path}' está vazio."

        lines = [f"📁 {p}/"]
        for entry in entries:
            prefix = "📁" if entry.is_dir() else "📄"
            size = ""
            if entry.is_file():
                with contextlib.suppress(OSError):
                    size = f" ({_format_size(entry.stat().st_size)})"
            lines.append(f"  {prefix} {entry.name}{size}")
        return "\n".join(lines)
    except ValueError as e:
        return f"Erro de segurança: {e}"
    except PermissionError:
        return f"Erro: Sem permissão para acessar '{path}'."
    except OSError as e:
        return f"Error listing '{path}': {e}"
