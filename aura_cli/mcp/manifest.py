"""MCP manifest generation."""

from __future__ import annotations

from .tool_adapter import ToolAdapter


def build_manifest(adapter: ToolAdapter, name: str = "aura-cli", version: str = "0.1.0") -> dict:
    return {"name": name, "version": version, "transport": {"type": "stdio"},
            "tools": adapter.list_tools()}
