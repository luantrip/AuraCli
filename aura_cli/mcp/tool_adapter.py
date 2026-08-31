"""Adapt ordinary Aura callables to MCP tool contracts."""

from __future__ import annotations

import inspect
from typing import Any, Callable


class ToolAdapter:
    def __init__(self, tools: dict[str, Callable[..., Any]], schemas: dict[str, dict] | None = None,
                 writable: set[str] | None = None) -> None:
        self.tools = tools
        self.schemas = schemas or {}
        self.writable = writable or set()

    def list_tools(self) -> list[dict]:
        result = []
        for name, function in self.tools.items():
            result.append({"name": name, "description": inspect.getdoc(function) or name,
                           "inputSchema": self.schemas.get(name, {"type": "object"})})
        return result

    def call(self, name: str, arguments: dict | None = None, allow_writes: bool = False) -> Any:
        if name not in self.tools:
            raise KeyError(f"unknown tool: {name}")
        if name in self.writable and not allow_writes:
            raise PermissionError(f"tool requires write permission: {name}")
        return self.tools[name](**(arguments or {}))
