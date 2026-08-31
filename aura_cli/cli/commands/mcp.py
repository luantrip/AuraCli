"""Public /mcp command for server inspection."""

from __future__ import annotations

import json
from typing import Any, Optional

from aura_cli.mcp.manifest import build_manifest
from aura_cli.mcp.server import MCPServer
from aura_cli.mcp.tool_adapter import ToolAdapter


def create_mcp_server(tools: Optional[dict] = None, allow_writes: bool = False) -> MCPServer:
    if tools is None:
        from aura_cli.core.service_registry import get_service_registry
        registry = get_service_registry()
        tools = {name: descriptor.function for name, descriptor in registry.get_all_tools().items()
                 if allow_writes or descriptor.effect == "read_only"}
        from aura_cli.core.tools.arena_tools import (
            arena_card,
            arena_status,
            arena_winner,
        )
        tools.update({"arena_status": arena_status, "arena_winner": arena_winner, "arena_card": arena_card})
    return MCPServer(ToolAdapter(tools), allow_writes=allow_writes)


def handle_mcp(args: str, app_loop: Any = None) -> Optional[str]:
    del app_loop
    command = (args.split() or ["status"])[0].lower()
    server = create_mcp_server()
    if command in ("manifest", "status"):
        return json.dumps(build_manifest(server.adapter), indent=2, default=str)
    if command == "start":
        tokens = args.split()
        if "--http" in tokens:
            port = int(tokens[tokens.index("--port") + 1]) if "--port" in tokens else 8765
            server.serve_http(port=port)
        else:
            server.serve_stdio()
        return None
    return "Uso: /mcp status|manifest|start"
