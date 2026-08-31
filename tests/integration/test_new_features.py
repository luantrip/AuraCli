import json
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request as HttpRequest
from urllib.request import urlopen

import pytest

from aura_cli.core.arena.engine import ArenaEngine
from aura_cli.core.reliability.faults import FaultInjector
from aura_cli.core.reliability.middleware import MiddlewareChain, Request, Response
from aura_cli.core.reliability.retry import RetryPolicy, retry_call
from aura_cli.core.skills.manager import SkillManager
from aura_cli.mcp.server import MCPServer
from aura_cli.mcp.tool_adapter import ToolAdapter


def test_new_features_compose_without_network(tmp_path: Path):
    arena = ArenaEngine(tmp_path / "arena")
    state = arena.init(2, 1, "integration task")
    assert len(state.agents) == 2
    manager = SkillManager(tmp_path / "skills")
    assert manager.list_installed() == []
    server = MCPServer(ToolAdapter({"ping": lambda: "pong"}))
    assert server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]


def test_fault_injection_recovers_at_mcp_boundary() -> None:
    injector = FaultInjector()
    injector.add("mcp-transport", ConnectionError("transient outage"), times=2)
    server = MCPServer(ToolAdapter({"ping": lambda: "pong"}))

    def transport(request: Request) -> Response:
        injector.check("mcp-transport")
        response = server.handle(request.payload)
        return Response(200, response)

    chain = MiddlewareChain(transport)
    request = Request(
        "POST",
        "/mcp",
        payload={
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "ping", "arguments": {}},
        },
    )
    response = retry_call(
        chain.send,
        request,
        policy=RetryPolicy(max_attempts=3, initial_delay=0, jitter=0),
    )

    assert response.status == 200
    assert response.payload["result"]["content"][0]["text"] == "pong"


def test_mcp_http_authentication_and_shutdown(monkeypatch) -> None:
    """HTTP transport rejects missing tokens and shuts down deterministically."""
    monkeypatch.setenv("AURA_MCP_TOKEN", "integration-secret")
    server = MCPServer(ToolAdapter({"ping": lambda: "pong"})).build_http_server(
        port=0
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    payload = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    ).encode()

    try:
        with pytest.raises(HTTPError) as error:
            urlopen(HttpRequest(url, data=payload, method="POST"), timeout=2)
        assert error.value.code == 401

        request = HttpRequest(
            url,
            data=payload,
            method="POST",
            headers={"Authorization": "Bearer integration-secret"},
        )
        with urlopen(request, timeout=2) as response:
            result = json.load(response)
        assert result["result"]["serverInfo"]["name"] == "aura-cli"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert not thread.is_alive()
