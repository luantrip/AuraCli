"""
Auxiliary advanced embedding utilities for explicit semantic-search flows.

Provides advanced semantic search using embeddings:
- Integration with fastembed (ONNX Runtime) for high-quality embeddings
- True vector search using cosine similarity
- Deep semantic similarity beyond textual matching
- Persistent embedding cache for performance
- Indexing of functions, classes and docstrings
- Configurable threshold for relevance

This module is a support layer for opt-in semantic indexing/search use cases.
It is not the canonical memory or context architecture of the product.
"""

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.paths import ArtifactLayout

logger = get_logger(__name__)

# Optional dependency names are declared at module level (as Any) so that they are
# always present as attributes — importable, referenceable and monkeypatchable in
# tests — regardless of whether the optional `embeddings` extra is installed.
TextEmbedding: Any = None
np: Any = None

try:
    from fastembed import TextEmbedding  # type: ignore[no-redef]
    import numpy as np

    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False
    if not hasattr(logger, "_embeddings_warning_logged"):
        logger.warning("fastembed não instalado. Embeddings avançados limitados.")
        logger._embeddings_warning_logged = True  # type: ignore[attr-defined]


class EmbeddingIndex:
    """Embedding index for vector search."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: Optional[str] = None,
    ):
        """
        Initialize embedding index.

        Args:
            model_name: fastembed model name
            cache_dir: Cache directory
        """
        if not HAS_EMBEDDINGS:
            raise ImportError("fastembed é necessário para embeddings avançados")

        self.model_name = model_name
        self.cache_dir = (
            Path(cache_dir)
            if cache_dir
            else ArtifactLayout().project("embeddings_cache")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Carregando modelo de embeddings: {model_name}")
        self.model = TextEmbedding(model_name=model_name)
        # Determine embedding dimension by encoding a test string
        test_emb = next(iter(self.model.embed(["test"])))
        self.embedding_dim = len(test_emb)

        self.embeddings: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self._index_file = self.cache_dir / "embeddings_index.json"

        self._load_index()

    def add_text(
        self,
        text: str,
        file_path: str,
        line_number: Optional[int] = None,
        context_type: str = "code",
    ) -> str:
        """Add a text document and its embedding to the store."""
        text_hash = hashlib.md5(
            f"{file_path}:{line_number}:{text}".encode(), usedforsecurity=False
        ).hexdigest()
        doc_id = f"{file_path}:{line_number}:{text_hash[:8]}"

        embedding = np.array(next(iter(self.model.embed([text]))))

        self.embeddings[doc_id] = embedding
        self.metadata[doc_id] = {
            "text": text,
            "file_path": file_path,
            "line_number": line_number,
            "context_type": context_type,
            "indexed_at": datetime.now().isoformat(),
        }

        return doc_id

    def add_batch(
        self,
        texts: List[str],
        file_paths: List[str],
        line_numbers: Optional[List[int]] = None,
        context_types: Optional[List[str]] = None,
    ) -> List[str]:
        """Add a batch of documents and embeddings."""
        if line_numbers is None:
            line_numbers = [None] * len(texts)  # type: ignore[list-item]
        if context_types is None:
            context_types = ["code"] * len(texts)

        embeddings = np.array(list(self.model.embed(texts)))

        doc_ids = []
        for i, (text, file_path, line_num, ctx_type) in enumerate(
            zip(texts, file_paths, line_numbers, context_types, strict=True)
        ):
            text_hash = hashlib.md5(
                f"{file_path}:{line_num}:{text}".encode(), usedforsecurity=False
            ).hexdigest()
            doc_id = f"{file_path}:{line_num}:{text_hash[:8]}"

            self.embeddings[doc_id] = embeddings[i]
            self.metadata[doc_id] = {
                "text": text,
                "file_path": file_path,
                "line_number": line_num,
                "context_type": ctx_type,
                "indexed_at": datetime.now().isoformat(),
            }
            doc_ids.append(doc_id)

        return doc_ids

    def search(
        self, query: str, top_k: int = 10, threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Semantic search using vector similarity."""
        if not self.embeddings:
            return []

        query_embedding = np.array(next(iter(self.model.embed([query]))))

        similarities = []
        for doc_id, doc_embedding in self.embeddings.items():
            similarity = float(
                np.dot(query_embedding, doc_embedding)
                / (np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding))
            )

            if similarity >= threshold:
                similarities.append((similarity, doc_id))

        similarities.sort(reverse=True, key=lambda x: x[0])

        results = []
        for similarity, doc_id in similarities[:top_k]:
            result = {
                "doc_id": doc_id,
                "similarity": similarity,
                **self.metadata[doc_id],
            }
            results.append(result)

        return results

    def find_similar(self, text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Find texts similar to a reference text."""
        return self.search(text, top_k=top_k)

    def _save_index(self):
        """Save index in cache"""
        try:
            cache_data = {
                "format_version": 1,
                "embeddings": {k: v.tolist() for k, v in self.embeddings.items()},
                "metadata": self.metadata,
                "model_name": self.model_name,
                "embedding_dim": self.embedding_dim,
                "timestamp": datetime.now().isoformat(),
            }

            with open(self._index_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False)

            logger.info(
                f"Índice de embeddings salvo: {len(self.embeddings)} documents"
            )
        except Exception as e:
            logger.warning(f"Error saving index: {e}")

    def _load_index(self):
        """Load index from cache"""
        if not self._index_file.exists():
            return

        try:
            with open(self._index_file, encoding="utf-8") as f:
                cache_data = json.load(f)
            if cache_data.get("format_version") != 1:
                logger.warning("Versão desconhecida do índice de embeddings")
                return

            if cache_data.get("model_name") != self.model_name:
                logger.warning(
                    f"Modelo no cache ({cache_data.get('model_name')}) diferente do atual ({self.model_name}). Recriando índice."
                )
                return

            self.embeddings = {
                k: np.array(v) for k, v in cache_data.get("embeddings", {}).items()
            }
            self.metadata = cache_data.get("metadata", {})

            logger.info(f"Index loaded: {len(self.embeddings)} documents")
        except Exception as e:
            logger.warning(f"Error loading index: {e}")

    def save(self):
        """Save index"""
        self._save_index()

    def clear(self):
        """Limpa index"""
        self.embeddings.clear()
        self.metadata.clear()
        if self._index_file.exists():
            self._index_file.unlink()


class CodebaseEmbeddings:
    """Manages embeddings for an entire codebase."""

    def __init__(self, scope: str = ".", model_name: str = "BAAI/bge-small-en-v1.5"):
        """Initialise the codebase embeddings manager."""
        if not HAS_EMBEDDINGS:
            raise ImportError("fastembed é necessário")

        self.scope = Path(scope).resolve()
        self.index = EmbeddingIndex(
            model_name=model_name,
            cache_dir=str(ArtifactLayout(self.scope).project("embeddings_cache")),
        )
        self._indexed = False

    def index_codebase(self, force_reindex: bool = False) -> Dict[str, Any]:
        """Index the full codebase with embeddings."""
        if self._indexed and not force_reindex and self.index.embeddings:
            logger.info("Codebase já indexado. Use force_reindex=True para reindexar.")
            return {"total_documents": len(self.index.embeddings), "status": "cached"}

        logger.info(f"Indexando codebase com embeddings em {self.scope}")

        if force_reindex:
            self.index.clear()

        python_files = list(self.scope.rglob("*.py"))
        python_files = [f for f in python_files if not self._should_ignore(f)]

        logger.info(f"Found {len(python_files)} Python files")

        total_docs = 0
        for file_path in python_files:
            try:
                docs = self._index_file(file_path)
                total_docs += docs
            except Exception as e:
                logger.warning(f"Error indexing {file_path}: {e}")

        self.index.save()
        self._indexed = True

        logger.info(f"Indexação concluída: {total_docs} documents indexados")

        return {
            "total_files": len(python_files),
            "total_documents": total_docs,
            "status": "indexed",
        }

    def _should_ignore(self, path: Path) -> bool:
        """Return True if a file should be excluded from indexing."""
        ignore_patterns = {
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
            ".aura",
            "coding",
            "ops_workspace",
        }
        path_str = str(path)
        return any(pattern in path_str for pattern in ignore_patterns)

    def _index_file(self, file_path: Path) -> int:
        """Indexa um arquivo individual"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.warning(f"Não foi possível ler {file_path}: {e}")
            return 0

        relative_path = str(file_path.relative_to(self.scope))
        lines = content.split("\n")

        texts = []
        file_paths = []
        line_numbers = []
        context_types = []

        import ast

        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_text = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                    texts.append(func_text)
                    file_paths.append(relative_path)
                    line_numbers.append(node.lineno)
                    context_types.append("function")

                    if (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                    ):
                        docstring = node.body[0].value.value
                        texts.append(docstring)
                        file_paths.append(relative_path)
                        line_numbers.append(node.lineno)
                        context_types.append("docstring")

                elif isinstance(node, ast.ClassDef):
                    class_text = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                    texts.append(class_text)
                    file_paths.append(relative_path)
                    line_numbers.append(node.lineno)
                    context_types.append("class")

                    if (
                        node.body
                        and isinstance(node.body[0], ast.Expr)
                        and isinstance(node.body[0].value, ast.Constant)
                        and isinstance(node.body[0].value.value, str)
                    ):
                        docstring = node.body[0].value.value
                        texts.append(docstring)
                        file_paths.append(relative_path)
                        line_numbers.append(node.lineno)
                        context_types.append("docstring")
        except SyntaxError:
            for i, line in enumerate(lines, 1):
                if line.strip() and not line.strip().startswith("#"):
                    texts.append(line)
                    file_paths.append(relative_path)
                    line_numbers.append(i)
                    context_types.append("code")

        if texts:
            self.index.add_batch(texts, file_paths, line_numbers, context_types)

        return len(texts)

    def semantic_search(
        self, query: str, top_k: int = 10, threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Semantic search within the indexed codebase."""
        if not self._indexed:
            self.index_codebase()

        return self.index.search(query, top_k=top_k, threshold=threshold)


def index_codebase_embeddings(
    scope: str = ".",
    model_name: str = "BAAI/bge-small-en-v1.5",
    force_reindex: bool = False,
) -> Dict[str, Any]:
    """Index a codebase with semantic embeddings."""
    if not HAS_EMBEDDINGS:
        raise ImportError("fastembed é necessário. Instale com: pip install fastembed")

    embeddings = CodebaseEmbeddings(scope=scope, model_name=model_name)
    return embeddings.index_codebase(force_reindex=force_reindex)


def semantic_search_codebase(
    query: str, scope: str = ".", top_k: int = 10, threshold: float = 0.3
) -> List[Dict[str, Any]]:
    """Semantic search across the codebase using embeddings."""
    if not HAS_EMBEDDINGS:
        raise ImportError("fastembed é necessário. Instale com: pip install fastembed")

    embeddings = CodebaseEmbeddings(scope=scope)
    return embeddings.semantic_search(query, top_k=top_k, threshold=threshold)
