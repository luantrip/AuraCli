"""Optional local embedding server — isolates fastembed/ONNX in a subprocess.

Exposes /health, /embed and /embed/batch over HTTP (default port
EMBEDDING_SERVER_PORT). Run as: python -m aura_cli.core.embeddings.server
The main app manages this as a subprocess; the product works without it.

NOTE: This is for local fastembed embeddings only. Gemini (generative chat)
does not provide an embedding endpoint — see docs/reference/EMBEDDINGS_E_GEMINI.md.
"""

import os

os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import time
from typing import Any

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("EmbeddingServer")

MODEL = None
MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB
logger.info("Initializing server...")
# Default model: BAAI/bge-small-en-v1.5 (384-dim, well-supported by fastembed)
_DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"


def _load_model():
    """Load fastembed model. Called once at server startup."""
    global MODEL
    try:
        from fastembed import TextEmbedding

        start_time = time.time()
        logger.info("Loading fastembed model '%s'...", _DEFAULT_MODEL)
        MODEL = TextEmbedding(model_name=_DEFAULT_MODEL)
        # Warm-up: embed a single string to trigger model loading
        list(MODEL.embed(["warm-up"]))
        duration = time.time() - start_time
        logger.info("Model loaded successfully in %.2f seconds.", duration)
    except ImportError as e:
        logger.warning("fastembed não disponível (%s). Embeddings desativados.", e)
        MODEL = None
    except Exception as e:
        logger.warning(
            "Modelo de embeddings não carregou (%s). Servidor sobe com /embed retornando 503.",
            e,
        )
        MODEL = None


class EmbeddingRequestHandler(BaseHTTPRequestHandler):
    """
    Handles HTTP requests for the embedding server.
    Only responds to POST requests on the /embed endpoint.
    """

    def do_POST(self):
        """Handles POST requests."""
        if self.path == "/embed/batch":
            self._handle_batch_request()
        elif self.path == "/embed":
            self._handle_single_request()
        else:
            self._send_response(404, {"error": "Not Found"})

    def _handle_single_request(self):
        """Handle single text embedding request."""
        if MODEL is None:
            self._send_response(
                503, {"error": "Model is not available. Check server logs."}
            )
            return

        try:
            content_length = int(self.headers["Content-Length"])
            if content_length > MAX_BODY_SIZE:
                self._send_response(
                    413,
                    {
                        "error": f"Request body too large. Maximum size is {MAX_BODY_SIZE} bytes."
                    },
                )
                return
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)

            text_to_embed = body.get("text")
            if not isinstance(text_to_embed, str):
                self._send_response(
                    400, {"error": "Invalid request. 'text' field must be a string."}
                )
                return

            if not text_to_embed.strip():
                self._send_response(
                    400, {"error": "Invalid request. 'text' field cannot be empty."}
                )
                return

            embeddings = list(MODEL.embed([text_to_embed]))
            embedding = embeddings[0].tolist()
            self._send_response(200, {"embedding": embedding})

        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON in request body."})
        except ValueError as e:
            self._send_response(400, {"error": f"Invalid request: {e}"})
        except Exception as e:
            logger.error(f"An error occurred during embedding: {e}", exc_info=True)
            self._send_response(500, {"error": f"Internal server error: {e}"})

    def _handle_batch_request(self):
        """Handle batch embedding request."""
        if MODEL is None:
            self._send_response(
                503, {"error": "Model is not available. Check server logs."}
            )
            return

        MAX_BATCH_SIZE = 1000
        MAX_TEXT_LENGTH = 10000

        try:
            content_length = int(self.headers["Content-Length"])
            if content_length > MAX_BODY_SIZE:
                self._send_response(
                    413,
                    {
                        "error": f"Request body too large. Maximum size is {MAX_BODY_SIZE} bytes."
                    },
                )
                return
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)

            texts = body.get("texts")
            if not isinstance(texts, list):
                self._send_response(
                    400, {"error": "Invalid request. 'texts' field must be a list."}
                )
                return

            if not texts:
                self._send_response(
                    400, {"error": "Invalid request. 'texts' list cannot be empty."}
                )
                return

            if len(texts) > MAX_BATCH_SIZE:
                self._send_response(
                    400,
                    {
                        "error": f"Invalid request. Batch size exceeds maximum of {MAX_BATCH_SIZE}."
                    },
                )
                return

            for i, text in enumerate(texts):
                if not isinstance(text, str):
                    self._send_response(
                        400,
                        {
                            "error": f"Invalid request. Item at index {i} must be a string."
                        },
                    )
                    return
                if len(text) > MAX_TEXT_LENGTH:
                    self._send_response(
                        400,
                        {
                            "error": f"Invalid request. Text at index {i} exceeds maximum length of {MAX_TEXT_LENGTH}."
                        },
                    )
                    return

            embeddings = list(MODEL.embed(texts))
            embeddings_list = [emb.tolist() for emb in embeddings]

            self._send_response(200, {"embeddings": embeddings_list})

        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON in request body."})
        except ValueError as e:
            self._send_response(400, {"error": f"Invalid request: {e}"})
        except Exception as e:
            logger.error(
                f"An error occurred during batch embedding: {e}", exc_info=True
            )
            self._send_response(500, {"error": f"Internal server error: {e}"})

    def do_GET(self):
        """Handles GET requests, used for a simple health check."""
        if self.path == "/health":
            status = "ok" if MODEL is not None else "model_not_loaded"
            self._send_response(200, {"status": status})
        else:
            self._send_response(404, {"error": "Not Found"})

    def _send_response(self, status_code: int, data: dict):
        """Sends a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, fmt: str, *args: Any) -> None:
        """Suppress default request logging to keep the output clean."""
        return


def run_server(
    server_class=HTTPServer,
    handler_class=EmbeddingRequestHandler,
    port=None,
):
    """
    Starts the embedding server on the specified port.
    """
    if port is None:
        try:
            from aura_cli.core.embeddings import EMBEDDING_SERVER_PORT

            port = EMBEDDING_SERVER_PORT
        except ImportError:
            port = 1333  # fallback when running from isolated venv

    _load_model()

    server_address = ("", port)
    httpd = server_class(server_address, handler_class)
    logger.info(f"Embedding server starting on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt as _e:
        pass  # silenced: {_e}
    finally:
        httpd.server_close()
        logger.info("Embedding server stopped.")


if __name__ == "__main__":
    run_server()
