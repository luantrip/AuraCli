"""Project indexer for the /init command.

Generates a file tree, uses the LLM to identify key files, concurrently
summarises each file (with mtime-based cache), infers coding conventions
and produces a high-level architecture overview.

Outputs under .aura/:
  contexts/       — per-file summaries
  file_index.json — file hashes
  conventions.md  — inferred conventions
  overview.md     — architecture overview
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aura_cli.core.llm.model_utils import DEFAULT_GEMINI_MODEL
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

AURA_DIR = ".aura"
CONTEXTS_DIR = "contexts"
INDEX_FILE = "file_index.json"
CONVENTIONS_FILE = "conventions.md"
OVERVIEW_FILE = "overview.md"
PROJECT_INDEXER_DEFAULT_MODEL = DEFAULT_GEMINI_MODEL

ANALYZABLE_EXTENSIONS = {
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
    ".zsh",
    ".dockerfile",
    ".sql",
    ".graphql",
}

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
    "*.egg-info",
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
    "htmlcov",
}


class ProjectContextManager:
    """
    Manages project context, file summaries, and indexing.

    Maintains a cache of file summaries with MD5 hashes to avoid
    redundant analysis of unchanged files.

    Attributes:
        project_root: Root directory of the project
        aura_dir: Path to .aura directory
        contexts_dir: Path to contexts subdirectory
        index: Dictionary containing file index data
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the project context manager.

        Args:
            project_root: Root directory of the project (default: cwd)
        """
        if project_root is None:
            from aura_cli.core.tools.file_system import get_allowed_base_dir

            project_root = get_allowed_base_dir()
        self.project_root = Path(project_root).expanduser().resolve()
        from aura_cli.core.paths import ArtifactLayout

        self.aura_dir = ArtifactLayout(self.project_root).project()
        self.contexts_dir = self.aura_dir / CONTEXTS_DIR
        self.index_path = self.aura_dir / INDEX_FILE
        self.index: Dict[str, Any] = {}

        # Sentinel integration for fast change detection
        try:
            from aura_cli.core.context.sentinel_manager import SentinelManager

            self.sentinel = SentinelManager(self.project_root)
            self.changes = self.sentinel.scan_changes()
            if self.changes:
                logger.info(
                    f"Sentinel active: {len(self.changes.modified)} modified, "
                    f"{len(self.changes.added)} added"
                )
        except Exception as e:
            logger.warning(f"Sentinel initialization failed: {e}")
            self.sentinel = None  # type: ignore[assignment]
            self.changes = None

        self._ensure_dirs()
        self._load_index()

    def _ensure_dirs(self) -> None:
        """Create necessary directories."""
        self.aura_dir.mkdir(exist_ok=True)
        self.contexts_dir.mkdir(exist_ok=True)

    def _load_index(self) -> None:
        """Load file index from disk."""
        if self.index_path.exists():
            try:
                with open(self.index_path, encoding="utf-8") as f:
                    self.index = json.load(f)
                logger.info(
                    f"Index loaded: {len(self.index.get('files', {}))} files"
                )
            except Exception as e:
                logger.error(f"Error loading index: {e}")
                self.index = {"files": {}, "last_updated": None}
        else:
            self.index = {"files": {}, "last_updated": None}

    def _save_index(self) -> None:
        """Save file index to disk."""
        try:
            from datetime import datetime

            self.index["last_updated"] = datetime.now().isoformat()
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(self.index, f, indent=2, ensure_ascii=False)
            logger.debug("Índice salvo")
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def _get_file_hash(self, file_path: Path) -> Optional[str]:
        """
        Calculate MD5 hash of file content.

        Args:
            file_path: Path to the file

        Returns:
            MD5 hash string or None on error
        """
        try:
            with open(file_path, "rb") as f:
                return hashlib.md5(f.read(), usedforsecurity=False).hexdigest()
        except Exception:
            return None

    def needs_update(self, file_path: str) -> bool:
        """
        Check if a file needs its context updated.

        Uses Sentinel if available, otherwise falls back to MD5 comparison.

        Args:
            file_path: Relative path to the file

        Returns:
            True if file needs update, False otherwise
        """
        if self.changes:
            if file_path in self.changes.modified or file_path in self.changes.added:
                return True

            files_index = self.index.get("files", {})
            return file_path not in files_index

        full_path = self.project_root / file_path
        if not full_path.exists():
            return False

        current_hash = self._get_file_hash(full_path)
        files_index = self.index.get("files", {})

        if file_path not in files_index:
            return True

        saved_hash = files_index[file_path].get("hash")
        return current_hash != saved_hash

    def get_context_file_path(self, file_path: str) -> Path:
        """
        Get the path to the context file for a given source file.

        Args:
            file_path: Relative path to the source file

        Returns:
            Path to the context file
        """
        safe_name = file_path.replace("/", "-@-").replace("\\", "-@-")
        return self.contexts_dir / f"{safe_name}.md"

    async def generate_file_summary(
        self,
        file_path: str,
        model: str,
        ui_callback: Optional[Callable[[str], None]] = None,
    ) -> Optional[str]:
        """
        Generate a summary for a file using LLM.

        Args:
            file_path: Relative path to the file
            model: LLM model to use
            ui_callback: Optional callback for UI feedback

        Returns:
            Generated summary or None on error
        """
        full_path = self.project_root / file_path

        try:
            with open(full_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None

        if len(content) > 100_000:
            logger.warning(f"File {file_path} too large, truncating")
            content = content[:100_000] + "\n\n[... conteúdo truncado ...]"

        prompt = f"""Analise este arquivo e forneça um resumo técnico conciso (máximo 300 palavras):

1. **Propósito:** O que este arquivo faz?
2. **Componentes:** Classes, funções ou módulos principais
3. **Dependências:** Imports e dependências importantes
4. **Padrões:** Padrões de código ou arquitetura utilizados
5. **Integração:** Como este arquivo se integra ao projeto

Arquivo: `{file_path}`

```
{content}
```
"""

        messages = [
            {
                "role": "system",
                "content": (
                    "Você é um analisador de código especializado. "
                    "Forneça resumos técnicos, concisos e úteis para desenvolvedores. "
                    "Use markdown para formatação."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        try:
            from aura_cli.core.llm.base import query_with_fallback

            response = query_with_fallback(model, messages, timeout=60.0)

            if response and response.choices:
                summary = response.choices[0].message.content

                context_file = self.get_context_file_path(file_path)
                context_file.parent.mkdir(parents=True, exist_ok=True)

                with open(context_file, "w", encoding="utf-8") as f:
                    f.write(f"# Analysis: {file_path}\n\n{summary}")

                self.index.setdefault("files", {})[file_path] = {
                    "hash": self._get_file_hash(full_path),
                    "context_file": str(context_file.relative_to(self.aura_dir)),
                    "summary_preview": summary[:200] if summary else "",
                }
                self._save_index()

                if ui_callback:
                    ui_callback(f"  ✓ {file_path}")

                return summary

        except Exception as e:
            logger.error(f"Error generating summary for {file_path}: {e}")
            if ui_callback:
                ui_callback(f"  ✗ {file_path}: {e}")

        return None

    def get_file_context(self, file_path: str) -> Optional[str]:
        """
        Get the stored context for a file.

        Args:
            file_path: Relative path to the file

        Returns:
            File context or None if not found
        """
        file_info = self.index.get("files", {}).get(file_path)
        if not file_info:
            return None

        context_file = self.aura_dir / file_info.get("context_file", "")
        if context_file.exists():
            try:
                return context_file.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def get_all_context(self) -> str:
        """
        Get all stored contexts concatenated.

        Returns:
            Combined context from all analyzed files
        """
        contexts = []
        for file_path, info in self.index.get("files", {}).items():
            context_file = self.aura_dir / info.get("context_file", "")
            if context_file.exists():
                try:
                    content = context_file.read_text(encoding="utf-8")
                    contexts.append(f"## {file_path}\n{content}")
                except Exception as _e:
                    logger.debug(f"Ignorado: {_e}")
        return "\n\n---\n\n".join(contexts)

    def get_indexed_files(self) -> List[str]:
        """
        Get list of all indexed files.

        Returns:
            List of file paths
        """
        return list(self.index.get("files", {}).keys())

    def clear_index(self) -> None:
        """Clear all indexed data."""
        self.index = {"files": {}, "last_updated": None}
        self._save_index()

        if self.contexts_dir.exists():
            for f in self.contexts_dir.glob("*.md"):
                try:
                    f.unlink()
                except Exception as _e:
                    logger.debug(f"Ignorado: {_e}")

        logger.info("Índice limpo")


def generate_file_tree(
    root: Path,
    max_depth: int = 4,
    prefix: str = "",
    is_last: bool = True,
    current_depth: int = 0,
) -> str:
    """
    Generate a text representation of the directory tree.

    Args:
        root: Root directory
        max_depth: Maximum depth to traverse
        prefix: Current prefix for formatting
        is_last: Whether this is the last item in parent
        current_depth: Current depth level

    Returns:
        Formatted tree string
    """
    if current_depth > max_depth:
        return ""

    if root.name in SKIP_DIRS or root.name.startswith("."):
        return ""

    connector = "└── " if is_last else "├── "
    result = (
        f"{prefix}{connector}{root.name}/\n" if current_depth > 0 else f"{root.name}/\n"
    )

    if not root.is_dir():
        return result

    try:
        items = sorted(root.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return result

    filtered_items = [
        item
        for item in items
        if item.name not in SKIP_DIRS
        and not item.name.startswith(".")
        and (item.is_dir() or item.suffix.lower() in ANALYZABLE_EXTENSIONS)
    ]

    if len(filtered_items) > 20:
        filtered_items = filtered_items[:20]
        result += f"{prefix}{'    ' if is_last else '│   '}... ({len(items) - 20} more items)\n"

    for i, item in enumerate(filtered_items):
        is_item_last = i == len(filtered_items) - 1
        new_prefix = prefix + ("    " if is_last else "│   ")

        if item.is_dir():
            result += generate_file_tree(
                item, max_depth, new_prefix, is_item_last, current_depth + 1
            )
        else:
            item_connector = "└── " if is_item_last else "├── "
            result += f"{new_prefix}{item_connector}{item.name}\n"

    return result


async def _identify_key_files(model, tree, max_files, ui_callback):
    """Ask LLM to identify key files from the project tree."""
    from aura_cli.core.llm.base import query_with_fallback

    if ui_callback:
        ui_callback("🔍 Identificando files-chave...")
    identify_prompt = (
        f"Analise esta árvore de files de um projeto de software.\n"
        f"Identifique os {max_files} files mais importantes para entender a arquitetura e funcionamento do projeto.\n\n"
        "Critérios de importância:\n"
        "1. Arquivos de entrada/configuração (main, config, settings)\n"
        "2. Definições de API/rotas\n"
        "3. Modelos de dados/schemas\n"
        "4. Serviços/lógica de negócio principais\n"
        "5. Arquivos de documentação importantes\n\n"
        "Retorne APENAS os caminhos dos files, um por linha, sem explicações.\n"
        "NÃO inclua diretórios, apenas files.\n\n"
        f"Árvore do projeto:\n```\n{tree}\n```\n"
    )
    messages = [
        {
            "role": "system",
            "content": "Você é um arquiteto de software experiente. Analise projetos e identifique files-chave.",
        },
        {"role": "user", "content": identify_prompt},
    ]
    response = query_with_fallback(model, messages, timeout=60.0)
    if not response or not response.choices:
        return []
    recommended = []
    for line in response.choices[0].message.content.strip().split("\n"):
        line = line.strip().lstrip("- ").lstrip("*").strip("`").strip()
        if line and os.path.isfile(line):
            recommended.append(line)
    return recommended


async def _generate_conventions(model, all_context, ctx_manager, ui_callback, results):
    """Generate and save project conventions."""
    from aura_cli.core.llm.base import query_with_fallback

    if not all_context:
        return
    if ui_callback:
        ui_callback("📐 Inferindo convenções do projeto...")
    conventions_prompt = (
        "Baseado nos resumos dos files analisados, infira as convenções de código deste projeto:\n\n"
        "1. **Padrões de Nomenclatura:** Como variáveis, funções, classes são nomeadas\n"
        "2. **Estrutura de Diretórios:** Organização do projeto\n"
        "3. **Padrões de Arquitetura:** MVC, Clean Architecture, etc.\n"
        "4. **Bibliotecas/Frameworks:** Principais tecnologias utilizadas\n"
        "5. **Estilo de Código:** Formatação, documentação, etc.\n"
        "6. **Padrões de Teste:** Se houver\n"
        "7. **Configuração:** Como o projeto é configurado\n\n"
        f"Contexto dos files analisados:\n{all_context[:50000]}\n"
    )
    messages = [
        {
            "role": "system",
            "content": "Você é um especialista em padrões de código e boas práticas.",
        },
        {"role": "user", "content": conventions_prompt},
    ]
    try:
        response = query_with_fallback(model, messages, timeout=90.0)
        if response and response.choices:
            conventions_content = (
                f"# Project Conventions\n\n{response.choices[0].message.content}"
            )
            (ctx_manager.aura_dir / CONVENTIONS_FILE).write_text(
                conventions_content, encoding="utf-8"
            )
            try:
                from aura_cli.core.memory.memory_service import get_memory_service

                memory_service = get_memory_service(ctx_manager.project_root)
                if memory_service.save_conventions(conventions_content):
                    logger.info("Convenções salvas no notebook (Nim)")
                else:
                    logger.warning("Failed to save conventions to notebook")
            except Exception as notebook_error:
                logger.warning(
                    f"Error saving conventions to notebook: {notebook_error}"
                )
            results["conventions_generated"] = True
            if ui_callback:
                ui_callback("  ✓ Convenções geradas")
    except Exception as e:
        logger.error(f"Error generating conventions: {e}")


async def _generate_overview(
    model, tree, all_context, ctx_manager, ui_callback, results
):
    """Generate and save project overview."""
    from aura_cli.core.llm.base import query_with_fallback

    if ui_callback:
        ui_callback("📖 Criando overview do projeto...")
    overview_prompt = (
        "Crie um overview de alto nível deste projeto de software:\n\n"
        "1. **Propósito:** O que o projeto faz\n"
        "2. **Arquitetura:** Estrutura principal e padrões\n"
        "3. **Componentes:** Módulos/pacotes principais e suas responsabilidades\n"
        "4. **Fluxo de Dados:** Como os dados fluem pelo sistema\n"
        "5. **Pontos de Extensão:** Onde e como o projeto pode ser estendido\n"
        "6. **Dependências Principais:** Bibliotecas e frameworks críticos\n\n"
        f"Árvore do projeto:\n```\n{tree[:5000]}\n```\n\n"
        f"Contexto dos files:\n{all_context[:30000]}\n"
    )
    messages = [
        {
            "role": "system",
            "content": "Você é um arquiteto de software técnico. Crie documentação clara e útil.",
        },
        {"role": "user", "content": overview_prompt},
    ]
    try:
        response = query_with_fallback(model, messages, timeout=90.0)
        if response and response.choices:
            overview_content = (
                f"# Overview do Projeto\n\n{response.choices[0].message.content}"
            )
            (ctx_manager.aura_dir / OVERVIEW_FILE).write_text(
                overview_content, encoding="utf-8"
            )
            try:
                from aura_cli.core.memory.memory_service import get_memory_service

                memory_service = get_memory_service(ctx_manager.project_root)
                saved = memory_service.notebook_manager.write_page(
                    "notebook", "overview.md", overview_content
                )
                if saved:
                    logger.info("Overview salvo no notebook (Nim)")
                else:
                    logger.warning("Failed to save overview to notebook")
            except Exception as notebook_error:
                logger.warning(f"Error saving overview to notebook: {notebook_error}")
            results["overview_generated"] = True
            if ui_callback:
                ui_callback("  ✓ Overview gerado")
    except Exception as e:
        logger.error(f"Error generating overview: {e}")


async def handle_init_command(
    model: str = PROJECT_INDEXER_DEFAULT_MODEL,
    ui_callback: Optional[Callable[[str], None]] = None,
    max_files: int = 15,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Handle the /init command to index the current project.

    Executes a multi-step project analysis:
    1. Generate file tree
    2. LLM identifies key files
    3. Generate file summaries concurrently
    4. Infer project conventions
    5. Create project overview

    Args:
        model: LLM model to use for analysis
        ui_callback: Optional callback for UI feedback
        max_files: Maximum number of files to analyze

    Returns:
        Dictionary with results and status
    """
    ctx_manager = ProjectContextManager(project_root)
    results: Dict[str, Any] = {
        "status": "success",
        "files_analyzed": 0,
        "files_skipped": 0,
        "conventions_generated": False,
        "overview_generated": False,
    }

    if ui_callback:
        ui_callback("📂 Gerando árvore de files...")

    tree = generate_file_tree(ctx_manager.project_root, max_depth=4)
    tree_lines = tree.split("\n")
    if len(tree_lines) > 100:
        tree = (
            "\n".join(tree_lines[:100]) + f"\n... ({len(tree_lines) - 100} more lines)"
        )

    try:
        recommended_files = await _identify_key_files(
            model, tree, max_files, ui_callback
        )
        if not recommended_files:
            if ui_callback:
                ui_callback("❌ Error identifying files")
            results["status"] = "error"
            results["error"] = "Failed to identify key files"
            return results
        if ui_callback:
            ui_callback(f"📋 {len(recommended_files)} files identificados")
    except Exception as e:
        logger.error(f"Error identifying files: {e}")
        if ui_callback:
            ui_callback(f"❌ Erro: {e}")
        results["status"] = "error"
        results["error"] = str(e)
        return results

    if ui_callback:
        ui_callback("📝 Gerando resumos dos files...")

    tasks = []
    for file_path in recommended_files[:max_files]:
        if ctx_manager.needs_update(file_path):
            tasks.append(
                ctx_manager.generate_file_summary(file_path, model, ui_callback)
            )
        else:
            results["files_skipped"] = results["files_skipped"] + 1
            if ui_callback:
                ui_callback(f"  ⏭ {file_path} (cache)")

    if tasks:
        summaries = await asyncio.gather(*tasks, return_exceptions=True)
        results["files_analyzed"] = sum(
            1 for s in summaries if s and not isinstance(s, Exception)
        )

    all_context = ctx_manager.get_all_context()
    await _generate_conventions(model, all_context, ctx_manager, ui_callback, results)
    await _generate_overview(
        model, tree, all_context, ctx_manager, ui_callback, results
    )
    return results


def get_project_context_manager() -> ProjectContextManager:
    """
    Get a ProjectContextManager instance for the current directory.

    Returns:
        ProjectContextManager instance
    """
    return ProjectContextManager()
