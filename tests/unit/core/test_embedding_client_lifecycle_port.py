"""Lifecycle port tests for the optional embedding server client."""

from aura_cli.core.embeddings import client as client_module
from aura_cli.core.embeddings.client import (
    EmbeddingClient,
    configure_embedding_server_starter,
)

_ORIGINAL_STARTER = client_module._server_starter


def teardown_function() -> None:
    configure_embedding_server_starter(_ORIGINAL_STARTER)


def test_lazy_start_is_inert_without_host_adapter() -> None:
    configure_embedding_server_starter(None)
    client = EmbeddingClient.__new__(EmbeddingClient)

    client._lazy_start_server()


def test_lazy_start_delegates_to_host_lifecycle() -> None:
    calls = []
    configure_embedding_server_starter(lambda: calls.append("start"))
    client = EmbeddingClient.__new__(EmbeddingClient)

    client._lazy_start_server()

    assert calls == ["start"]
