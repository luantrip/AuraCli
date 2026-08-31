"""Unit tests for adk.tools — ToolRegistry, Tool, @tool decorator."""

from __future__ import annotations

import asyncio

import pytest

from aura_cli.adk.tools import (
    Tool,
    ToolCategory,
    ToolRegistry,
    ToolResult,
    ToolSchema,
    get_tool_registry,
    reset_tool_registry,
    tool,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def isolated_registry():
    """Give each test a fresh global registry."""
    reset_tool_registry()
    yield
    reset_tool_registry()


# ---------------------------------------------------------------------------
# ToolSchema
# ---------------------------------------------------------------------------


def test_tool_schema_to_openai_format() -> None:
    schema = ToolSchema(
        name="greet",
        description="Greet a person",
        parameters={"name": {"type": "string", "required": True}},
    )
    result = schema.to_openai_schema()
    assert result["type"] == "function"
    assert result["function"]["name"] == "greet"
    assert "name" in result["function"]["parameters"]["properties"]
    assert "name" in result["function"]["parameters"]["required"]


def test_tool_schema_to_anthropic_format() -> None:
    schema = ToolSchema(
        name="greet",
        description="Greet",
        parameters={"name": {"type": "string", "required": True}},
    )
    result = schema.to_anthropic_schema()
    assert result["name"] == "greet"
    assert "input_schema" in result
    assert "name" in result["input_schema"]["required"]


def test_tool_schema_no_required_params() -> None:
    schema = ToolSchema(
        name="ping",
        description="Ping",
        parameters={"host": {"type": "string", "required": False}},
    )
    openai = schema.to_openai_schema()
    assert openai["function"]["parameters"]["required"] == []


# ---------------------------------------------------------------------------
# ToolRegistry — register / get / unregister
# ---------------------------------------------------------------------------


def test_registry_register_and_get_tool() -> None:
    class MyTool(Tool):
        name = "my_tool"
        description = "Does something"
        category = ToolCategory.UTILITY

        async def execute(self, value: str) -> ToolResult:
            return ToolResult.ok(value)

    registry = ToolRegistry()
    instance = MyTool()
    registry.register(instance)

    assert "my_tool" in registry
    assert registry.get("my_tool") is instance


def test_registry_get_schema_after_register() -> None:
    class AnotherTool(Tool):
        name = "another_tool"
        description = "Another"
        category = ToolCategory.CODE

        async def execute(self, x: int) -> ToolResult:
            return ToolResult.ok(x * 2)

    registry = ToolRegistry()
    registry.register(AnotherTool())
    schema = registry.get_schema("another_tool")
    assert schema is not None
    assert schema.name == "another_tool"
    assert schema.category == ToolCategory.CODE


def test_registry_unregister() -> None:
    class RemovableTool(Tool):
        name = "removable"
        description = "Will be removed"

        async def execute(self) -> ToolResult:
            return ToolResult.ok("ok")

    registry = ToolRegistry()
    registry.register(RemovableTool())
    assert "removable" in registry
    assert registry.unregister("removable") is True
    assert "removable" not in registry
    assert registry.unregister("removable") is False


def test_registry_unregister_unknown_returns_false() -> None:
    registry = ToolRegistry()
    assert registry.unregister("__ghost__") is False


def test_registry_list_tools_all() -> None:
    registry = ToolRegistry()

    class T1(Tool):
        name = "t1"
        description = "t1"
        category = ToolCategory.FILE_SYSTEM

        async def execute(self) -> ToolResult:
            return ToolResult.ok("t1")

    class T2(Tool):
        name = "t2"
        description = "t2"
        category = ToolCategory.SHELL

        async def execute(self) -> ToolResult:
            return ToolResult.ok("t2")

    registry.register(T1())
    registry.register(T2())
    names = registry.list_tools()
    assert "t1" in names
    assert "t2" in names


def test_registry_list_tools_by_category() -> None:
    registry = ToolRegistry()

    class FST(Tool):
        name = "fst"
        description = "fs"
        category = ToolCategory.FILE_SYSTEM

        async def execute(self) -> ToolResult:
            return ToolResult.ok("fst")

    class ShellT(Tool):
        name = "shellt"
        description = "shell"
        category = ToolCategory.SHELL

        async def execute(self) -> ToolResult:
            return ToolResult.ok("shellt")

    registry.register(FST())
    registry.register(ShellT())
    assert registry.list_tools(ToolCategory.FILE_SYSTEM) == ["fst"]
    assert registry.list_tools(ToolCategory.SHELL) == ["shellt"]


def test_registry_len() -> None:
    registry = ToolRegistry()

    class Tiny(Tool):
        name = "tiny"
        description = "tiny"

        async def execute(self) -> ToolResult:
            return ToolResult.ok("x")

    assert len(registry) == 0
    registry.register(Tiny())
    assert len(registry) == 1


# ---------------------------------------------------------------------------
# ToolRegistry — execute
# ---------------------------------------------------------------------------


def test_registry_execute_tool_instance() -> None:
    class EchoTool(Tool):
        name = "echo"
        description = "Echoes input"

        async def execute(self, msg: str) -> ToolResult:
            return ToolResult.ok(f"echo:{msg}")

    registry = ToolRegistry()
    registry.register(EchoTool())
    result = asyncio.run(registry.execute("echo", msg="hello"))
    assert result.success
    assert result.data == "echo:hello"


def test_registry_execute_unknown_tool_returns_failure() -> None:
    registry = ToolRegistry()
    result = asyncio.run(registry.execute("__nope__"))
    assert not result.success


def test_registry_execute_sync_function() -> None:
    registry = ToolRegistry()

    def add(a: int, b: int) -> int:
        return a + b

    registry.register_function("add", add, description="Add two numbers")
    result = asyncio.run(registry.execute("add", a=2, b=3))
    assert result.success
    assert result.data == 5


def test_registry_execute_async_function() -> None:
    registry = ToolRegistry()

    async def double(n: int) -> int:
        return n * 2

    registry.register_function("double", double, description="Double a number")
    result = asyncio.run(registry.execute("double", n=7))
    assert result.success
    assert result.data == 14


def test_registry_execute_raising_tool_returns_failure() -> None:
    class BrokenTool(Tool):
        name = "broken"
        description = "Always fails"

        async def execute(self) -> ToolResult:
            raise ValueError("intentional error")

    registry = ToolRegistry()
    registry.register(BrokenTool())
    result = asyncio.run(registry.execute("broken"))
    assert not result.success
    assert "intentional error" in result.error


# ---------------------------------------------------------------------------
# ToolRegistry — schemas export
# ---------------------------------------------------------------------------


def test_get_all_schemas() -> None:
    registry = ToolRegistry()
    registry.register_function("s1", lambda: None, description="s1")
    registry.register_function("s2", lambda: None, description="s2")
    schemas = registry.get_all_schemas()
    names = [s.name for s in schemas]
    assert "s1" in names and "s2" in names


def test_get_openai_schemas_format() -> None:
    registry = ToolRegistry()
    registry.register_function("f1", lambda x: x, description="f1")
    schemas = registry.get_openai_schemas()
    assert all(s["type"] == "function" for s in schemas)


def test_get_anthropic_schemas_format() -> None:
    registry = ToolRegistry()
    registry.register_function("f2", lambda x: x, description="f2")
    schemas = registry.get_anthropic_schemas()
    assert all("input_schema" in s for s in schemas)


# ---------------------------------------------------------------------------
# @tool decorator
# ---------------------------------------------------------------------------


def test_tool_decorator_sync_function() -> None:
    @tool(name="_dec_sync", description="sync decorated")
    def _sync(value: str) -> str:
        return value.upper()

    registry = get_tool_registry()
    assert "_dec_sync" in registry
    result = asyncio.run(registry.execute("_dec_sync", value="hello"))
    assert result.success
    assert result.data == "HELLO"


def test_tool_decorator_async_function() -> None:
    @tool(name="_dec_async", description="async decorated")
    async def _async(n: int) -> int:
        return n + 1

    registry = get_tool_registry()
    assert "_dec_async" in registry
    result = asyncio.run(registry.execute("_dec_async", n=4))
    assert result.success
    assert result.data == 5


def test_tool_decorator_preserves_name_when_not_given() -> None:
    @tool(description="auto-named")
    def _auto_named_tool_xyz() -> str:
        return "x"

    registry = get_tool_registry()
    assert "_auto_named_tool_xyz" in registry


def test_tool_decorator_raises_returns_failure() -> None:
    @tool(name="_dec_raises")
    def _raises() -> str:
        raise RuntimeError("boom")

    registry = get_tool_registry()
    result = asyncio.run(registry.execute("_dec_raises"))
    assert not result.success
    assert "boom" in result.error


# ---------------------------------------------------------------------------
# Global registry singleton
# ---------------------------------------------------------------------------


def test_get_tool_registry_returns_same_instance() -> None:
    r1 = get_tool_registry()
    r2 = get_tool_registry()
    assert r1 is r2


def test_reset_tool_registry_clears_instance() -> None:
    r1 = get_tool_registry()
    r1.register_function("_tmp", lambda: None)
    reset_tool_registry()
    r2 = get_tool_registry()
    assert r1 is not r2
    assert "_tmp" not in r2
