"""Auxiliary cache infrastructure for specialised use cases.

This package does not represent a central cache subsystem of the product.
Its role is split between:
- `ToolResultCache`, which remains useful at the tools/registry level;
- persistent or lateral caches for analysis and embeddings;
- on-demand technical support, without architectural centrality.
"""

from aura_cli.core.cache_advanced.analysis_cache import (
    AnalysisCache,
    get_analysis_cache,
)
from aura_cli.core.cache_advanced.embedding_cache import (
    EmbeddingCache,
    get_embedding_cache,
)
from aura_cli.core.cache_advanced.persistent_cache import (
    PersistentCache,
    get_persistent_cache,
)
from aura_cli.core.cache_advanced.tool_result_cache import (
    CachedResult,
    ToolResultCache,
)

__all__ = [
    "AnalysisCache",
    "CachedResult",
    "EmbeddingCache",
    "PersistentCache",
    "ToolResultCache",
    "get_analysis_cache",
    "get_embedding_cache",
    "get_persistent_cache",
]
