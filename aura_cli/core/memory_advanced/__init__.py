"""Compatibility shim — memory_advanced merged into core.memory.

All symbols are re-exported from their new canonical location.
Import directly from ``aura_cli.core.memory`` for new code.
"""

from aura_cli.core.memory.embeddings import EmbeddingGenerator, EmbeddingModel
from aura_cli.core.memory.semantic_search import (
    SearchQuery,
    SearchResult,
    SemanticSearch,
)
from aura_cli.core.memory.vector_storage import (
    VectorDocument,
    VectorStorage,
)

__all__ = [
    "EmbeddingGenerator",
    "EmbeddingModel",
    "SearchQuery",
    "SearchResult",
    "SemanticSearch",
    "VectorDocument",
    "VectorStorage",
]
