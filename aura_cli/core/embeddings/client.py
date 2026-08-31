"""
Optional HTTP client for the local embedding server.

Provides a unified interface to generate embeddings via the embedding server,
with automatic fallback to local models when the server is unavailable.

This client supports auxiliary semantic features. It should not be treated
as a mandatory runtime dependency for the main chat/worker product flow.
"""

import json
from typing import Callable, List, Optional

import requests

from aura_cli.core.embeddings import EMBEDDING_SERVER_PORT
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

DEFAULT_SERVER_URL = f"http://127.0.0.1:{EMBEDDING_SERVER_PORT}"
EMBED_ENDPOINT = "/embed"
EMBED_BATCH_ENDPOINT = "/embed/batch"
HEALTH_ENDPOINT = "/health"
_server_starter: Optional[Callable[[], None]] = None


def configure_embedding_server_starter(
    starter: Optional[Callable[[], None]],
) -> None:
    """Configure the host-owned lifecycle callback for the optional server."""
    global _server_starter
    _server_starter = starter


class EmbeddingClient:
    """
    HTTP client for the optional embedding server.

    Provides methods to generate embeddings via HTTP requests to the
    embedding server, with automatic fallback when the server is unavailable.
    """

    def __init__(self, server_url: str = DEFAULT_SERVER_URL, timeout: int = 3):
        """
        Initialize embedding client.

        Args:
            server_url: Base URL of the embedding server
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self._server_available: Optional[bool] = None
        self._retry_count: int = 0
        self._max_retries: int = 3
        self._check_server_health()

    def _check_server_health(self) -> bool:
        """Check if the embedding server is available; lazy-start if needed."""
        if self._server_available is True:
            return True

        import time as _time

        for attempt in range(self._max_retries):
            try:
                response = requests.get(
                    f"{self.server_url}{HEALTH_ENDPOINT}", timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()
                if data.get("status") == "ok":
                    self._server_available = True
                    self._retry_count = 0
                    return True
            except Exception:
                # On first failure, try to lazy-start the server
                if attempt == 0:
                    self._lazy_start_server()
                    _time.sleep(2.0)  # Give server time to load model
                elif attempt < self._max_retries - 1:
                    _time.sleep(0.5 * (attempt + 1))

        self._server_available = False
        return False

    def _lazy_start_server(self) -> None:
        """Start the embedding server if not already running."""
        if _server_starter is None:
            logger.debug("Embedding server starter is not configured")
            return
        try:
            _server_starter()
            logger.debug("Embedding server lazy-started on first use")
        except Exception as e:
            logger.debug(f"Could not lazy-start embedding server: {e}")

    def embed(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if server unavailable
        """
        if not self._check_server_health():
            return None

        try:
            response = requests.post(
                f"{self.server_url}{EMBED_ENDPOINT}",
                json={"text": text},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding")
            if isinstance(embedding, list):
                return embedding
            logger.warning("Embedding server returned invalid data")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Embedding server request failed: {e}")
            self._server_available = False
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON response from embedding server: {e}")
            self._server_available = False
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling embedding server: {e}")
            self._server_available = False
            return None

    def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Generate embeddings for multiple texts using batch endpoint.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors or None if server unavailable
        """
        if not texts:
            return []

        if not self._check_server_health():
            return None

        try:
            response = requests.post(  # nosec B113 - timeout is set below
                f"{self.server_url}{EMBED_BATCH_ENDPOINT}",
                json={"texts": texts},
                timeout=max(self.timeout, len(texts) * 0.1),
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings")
            if isinstance(embeddings, list) and len(embeddings) == len(texts):
                return embeddings
            logger.warning("Embedding server returned invalid batch data")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Embedding server batch request failed: {e}")
            self._server_available = False
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON response from embedding server: {e}")
            self._server_available = False
            return None
        except Exception as e:
            logger.error(f"Unexpected error calling embedding server batch: {e}")
            self._server_available = False
            return None

    def is_available(self) -> bool:
        """Check if the embedding server is available."""
        return self._check_server_health()

    def reset_health_check(self) -> None:
        """Reset health check status (force re-check on next call)."""
        self._server_available = None


_global_client: Optional[EmbeddingClient] = None


def get_embedding_client(server_url: str = DEFAULT_SERVER_URL) -> EmbeddingClient:
    """
    Get or create global EmbeddingClient instance.

    Args:
        server_url: Base URL of the embedding server

    Returns:
        EmbeddingClient instance
    """
    global _global_client
    if _global_client is None:
        _global_client = EmbeddingClient(server_url=server_url)
    return _global_client
