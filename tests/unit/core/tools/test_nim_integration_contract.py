"""Contract tests for Nim integration payloads."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeGraph:
    nodes: set
    dependencies: dict
    dependents: dict


@dataclass
class _FakeDiff:
    added: list
    modified: list
    deleted: list
    stats: dict

    def to_dict(self):
        return {
            "added": self.added,
            "modified": self.modified,
            "deleted": self.deleted,
            "stats": self.stats,
        }


@dataclass
class _FakeForgeResult:
    success: bool
    code: str
    errors: list
    logs: list

    def to_dict(self):
        return {
            "success": self.success,
            "code": self.code,
            "errors": self.errors,
            "logs": self.logs,
        }


def test_nexus_success_contract(monkeypatch):
    """Nexus payload should expose standardized success keys."""
    from aura_cli.core.tools import nim_integration

    class _GraphService:
        def __init__(self, _path):
            self.available = True
            self.last_error = None
            self.backend = "nim"

        def build_graph(self):
            return _FakeGraph(
                nodes={"a.py"},
                dependencies={"a.py": []},
                dependents={"a.py": []},
            )

    monkeypatch.setattr(nim_integration, "GraphService", _GraphService)

    result = nim_integration.analyze_dependencies(".")
    assert result["ok"] is True
    assert result["tool"] == "nexus.analyze_dependencies"
    assert result["backend"] == "nim"
    assert "nodes" in result or "nodes_sample" in result  # key may be truncated


def test_imagination_success_contract(monkeypatch):
    """Imagination payload should expose standardized success keys."""
    from aura_cli.core.tools import nim_integration

    class _ImaginationManager:
        def __init__(self, _path):
            self.available = True
            self.last_error = None

        def scan_project(self, path, context=None, limit=10, no_preview=False):
            return {
                "root_path": path,
                "total_files": 3,
                "context": context,
                "limit": limit,
                "no_preview": no_preview,
            }

    monkeypatch.setattr(nim_integration, "ImaginationManager", _ImaginationManager)

    result = nim_integration.scan_project("src", context="auth login", limit=7)
    assert result["ok"] is True
    assert result["tool"] == "imagination.scan_project"
    assert result["backend"] == "nim"
    assert result["root_path"] == "src"
    assert result["total_files"] == 3


def test_monitor_unavailable_contract(monkeypatch):
    """Monitor unavailable should return normalized error payload."""
    from aura_cli.core.tools import nim_integration

    class _MonitorManager:
        def __init__(self, _path):
            self.available = False
            self.last_error = "Monitor binary not found."

    monkeypatch.setattr(nim_integration, "MonitorManager", _MonitorManager)

    result = nim_integration.browse_content("https://example.com", mode="text")
    assert result["ok"] is False
    assert result["tool"] == "monitor.browse_content"
    assert result["error"] == "Monitor binary not found."
    assert result["error_code"] == "binary_unavailable"
    assert result["source"] == "https://example.com"


def test_nexus_unavailable_uses_python_fallback_contract(monkeypatch):
    """Nexus absence should succeed when the AST fallback returns a graph."""
    from aura_cli.core.tools import nim_integration

    class _GraphService:
        def __init__(self, _path):
            self.available = False
            self.last_error = "Nexus binary not found."
            self.backend = "python"

        def build_graph(self):
            return _FakeGraph(
                nodes={"a.py"},
                dependencies={"a.py": []},
                dependents={"a.py": []},
            )

    monkeypatch.setattr(nim_integration, "GraphService", _GraphService)

    result = nim_integration.analyze_dependencies(".")
    assert result["ok"] is True
    assert result["backend"] == "python"
    assert result["total_nodes"] == 1


def test_sentinel_success_contract(monkeypatch):
    """Sentinel payload should include standardized metadata."""
    from aura_cli.core.tools import nim_integration

    class _SentinelManager:
        def __init__(self, _path):
            self.available = True
            self.last_error = None

        def scan_changes(self):
            return _FakeDiff(
                added=["x.py"],
                modified=["y.py"],
                deleted=[],
                stats={"total": 2},
            )

    monkeypatch.setattr(nim_integration, "SentinelManager", _SentinelManager)

    result = nim_integration.check_file_changes(".")
    assert result["ok"] is True
    assert result["tool"] == "sentinel.detect_changes"
    assert result["added"] == ["x.py"]
    assert result["stats"]["total"] == 2


def test_forge_failure_contract(monkeypatch):
    """Forge failures should keep legacy fields and normalized error metadata."""
    from aura_cli.core.tools import nim_integration

    class _ForgeManager:
        def __init__(self):
            self.available = True
            self.last_error = None

        def validate_and_fix(self, code, language, fix):
            return _FakeForgeResult(
                success=False,
                code=code,
                errors=["lint failed"],
                logs=["line 1"],
            )

    monkeypatch.setattr(nim_integration, "ForgeManager", _ForgeManager)

    result = nim_integration.sanitize_code("print('x')", fix=True)
    assert result["ok"] is False
    assert result["error"] == "lint failed"
    assert result["error_code"] == "validation_failed"
    # Legacy compatibility
    assert result["success"] is False
    assert result["code"] == "print('x')"


# --- Notebook contract tests ---


class _FakeNotebookService:
    """Fake service for notebook contract tests."""

    def write_page(self, content, summary=None):
        return "/tmp/notebook/page_001.md"

    def read_page(self, page_path):
        return "page content here"

    def list_pages(self):
        return ["/tmp/notebook/page_001.md", "/tmp/notebook/page_002.md"]

    def read_index(self):
        return (
            "- **Arquivo:** `page_001.md` - summary one\n"
            "- **Arquivo:** `page_002.md` - summary two\n"
            "- unrelated line\n"
        )


def test_notebook_write_success_contract(monkeypatch):
    """notebook_write should return standardized payload with page_path."""
    from aura_cli.core.tools import nim_integration

    monkeypatch.setattr(
        nim_integration, "get_notebook_service", lambda: _FakeNotebookService()
    )

    result = nim_integration.notebook_write("test content", summary="test summary")
    assert result["ok"] is True
    assert result["tool"] == "notebook.write"
    assert result["backend"] == "nim"
    assert result["page_path"] == "/tmp/notebook/page_001.md"
    assert result["summary"] == "test summary"


def test_notebook_write_error_contract(monkeypatch):
    """notebook_write should return normalized error on failure."""
    from aura_cli.core.tools import nim_integration

    def _failing_service():
        raise RuntimeError("disk full")

    monkeypatch.setattr(nim_integration, "get_notebook_service", _failing_service)

    result = nim_integration.notebook_write("content")
    assert result["ok"] is False
    assert result["tool"] == "notebook.write"
    assert result["error_code"] == "runtime_error"
    assert "disk full" in result["error"]


def test_notebook_read_success_contract(monkeypatch):
    """notebook_read should return standardized payload with content."""
    from aura_cli.core.tools import nim_integration

    monkeypatch.setattr(
        nim_integration, "get_notebook_service", lambda: _FakeNotebookService()
    )

    result = nim_integration.notebook_read("page_001.md")
    assert result["ok"] is True
    assert result["tool"] == "notebook.read"
    assert result["content"] == "page content here"
    assert result["page_path"] == "page_001.md"


def test_notebook_list_success_contract(monkeypatch):
    """notebook_list should return standardized payload with pages list."""
    from aura_cli.core.tools import nim_integration

    monkeypatch.setattr(
        nim_integration, "get_notebook_service", lambda: _FakeNotebookService()
    )

    result = nim_integration.notebook_list()
    assert result["ok"] is True
    assert result["tool"] == "notebook.list"
    assert result["total_pages"] == 2
    assert len(result["pages"]) == 2


def test_notebook_search_success_contract(monkeypatch):
    """notebook_search should return matching page references."""
    from aura_cli.core.tools import nim_integration

    monkeypatch.setattr(
        nim_integration, "get_notebook_service", lambda: _FakeNotebookService()
    )

    result = nim_integration.notebook_search("summary one")
    assert result["ok"] is True
    assert result["tool"] == "notebook.search"
    assert result["total_results"] == 1
    assert "page_001.md" in result["results"]


def test_notebook_search_no_match_contract(monkeypatch):
    """notebook_search with no matches should return empty results."""
    from aura_cli.core.tools import nim_integration

    monkeypatch.setattr(
        nim_integration, "get_notebook_service", lambda: _FakeNotebookService()
    )

    result = nim_integration.notebook_search("nonexistent query xyz")
    assert result["ok"] is True
    assert result["tool"] == "notebook.search"
    assert result["total_results"] == 0
    assert result["results"] == []
