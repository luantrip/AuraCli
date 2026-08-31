"""Auxiliary semantic-memory stack for embeddings and semantic search.

STATUS (2026-08): ACTIVE — two real runtime callers:
  1. core/tools/dev_tools.py → SemanticSearch (tool semantic_search_advanced)
  2. core/refactoring/semantic_similarity.py → EmbeddingGenerator

NOT a replacement for memory/ (canonical):
  - memory/  = conversation, SQLite persistence, snapshots, general VectorStore
  - memory_advanced/ = code-specialised embeddings + semantic search
    (fastembed/OpenAI/CodeBERT) over pre-built indexes.

New memory behaviour should extend memory/, not this package.
"""

from aura_cli.core.memory_advanced.embeddings import EmbeddingGenerator, EmbeddingModel
from aura_cli.core.memory_advanced.semantic_search import (
    SearchQuery,
    SearchResult,
    SemanticSearch,
)
from aura_cli.core.memory_advanced.vector_storage import (
    VectorDocument,
    VectorIndex,
    VectorStorage,
)

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
