"""Auxiliary semantic search on the legacy advanced vector stack.

SemanticSearch wraps VectorStorage + EmbeddingGenerator for meaning-based
search with metadata filtering and cosine-similarity ranking. Not the
primary runtime memory surface — see core.memory for that.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from aura_cli.core.logger import get_logger
from aura_cli.core.memory_advanced.embeddings import EmbeddingGenerator
from aura_cli.core.memory_advanced.vector_storage import VectorStorage
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


@dataclass
class SearchQuery:
    """Search query (query_text, top_k, filters)."""

    query_text: str
    top_k: int = 10
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Search result (doc_id, content, score, metadata)."""

    doc_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticSearch:
    """Semantic search system with indexing, filtering and refinement."""

    def __init__(
        self,
        index_id: str = "default",
        embedding_model: Optional[EmbeddingGenerator] = None,
        use_code_embeddings: bool = True,
    ):
        """Initialise the semantic search system."""
        self.index_id = index_id
        self.vector_storage = VectorStorage()

        if embedding_model is None and use_code_embeddings:
            from aura_cli.core.memory_advanced.embeddings import EmbeddingModel

            try:
                # Prefer fastembed (fast ONNX) for code embeddings.
                # CODEBERTA is deprecated (incompatible with current HF API).
                embedding_model = EmbeddingGenerator(
                    model=EmbeddingModel.FASTEMBED, dimension=384
                )
                logger.info("Usando fastembed para embeddings de código")
            except Exception as e:
                logger.warning(f"Error loading fastembed: {e}, using default model")
                embedding_model = EmbeddingGenerator()

        self.embedding_generator = embedding_model or EmbeddingGenerator()
        self.stats = get_stats()

        if index_id not in self.vector_storage.indices:
            self.vector_storage.create_index(
                index_id, dimension=self.embedding_generator.dimension
            )

        logger.info(
            f"SemanticSearch initialized (index: {index_id}, dimensão: {self.embedding_generator.dimension})"
        )

    def index_document(
        self, doc_id: str, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Index a single document."""
        vector = self.embedding_generator.generate(content)

        self.vector_storage.add_document(
            self.index_id, doc_id, content, vector, metadata
        )

        logger.debug(f"Documento '{doc_id}' indexado")

    def index_documents(self, documents: List[Dict[str, str]]) -> None:
        """Index multiple documents."""
        from aura_cli.core.embeddings.client import get_embedding_client

        contents = [doc["content"] for doc in documents]
        client = get_embedding_client()
        batch_embeddings = client.embed_batch(contents)

        if batch_embeddings is not None:
            vectors = [np.array(emb, dtype="float32") for emb in batch_embeddings]
        else:
            vectors = self.embedding_generator.generate_batch(contents)  # type: ignore[assignment]

        for i, doc in enumerate(documents):
            self.vector_storage.add_document(
                self.index_id,
                doc["doc_id"],
                doc["content"],
                vectors[i],
                doc.get("metadata", {}),  # type: ignore[arg-type]
            )

        logger.info(f"{len(documents)} documents indexed")

    def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search indexed documents and return results."""
        from aura_cli.core.embeddings.client import get_embedding_client

        client = get_embedding_client()
        embedding_list = client.embed(query.query_text)

        if embedding_list is not None:
            query_vector = np.array(embedding_list, dtype="float32")
        else:
            query_vector = self.embedding_generator.generate(query.query_text)

        results = self.vector_storage.search(
            self.index_id, query_vector, top_k=query.top_k
        )

        # Apply cognitive re-ranking (Fase 4.2)
        try:
            from aura_cli.core.memory_advanced.cognitive_refinement import (
                CognitiveRefinement,
            )

            cr = CognitiveRefinement(self.vector_storage)
            refined = cr.rerank(self.index_id, results)
            results = [(r.doc, r.refined_score) for r in refined]
        except Exception as _cr_err:
            logger.debug(f"Cognitive rerank skipped: {_cr_err}")

        search_results = []
        for doc, similarity in results:
            if query.filters:
                matches = all(
                    doc.metadata.get(key) == value
                    for key, value in query.filters.items()
                )
                if not matches:
                    continue

            result = SearchResult(
                doc_id=doc.doc_id,
                content=doc.content,
                score=similarity,
                metadata=doc.metadata,
            )
            search_results.append(result)

        logger.debug(f"Busca retornou {len(search_results)} resultados")

        self.stats.track_tool_usage("semantic_search")

        return search_results
