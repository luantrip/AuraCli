from aura_cli.mcp.server import MCPServer


def serve(server: MCPServer, host: str = "127.0.0.1", port: int = 8765) -> None:
    server.serve_http(host=host, port=port)
