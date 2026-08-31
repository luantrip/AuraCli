"""Vector store for Aura CLI — semantic search with pluggable backends.

Backend priority: user config → chromadb → faiss → keyword (built-in fallback).
Use pip install -e ".[vector]" for ChromaDB or ".[vector-faiss]" for FAISS.

Security (ChromaDB): used strictly in embedded PersistentClient mode.
Known CVEs (PYSEC-2026-311, CVE-2026-45830/31/33) target the network server
endpoints — not reachable in embedded mode. Do NOT add HttpClient without a
dedicated security review. See docs/internal/audit-2026-08-31.md.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

from aura_cli.core.paths import aura_path

logger = logging.getLogger(__name__)
DEFAULT_VECTOR_DB_PATH = str(aura_path("vector_db"))


@dataclass
class SearchResult:
    """Result from vector search."""

    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize search result to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
        }


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """Add document to store, returns document ID."""

    @abstractmethod
    def add_many(
        self,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add multiple documents, returns list of IDs."""

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents."""

    @abstractmethod
    def get(self, doc_id: str) -> Optional[SearchResult]:
        """Get document by ID."""

    @abstractmethod
    def delete(self, doc_id: str) -> bool:
        """Delete document by ID."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all documents."""

    @abstractmethod
    def count(self) -> int:
        """Get document count."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Get backend name (chromadb, faiss, keyword)."""


class ChromaDBVectorStore(VectorStore):
    """
    Vector store using ChromaDB.

    ChromaDB is the preferred backend:
    - Easy installation (pip install chromadb)
    - Built-in persistence
    - Built-in embedding models
    - Metadata filtering
    - No numpy/faiss compilation issues

    Security note (embedded-only):
        Aura uses ChromaDB strictly in *embedded* mode via ``PersistentClient`` /
        ``Client`` — never as a network server (``HttpClient``). The known ChromaDB
        advisories (PYSEC-2026-311, CVE-2026-45830/45831/45833) affect only the
        Python *server*: cross-tenant authorization bypass and pre/post-auth code
        injection on server endpoints. None of those code paths are reachable in the
        embedded, single-process, no-auth usage here. Do NOT introduce
        ``chromadb.HttpClient`` or run a ChromaDB server from this code without a
        dedicated security review. See docs/internal/audit-2026-08-31.md.
    """

    def __init__(
        self,
        collection_name: str = "aura_memory",
        persist_path: Optional[str] = None,
        embedding_model: str = "BAAI/bge-small-en-v1.5",
    ):
        """
        Initialize ChromaDB store.

        Args:
            collection_name: Name of the collection
            persist_path: Path for persistent storage
            embedding_model: Embedding model name (uses fastembed for consistency)
        """
        import chromadb

        self._collection_name = collection_name
        self._persist_path = persist_path or DEFAULT_VECTOR_DB_PATH
        os.makedirs(self._persist_path, exist_ok=True)

        try:
            self._client: Any = chromadb.PersistentClient(
                path=self._persist_path,
            )
        except (TypeError, AttributeError):
            from chromadb.config import Settings

            self._client = chromadb.Client(
                Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=self._persist_path,
                    anonymized_telemetry=False,
                )
            )

        # Use fastembed for consistent embeddings across the system
        embedding_fn: Any = None
        try:
            from fastembed import TextEmbedding

            class FastEmbedFunction:
                """Custom embedding function using fastembed for consistency."""

                def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
                    self._model: Optional[TextEmbedding] = None
                    self._model_name = model_name

                def __call__(self, inputs: list) -> list:
                    if self._model is None:
                        self._model = TextEmbedding(model_name=self._model_name)
                    embeddings = list(self._model.embed(inputs))
                    return [e.tolist() for e in embeddings]

            embedding_fn = FastEmbedFunction(embedding_model)
            logger.debug(f"Using fastembed ({embedding_model}) for ChromaDB embeddings")
        except ImportError:
            logger.warning(
                "fastembed not available; ChromaDB will use its default embedding model"
            )

        self._embedding_fn = embedding_fn

        self._collection: Any = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=embedding_fn,
        )

        logger.info(f"ChromaDB initialized: {collection_name} at {self._persist_path}")

    def close(self) -> None:
        """Release ChromaDB client resources."""
        if hasattr(self, "_client") and self._client is not None:
            try:
                if hasattr(self._client, "_persist"):
                    self._client._persist()
            except Exception:
                pass
            self._client = None
            self._collection = None

    def __enter__(self) -> "ChromaDBVectorStore":
        """Context manager entry."""
        return self

    def __exit__(self, *exc: Any) -> None:
        """Context manager exit — release resources."""
        self.close()

    def __del__(self) -> None:
        """Ensure resources are released on garbage collection."""
        self.close()

    @property
    def backend_name(self) -> str:
        """Return the backend identifier string."""
        return "chromadb"

    def _generate_id(self, content: str) -> str:
        """Generate deterministic ID from content."""
        return hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()[:16]

    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """Add document to ChromaDB."""
        doc_id = doc_id or self._generate_id(content)
        metadata_list = [metadata] if metadata else None

        self._collection.add(
            documents=[content],
            metadatas=metadata_list,
            ids=[doc_id],
        )

        return doc_id

    def add_many(
        self,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add multiple documents."""
        if ids is None:
            ids = [self._generate_id(c) for c in contents]

        if metadatas is None:
            metadata_list = None
        else:
            metadata_list = [m if m else None for m in metadatas]
            if all(m is None for m in metadata_list):
                metadata_list = None

        self._collection.add(
            documents=contents,
            metadatas=metadata_list,
            ids=ids,
        )

        return ids

    def search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents."""
        where = filter_metadata if filter_metadata else None

        results = self._collection.query(
            query_texts=[query],
            n_results=limit,
            where=where,
        )

        search_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                content = results["documents"][0][i] if results["documents"] else ""
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0.0
                score = max(0.0, 1.0 - distance)

                search_results.append(
                    SearchResult(
                        id=doc_id,
                        content=content,
                        score=score,
                        metadata=dict(metadata),
                    )
                )

        return search_results

    def get(self, doc_id: str) -> Optional[SearchResult]:
        """Get document by ID."""
        results = self._collection.get(ids=[doc_id])

        if results and results["ids"]:
            return SearchResult(
                id=results["ids"][0],
                content=results["documents"][0] if results["documents"] else "",
                score=1.0,
                metadata=dict(results["metadatas"][0]) if results["metadatas"] else {},
            )
        return None

    def delete(self, doc_id: str) -> bool:
        """Delete document by ID."""
        try:
            self._collection.delete(ids=[doc_id])
            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all documents."""
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self._embedding_fn,
        )

    def count(self) -> int:
        """Get document count."""
        return self._collection.count()

    def persist(self) -> None:
        """Persist to disk."""
        self._client.persist()


class FAISSVectorStore(VectorStore):
    """
    Vector store using FAISS + fastembed.

    Fallback for when ChromaDB is not available.
    Requires: faiss-cpu, fastembed, numpy
    """

    def __init__(
        self,
        collection_name: str = "aura_memory",
        persist_path: Optional[str] = None,
        model_name: str = "BAAI/bge-small-en-v1.5",
        dimension: int = 384,
    ):
        """Initialize FAISS store."""

        import faiss
        from fastembed import TextEmbedding
        import numpy as np

        self._collection_name = collection_name
        self._persist_path = Path(persist_path or DEFAULT_VECTOR_DB_PATH)
        self._persist_path.mkdir(parents=True, exist_ok=True)

        self._dimension = dimension
        self._np = np
        self._faiss = faiss
        self._model = TextEmbedding(model_name=model_name)
        self._index = faiss.IndexFlatIP(dimension)
        self._id_map: List[str] = []
        self._documents: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._load()

        logger.info(f"FAISS initialized: {collection_name}")

    @property
    def backend_name(self) -> str:
        """Return the backend identifier string."""
        return "faiss"

    def _get_embedding(self, text: str) -> Any:
        """Generate normalized embedding for the given text."""
        from aura_cli.core.embeddings.client import get_embedding_client

        client = get_embedding_client()
        embedding_list = client.embed(text)

        if embedding_list is not None:
            embedding = self._np.array(embedding_list, dtype="float32")
        else:
            embedding = self._np.array(
                next(iter(self._model.embed([text]))), dtype="float32"
            )

        norm = self._np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def _generate_id(self, content: str) -> str:
        """Generate a short deterministic-ish ID from content and current timestamp."""
        return hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()[:16]

    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """Add document to FAISS."""
        doc_id = doc_id or self._generate_id(content)
        embedding = self._get_embedding(content)
        with self._lock:
            self._index.add(self._np.array([embedding]).astype("float32"))
            self._id_map.append(doc_id)
            self._documents[doc_id] = {
                "content": content,
                "metadata": metadata or {},
            }
            self._save()
        return doc_id

    def add_many(
        self,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add multiple documents."""
        if ids is None:
            ids = [self._generate_id(c) for c in contents]
        if metadatas is None:
            metadatas = [{} for _ in contents]
        from aura_cli.core.embeddings.client import get_embedding_client

        client = get_embedding_client()
        batch_embeddings = client.embed_batch(contents)
        if batch_embeddings is not None:
            embeddings = [
                self._np.array(emb, dtype="float32") for emb in batch_embeddings
            ]
        else:
            embeddings = []
            for content in contents:
                embedding = self._get_embedding(content)
                embeddings.append(embedding)
        with self._lock:
            for i, embedding in enumerate(embeddings):
                norm = self._np.linalg.norm(embedding)
                if norm > 0:
                    embeddings[i] = embedding / norm
                self._id_map.append(ids[i])
                self._documents[ids[i]] = {
                    "content": contents[i],
                    "metadata": metadatas[i],
                }
            self._index.add(self._np.array(embeddings).astype("float32"))
            self._save()
        return ids

    def search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar documents."""
        query_embedding = self._get_embedding(query)
        with self._lock:
            if not self._id_map:
                return []
            k = min(limit * 2, len(self._id_map))  # Get more for filtering
            scores, indices = self._index.search(
                self._np.array([query_embedding]).astype("float32"), k
            )
            results = []
            for score, idx in zip(scores[0], indices[0], strict=False):
                if idx < 0 or idx >= len(self._id_map):
                    continue
                doc_id = self._id_map[idx]
                doc = self._documents.get(doc_id)
                if not doc:
                    continue
                if filter_metadata:
                    match = all(
                        doc.get("metadata", {}).get(k) == v
                        for k, v in filter_metadata.items()
                    )
                    if not match:
                        continue
                results.append(
                    SearchResult(
                        id=doc_id,
                        content=doc["content"],
                        score=float(score),
                        metadata=doc.get("metadata", {}),
                    )
                )
                if len(results) >= limit:
                    break
            return results

    def get(self, doc_id: str) -> Optional[SearchResult]:
        """Get document by ID."""
        with self._lock:
            doc = self._documents.get(doc_id)
            if doc:
                return SearchResult(
                    id=doc_id,
                    content=doc["content"],
                    score=1.0,
                    metadata=doc.get("metadata", {}),
                )
            return None

    def delete(self, doc_id: str) -> bool:
        """Delete document (marks as deleted, index not rebuilt)."""
        with self._lock:
            if doc_id in self._documents:
                del self._documents[doc_id]
                self._save()
                return True
            return False

    def clear(self) -> None:
        """Clear all documents and reset index."""
        with self._lock:
            self._index = self._faiss.IndexFlatIP(self._dimension)
            self._id_map = []
            self._documents = {}
            self._save()

    def count(self) -> int:
        """Get document count."""
        with self._lock:
            return len(self._documents)

    def _save(self) -> None:
        """Publish a coherent FAISS index/metadata generation atomically."""
        with self._lock:
            generation = f"{time.time_ns()}-{os.getpid()}"
            index_name = f"{self._collection_name}.{generation}.index"
            meta_name = f"{self._collection_name}.{generation}.json"
            manifest_path = (
                self._persist_path / f"{self._collection_name}.manifest.json"
            )
            index_path = self._persist_path / index_name
            meta_path = self._persist_path / meta_name
            temporary_index: Optional[Path] = None
            temporary_meta: Optional[Path] = None
            temporary_manifest: Optional[Path] = None
            try:
                temporary_index = self._persist_path / f".{index_name}.tmp"
                self._faiss.write_index(self._index, str(temporary_index))
                with temporary_index.open("rb") as handle:
                    os.fsync(handle.fileno())
                os.replace(temporary_index, index_path)
                temporary_index = None

                metadata = {"id_map": self._id_map, "documents": self._documents}
                temporary_meta = self._persist_path / f".{meta_name}.tmp"
                with temporary_meta.open("w", encoding="utf-8") as handle:
                    json.dump(metadata, handle, ensure_ascii=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_meta, meta_path)
                temporary_meta = None

                manifest = {
                    "format_version": 1,
                    "index": index_name,
                    "metadata": meta_name,
                    "index_sha256": self._sha256_file(index_path),
                    "metadata_sha256": self._sha256_file(meta_path),
                }
                temporary_manifest = self._persist_path / (
                    f".{manifest_path.name}.{generation}.tmp"
                )
                with temporary_manifest.open("w", encoding="utf-8") as handle:
                    json.dump(manifest, handle, ensure_ascii=False, indent=2)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_manifest, manifest_path)
                temporary_manifest = None
            finally:
                for temporary_path in (
                    temporary_index,
                    temporary_meta,
                    temporary_manifest,
                ):
                    if temporary_path is not None:
                        temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _load(self) -> None:
        """Load the last verified generation, with legacy-file fallback."""
        manifest_path = self._persist_path / f"{self._collection_name}.manifest.json"
        if manifest_path.exists():
            try:
                with manifest_path.open(encoding="utf-8") as handle:
                    manifest = json.load(handle)
                index_name = manifest["index"]
                meta_name = manifest["metadata"]
                if (
                    Path(index_name).name != index_name
                    or Path(meta_name).name != meta_name
                    or manifest.get("format_version") != 1
                ):
                    raise ValueError("invalid FAISS manifest paths or version")
                index_path = self._persist_path / index_name
                meta_path = self._persist_path / meta_name
                if (
                    not index_path.is_file()
                    or not meta_path.is_file()
                    or self._sha256_file(index_path) != manifest["index_sha256"]
                    or self._sha256_file(meta_path) != manifest["metadata_sha256"]
                ):
                    raise ValueError("FAISS generation checksum mismatch")
                self._index = self._faiss.read_index(str(index_path))
                with meta_path.open(encoding="utf-8") as handle:
                    data = json.load(handle)
                self._id_map = data.get("id_map", [])
                self._documents = data.get("documents", {})
                logger.debug(
                    f"Loaded verified FAISS index: {len(self._documents)} documents"
                )
                return
            except Exception as e:
                logger.warning(f"Failed to load FAISS manifest: {e}")

        index_path = self._persist_path / f"{self._collection_name}.index"
        meta_path = self._persist_path / f"{self._collection_name}.json"
        if index_path.exists() and meta_path.exists():
            try:
                self._index = self._faiss.read_index(str(index_path))
                with meta_path.open(encoding="utf-8") as handle:
                    data = json.load(handle)
                self._id_map = data.get("id_map", [])
                self._documents = data.get("documents", {})
                logger.debug(
                    f"Loaded legacy FAISS index: {len(self._documents)} documents"
                )
            except Exception as e:
                logger.warning(f"Failed to load legacy FAISS index: {e}")


class KeywordVectorStore(VectorStore):
    """
    Simple keyword-based search fallback.

    Used when neither ChromaDB nor FAISS is available.
    No external dependencies required.
    """

    def __init__(
        self,
        collection_name: str = "aura_memory",
        persist_path: Optional[str] = None,
    ):
        """Initialize keyword store."""
        self._collection_name = collection_name
        self._persist_path = Path(persist_path or DEFAULT_VECTOR_DB_PATH)
        self._persist_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self._documents: Dict[str, Dict[str, Any]] = {}
        self._load()

        logger.info(f"Keyword store initialized: {collection_name} (no vector search)")

    @property
    def backend_name(self) -> str:
        """Return the backend identifier string."""
        return "keyword"

    def _generate_id(self, content: str) -> str:
        """Generate a deterministic short ID from content and timestamp."""
        return hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()[:16]

    def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """Add document."""
        doc_id = doc_id or self._generate_id(content)
        with self._lock:
            self._documents[doc_id] = {
                "content": content,
                "metadata": metadata or {},
                "timestamp": time.time(),
            }
            self._save()
        return doc_id

    def add_many(
        self,
        contents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add multiple documents."""
        if ids is None:
            ids = [self._generate_id(c) for c in contents]
        if metadatas is None:
            metadatas = [{} for _ in contents]

        with self._lock:
            for i, content in enumerate(contents):
                self._documents[ids[i]] = {
                    "content": content,
                    "metadata": metadatas[i],
                    "timestamp": time.time(),
                }

            self._save()
        return ids

    def search(
        self,
        query: str,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search by keyword matching."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        with self._lock:
            documents = list(self._documents.items())

        results = []
        for doc_id, doc in documents:
            content = doc["content"]
            content_lower = content.lower()

            # Apply metadata filter
            if filter_metadata:
                match = all(
                    doc.get("metadata", {}).get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue

            content_words = set(content_lower.split())
            overlap = len(query_words & content_words)

            if overlap > 0 or query_lower in content_lower:
                score = overlap / max(len(query_words), 1)
                if query_lower in content_lower:
                    score += 0.5

                results.append(
                    SearchResult(
                        id=doc_id,
                        content=content,
                        score=min(1.0, score),
                        metadata=doc.get("metadata", {}),
                    )
                )

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def get(self, doc_id: str) -> Optional[SearchResult]:
        """Get document by ID."""
        with self._lock:
            doc = self._documents.get(doc_id)
        if doc:
            return SearchResult(
                id=doc_id,
                content=doc["content"],
                score=1.0,
                metadata=doc.get("metadata", {}),
            )
        return None

    def delete(self, doc_id: str) -> bool:
        """Delete document."""
        with self._lock:
            if doc_id in self._documents:
                del self._documents[doc_id]
                self._save()
                return True
        return False

    def clear(self) -> None:
        """Clear all documents."""
        with self._lock:
            self._documents = {}
            self._save()

    def count(self) -> int:
        """Get document count."""
        with self._lock:
            return len(self._documents)

    def _save(self) -> None:
        """Save to disk atomically under the store lock."""
        with self._lock:
            self._save_locked()

    def _save_locked(self) -> None:
        """Write the current documents atomically while locked."""
        path = self._persist_path / f"{self._collection_name}.json"
        temporary_path: Optional[Path] = None
        try:
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as f:
                json.dump(self._documents, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary_path, path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def _load(self) -> None:
        """Load from disk."""
        path = self._persist_path / f"{self._collection_name}.json"
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    self._documents = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load keyword store: {e}")
                self._documents = {}


_available_backend: Optional[str] = None


def detect_best_backend() -> str:
    """
    Detect the best available vector store backend.

    Checks user configuration first, then falls back to auto-detection.

    Returns:
        Backend name: 'chromadb', 'faiss', or 'simple'
    """
    global _available_backend

    try:
        from aura_cli.core.config import get_config_manager

        config = get_config_manager()
        configured_backend = config.get("vector_backend")
        if configured_backend:
            _available_backend = configured_backend
            logger.info(f"Vector store backend (from config): {configured_backend}")
            return _available_backend
    except Exception as e:
        logger.debug(f"Could not read vector_backend from config: {e}")

    if _available_backend is not None:
        return _available_backend

    try:
        import chromadb as _chromadb

        assert _chromadb is not None
        _available_backend = "chromadb"
        logger.info("Vector store backend (auto-detected): ChromaDB")
        return _available_backend
    except ImportError as _e:
        pass  # silenced: {_e}

    try:
        import faiss as _faiss

        assert _faiss is not None
        _available_backend = "faiss"
        logger.info("Vector store backend (auto-detected): FAISS")
        return _available_backend
    except ImportError as _e:
        pass  # silenced: {_e}

    _available_backend = "simple"
    logger.warning(
        "Vector store backend (fallback): Simple (keyword-based, no vector embeddings)"
    )
    return _available_backend


def create_vector_store(
    collection_name: str = "aura_memory",
    persist_path: Optional[str] = None,
    backend: Optional[str] = None,
) -> VectorStore:
    """
    Factory function to create the best available vector store.

    Args:
        collection_name: Name of the collection
        persist_path: Path for persistent storage
        backend: Force specific backend ('chromadb', 'faiss', 'keyword')

    Returns:
        VectorStore instance

    Example:
        store = create_vector_store("my_memories")
        store.add("Important information", metadata={"type": "note"})
        results = store.search("information")
    """
    backend = backend or detect_best_backend()

    if backend == "chromadb":
        try:
            return ChromaDBVectorStore(collection_name, persist_path)
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}, falling back")
            return create_vector_store(collection_name, persist_path, "faiss")

    elif backend == "faiss":
        try:
            return FAISSVectorStore(collection_name, persist_path)
        except Exception as e:
            logger.warning(f"FAISS initialization failed: {e}, falling back")
            return create_vector_store(collection_name, persist_path, "keyword")

    else:
        return KeywordVectorStore(collection_name, persist_path)
