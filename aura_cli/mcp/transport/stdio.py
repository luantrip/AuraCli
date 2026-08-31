from aura_cli.mcp.server import MCPServer


def serve(server: MCPServer) -> None:
    server.serve_stdio()
