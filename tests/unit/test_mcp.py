import io
import json

from aura_cli.mcp.server import MCPServer
from aura_cli.mcp.tool_adapter import ToolAdapter


def test_mcp_stdio_initialize_and_call():
    adapter = ToolAdapter({"echo": lambda value: value})
    server = MCPServer(adapter)
    source = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}) + "\n" +
                         json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "echo", "arguments": {"value": "ok"}}}) + "\n")
    target = io.StringIO()
    server.serve_stdio(source, target)
    responses = [json.loads(line) for line in target.getvalue().splitlines()]
    assert responses[0]["result"]["serverInfo"]["name"] == "aura-cli"
    assert responses[1]["result"]["content"][0]["text"] == "ok"


def test_mcp_lists_optional_capability_surfaces() -> None:
    server = MCPServer(ToolAdapter({}))

    initialize = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    resources = server.handle({"jsonrpc": "2.0", "id": 2, "method": "resources/list"})
    prompts = server.handle({"jsonrpc": "2.0", "id": 3, "method": "prompts/list"})

    assert initialize["result"]["capabilities"] == {
        "tools": {},
        "resources": {},
        "prompts": {},
    }
    assert resources["result"] == {"resources": []}
    assert prompts["result"] == {"prompts": []}
