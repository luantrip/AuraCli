"""
Context Selector TUI for Aura CLI.

This module provides an interactive file selector for choosing
multiple files to add to the agent's context.

Features:
    - Browse directory tree
    - Select multiple files with checkboxes
    - Search/filter files
    - Preview file content
    - Aggregate selected files into context

Usage:
    >>> from aura_cli.tui.screens.context_selector import run_context_selector
    >>> selected_files = run_context_selector()

Integration:
    The /context command triggers this selector, allowing users
    to manually choose which files to provide as context.
"""

import os
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

# File extensions to include
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".swift",
    ".kt",
    ".scala",
    ".md",
    ".rst",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".sh",
    ".bash",
    ".sql",
    ".html",
    ".css",
    ".scss",
}

# Directories to skip
SKIP_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".nox",
    ".eggs",
    "dist",
    "build",
    ".venv",
    "venv",
    "env",
    ".env",
    ".idea",
    ".vscode",
    ".aura",
    "target",
    "out",
    "bin",
    "obj",
    "coverage",
    ".coverage",
}


def get_project_files(
    root: Path | None = None,
    max_files: int = 100,
    max_depth: int = 4,
) -> List[Path]:
    """
    Get list of project files for selection.

    Args:
        root: Root directory (default: cwd)
        max_files: Maximum number of files to return
        max_depth: Maximum directory depth to traverse

    Returns:
        List of file paths
    """
    root = root or Path.cwd()
    files = []  # type: ignore[var-annotated]

    def walk(path: Path, depth: int = 0):
        """Walk the directory tree and yield matching paths."""
        if depth > max_depth or len(files) >= max_files:
            return

        try:
            items = sorted(
                path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())
            )
        except PermissionError:
            return

        for item in items:
            if item.name in SKIP_DIRS or item.name.startswith("."):
                continue

            if item.is_dir():
                walk(item, depth + 1)
            elif (
                item.is_file()
                and item.suffix.lower() in CODE_EXTENSIONS
                and len(files) < max_files
            ):
                files.append(item)

    walk(root)
    return files


def run_context_selector(
    root: Path | None = None,
    max_files: int = 100,
) -> List[str]:
    """
    Run interactive context file selector.

    Uses terminal-based selection with checkboxes.

    Args:
        root: Root directory
        max_files: Maximum files to show

    Returns:
        List of selected file paths
    """
    console = Console()
    root = root or Path.cwd()

    # Get files
    console.print("[cyan]▷ Loading project files...[/cyan]")
    files = get_project_files(root, max_files)

    if not files:
        console.print("[yellow]No code files found.[/yellow]")
        return []

    # Convert to relative paths
    relative_files = []
    for f in files:
        try:
            rel = f.relative_to(root)
            relative_files.append(str(rel))
        except ValueError:
            relative_files.append(str(f))

    # Try to use prompt_toolkit for better selection
    try:
        from prompt_toolkit.shortcuts import checkboxlist_dialog
        from prompt_toolkit.styles import Style

        dialog_style = Style.from_dict(
            {
                "dialog": "bg:#000044",
                "dialog.body": "bg:#000022 #ffffff",
                "checkbox-list": "bg:#000022",
                "checkbox": "#ffffff",
                "checkbox-checked": "#00ff00 bold",
            }
        )

        # Build checkbox list
        values = [(f, f) for f in relative_files[:50]]  # Limit to 50 for UI

        console.print()
        console.print("[bold cyan]▷ Select files for context[/bold cyan]")
        console.print(
            f"[dim]({len(relative_files)} arquivos disponíveis, mostrando até 50)[/dim]"
        )
        console.print()

        result = checkboxlist_dialog(
            title="Seleção de Contexto",
            text="Use ESPAÇO para selecionar, ENTER para confirmar:",
            values=values,
            style=dialog_style,
        ).run()

        if result:
            return [str(root / f) for f in result]
        return []

    except ImportError:
        # Fallback to simple numbered selection
        return _simple_selector(console, root, relative_files)


def _parse_selection(selection: str, files: List[str]) -> List[str]:
    """Parse comma-separated numbers/ranges into file list."""
    selected = []  # type: ignore[var-annotated]
    for part in selection.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                selected.extend(
                    files[i - 1] for i in range(start, end + 1) if 1 <= i <= len(files)
                )
            except ValueError as _e:
                logger.debug(f"Ignorado: {_e}")
        else:
            try:
                i = int(part)
                if 1 <= i <= len(files):
                    selected.append(files[i - 1])
            except ValueError as _e:
                logger.debug(f"Ignorado: {_e}")
    return selected


def _simple_selector(
    console: Console,
    root: Path,
    files: List[str],
) -> List[str]:
    """
    Simple numbered file selector fallback.

    Args:
        console: Rich console
        root: Root directory
        files: List of relative file paths

    Returns:
        List of selected file paths
    """
    console.print()
    console.print("[bold cyan]▷ Files available for context:[/bold cyan]")
    console.print()

    # Show files in a table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Arquivo", style="white")
    table.add_column("Tamanho", style="dim", width=10)

    for i, f in enumerate(files[:30], 1):  # Limit display
        try:
            size = os.path.getsize(root / f)
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f}KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f}MB"
        except Exception:
            size_str = "?"

        table.add_row(str(i), f, size_str)

    if len(files) > 30:
        table.add_row("...", f"... e mais {len(files) - 30} arquivos", "")

    console.print(table)
    console.print()

    # Get selection
    console.print(
        "[bold]Digite os números dos arquivos separados por vírgula (ex: 1,3,5):[/bold]"
    )
    console.print("[dim]Ou 'all' para selecionar todos, 'q' para cancelar[/dim]")

    try:
        selection = input("> ").strip().lower()

        if selection == "q" or selection == "":
            return []
        if selection == "all":
            return [str(root / f) for f in files]
        return [str(root / f) for f in _parse_selection(selection, files)]

    except (EOFError, KeyboardInterrupt):
        return []


def aggregate_context(files: List[str], max_chars: int = 100000) -> str:
    """
    Aggregate selected files into a context string.

    Args:
        files: List of file paths
        max_chars: Maximum total characters

    Returns:
        Aggregated context string
    """
    context_parts = []
    total_chars = 0

    for file_path in files:
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Truncate if too large
            remaining = max_chars - total_chars
            if remaining <= 0:
                break

            if len(content) > remaining:
                content = content[:remaining] + "\n\n[... truncado ...]"

            # Format with XML-style tags
            rel_path = file_path
            try:
                rel_path = str(Path(file_path).relative_to(Path.cwd()))
            except ValueError as _e:
                logger.debug(f"Ignorado: {_e}")

            context_parts.append(f'<file path="{rel_path}">\n{content}\n</file>')
            total_chars += len(content)

        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")

    return "\n\n".join(context_parts)


def handle_context_command(conversation_history: List[dict]) -> int:
    """
    Handle the /context command.

    Runs the context selector and adds selected files to conversation history.

    Args:
        conversation_history: Current conversation history (will be modified)

    Returns:
        Number of files added to context
    """
    console = Console()

    try:
        selected_files = run_context_selector()

        if not selected_files:
            console.print("[yellow]No files selected.[/yellow]")
            return 0

        # Aggregate context
        console.print(f"[cyan]✎ Agregando {len(selected_files)} arquivo(s)...[/cyan]")
        context = aggregate_context(selected_files)

        if not context:
            console.print("[yellow]No content extracted from files.[/yellow]")
            return 0

        # Add to conversation history
        conversation_history.insert(
            0,
            {
                "role": "user",
                "content": f"[CONTEXTO DO PROJETO - {len(selected_files)} arquivos selecionados]\n\n{context}",
            },
        )

        console.print(
            f"[bold green]✔ {len(selected_files)} arquivo(s) adicionados ao contexto![/bold green]"
        )
        console.print(f"[dim]Total: {len(context):,} caracteres[/dim]")

        return len(selected_files)

    except Exception as e:
        logger.error(f"Erro no comando /context: {e}", exc_info=True)
        console.print(f"[red]Erro: {e}[/red]")
        return 0
