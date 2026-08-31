"""
Nim Tools Integration - Wrappers for Aura's High-Performance Nim Engines.

This module provides Python interfaces for the compiled Nim binaries and libraries,
exposing them as standard Agent Tools.

Tools:
- Imagination: Ultra-fast filesystem scanner
- Notebook: Persistent long-term memory
- Monitor: Headless content browser for agents
- Nexus: Dependency graph builder
- Sentinel: Change detection system
- Forge: Code sandbox and sanitization
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.context.graph_service import GraphService
from aura_cli.core.context.imagination_manager import ImaginationManager
from aura_cli.core.context.monitor_manager import MonitorManager
from aura_cli.core.context.sentinel_manager import SentinelManager
from aura_cli.core.memory.notebook_service import get_notebook_service
from aura_cli.core.nim_runtime import (
    build_nim_error_payload,
    build_nim_success_payload,
)
from aura_cli.core.quality.forge_bridge import ForgeManager


def _truncate_scan_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Truncate the scan result to avoid exceeding the LLM context window."""
    if not isinstance(result, dict):
        return result
    truncated = {
        k: v for k, v in result.items() if k not in ("files", "relevant_pages")
    }
    files = result.get("files", [])
    if files:
        truncated["files_sample"] = [
            {
                "name": f.get("name", ""),
                "path": f.get("path", ""),
                "category": f.get("category", ""),
            }
            for f in files[:20]
        ]
        truncated["files_truncated"] = len(files) > 20
    return truncated


class NimToolBase:
    """Base class for Nim tool wrappers."""

    def _success(
        self, tool: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build a standardized success payload."""
        return build_nim_success_payload(tool, payload=payload)

    def _error(
        self,
        tool: str,
        message: str,
        code: str,
        *,
        details: Optional[Any] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a standardized error payload (legacy-compatible)."""
        return build_nim_error_payload(
            tool,
            message,
            code,
            details=details,
            payload=payload,
        )


class ImaginationTool(NimToolBase):
    """Wrapper for the Imagination Engine (Scanner)."""

    def scan_project(
        self,
        path: str = ".",
        context: Optional[str] = None,
        limit: int = 10,
        no_preview: bool = False,
    ) -> Dict[str, Any]:
        """
        Scan a directory structure quickly.

        Args:
            path: Directory to scan
            context: Optional keywords to filter relevance (separate by spaces)
            limit: Max results for context search
            no_preview: If True, skips generating file previews
        """
        tool_name = "imagination.scan_project"
        imagination = ImaginationManager(Path.cwd())
        if not imagination.available:
            return self._error(
                tool_name,
                imagination.last_error
                or "Imagination binary not found. Compile the Nim modules.",
                "binary_unavailable",
            )

        result = imagination.scan_project(
            path=path,
            context=context,
            limit=limit,
            no_preview=no_preview,
        )
        if result is None:
            return self._error(
                tool_name,
                imagination.last_error or "Failed to run Imagination.",
                "execution_failed",
                details={"path": path, "context": context, "limit": limit},
            )

        return self._success(tool_name, _truncate_scan_result(result))


class MonitorTool(NimToolBase):
    """Wrapper for the Monitor (Browser)."""

    def browse(self, url_or_path: str, render_mode: str = "text") -> Dict[str, Any]:
        """
        Fetch and render a URL or file.

        Args:
            url_or_path: URL (http/https) or local file path
            render_mode: 'text' (default) or 'json' (structured with links)
        """
        tool_name = "monitor.browse_content"
        monitor = MonitorManager(Path.cwd())
        if not monitor.available:
            return self._error(
                tool_name,
                monitor.last_error
                or "Monitor binary not found. Compile the Nim modules.",
                "binary_unavailable",
                details={"source": url_or_path},
                payload={"source": url_or_path, "render_mode": render_mode},
            )

        result = monitor.browse(url_or_path, render_mode)
        if result is None:
            return self._error(
                tool_name,
                monitor.last_error or f"Failed to access {url_or_path}",
                "execution_failed",
                payload={"source": url_or_path, "render_mode": render_mode},
            )
        return self._success(tool_name, result)


class NexusTool(NimToolBase):
    """Wrapper for Nexus (Dependency Graph) via GraphService bridge."""

    def analyze_dependencies(self, root_path: str = ".") -> Dict[str, Any]:
        """
        Build a dependency graph of the codebase.

        Args:
            root_path: Root directory to analyze
        """
        tool_name = "nexus.analyze_dependencies"
        graph_service = GraphService(Path(root_path))
        graph = graph_service.build_graph()
        if graph is None:
            return self._error(
                tool_name,
                graph_service.last_error
                or "Failed to build dependency graph with Nexus.",
                "execution_failed",
                details={"root_path": root_path},
            )

        return self._success(
            tool_name,
            {
                "root_path": root_path,
                "backend": graph_service.backend,
                "total_nodes": len(graph.nodes),
                # Limit to 30 nodes to avoid exceeding the LLM context window
                "nodes_sample": sorted(graph.nodes)[:30],
                "nodes_truncated": len(graph.nodes) > 30,
                # Top 15 most-depended-upon modules (names only, no lists)
                "most_connected": [
                    {"module": k, "dep_count": len(v)}
                    for k, v in sorted(
                        graph.dependencies.items(),
                        key=lambda x: len(x[1]),
                        reverse=True,
                    )[:15]
                ],
            },
        )


class SentinelTool(NimToolBase):
    """Wrapper for Sentinel (Change Detector) via SentinelManager bridge."""

    def detect_changes(self, root_path: str = ".") -> Dict[str, Any]:
        """
        Check for file changes since the last run.

        Args:
            root_path: Directory to monitor
        """
        tool_name = "sentinel.detect_changes"
        sentinel = SentinelManager(Path(root_path))
        if not sentinel.available:
            return self._error(
                tool_name,
                sentinel.last_error
                or "Sentinel binary not found. Compile the Nim modules.",
                "binary_unavailable",
                details={"root_path": root_path},
            )

        diff = sentinel.scan_changes()
        if diff is None:
            return self._error(
                tool_name,
                sentinel.last_error or "Sentinel failed to scan changes.",
                "execution_failed",
                details={"root_path": root_path},
            )
        return self._success(
            tool_name,
            {"root_path": root_path, **diff.to_dict()},
        )


class ForgeTool(NimToolBase):
    """Wrapper for Forge (Code Sandbox) via ForgeManager bridge."""

    def sanitize_code(
        self, code: str, language: str = "python", fix: bool = True
    ) -> Dict[str, Any]:
        """
        Lint and format code in a sandbox.

        Args:
            code: Source code string
            language: Programming language (currently python)
            fix: Whether to attempt auto-fixing
        """
        tool_name = "forge.sanitize_code"
        forge = ForgeManager()
        if not forge.available:
            return self._error(
                tool_name,
                forge.last_error
                or "Forge binary not found. Compile the Nim modules.",
                "binary_unavailable",
                details={"language": language, "fix": fix},
            )

        result = forge.validate_and_fix(code=code, language=language, fix=fix)
        payload = result.to_dict()
        if not result.success:
            return self._error(
                tool_name,
                result.errors[0] if result.errors else "Forge validation failed.",
                "validation_failed",
                details={"errors": result.errors, "logs": result.logs},
                payload=payload,
            )
        return self._success(tool_name, payload)


class NotebookTool(NimToolBase):
    """Wrapper for Notebook long-term memory service."""

    def write(self, content: str, summary: str = "") -> Dict[str, Any]:
        """Write a notebook page."""
        tool_name = "notebook.write"
        try:
            service = get_notebook_service()
            page_path = service.write_page(content, summary if summary else None)
            return self._success(
                tool_name,
                {
                    "page_path": page_path,
                    "summary": summary or None,
                },
            )
        except Exception as exc:
            return self._error(
                tool_name,
                f"Failed to write notebook page: {exc}",
                "runtime_error",
                details={"summary": summary or None},
            )

    def read(self, page_path: str) -> Dict[str, Any]:
        """Read a notebook page."""
        tool_name = "notebook.read"
        try:
            service = get_notebook_service()
            content = service.read_page(page_path)
            return self._success(
                tool_name,
                {
                    "page_path": page_path,
                    "content": content,
                },
            )
        except Exception as exc:
            return self._error(
                tool_name,
                f"Failed to read notebook page: {exc}",
                "runtime_error",
                payload={"page_path": page_path},
            )

    def list(self) -> Dict[str, Any]:
        """List notebook pages in the current session."""
        tool_name = "notebook.list"
        try:
            service = get_notebook_service()
            pages = service.list_pages()
            return self._success(
                tool_name,
                {
                    "pages": pages,
                    "total_pages": len(pages),
                },
            )
        except Exception as exc:
            return self._error(
                tool_name,
                f"Failed to list notebook pages: {exc}",
                "runtime_error",
            )

    def search(self, query: str) -> Dict[str, Any]:
        """Search notebook index for page references matching the query."""
        tool_name = "notebook.search"
        try:
            service = get_notebook_service()
            index = service.read_index()
            results: List[str] = []

            lowered_query = query.lower()
            for line in index.splitlines():
                if lowered_query in line.lower() and "- **Arquivo:**" in line:
                    try:
                        parts = line.split("`")
                        if len(parts) >= 2:
                            results.append(parts[1])
                    except Exception:
                        continue

            return self._success(
                tool_name,
                {
                    "query": query,
                    "results": results,
                    "total_results": len(results),
                },
            )
        except Exception as exc:
            return self._error(
                tool_name,
                f"Failed to search notebook index: {exc}",
                "runtime_error",
                payload={"query": query},
            )


# Helper functions to be exposed as Tools


def scan_project(path: str = ".", context: str = "", limit: int = 10) -> Dict[str, Any]:
    """
    Scans the project directory structure using the high-performance Imagination Engine.

    Args:
        path: Root path to scan (default: current directory)
        context: Optional keywords to filter results by relevance (e.g. "auth login")
        limit: Maximum number of relevant files to return when using context

    Returns:
        JSON object containing file tree, categories, and relevance scores.
    """
    tool = ImaginationTool()
    return tool.scan_project(path, context if context else None, limit)


def browse_content(url: str, mode: str = "text") -> Dict[str, Any]:
    """
    Fetches and renders content from a URL or local file using the Aura Monitor.
    Useful for reading documentation, checking external APIs, or reading local markdown/html files.

    Args:
        url: URL (http/https) or local file path
        mode: Output format - 'text' (rendered view) or 'json' (structured data with links)
    """
    tool = MonitorTool()
    return tool.browse(url, mode)


def analyze_dependencies(path: str = ".") -> Dict[str, Any]:
    """
    Analyzes codebase dependencies to build an import graph using Aura Nexus.
    Helps understand project structure and coupling.

    Args:
        path: Root path to analyze
    """
    tool = NexusTool()
    return tool.analyze_dependencies(path)


def check_file_changes(path: str = ".") -> Dict[str, Any]:
    """
    Detects modified, added, or deleted files since the last check using Aura Sentinel.
    Useful for incrementally processing changes.

    Args:
        path: Root path to monitor
    """
    tool = SentinelTool()
    return tool.detect_changes(path)


def sanitize_code(code: str, fix: bool = True) -> Dict[str, Any]:
    """
    Safe-checks, lints, and formats code using Aura Forge sandbox.
    Currently supports Python.

    Args:
        code: The source code to process
        fix: Whether to attempt automatic fixing (formatting, safe lint fixes)
    """
    tool = ForgeTool()
    return tool.sanitize_code(code, "python", fix)


def format_file(path: str) -> Dict[str, Any]:
    """
    Formats and lints a source file in-place using Aura Forge.
    Reads the file, applies formatting/linting fixes, and writes it back.
    Use this when asked to 'format', 'lint', 'clean' or 'organize' a file.

    Args:
        path: Path to the file to format
    """
    from aura_cli.core.tools.file_system import read_file as _read
    from aura_cli.core.tools.file_system import write_file as _write

    read_result = _read(path)
    if isinstance(read_result, dict) and read_result.get("error"):
        return read_result
    content = read_result if isinstance(read_result, str) else str(read_result)
    sanitize_result = sanitize_code(content, fix=True)
    if not isinstance(sanitize_result, dict):
        return {
            "ok": False,
            "path": path,
            "message": "Resposta inválida do Forge.",
            "details": sanitize_result,
        }
    if not sanitize_result.get("ok"):
        return {
            "ok": False,
            "path": path,
            "message": sanitize_result.get("error")
            or "Forge não conseguiu validar o arquivo.",
            "details": sanitize_result,
        }
    fixed_code = sanitize_result.get("code")
    if isinstance(fixed_code, str) and fixed_code != content:
        write_result = _write(path, fixed_code)
        if isinstance(write_result, dict) and write_result.get("error"):
            return {
                "ok": False,
                "path": path,
                "message": write_result["error"],
                "details": sanitize_result,
            }
        return {
            "ok": True,
            "path": path,
            "message": f"Arquivo {path} formatado com sucesso.",
            "changed": True,
        }
    return {
        "ok": True,
        "path": path,
        "message": f"Arquivo {path} verificado (sem alterações necessárias).",
        "changed": False,
        "details": sanitize_result,
    }


# Notebook tools are wrappers around the shared library service


def notebook_write(content: str, summary: str = "") -> Dict[str, Any]:
    """
    Writes a new page to the agent's persistent Notebook memory.
    Use this to save important context, plans, or research notes that should persist.

    Args:
        content: The detailed content to save
        summary: A one-line summary for the index

    Returns:
        Standardized payload with the saved page path.
    """
    tool = NotebookTool()
    return tool.write(content, summary)


def notebook_read(page_path: str) -> Dict[str, Any]:
    """Reads a previously saved Notebook page and returns its content. Use after notebook_list to retrieve stored context.

    Args:
        page_path: Path to the page file (as returned by notebook_write or notebook_list).
    """
    tool = NotebookTool()
    return tool.read(page_path)


def notebook_list() -> Dict[str, Any]:
    """
    Lists all pages in the current Notebook session.
    """
    tool = NotebookTool()
    return tool.list()


def notebook_search(query: str) -> Dict[str, Any]:
    """
    Searches the Notebook index (and potentially content) for keywords.
    Note: Currently performs a simple filter on the file list/index.
    """
    tool = NotebookTool()
    return tool.search(query)
