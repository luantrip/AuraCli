"""Contracts for manifest-backed lazy tool loading."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from aura_cli.core.llm.tool_schemas import create_tool_schemas
from aura_cli.core.service_registry import LazyTool, ServiceRegistry
from aura_cli.core.tool_manifest import TOOL_MANIFEST


def _schema(name: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": "Test tool",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    }


def test_manifest_names_are_unique_and_resolvable() -> None:
    names = [entry["name"] for entry in TOOL_MANIFEST]

    assert len(names) >= 90
    assert len(names) == len(set(names))
    assert all(entry["module"] and entry["qualname"] for entry in TOOL_MANIFEST)
    assert all(entry["effect"] in {"read_only", "mutating"} for entry in TOOL_MANIFEST)
    assert all(entry["cacheable"] is False for entry in TOOL_MANIFEST)


def test_known_mutating_tools_are_not_cacheable() -> None:
    entries = {entry["name"]: entry for entry in TOOL_MANIFEST}

    for name in {"write_file", "edit_file", "git_commit", "docker_exec"}:
        assert entries[name]["effect"] == "mutating"
        assert entries[name]["cacheable"] is False


def test_catalog_does_not_resolve_implementations() -> None:
    tools = {
        name: descriptor.function
        for name, descriptor in ServiceRegistry().get_all_tools().items()
    }

    assert tools
    assert all(isinstance(tool, LazyTool) for tool in tools.values())
    assert all(not tool.is_resolved for tool in tools.values())


def test_schema_generation_uses_manifest_without_importing_tool() -> None:
    tool = LazyTool("sample", "unavailable.module", "sample", _schema("sample"))

    schemas = create_tool_schemas({"sample": tool})

    assert schemas == [_schema("sample")]
    assert not tool.is_resolved


def test_lazy_tool_imports_once_on_first_call() -> None:
    implementation = Mock(return_value="ok")
    module = SimpleNamespace(sample=implementation)
    tool = LazyTool("sample", "example.tools", "sample", _schema("sample"))

    with patch(
        "aura_cli.core.service_registry.importlib.import_module",
        return_value=module,
    ) as import_module:
        assert tool(value=1) == "ok"
        assert tool(value=2) == "ok"

    import_module.assert_called_once_with("example.tools")
    assert implementation.call_count == 2
    assert tool.is_resolved


def test_registry_executes_manifest_backed_tool(tmp_path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text("lazy execution", encoding="utf-8")
    registry = ServiceRegistry()

    result = registry.execute_tool("read_file", {"path": str(source)})

    assert "lazy execution" in result
    assert registry.tools["read_file"].function.is_resolved
