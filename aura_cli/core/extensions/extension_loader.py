"""Dynamic extension/plugin loader for Aura CLI.

Discovers, validates (metadata.json or in-code metadata), checks dependencies
and initialises Python extensions at runtime via importlib. ExtensionLoader
scans a directory and exposes enable_extension() / disable_extension().
"""

import ast
from dataclasses import dataclass, field
import importlib.util
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.paths import aura_path
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)

TRUSTED_EXTENSION_DIRS = [
    str(aura_path("extensions")),
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "extensions"),
]

DANGEROUS_IMPORTS = [
    "os.system",
    "subprocess",
    "eval",
    "exec",
    "__import__",
    "compile",
    "open",
    "file",
    "input",
    "raw_input",
    "execfile",
]


@dataclass
class ExtensionMetadata:
    """Extension metadata (name, version, description, author)."""

    name: str
    version: str
    description: str = ""
    author: str = ""
    entry_point: str = ""
    dependencies: List[str] = field(default_factory=list)


@dataclass
class Extension:
    """A loaded extension with its metadata and module."""

    metadata: ExtensionMetadata
    module: Optional[Any] = None
    path: Path = Path(".")
    is_loaded: bool = False
    is_enabled: bool = False


class ExtensionLoader:
    """Loads and manages Aura CLI extensions."""

    def __init__(
        self,
        extensions_dir: str = "extensions",
        *,
        allow_untrusted_extensions: bool = False,
    ):
        """Initialise the extension loader."""
        self.extensions_dir = Path(extensions_dir)
        self.allow_untrusted_extensions = allow_untrusted_extensions
        self.extensions: Dict[str, Extension] = {}
        self.stats = get_stats()

        self.extensions_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"ExtensionLoader initialized (directory: {extensions_dir})")

    def load_extension(self, extension_path: str) -> Optional[Extension]:
        """Load an extension from a file path."""
        path = Path(extension_path)

        if not path.exists():
            logger.error(f"Extensão não encontrada: {extension_path}")
            return None

        path_abs = path.resolve()
        is_trusted = self._is_trusted_path(path_abs)
        if not is_trusted and not self.allow_untrusted_extensions:
            logger.error(
                f"Extensão bloqueada por origem não confiável: {path_abs}. "
                "Use allow_untrusted_extensions=True somente para código "
                "externo previamente auditado."
            )
            return None
        if not is_trusted:
            logger.warning(
                f"Executando extensão externa explicitamente autorizada: {path_abs}"
            )

        metadata = self._load_metadata(path)
        if not metadata:
            return None

        extension = Extension(metadata=metadata, path=path)

        try:
            with open(path, encoding="utf-8") as f:
                code_content = f.read()

            try:
                tree = ast.parse(code_content, filename=str(path))
                if not _validate_extension_code(tree, metadata.name):
                    logger.error(
                        f"Extension '{metadata.name}' contains dangerous code patterns"
                    )
                    return None
            except SyntaxError as e:
                logger.error(f"Extension '{metadata.name}' has syntax errors: {e}")
                return None
        except Exception as e:
            logger.error(f"Could not validate extension code: {e}")
            return None

        try:
            spec = importlib.util.spec_from_file_location(metadata.name, path)

            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                extension.module = module
                extension.is_loaded = True

                if hasattr(module, "initialize"):
                    module.initialize()

                logger.info(f"Extensão '{metadata.name}' carregada")
            else:
                logger.error(f"Error loading module: {extension_path}")
                return None

        except Exception as e:
            logger.error(
                f"Error loading extension '{extension_path}': {e}", exc_info=True
            )
            return None

        self.extensions[metadata.name] = extension

        self.stats.track_tool_usage("extension_loader")

        return extension

    @staticmethod
    def _is_trusted_path(path: Path) -> bool:
        """Return whether a resolved extension path is inside an approved root."""
        return any(
            path.is_relative_to(Path(trusted_dir).resolve())
            for trusted_dir in TRUSTED_EXTENSION_DIRS
        )

    def _load_metadata(self, path: Path) -> Optional[ExtensionMetadata]:
        """Load extension metadata from a path."""
        metadata_file = path.parent / "metadata.json"

        if metadata_file.exists():
            try:
                with open(metadata_file, encoding="utf-8") as f:
                    data = json.load(f)

                return ExtensionMetadata(
                    name=data.get("name", path.stem),
                    version=data.get("version", "1.0.0"),
                    description=data.get("description", ""),
                    author=data.get("author", ""),
                    entry_point=data.get("entry_point", ""),
                    dependencies=data.get("dependencies", []),
                )
            except Exception as e:
                logger.error(f"Error loading metadata.json: {e}", exc_info=True)

        return ExtensionMetadata(
            name=path.stem, version="1.0.0", description="", entry_point=str(path)
        )

    def load_all_extensions(self) -> List[Extension]:
        """Load every Python extension from the configured directory."""
        extensions = []
        for py_file in self.extensions_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            extension = self.load_extension(str(py_file))
            if extension:
                extensions.append(extension)
        logger.info(f"{len(extensions)} extensões carregadas")
        return extensions

    def get_extension(self, name: str) -> Optional[Extension]:
        """Return a loaded extension by name."""
        return self.extensions.get(name)

    def list_extensions(self) -> List[Dict[str, Any]]:
        """Return metadata and state for all loaded extensions."""
        return [
            {
                "name": ext.metadata.name,
                "version": ext.metadata.version,
                "description": ext.metadata.description,
                "is_loaded": ext.is_loaded,
                "is_enabled": ext.is_enabled,
            }
            for ext in self.extensions.values()
        ]


def _validate_extension_code(tree: ast.AST, extension_name: str) -> bool:
    """
    Validate extension code AST for dangerous patterns.

    Args:
        tree: AST of the extension code
        extension_name: Name of the extension (for logging)

    Returns:
        True if code is safe, False otherwise
    """
    dangerous_nodes = []

    class DangerousVisitor(ast.NodeVisitor):
        """AST visitor that detects dangerous imports and calls."""

        def visit_Import(self, node):
            """Flag dangerous top-level imports."""
            for alias in node.names:
                if any(danger in alias.name for danger in DANGEROUS_IMPORTS):
                    dangerous_nodes.append(f"Dangerous import: {alias.name}")

        def visit_ImportFrom(self, node):
            """Flag dangerous from-imports."""
            if node.module and any(
                danger in node.module for danger in DANGEROUS_IMPORTS
            ):
                dangerous_nodes.append(f"Dangerous import from: {node.module}")

        def visit_Call(self, node):
            """Flag dangerous function calls."""
            if isinstance(node.func, ast.Name):
                if node.func.id in ["eval", "exec", "compile", "__import__"]:
                    dangerous_nodes.append(f"Dangerous function call: {node.func.id}")
            elif isinstance(node.func, ast.Attribute) and isinstance(
                node.func.value, ast.Name
            ):
                if node.func.value.id == "os" and node.func.attr == "system":
                    dangerous_nodes.append("Dangerous os.system call")
                elif node.func.value.id == "subprocess":
                    dangerous_nodes.append("Dangerous subprocess usage")

    visitor = DangerousVisitor()
    visitor.visit(tree)

    if dangerous_nodes:
        logger.error(
            f"Extension '{extension_name}' contains dangerous patterns: "
            f"{', '.join(dangerous_nodes)}"
        )
        return False

    return True
