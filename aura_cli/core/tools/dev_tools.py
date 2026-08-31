"""Essential code development tools for the AGI agent.

Covers: safe file editing (edit_file), static/NLP code analysis,
advanced search (find_in_files, semantic_search_advanced), syntax
validation, duplicate detection, ML-based test generation, backup/restore,
directory tree visualisation, and code tokenisation.
"""

import ast
import contextlib
from io import StringIO
import json
import os
from pathlib import Path
import re
import shutil
from typing import Any, List, Optional

from rich import print as rprint
from rich.console import Console
from rich.tree import Tree

from aura_cli.application.execution_feedback import (
    LoadingState,
    present_file_edit,
    show_tool_feedback,
)
from aura_cli.core.cache import cache_result
from aura_cli.core.logger import get_logger

# NOTE: AgentTask, TestAgent, NLPAnalyzer, CodeTokenizer, Language,
#       SearchQuery, SemanticSearch, ForgeManager are lazy-imported inside
#       functions to avoid circular: dev_tools → refactoring → dev_tools
from aura_cli.core.stats import get_stats
from aura_cli.core.tools.human_intervention_adapter import (
    confirm_tool_execution_locally,
    request_local_confirmation,
)
from aura_cli.core.ui import display_tool_call
from aura_cli.core.ui_bridge import UIIcons, UIStyles

logger = get_logger(__name__)
console = Console()


def edit_file(path: str, old_content: str, new_content: str) -> str:
    """Edit a file by replacing old_content with new_content (first occurrence).

    Args:
        path: File to edit (relative or absolute).
        old_content: Exact string to replace (case-sensitive, including whitespace).
        new_content: Replacement string.

    Asks for user confirmation unless auto-confirm is active. Returns a
    success or error message string. Replaces only the first occurrence.
    """
    display_tool_call(
        "edit_file",
        {
            "path": path,
            "old_content": old_content[:50] + "...",
            "new_content": new_content[:50] + "...",
        },
    )

    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()

        if old_content not in content:
            error_msg = f"Error: Content to replace not found in '{path}'"
            error_style = UIStyles.safe_style("ERROR", "red")
            rprint(f"[{error_style}]{error_msg}[/{error_style}]")
            return error_msg

        new_file_content = content.replace(old_content, new_content, 1)

        warning_style = UIStyles.safe_style("WARNING", "yellow")
        rprint(
            f"\n[{warning_style}]{UIIcons.WARNING} Aura quer editar arquivo:[/{warning_style}] '{path}'"
        )
        warning_style = UIStyles.safe_style("WARNING", "yellow")
        muted_style = UIStyles.safe_style("MUTED", "dim white")
        rprint(f"[{warning_style}]Substituindo:[/{warning_style}]")
        rprint(f"[{muted_style}]{old_content[:100]}...[/{muted_style}]")
        rprint(f"[{warning_style}]Por:[/{warning_style}]")
        rprint(f"[{muted_style}]{new_content[:100]}...[/{muted_style}]")

        stats = get_stats()
        success_style = UIStyles.safe_style("SUCCESS", "green")
        confirm = confirm_tool_execution_locally(
            "edit_file",
            {"path": path, "old_content": old_content, "new_content": new_content},
            fallback_message="Confirmar edição do arquivo?",
            fallback_context=path,
            console=console,
            auto_confirm_message=(
                f"[{success_style}]{UIIcons.SUCCESS} "
                "Auto-run: Editando arquivo automaticamente."
                f"[/{success_style}]"
            ),
        )

        if confirm:
            try:
                loading = show_tool_feedback(console, "edit_file", {"path": path})
                loading.update(LoadingState.EXECUTING, "Editando...")
            except Exception:
                loading = None

            try:
                stats = get_stats()
                stats.track_tool_usage("edit_file")

                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_file_content)

                stats.increment_files_edited(path)

                if loading:
                    loading.update(LoadingState.FINALIZING, "Processando...")
                    loading.complete()

                with contextlib.suppress(Exception):
                    present_file_edit(path, old_content, new_content, show_preview=True)

                success_msg = (
                    f"Arquivo '{path}' editado com sucesso. Conteúdo atualizado."
                )
                success_style = UIStyles.safe_style("SUCCESS", "green")
                console.print(
                    f"[{success_style}]{UIIcons.SUCCESS} Arquivo editado[/{success_style}]"
                )
                return success_msg
            except Exception as e:
                if loading:
                    loading.error(str(e))
                error_msg = f"Error editing file '{path}': {e}"
                error_style = UIStyles.safe_style("ERROR", "red")
                console.print(f"[{error_style}]{error_msg}[/{error_style}]")
                return error_msg
        else:
            warning_style = UIStyles.safe_style("WARNING", "yellow")
            console.print(
                f"[{warning_style}]{UIIcons.CANCEL} Edição cancelada pelo usuário.[/{warning_style}]"
            )
            return "Edição cancelada pelo usuário."

    except FileNotFoundError:
        error_msg = f"Error: File '{path}' not found."
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except Exception as e:
        error_msg = f"Error editing file '{path}':"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        rprint(e)
        return f"{error_msg} {e}"


def find_in_files(
    pattern: str,
    path: str = ".",
    file_extensions: Optional[List[str]] = None,
    max_results: int = 50,
) -> str:
    """Search for a pattern across project files."""
    display_tool_call(
        "find_in_files",
        {"pattern": pattern, "path": path, "file_extensions": file_extensions},
    )

    try:
        results = []
        count = 0
        regex = re.compile(pattern)

        for root, dirs, files in os.walk(path):
            dirs[:] = [
                d
                for d in dirs
                if d
                not in {
                    ".git",
                    "__pycache__",
                    "node_modules",
                    ".venv",
                    "venv",
                    "build",
                    "dist",
                    ".pytest_cache",
                }
            ]

            for file in files:
                if file_extensions and not any(
                    file.endswith(ext) for ext in file_extensions
                ):
                    continue
                file_path = os.path.join(root, file)

                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                results.append(f"{file_path}:{line_num}:{line.strip()}")
                                count += 1

                                if count >= max_results:
                                    break
                except (UnicodeDecodeError, PermissionError):
                    continue

                if count >= max_results:
                    break

            if count >= max_results:
                break

        if results:
            output = "\n".join(results)
            if count >= max_results:
                output += f"\n\n... (limitado a {max_results} resultados)"

            success_style = UIStyles.safe_style("SUCCESS", "green")
            rprint(
                f"[{success_style}]{UIIcons.SUCCESS} Encontrados {len(results)} resultados para '{pattern}'[/{success_style}]"
            )
            return output
        else:
            msg = f"Nenhum resultado encontrado para '{pattern}' em '{path}'"
            warning_style = UIStyles.safe_style("WARNING", "yellow")
            rprint(f"[{warning_style}]{msg}[/{warning_style}]")
            return msg

    except Exception as e:
        error_msg = f"Error searching: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def tree_view(path: str = ".", max_depth: int = 3, show_hidden: bool = False) -> str:
    """Display a Linux-style directory tree."""
    display_tool_call(
        "tree_view", {"path": path, "max_depth": max_depth, "show_hidden": show_hidden}
    )

    IGNORE_DIRS = {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "build",
        "dist",
        ".pytest_cache",
        ".egg-info",
        ".mypy_cache",
        ".tox",
        "htmlcov",
        ".coverage",
    }

    def build_tree(dir_path: Path, tree: Tree, current_depth: int) -> None:
        """Build the directory tree recursively."""
        if current_depth > max_depth:
            return

        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))

            for item in items:
                if not show_hidden and item.name.startswith("."):
                    continue

                if item.is_dir() and item.name in IGNORE_DIRS:
                    continue

                if item.is_dir():
                    secondary_style = UIStyles.safe_style("SECONDARY", "blue")
                    branch = tree.add(
                        f"[bold {secondary_style}]:file_folder: {item.name}/[/bold {secondary_style}]"
                    )
                    build_tree(item, branch, current_depth + 1)
                else:
                    ext = item.suffix.lower()
                    if ext in {
                        ".py",
                        ".js",
                        ".ts",
                        ".java",
                        ".cpp",
                        ".c",
                        ".go",
                        ".rs",
                    }:
                        icon = ":page_facing_up:"
                    elif ext in {".md", ".txt", ".rst"}:
                        icon = ":page_with_curl:"
                    elif ext in {".json", ".yml", ".yaml", ".toml", ".xml"}:
                        icon = ":gear:"
                    elif ext in {".sh", ".bat", ".ps1"}:
                        icon = ":zap:"
                    else:
                        icon = ":page_facing_up:"

                    success_style = UIStyles.safe_style("SUCCESS", "green")
                    tree.add(f"[{success_style}]{icon} {item.name}[/{success_style}]")

        except PermissionError:
            error_style = UIStyles.safe_style("ERROR", "red")
            tree.add(f"[{error_style}]Permissão negada[/{error_style}]")

    try:
        root_path = Path(path)

        if not root_path.exists():
            error_msg = f"Error: Path '{path}' not found."
            error_style = UIStyles.safe_style("ERROR", "red")
            rprint(f"[{error_style}]{error_msg}[/{error_style}]")
            return error_msg

        title_style = UIStyles.safe_style("TITLE", "bold white")
        primary_style = UIStyles.safe_style("PRIMARY", "cyan")
        tree = Tree(
            f"[{title_style}]:file_folder: {root_path.absolute()}[/{title_style}]",
            guide_style=primary_style,
        )

        build_tree(root_path, tree, 1)

        string_io = StringIO()
        temp_console = Console(file=string_io, width=120)
        temp_console.print(tree)
        result = string_io.getvalue()

        console.print(tree)

        success_style = UIStyles.safe_style("SUCCESS", "green")
        rprint(
            f"[{success_style}]{UIIcons.SUCCESS} Árvore de diretórios gerada para '{path}'[/{success_style}]"
        )
        return result

    except Exception as e:
        error_msg = f"Error generating tree: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


@cache_result(ttl=1800)
def analyze_code(file_path: str) -> str:
    """Analyse code structure and return metrics."""
    display_tool_call("analyze_code", {"file_path": file_path})

    def _cached_analyze(path: str) -> str:
        """Return cached or freshly computed analysis for the given file path."""
        path_obj = Path(path)
        if not path_obj.exists():
            error_msg = f"Error: File '{path}' not found."
            error_style = UIStyles.safe_style("ERROR", "red")
            rprint(f"[{error_style}]{error_msg}[/{error_style}]")
            return error_msg

        if path_obj.is_dir():
            error_msg = f"Erro: '{path}' é um diretório, não um arquivo. Use 'list_directory' para listar diretórios ou especifique um arquivo específico."
            error_style = UIStyles.safe_style("ERROR", "red")
            rprint(f"[{error_style}]{error_msg}[/{error_style}]")
            return error_msg

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()

            ext = Path(path).suffix.lower()

            if ext == ".py":
                return _analyze_python(path, content)
            elif ext in {".js", ".ts", ".jsx", ".tsx"}:
                return _analyze_javascript(path, content)
            else:
                return _analyze_generic(path, content)

        except FileNotFoundError:
            error_msg = f"Error: File '{path}' not found."
            error_style = UIStyles.safe_style("ERROR", "red")
            rprint(f"[{error_style}]{error_msg}[/{error_style}]")
            return error_msg
        except IsADirectoryError:
            error_msg = f"Erro: '{path}' é um diretório, não um arquivo. Use 'list_directory' para explorar diretórios."
            error_style = UIStyles.safe_style("ERROR", "red")
            rprint(f"[{error_style}]{error_msg}[/{error_style}]")
            return error_msg
        except Exception as e:
            error_msg = f"Error analyzing file: {e}"
            error_style = UIStyles.safe_style("ERROR", "red")
            rprint(f"[{error_style}]{error_msg}[/{error_style}]")
            return error_msg

    return _cached_analyze(file_path)


def _format_item_list(
    icon: str, label: str, items: list, fmt_fn: Any, max_items: int = 10
) -> list:
    """Format a list of items with icon, label and truncation."""
    if not items:
        return []
    lines = [f"{icon} {label}:"]
    for item in items[:max_items]:
        lines.append(fmt_fn(item))
    if len(items) > max_items:
        lines.append(f"  ... e mais {len(items) - max_items}")
    lines.append("")
    return lines


def _analyze_python(file_path: str, content: str) -> str:
    """Detailed analysis of Python code."""
    try:
        tree = ast.parse(content)

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                classes.append(
                    {"name": node.name, "methods": methods, "line": node.lineno}
                )
            elif isinstance(node, ast.FunctionDef):
                if not any(
                    node in cls_node.body
                    for cls_node in ast.walk(tree)
                    if isinstance(cls_node, ast.ClassDef)
                ):
                    functions.append(
                        {
                            "name": node.name,
                            "args": [arg.arg for arg in node.args.args],
                            "line": node.lineno,
                        }
                    )
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                else:
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(
                            f"{module}.{alias.name}" if module else alias.name
                        )

        lines = content.split("\n")
        total_lines = len(lines)
        code_lines = len(
            [
                line
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
        )

        result = [
            f"[FILE] Análise de {file_path}",
            "",
            "[STATS] Estatísticas:",
            f"  * Total de linhas: {total_lines}",
            f"  * Linhas de código: {code_lines}",
            f"  * Classes: {len(classes)}",
            f"  * Funções: {len(functions)}",
            f"  * Imports: {len(imports)}",
            "",
        ]

        result.extend(
            _format_item_list(UIIcons.FILE, "Imports", imports, lambda i: f"  • {i}")
        )
        result.extend(
            _format_item_list(
                UIIcons.OPS,
                "Classes",
                classes,
                lambda c: f"  • {c['name']} (linha {c['line']})",
            )
        )
        result.extend(
            _format_item_list(
                UIIcons.RUN,
                "Funções",
                functions,
                lambda f: (
                    f"  • {f['name']}({', '.join(f['args'])}) (linha {f['line']})"
                ),
            )
        )

        output = "\n".join(result)
        success_style = UIStyles.safe_style("SUCCESS", "green")
        rprint(
            f"[{success_style}]{UIIcons.SUCCESS} Análise Python completa de '{file_path}'[/{success_style}]"
        )
        return output

    except SyntaxError as e:
        return f"Erro de sintaxe Python: {e}"


def _analyze_javascript(file_path: str, content: str) -> str:
    """Basic analysis of JavaScript/TypeScript."""
    lines = content.split("\n")

    import_pattern = re.compile(r"^import\s+.*\s+from\s+[\'\"](.+)[\'\"]")
    function_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)")
    class_pattern = re.compile(r"^\s*(?:export\s+)?class\s+(\w+)")
    const_func_pattern = re.compile(
        r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\("
    )

    imports = []
    functions = []
    classes = []

    for i, line in enumerate(lines, 1):
        if match := import_pattern.match(line):
            imports.append(match.group(1))
        elif match := function_pattern.match(line):
            functions.append((match.group(1), i))
        elif match := class_pattern.match(line):
            classes.append((match.group(1), i))
        elif match := const_func_pattern.match(line):
            functions.append((match.group(1), i))

    result = [
        f"{UIIcons.FILE} Análise de {file_path}",
        "",
        f"{UIIcons.STATS} Estatísticas:",
        f"  {UIIcons.BULLET} Total de linhas: {len(lines)}",
        f"  {UIIcons.BULLET} Imports: {len(imports)}",
        f"  {UIIcons.BULLET} Funções: {len(functions)}",
        f"  {UIIcons.BULLET} Classes: {len(classes)}",
        "",
    ]

    if imports:
        result.append(f"{UIIcons.FILE} Imports:")
        for imp in imports[:10]:
            result.append(f"  {UIIcons.BULLET} {imp}")
        if len(imports) > 10:
            result.append(f"  ... e mais {len(imports) - 10}")
        result.append("")

    if classes:
        result.append(f"{UIIcons.OPS} Classes:")
        for name, lineno in classes[:10]:
            result.append(f"  {UIIcons.BULLET} {name} (linha {lineno})")
        result.append("")

    if functions:
        result.append(f"{UIIcons.RUN} Funções:")
        for name, lineno in functions[:10]:
            result.append(f"  {UIIcons.BULLET} {name}() (linha {lineno})")
        if len(functions) > 10:
            result.append(f"  ... e mais {len(functions) - 10} funções")

    output = "\n".join(result)
    success_style = UIStyles.safe_style("SUCCESS", "green")
    rprint(
        f"[{success_style}]{UIIcons.SUCCESS} Análise JavaScript/TypeScript de '{file_path}'[/{success_style}]"
    )
    return output


def _analyze_generic(file_path: str, content: str) -> str:
    """Generic analysis for any file type."""
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    lines = content.split("\n")

    result = [
        f"{UIIcons.FILE} Análise de {file_path}",
        "",
        f"{UIIcons.STATS} Estatísticas:",
        f"  {UIIcons.BULLET} Total de linhas: {len(lines)}",
        f"  {UIIcons.BULLET} Tamanho: {len(content)} bytes",
        f"  {UIIcons.BULLET} Extensão: {Path(file_path).suffix}",
    ]

    output = "\n".join(result)
    success_style = UIStyles.safe_style("SUCCESS", "green")
    rprint(
        f"[{success_style}]{UIIcons.SUCCESS} Análise genérica de '{file_path}'[/{success_style}]"
    )
    return output


def backup_file(path: str) -> str:
    """Create a backup copy of a file."""
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIStyles

    display_tool_call("backup_file", {"path": path})

    try:
        from datetime import datetime

        source = Path(path)

        if not source.exists():
            error_msg = f"Error: File '{path}' not found."
            error_style = UIStyles.safe_style("ERROR", "red")
            rprint(f"[{error_style}]{error_msg}[/{error_style}]")
            return error_msg

        from aura_cli.core.paths import ArtifactLayout

        backup_dir = ArtifactLayout().project("backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source.stem}_{timestamp}{source.suffix}.bak"
        backup_path = backup_dir / backup_name

        shutil.copy2(source, backup_path)

        success_msg = f"Backup created: {backup_path}"
        success_style = UIStyles.safe_style("SUCCESS", "green")
        rprint(f"[{success_style}]{success_msg}[/{success_style}]")
        return str(backup_path)

    except Exception as e:
        error_msg = f"Error creating backup: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def restore_backup(original_path: str, backup_path: Optional[str] = None) -> str:
    """Restores a file from a previously created backup. Use after a failed edit to recover the original.

    Args:
        original_path: Path of the file to restore.
        backup_path: Path to a specific backup file (None = use the most recent backup).
    """
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call(
        "restore_backup", {"original_path": original_path, "backup_path": backup_path}
    )

    try:
        from aura_cli.core.paths import ArtifactLayout

        backup_dir = ArtifactLayout().project("backups")

        if not backup_dir.exists():
            error_msg = "Error: Backup directory not found."
            error_style = UIStyles.safe_style("ERROR", "red")
            rprint(f"[{error_style}]{error_msg}[/{error_style}]")
            return error_msg

        original = Path(original_path)

        if backup_path:
            backup = Path(backup_path)
        else:
            pattern = f"{original.stem}_*{original.suffix}.bak"
            backups = sorted(
                backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True
            )

            if not backups:
                error_msg = f"Erro: Nenhum backup encontrado para '{original_path}'"
                error_style = UIStyles.safe_style("ERROR", "red")
                rprint(f"[{error_style}]{error_msg}[/{error_style}]")
                return error_msg

            backup = backups[0]

        warning_style = UIStyles.safe_style("WARNING", "yellow")
        rprint(
            f"\n[{warning_style}]{UIIcons.WARNING} Restaurar backup?[/{warning_style}]"
        )
        rprint(f"[{warning_style}]Arquivo:[/{warning_style}] {original_path}")
        rprint(f"[{warning_style}]Backup:[/{warning_style}] {backup}")

        stats = get_stats()
        if stats.skip_confirmations:
            success_style = UIStyles.safe_style("SUCCESS", "green")
            console.print(
                f"[{success_style}]{UIIcons.SUCCESS} Auto-run: Restaurando backup automaticamente.[/{success_style}]"
            )
            confirm = True
        else:
            confirm = request_local_confirmation("Confirmar restauração do backup?")

        if confirm:
            try:
                loading = show_tool_feedback(
                    console, "restore_backup", {"original_path": original_path}
                )
            except Exception:
                loading = None
            if loading:
                loading.update(LoadingState.EXECUTING, "Restaurando...")

            try:
                shutil.copy2(backup, original)

                if loading:
                    loading.update(LoadingState.FINALIZING, "Processando...")
                    loading.complete()

                success_msg = f"Arquivo '{original_path}' restaurado de '{backup}'"
                success_style = UIStyles.safe_style("SUCCESS", "green")
                console.print(
                    f"[{success_style}]{UIIcons.SUCCESS} {success_msg}[/{success_style}]"
                )
                return success_msg
            except Exception as e:
                if loading:
                    loading.error(str(e))
                error_msg = f"Error restoring backup: {e}"
                error_style = UIStyles.safe_style("ERROR", "red")
                console.print(f"[{error_style}]{error_msg}[/{error_style}]")
                return error_msg
        else:
            warning_style = UIStyles.safe_style("WARNING", "yellow")
            console.print(
                f"[{warning_style}]{UIIcons.CANCEL} Restauração cancelada pelo usuário.[/{warning_style}]"
            )
            return "Restauração cancelada pelo usuário."

    except Exception as e:
        error_msg = f"Error restoring backup: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def verify_code_snippet(code: str, language: str = "python", fix: bool = True) -> str:
    """Verify a code snippet for correctness."""
    from aura_cli.core.quality.forge_bridge import ForgeManager
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("verify_code_snippet", {"language": language, "fix": fix})

    try:
        forge = ForgeManager()
        if not forge.available:
            return "Forge (Sandbox) não disponível. Compile os módulos Nim e verifique 'nim_binary_path' em /settings."

        result = forge.validate_and_fix(code, language, fix)

        stats = get_stats()
        stats.track_tool_usage("verify_code_snippet")

        if result.success:
            if result.code != code:
                console.print(
                    f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Código verificado e formatado.[/{UIStyles.SUCCESS}]"
                )
                return f"Código Verificado e Polido:\n\n{result.code}"
            else:
                console.print(
                    f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Código verificado (sem alterações).[/{UIStyles.SUCCESS}]"
                )
                return "Código válido."
        else:
            error_msg = "\n".join(result.errors)
            console.print(
                f"[{UIStyles.ERROR}]{UIIcons.ERROR} Erros encontrados no código.[/{UIStyles.ERROR}]"
            )
            return f"Erros de validação:\n{error_msg}"

    except Exception as e:
        logger.error(f"Error checking code: {e}", exc_info=True)
        return f"Erro interno ao verificar código: {e}"


def validate_syntax(content: str, language: str) -> str:
    """Validate syntax for a code snippet or file."""
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("validate_syntax", {"language": language})

    language = language.lower()

    try:
        if language == "python":
            ast.parse(content)
            success_style = UIStyles.safe_style("SUCCESS", "green")
            rprint(
                f"[{success_style}]{UIIcons.SUCCESS} Sintaxe Python válida[/{success_style}]"
            )
            return "OK"

        elif language == "json":
            json.loads(content)
            success_style = UIStyles.safe_style("SUCCESS", "green")
            rprint(
                f"[{success_style}]{UIIcons.SUCCESS} Sintaxe JSON válida[/{success_style}]"
            )
            return "OK"

        elif language in {"yaml", "yml"}:
            import yaml

            yaml.safe_load(content)
            success_style = UIStyles.safe_style("SUCCESS", "green")
            rprint(
                f"[{success_style}]{UIIcons.SUCCESS} Sintaxe YAML válida[/{success_style}]"
            )
            return "OK"

        else:
            msg = f"Linguagem '{language}' não suportada para validação"
            warning_style = UIStyles.safe_style("WARNING", "yellow")
            rprint(f"[{warning_style}]{msg}[/{warning_style}]")
            return msg

    except SyntaxError as e:
        error_msg = f"Erro de sintaxe {language.upper()}: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except json.JSONDecodeError as e:
        error_msg = f"Erro JSON: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
    except Exception as e:
        error_msg = f"Erro de validação: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def tokenize_code(code: str, language: Optional[str] = None) -> str:
    """Tokenise code using specialised HuggingFace models."""
    from aura_cli.core.code_analysis.tokenizer import CodeTokenizer, Language
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("tokenize_code", {"code_length": len(code), "language": language})

    try:
        lang_enum = None
        if language:
            lang_map = {
                "python": Language.PYTHON,
                "javascript": Language.JAVASCRIPT,
                "typescript": Language.TYPESCRIPT,
                "java": Language.JAVA,
                "cpp": Language.CPP,
                "c": Language.C,
                "go": Language.GO,
                "rust": Language.RUST,
            }
            lang_enum = lang_map.get(language.lower())

        tokenizer = CodeTokenizer(language=lang_enum)
        result = tokenizer.tokenize(code)
        analysis = tokenizer.analyze_tokens(result)

        output = [
            f"{UIIcons.FILE} Tokenização de Código",
            "",
            f"{UIIcons.STATS} Estatísticas:",
            f"  {UIIcons.BULLET} Total de tokens: {analysis['total_tokens']}",
            f"  {UIIcons.BULLET} Tokens únicos: {analysis['unique_tokens']}",
            f"  {UIIcons.BULLET} Linguagem: {result.language.value}",
            f"  {UIIcons.BULLET} Comprimento médio: {analysis['avg_token_length']:.2f}",
            f"  {UIIcons.BULLET} Keywords: {analysis.get('keywords', 0)}",
            f"  {UIIcons.BULLET} Identificadores: {analysis.get('identifiers', 0)}",
            f"  {UIIcons.BULLET} Operadores: {analysis.get('operators', 0)}",
        ]

        rprint(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Código tokenizado: {analysis['total_tokens']} tokens[/{UIStyles.SUCCESS}]"
        )
        return "\n".join(output)

    except Exception as e:
        error_msg = f"Error tokenizing code: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def analyze_code_nlp(file_path: str) -> str:
    """Analyse code using NLP and return insights."""
    from pathlib import Path

    from aura_cli.core.code_analysis.nlp_analyzer import NLPAnalyzer
    from aura_cli.core.tools.file_system import read_file
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("analyze_code_nlp", {"file_path": file_path})
    path_obj = Path(file_path)
    if not path_obj.exists():
        error_msg = f"Error: File '{file_path}' not found."
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg

    if path_obj.is_dir():
        error_msg = f"Erro: '{file_path}' é um diretório, não um arquivo. Use 'list_directory' para explorar diretórios ou 'codebase_search' para buscar no código."
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg

    try:
        content = read_file(file_path)

        nlp_analyzer = NLPAnalyzer()
        classification = nlp_analyzer.classify_code(content)
        summary = nlp_analyzer.summarize_code(content)

        output = [
            f"{UIIcons.FILE} Análise NLP de {file_path}",
            "",
            f"{UIIcons.AGENT} Classificação:",
            f"  {UIIcons.BULLET} Tipo de Função: {classification.function_type.value}",
            f"  {UIIcons.BULLET} Complexidade: {classification.complexity.value}",
            f"  {UIIcons.BULLET} Intenção: {classification.intent}",
            f"  {UIIcons.BULLET} Confiança: {classification.confidence:.2%}",
            "",
            f"{UIIcons.INFO} Resumo:",
            f"  {summary.summary}",
            "",
            f"{UIIcons.STATS} Pontos-chave:",
        ]

        for point in summary.key_points[:5]:
            output.append(f"  {UIIcons.BULLET} {point}")

        if summary.suggestions:
            output.append("")
            output.append(f"{UIIcons.WARNING} Sugestões:")
            for suggestion in summary.suggestions[:3]:
                output.append(f"  {UIIcons.BULLET} {suggestion}")

        rprint(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Análise NLP concluída para '{file_path}'[/{UIStyles.SUCCESS}]"
        )
        return "\n".join(output)

    except Exception as e:
        error_msg = f"Erro na análise NLP: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def classify_code(file_path: str) -> str:
    """Classifies a code file by type, language, and purpose using NLP analysis (e.g. "REST API handler", "data model", "utility").

    Args:
        file_path: Path to the source file to classify.
    """
    from aura_cli.core.code_analysis.nlp_analyzer import NLPAnalyzer
    from aura_cli.core.tools.file_system import read_file
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("classify_code", {"file_path": file_path})

    try:
        content = read_file(file_path)
        nlp_analyzer = NLPAnalyzer()
        classification = nlp_analyzer.classify_code(content)

        output = f"""Classificação de {file_path}:
  Tipo: {classification.function_type.value}
  Complexidade: {classification.complexity.value}
  Intenção: {classification.intent}
  Confiança: {classification.confidence:.2%}"""

        rprint(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Código classificado[/{UIStyles.SUCCESS}]"
        )
        return output

    except Exception as e:
        error_msg = f"Error classifying code: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def summarize_code(file_path: str) -> str:
    """Generates a natural-language summary of what a code file does, its main functions, and its role in the project.

    Args:
        file_path: Path to the source file to summarize.
    """
    from aura_cli.core.code_analysis.nlp_analyzer import NLPAnalyzer
    from aura_cli.core.tools.file_system import read_file
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("summarize_code", {"file_path": file_path})

    try:
        content = read_file(file_path)
        nlp_analyzer = NLPAnalyzer()
        summary = nlp_analyzer.summarize_code(content)

        output = [
            f"{UIIcons.INFO} Sumário de {file_path}:",
            "",
            summary.summary,
            "",
            f"{UIIcons.STATS} Pontos-chave:",
        ]

        for point in summary.key_points:
            output.append(f"  {UIIcons.BULLET} {point}")

        if summary.suggestions:
            output.append("")
            output.append(f"{UIIcons.WARNING} Sugestões:")
            for suggestion in summary.suggestions:
                output.append(f"  {UIIcons.BULLET} {suggestion}")

        rprint(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Código sumarizado[/{UIStyles.SUCCESS}]"
        )
        return "\n".join(output)

    except Exception as e:
        error_msg = f"Error summarizing code: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def find_duplicate_code(path: str = ".", similarity_threshold: float = 0.85) -> str:
    """Find duplicate code using semantic similarity."""
    import os

    from aura_cli.core.refactoring.semantic_similarity import SemanticSimilarityAnalyzer
    from aura_cli.core.tools.file_system import read_file
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call(
        "find_duplicate_code", {"path": path, "threshold": similarity_threshold}
    )

    try:
        snippets = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [
                d
                for d in dirs
                if d
                not in {
                    ".git",
                    "__pycache__",
                    "node_modules",
                    ".venv",
                    "venv",
                    "build",
                    "dist",
                }
            ]

            for file in files:
                if not file.endswith((".py", ".js", ".ts", ".java", ".cpp", ".c")):
                    continue

                file_path = os.path.join(root, file)
                try:
                    content = read_file(file_path)
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if line.strip().startswith(
                            ("def ", "class ", "function ", "const ")
                        ):
                            snippet = "\n".join(lines[i : i + 20])
                            snippets.append(
                                {"code": snippet, "file": file_path, "line": i + 1}
                            )
                except Exception:
                    continue

        if len(snippets) < 2:
            msg = "Poucos snippets para análise de duplicação"
            warning_style = UIStyles.safe_style("WARNING", "yellow")
            rprint(f"[{warning_style}]{msg}[/{warning_style}]")
            return msg

        analyzer = SemanticSimilarityAnalyzer(similarity_threshold=similarity_threshold)
        duplicates = analyzer.find_duplicate_code(snippets)

        if not duplicates:
            msg = f"Nenhum código duplicado encontrado (threshold: {similarity_threshold})"
            rprint(f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} {msg}[/{UIStyles.SUCCESS}]")
            return msg

        output = [
            f"{UIIcons.SEARCH} Código Duplicado Encontrado ({len(duplicates)} pares):",
            "",
        ]

        for dup in duplicates[:10]:  # Limita a 10
            output.append(
                f"  {UIIcons.BULLET} Similaridade: {dup.similarity_score:.2%}"
            )
            output.append(f"    Arquivo 1: {dup.file1}:{dup.line1}")
            output.append(f"    Arquivo 2: {dup.file2}:{dup.line2}")
            output.append("")

        if len(duplicates) > 10:
            output.append(f"  ... e mais {len(duplicates) - 10} pares")

        rprint(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Encontrados {len(duplicates)} pares duplicados[/{UIStyles.SUCCESS}]"
        )
        return "\n".join(output)

    except Exception as e:
        error_msg = f"Error searching for duplicate code: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def semantic_search_advanced(
    query: str, index_id: str = "codebase", top_k: int = 10
) -> str:
    """Advanced semantic search using HuggingFace embeddings."""
    from aura_cli.core.semantic.search import (
        SearchQuery,
        SemanticSearch,
    )
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("semantic_search_advanced", {"query": query, "top_k": top_k})
    try:
        search = SemanticSearch(index_id=index_id, use_code_embeddings=True)

        search_query = SearchQuery(query_text=query, top_k=top_k)

        results = search.search(search_query)

        if not results:
            msg = f"Nenhum resultado encontrado para '{query}'"
            warning_style = UIStyles.safe_style("WARNING", "yellow")
            rprint(f"[{warning_style}]{msg}[/{warning_style}]")
            return msg

        output = [
            f"{UIIcons.SEARCH} Busca Semântica: '{query}'",
            f"{UIIcons.SUCCESS} {len(results)} resultados encontrados:",
            "",
        ]

        for i, result in enumerate(results, 1):
            output.append(f"{i}. {result.doc_id} (score: {result.score:.2%})")
            output.append(f"   {result.content[:100]}...")
            output.append("")

        rprint(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Busca concluída: {len(results)} resultados[/{UIStyles.SUCCESS}]"
        )
        return "\n".join(output)

    except Exception as e:
        error_msg = f"Erro na busca semântica: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def generate_tests_ml(file_path: str) -> str:
    """Generate test cases using ML-based analysis."""
    from aura_cli.core.agents.agent_base import AgentTask
    from aura_cli.core.agents.specialized_agents.test_agent import TestAgent
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("generate_tests_ml", {"file_path": file_path})
    try:
        test_agent = TestAgent()
        task = AgentTask(
            id="generate_tests",
            description="Gerar testes",
            parameters={"type": "generate_tests", "file_path": file_path},
        )

        result = test_agent._handle_generate_tests(task)

        rprint(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Testes gerados para '{file_path}'[/{UIStyles.SUCCESS}]"
        )
        return result

    except Exception as e:
        error_msg = f"Error generating tests: {e}"
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def generate_ascii_art(
    prompt: str, width: int = 60, height: int = 15, mode: str = "auto"
) -> str:
    """Generate ASCII/ANSI art for visual elements in responses.

    Use this tool to create logos, icons, diagrams, or decorative ASCII art.

    Args:
        prompt: What to draw (e.g., "Aura CLI logo", "star icon")
        width: Canvas width (default 60)
        height: Canvas height (default 15)
        mode: auto/ascii/primitives/hybrid

    Returns:
        ASCII art string
    """
    try:
        from aura_cli.core.tools.ascii_art_tool import generate_ascii_art_sync

        return generate_ascii_art_sync(prompt, width, height, mode)
    except Exception as e:
        return f"[ASCII art unavailable: {e}]"
