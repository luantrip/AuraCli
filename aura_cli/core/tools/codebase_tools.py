"""Advanced codebase search and navigation tools for Aura CLI.

Covers: codebase_search (text/regex/symbol across files), view_repo_map
(hierarchical project structure), view_subdirectory, glob_search and
inspect_code_structure. Optimised for large codebases with result limits
and extension/directory filters.
"""

import fnmatch
import glob
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.tree import Tree

from aura_cli.core.context.graph_service import GraphService
from aura_cli.core.logger import get_logger
from aura_cli.core.memory.prism_bridge import PrismManager
from aura_cli.core.stats import get_stats
from aura_cli.core.ui import display_tool_call
from aura_cli.core.ui_bridge import UIIcons, UIStyles

logger = get_logger(__name__)
console = Console()


def inspect_code_structure(file_path: str, max_chunk_size: int = 2000) -> str:
    """Inspect the semantic structure of a code file using Prism."""
    display_tool_call("inspect_code_structure", {"file_path": file_path})

    if not os.path.exists(file_path):
        return f"File not found: {file_path}"

    try:
        prism = PrismManager()
        if not prism.available:
            return "Prism não disponível. Compile os módulos Nim e verifique 'nim_binary_path' em /settings."

        chunks = prism.chunk_file(file_path, max_chunk_size)

        if not chunks:
            return f"Nenhuma estrutura detectada em '{file_path}' (ou arquivo vazio)."

        # Format output for LLM consumption
        structure_info = []
        for chunk in chunks:
            # Filter only interesting chunks (skip generic blocks unless large)
            if chunk.kind in ["function", "class"] or len(chunk.content) > 100:
                structure_info.append(
                    {
                        "kind": chunk.kind,
                        "name": chunk.name or "(block)",
                        "lines": f"{chunk.start_line}-{chunk.end_line}",
                        "size_chars": len(chunk.content),
                    }
                )

        output = [f"Estrutura de '{file_path}':\n"]
        output.append(json.dumps(structure_info, indent=2))

        stats = get_stats()
        stats.track_tool_usage("inspect_code_structure")

        console.print(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
            f"Estrutura analisada: {len(structure_info)} definições[/{UIStyles.SUCCESS}]"
        )

        return "\n".join(output)

    except Exception as e:
        error_msg = f"Error inspecting structure: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def analyze_dependencies(file_path: str) -> str:
    """Analyse file dependencies using Nexus static analysis."""
    display_tool_call("analyze_dependencies", {"file_path": file_path})

    try:
        graph_service = GraphService()
        if not graph_service.available:
            return "Nexus (Dependency Graph) não disponível. Compile os módulos Nim e verifique 'nim_binary_path' em /settings."

        graph = graph_service.build_graph()
        if not graph:
            return "Failed to build dependency graph."

        dependencies = graph.get_dependencies(file_path)
        dependents = graph.get_dependents(file_path)

        output = [f"Análise de Dependências para '{file_path}':\n"]

        output.append(f"📥 Importa ({len(dependencies)}):")
        for dep in dependencies:
            output.append(f"  - {dep}")

        output.append(f"\n📤 Usado por ({len(dependents)}):")
        if dependents:
            for dep in dependents:
                output.append(f"  - {dep}")
        else:
            output.append("  (Nenhum arquivo depende deste)")

        stats = get_stats()
        stats.track_tool_usage("analyze_dependencies")

        console.print(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
            f"Dependências analisadas[/{UIStyles.SUCCESS}]"
        )

        return "\n".join(output)

    except Exception as e:
        error_msg = f"Error analyzing dependencies: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def codebase_search(
    query: str,
    path: str = ".",
    filters: Optional[Dict[str, Any]] = None,
    max_results: int = 50,
) -> str:
    """Fast text/regex/symbol search across multiple files in a directory.

    For single-file reading use read_file; for deep structural analysis use
    investigate_codebase; for directory listing use list_directory.

    Args:
        query: Search string or regex (e.g. "def authenticate", "class.*Service").
        path: Root directory for search. Default ".".
        filters: Optional dict with file_extensions, exclude_dirs,
                 case_sensitive (False), search_in_comments (True).
        max_results: Maximum results to return. Default 50.

    Returns formatted string with file path, line number and context for each match.
    """
    display_tool_call(
        "codebase_search", {"query": query, "path": path, "filters": filters}
    )

    filters = filters or {}
    file_extensions = filters.get("file_extensions")
    exclude_dirs = filters.get(
        "exclude_dirs", [".git", "__pycache__", "node_modules", ".venv"]
    )
    case_sensitive = filters.get("case_sensitive", False)
    search_in_comments = filters.get("search_in_comments", True)

    try:
        if case_sensitive:
            pattern = re.compile(query)
        else:
            pattern = re.compile(query, re.IGNORECASE)
    except re.error:
        escaped = re.escape(query)
        if case_sensitive:
            pattern = re.compile(escaped)
        else:
            pattern = re.compile(escaped, re.IGNORECASE)

    results = []
    count = 0

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if count >= max_results:
                break

            if file_extensions and not any(
                file.endswith(ext) for ext in file_extensions
            ):
                continue
            file_path = os.path.join(root, file)

            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if count >= max_results:
                            break

                        if pattern.search(line):
                            stripped = line.strip()
                            if not search_in_comments and stripped.startswith(
                                ("#", "//")
                            ):
                                continue
                            results.append(
                                {
                                    "file": file_path,
                                    "line": line_num,
                                    "content": line.rstrip(),
                                }
                            )
                            count += 1
            except (UnicodeDecodeError, PermissionError):
                continue

    if not results:
        return f"Nenhum resultado encontrado para '{query}'"

    output = [f"Encontrados {len(results)} resultados para '{query}':\n"]

    for result in results:
        output.append(f"{result['file']}:{result['line']}: {result['content']}")

    stats = get_stats()
    stats.track_tool_usage("codebase_search")

    console.print(
        f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
        f"Busca concluída: {len(results)} resultados[/{UIStyles.SUCCESS}]"
    )

    return "\n".join(output)


def view_repo_map(depth: int = 3, path: str = ".") -> str:
    """Returns a plain-text directory tree of the repository, similar to the `tree` command.
    Skips hidden dirs, node_modules, __pycache__, .venv, build, dist.
    Use this to get a structural overview before diving into specific files.

    Args:
        depth: Maximum directory depth to traverse (default: 3).
        path: Root directory to start from (default: current dir).
    """
    display_tool_call("view_repo_map", {"depth": depth, "path": path})

    tree = Tree(f"[{UIStyles.PRIMARY}]{path}[/{UIStyles.PRIMARY}]")

    def build_tree(dir_path: Path, tree_node: Tree, current_depth: int) -> None:
        """Build the directory tree recursively."""
        if current_depth >= depth:
            return

        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name))

            for item in items:
                if item.name.startswith(".") and item.name not in [".git"]:
                    continue

                if item.is_dir():
                    if item.name in [
                        "node_modules",
                        "__pycache__",
                        ".venv",
                        "venv",
                        "build",
                        "dist",
                    ]:
                        continue

                    dir_node = tree_node.add(
                        f"[{UIStyles.SECONDARY}]{UIIcons.DIR} {item.name}/[/{UIStyles.SECONDARY}]"
                    )
                    build_tree(item, dir_node, current_depth + 1)
                else:
                    tree_node.add(
                        f"[{UIStyles.MUTED}]{UIIcons.FILE} {item.name}[/{UIStyles.MUTED}]"
                    )
        except PermissionError as _e:
            logger.debug(f"Ignorado: {_e}")

    root_path = Path(path)
    build_tree(root_path, tree, 0)

    console.print(tree)

    stats = get_stats()
    stats.track_tool_usage("view_repo_map")

    # Build plain-text version for LLM consumption
    lines: list[str] = []

    def _collect(dir_path: Path, prefix: str, current_depth: int) -> None:
        if current_depth >= depth:
            return
        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name))
            for item in items:
                if item.name.startswith(".") and item.name not in [".git"]:
                    continue
                if item.is_dir() and item.name in {
                    "node_modules",
                    "__pycache__",
                    ".venv",
                    "venv",
                    "build",
                    "dist",
                }:
                    continue
                connector = "├── " if item != items[-1] else "└── "
                lines.append(
                    f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}"
                )
                if item.is_dir():
                    extension = "│   " if item != items[-1] else "    "
                    _collect(item, prefix + extension, current_depth + 1)
        except PermissionError:
            pass

    lines.append(f"{path}/")
    _collect(root_path, "", 0)
    return "\n".join(lines)


def view_subdirectory(path: str, max_depth: int = 2, show_files: bool = True) -> str:
    """Returns a plain-text directory tree for a specific subdirectory.
    Useful for exploring a module or package in detail without scanning the whole repo.

    Args:
        path: Path to the subdirectory to inspect.
        max_depth: Maximum depth to traverse (default: 2).
        show_files: If True, includes files; if False, shows only directories (default: True).
    """
    display_tool_call("view_subdirectory", {"path": path, "max_depth": max_depth})

    if not os.path.isdir(path):
        error_msg = f"Diretório '{path}' not found"
        console.print(f"[{UIStyles.ERROR}]{error_msg}[/{UIStyles.ERROR}]")
        return error_msg

    tree = Tree(f"[{UIStyles.PRIMARY}]{path}[/{UIStyles.PRIMARY}]")

    def build_subtree(dir_path: Path, tree_node: Tree, current_depth: int) -> None:
        """Build a subtree recursively."""
        if current_depth >= max_depth:
            return

        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name))

            for item in items:
                if item.is_dir():
                    dir_node = tree_node.add(
                        f"[{UIStyles.SECONDARY}]{UIIcons.DIR} {item.name}/[/{UIStyles.SECONDARY}]"
                    )
                    build_subtree(item, dir_node, current_depth + 1)
                elif show_files:
                    tree_node.add(
                        f"[{UIStyles.MUTED}]{UIIcons.FILE} {item.name}[/{UIStyles.MUTED}]"
                    )
        except PermissionError as _e:
            logger.debug(f"Ignorado: {_e}")

    root_path = Path(path)
    build_subtree(root_path, tree, 0)

    console.print(tree)

    stats = get_stats()
    stats.track_tool_usage("view_subdirectory")

    lines: list[str] = []

    def _collect(dir_path: Path, prefix: str, current_depth: int) -> None:
        if current_depth >= max_depth:
            return
        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name))
            for item in items:
                if not show_files and item.is_file():
                    continue
                connector = "├── " if item != items[-1] else "└── "
                lines.append(
                    f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}"
                )
                if item.is_dir():
                    extension = "│   " if item != items[-1] else "    "
                    _collect(item, prefix + extension, current_depth + 1)
        except PermissionError:
            pass

    lines.append(f"{path}/")
    _collect(root_path, "", 0)
    return "\n".join(lines)


def glob_search(
    pattern: str, path: str = ".", exclude: Optional[List[str]] = None
) -> str:
    """Finds files matching a glob pattern recursively. Faster than grep for locating files by name/extension.
    Examples: '**/*.py' finds all Python files, 'src/**/*.ts' finds TypeScript in src/.

    Args:
        pattern: Glob pattern to match (e.g. '**/*.py', '**/*test*.py').
        path: Root directory to search from (default: current dir).
        exclude: List of glob patterns to exclude from results.
    """
    display_tool_call("glob_search", {"pattern": pattern, "path": path})

    exclude = exclude or []

    matches = []
    for match in glob.glob(os.path.join(path, pattern), recursive=True):
        should_exclude = False
        for excl_pattern in exclude:
            if fnmatch.fnmatch(match, excl_pattern):
                should_exclude = True
                break

        if not should_exclude and os.path.isfile(match):
            matches.append(match)

    if not matches:
        return f"Nenhum arquivo encontrado para padrão '{pattern}'"

    output = [f"Encontrados {len(matches)} arquivos:\n"]
    for match in sorted(matches):
        output.append(f"  {match}")

    stats = get_stats()
    stats.track_tool_usage("glob_search")

    console.print(
        f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
        f"{len(matches)} arquivos encontrados[/{UIStyles.SUCCESS}]"
    )

    return "\n".join(output)


def advanced_grep_search(
    pattern: str, path: str = ".", options: Optional[Dict[str, Any]] = None
) -> str:
    """Searches file contents using a regex pattern with context lines, extension filters, and more.
    Prefer this over run_shell_command('grep ...') for structured, filtered code searches.

    Args:
        pattern: Regex pattern to search for.
        path: Root directory to search (default: current dir).
        options: Dict with optional keys:
            - file_extensions (list): e.g. ['.py', '.ts']
            - exclude_dirs (list): directories to skip
            - context_lines (int): lines of context around each match
            - case_sensitive (bool): default True
            - whole_word (bool): match whole words only
            - invert_match (bool): return lines that do NOT match

    Returns:
        Resultados formatados com contexto
    """
    display_tool_call(
        "advanced_grep_search", {"pattern": pattern, "path": path, "options": options}
    )

    options = options or {}
    file_extensions = options.get("file_extensions")
    exclude_dirs = options.get("exclude_dirs", [".git", "__pycache__", "node_modules"])
    context_lines = options.get("context_lines", 0)
    case_sensitive = options.get("case_sensitive", False)
    whole_word = options.get("whole_word", False)
    invert_match = options.get("invert_match", False)

    if whole_word:
        pattern = f"\\b{pattern}\\b"

    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
    except re.error as e:
        error_msg = f"Invalid regex pattern: {e}"
        console.print(f"[{UIStyles.ERROR}]{error_msg}[/{UIStyles.ERROR}]")
        return error_msg

    results = []

    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file_extensions and not any(
                file.endswith(ext) for ext in file_extensions
            ):
                continue
            file_path = os.path.join(root, file)

            try:
                with open(file_path, encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        match = regex.search(line)
                        should_match = bool(match) != invert_match

                        if should_match:
                            start_line = max(1, line_num - context_lines)
                            end_line = min(len(lines), line_num + context_lines)

                            context = []
                            for ctx_line_num in range(start_line, end_line + 1):
                                ctx_line = lines[ctx_line_num - 1]
                                marker = ">>>" if ctx_line_num == line_num else "   "
                                context.append(
                                    f"{marker} {ctx_line_num}: {ctx_line.rstrip()}"
                                )

                            results.append(
                                {
                                    "file": file_path,
                                    "line": line_num,
                                    "content": line.rstrip(),
                                    "context": "\n".join(context),
                                }
                            )
            except (UnicodeDecodeError, PermissionError):
                continue

    if not results:
        return f"Nenhum resultado encontrado para padrão '{pattern}'"

    output = [f"Encontrados {len(results)} resultados:\n"]

    for result in results:
        output.append(f"\n{result['file']}:{result['line']}")
        if context_lines > 0:
            output.append(str(result["context"]))
        else:
            output.append(f"  {result['content']}")

    stats = get_stats()
    stats.track_tool_usage("advanced_grep_search")

    console.print(
        f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
        f"{len(results)} resultados encontrados[/{UIStyles.SUCCESS}]"
    )

    return "\n".join(output)
