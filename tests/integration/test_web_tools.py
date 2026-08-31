from aura_cli.mcp.server import MCPServer
from aura_cli.mcp.tool_adapter import ToolAdapter


def test_web_tool_boundary_is_mcp_serializable():
    server = MCPServer(ToolAdapter({"web_read": lambda url: {"url": url}}))
    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                              "params": {"name": "web_read", "arguments": {"url": "https://example.test"}}})
    assert response["result"]["content"][0]["text"]
