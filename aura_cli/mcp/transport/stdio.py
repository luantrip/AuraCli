"""stdio transport layer for the MCP server (line-delimited JSON over stdin/stdout)."""

from aura_cli.mcp.server import MCPServer


def serve(server: MCPServer) -> None:
    """Start the stdio MCP transport server, reading from stdin and writing to stdout."""
    server.serve_stdio()
