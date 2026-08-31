"""Advanced in-memory vector storage for semantic-memory flows.

Manages multiple named VectorIndex instances (each holding VectorDocument
records + NumPy matrix). Supports cosine-similarity search, persistence to
disk and multiple concurrent indexes. Complements core.memory.vector_store
which is the canonical general-purpose vector store.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import numpy as np

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


@dataclass
class VectorDocument:
    """Vector document (doc_id, content, vector, metadata)."""

    doc_id: str
    content: str
    vector: np.ndarray
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorIndex:
    """A named vector index containing documents and a numpy matrix."""

    index_id: str
    dimension: int
    documents: List[VectorDocument] = field(default_factory=list)
    vectors: Optional[np.ndarray] = None


class VectorStorage:
    """Vector storage with similarity search and persistence."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialise the vector storage."""
        from aura_cli.core.paths import ArtifactLayout

        self.storage_path = (
            Path(storage_path)
            if storage_path is not None
            else ArtifactLayout(project_root=Path.cwd()).project("vector_db")
        )
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.indices: Dict[str, VectorIndex] = {}
        self.stats = get_stats()

        logger.info(f"VectorStorage initialized (path: {storage_path})")

    def create_index(self, index_id: str, dimension: int = 384) -> VectorIndex:
        """Create a new named vector index."""
        index = VectorIndex(index_id=index_id, dimension=dimension)

        self.indices[index_id] = index

        logger.debug(f"Índice '{index_id}' created (dimension: {dimension})")

        return index

    def add_document(
        self,
        index_id: str,
        doc_id: str,
        content: str,
        vector: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a document and its embedding to an index."""
        if index_id not in self.indices:
            logger.error(f"Índice '{index_id}' not found")
            return

        index = self.indices[index_id]

        if len(vector) != index.dimension:
            logger.error(
                f"Dimensão do vetor ({len(vector)}) "
                f"não corresponde à dimensão do índice ({index.dimension})"
            )
            return

        document = VectorDocument(
            doc_id=doc_id, content=content, vector=vector, metadata=metadata or {}
        )

        index.documents.append(document)

        if index.vectors is None:
            index.vectors = vector.reshape(1, -1)
        else:
            index.vectors = np.vstack([index.vectors, vector])

        logger.debug(f"Documento '{doc_id}' adicionado ao índice '{index_id}'")

    def search(
        self, index_id: str, query_vector: np.ndarray, top_k: int = 10
    ) -> List[Tuple[VectorDocument, float]]:
        """Search for similar documents by vector."""
        if index_id not in self.indices:
            logger.error(f"Índice '{index_id}' not found")
            return []

        index = self.indices[index_id]

        if index.vectors is None or len(index.vectors) == 0:
            return []

        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            return []

        query_vector = query_vector / query_norm

        norms = np.linalg.norm(index.vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized_vectors = index.vectors / norms

        similarities = np.dot(normalized_vectors, query_vector)

        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            doc = index.documents[idx]
            similarity = float(similarities[idx])
            results.append((doc, similarity))

        logger.debug(f"Busca em '{index_id}': {len(results)} resultados")

        return results

    def save_index(self, index_id: str) -> bool:
        """Persist an index to disk."""
        if index_id not in self.indices:
            return False

        index = self.indices[index_id]
        index_file = self.storage_path / f"{index_id}.json"
        vectors_file = self.storage_path / f"{index_id}.npy"

        try:
            metadata = {
                "index_id": index.index_id,
                "dimension": index.dimension,
                "documents": [
                    {
                        "doc_id": doc.doc_id,
                        "content": doc.content,
                        "metadata": doc.metadata,
                    }
                    for doc in index.documents
                ],
            }

            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            if index.vectors is not None:
                np.save(vectors_file, index.vectors)

            logger.info(f"Índice '{index_id}' salvo")
            return True

        except Exception as e:
            logger.error(f"Error saving index '{index_id}': {e}", exc_info=True)
            return False

    def load_index(self, index_id: str) -> bool:
        """Load an index from disk."""
        index_file = self.storage_path / f"{index_id}.json"
        vectors_file = self.storage_path / f"{index_id}.npy"

        if not index_file.exists():
            return False

        try:
            with open(index_file, encoding="utf-8") as f:
                metadata = json.load(f)

            index = VectorIndex(
                index_id=metadata["index_id"], dimension=metadata["dimension"]
            )

            if vectors_file.exists():
                index.vectors = np.load(vectors_file)

            for doc_data in metadata["documents"]:
                doc_idx = len(index.documents)
                vector = (
                    index.vectors[doc_idx]
                    if index.vectors is not None
                    else np.zeros(index.dimension)
                )

                document = VectorDocument(
                    doc_id=doc_data["doc_id"],
                    content=doc_data["content"],
                    vector=vector,
                    metadata=doc_data.get("metadata", {}),
                )
                index.documents.append(document)

            self.indices[index_id] = index

            logger.info(f"Índice '{index_id}' loaded")
            return True

        except Exception as e:
            logger.error(f"Error loading index '{index_id}': {e}", exc_info=True)
            return False
