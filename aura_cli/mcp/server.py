"""MCP JSON-RPC handlers over a dependency-free stdio transport."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sys
from typing import Any

from .auth import authorize
from .tool_adapter import ToolAdapter


class MCPServer:
    protocol_version = "2024-11-05"

    def __init__(self, adapter: ToolAdapter, name: str = "aura-cli", version: str = "0.1.0",
                 allow_writes: bool = False) -> None:
        self.adapter = adapter
        self.name = name
        self.version = version
        self.allow_writes = allow_writes

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        request_id = request.get("id")
        if method == "notifications/initialized":
            return None
        result: dict[str, Any]
        if method == "initialize":
            result = {"protocolVersion": self.protocol_version,
                      "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                      "serverInfo": {"name": self.name, "version": self.version}}
        elif method == "tools/list":
            result = {"tools": self.adapter.list_tools()}
        elif method == "resources/list":
            result = {"resources": []}
        elif method == "prompts/list":
            result = {"prompts": []}
        elif method == "tools/call":
            params = request.get("params", {})
            try:
                value = self.adapter.call(params["name"], params.get("arguments"), self.allow_writes)
                result = {"content": [{"type": "text", "text": self._text(value)}]}
            except Exception as exc:
                result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def serve_stdio(self, input_stream=None, output_stream=None) -> None:
        input_stream = input_stream or sys.stdin
        output_stream = output_stream or sys.stdout
        for line in input_stream:
            if not line.strip():
                continue
            request = json.loads(line)
            response = self.handle(request)
            if response is not None:
                output_stream.write(json.dumps(response) + "\n")
                output_stream.flush()

    def serve_http(self, host: str = "127.0.0.1", port: int = 8765) -> None:
        """Serve JSON-RPC POST requests on a local HTTP endpoint."""
        http_server = self.build_http_server(host=host, port=port)
        try:
            http_server.serve_forever()
        finally:
            http_server.server_close()

    def build_http_server(
        self, host: str = "127.0.0.1", port: int = 8765
    ) -> ThreadingHTTPServer:
        """Build a controllable HTTP server for embedding and lifecycle tests."""
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/sse":
                    self.send_response(404)
                    self.end_headers()
                    return
                if not authorize(self.headers.get("Authorization", "").removeprefix("Bearer ").strip() or None):
                    self.send_response(401)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                self.wfile.write(b"event: endpoint\ndata: /\n\n")
                self.wfile.flush()

            def do_POST(self):
                if not authorize(self.headers.get("Authorization", "").removeprefix("Bearer ").strip() or None):
                    self.send_response(401)
                    self.end_headers()
                    return
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length))
                response = server.handle(request)
                self.send_response(204 if response is None else 200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if response is not None:
                    self.wfile.write(json.dumps(response).encode("utf-8"))

            def log_message(self, *_args):
                return

        return ThreadingHTTPServer((host, port), Handler)

    @staticmethod
    def _text(value: Any) -> str:
        return value if isinstance(value, str) else json.dumps(value, default=str)
