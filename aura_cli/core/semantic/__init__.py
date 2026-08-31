"""Canonical public surface for semantic code-search infrastructure."""

from aura_cli.core.semantic.embeddings import EmbeddingGenerator, EmbeddingModel
from aura_cli.core.semantic.search import SearchQuery, SearchResult, SemanticSearch
from aura_cli.core.semantic.storage import VectorDocument, VectorIndex, VectorStorage

__all__ = [
    "EmbeddingGenerator",
    "EmbeddingModel",
    "SearchQuery",
    "SearchResult",
    "SemanticSearch",
    "VectorDocument",
    "VectorIndex",
    "VectorStorage",
]
