"""
Embeddings Cache for Aura CLI.

This module implements a specialized cache for vector embeddings,
optimized for efficient storage of numpy arrays.

Features:
    - Cache embeddings by text and model
    - Efficient storage with numpy
    - Similarity search in cache
    - Long TTL (embeddings are deterministic)

Usage:
    >>> from aura_cli.core.cache.embedding_cache import get_embedding_cache
    >>> cache = get_embedding_cache()
    >>> embedding = cache.get("Hello world", "text-embedding-ada-002")
    >>> if not embedding:
    ...     embedding = generate_embedding("Hello world")
    ...     cache.set("Hello world", "text-embedding-ada-002", embedding)
"""

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from aura_cli.core.logger import get_logger
from aura_cli.core.paths import aura_path

logger = get_logger(__name__)

try:
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.debug("NumPy not available - embedding cache will use JSON serialization")


class EmbeddingCache:
    """
    Specialized cache for vector embeddings.

    Optimized for efficient storage of high-dimensional vectors.
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_size_mb: int = 200,
        ttl_days: int = 30,
    ):
        """Initialise the embedding cache."""
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = aura_path("embeddings_cache")

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl_seconds = ttl_days * 24 * 3600

        self.index_file = self.cache_dir / "index.json"
        self.index: Dict[str, Dict] = {}

        self._load_index()

        logger.info(f"EmbeddingCache initialized: {len(self.index)} embeddings")

    def _load_index(self):
        """Load index from disk"""
        if self.index_file.exists():
            try:
                with open(self.index_file) as f:
                    self.index = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading embeddings index: {e}")
                self.index = {}

    def _save_index(self):
        """Save index to disk"""
        try:
            with open(self.index_file, "w") as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving embeddings index: {e}")

    def _generate_key(self, text: str, model: str) -> str:
        """Generate a cache key for a text input."""
        combined = f"{model}:{text}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]

    def _get_cache_path(self, key: str) -> Path:
        """Return the cache file path."""
        ext = ".npy" if NUMPY_AVAILABLE else ".json"
        return self.cache_dir / f"{key}{ext}"

    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Return an embedding from the cache, or None if not found."""
        key = self._generate_key(text, model)

        if key not in self.index:
            return None

        cache_file = self._get_cache_path(key)

        if not cache_file.exists():
            del self.index[key]
            self._save_index()
            return None

        try:
            if NUMPY_AVAILABLE and cache_file.suffix == ".npy":
                embedding = np.load(cache_file).tolist()
            else:
                with open(cache_file) as f:
                    embedding = json.load(f)

            self.index[key]["access_count"] = self.index[key].get("access_count", 0) + 1
            self._save_index()

            logger.debug(f"Embedding cache hit: {text[:30]}...")
            return embedding

        except Exception as e:
            logger.error(f"Error reading embedding from cache: {e}")
            return None

    def set(self, text: str, model: str, embedding: List[float]):
        """
        Armazena embedding no cache.

        Args:
            text: Texto original
            model: Nome do modelo de embedding
            embedding: Vetor de embedding
        """
        key = self._generate_key(text, model)
        cache_file = self._get_cache_path(key)

        try:
            if NUMPY_AVAILABLE:
                np.save(cache_file, np.array(embedding, dtype=np.float32))
            else:
                with open(cache_file, "w") as f:
                    json.dump(embedding, f)

            self.index[key] = {
                "model": model,
                "text_hash": hashlib.md5(
                    text.encode(), usedforsecurity=False
                ).hexdigest(),
                "text_preview": text[:50],
                "dimensions": len(embedding),
                "size": cache_file.stat().st_size,
                "access_count": 0,
            }
            self._save_index()

            logger.debug(f"Embedding cacheado: {text[:30]}... ({len(embedding)} dims)")

            self._cleanup_if_needed()

        except Exception as e:
            logger.error(f"Error saving embedding: {e}")

    def _cleanup_if_needed(self):
        """Remove embeddings antigos se cache exceder limite."""
        total_size = sum(entry.get("size", 0) for entry in self.index.values())

        if total_size <= self.max_size_bytes:
            return

        # Ordenar por acesso (menos acessados primeiro)
        sorted_keys = sorted(
            self.index.keys(), key=lambda k: self.index[k].get("access_count", 0)
        )

        target_size = int(self.max_size_bytes * 0.8)
        removed = 0

        while total_size > target_size and sorted_keys:
            key = sorted_keys.pop(0)
            entry = self.index[key]

            cache_file = self._get_cache_path(key)
            if cache_file.exists():
                cache_file.unlink()

            total_size -= entry.get("size", 0)
            del self.index[key]
            removed += 1

        if removed > 0:
            self._save_index()
            logger.info(f"Embedding cache cleanup: {removed} embeddings removed")

    def get_or_compute(
        self, text: str, model: str, compute_fn: Callable[..., Any]
    ) -> List[float]:
        """Get a cached embedding or compute and cache it."""
        cached = self.get(text, model)
        if cached is not None:
            return cached

        embedding = compute_fn(text)
        self.set(text, model, embedding)
        return embedding

    def batch_get(
        self, texts: List[str], model: str
    ) -> Tuple[Dict[str, List[float]], List[str]]:
        """Get or compute embeddings for a batch of texts."""
        hits = {}
        misses = []

        for text in texts:
            embedding = self.get(text, model)
            if embedding is not None:
                hits[text] = embedding
            else:
                misses.append(text)

        return hits, misses

    def get_stats(self) -> Dict[str, Any]:
        """Return embedding cache statistics as a dict."""
        total_size = sum(entry.get("size", 0) for entry in self.index.values())

        models: dict[str, int] = {}
        for entry in self.index.values():
            model = entry.get("model", "unknown")
            models[model] = models.get(model, 0) + 1

        return {
            "total_embeddings": len(self.index),
            "size_mb": round(total_size / 1024 / 1024, 2),
            "max_size_mb": self.max_size_bytes / 1024 / 1024,
            "utilization_percent": round(total_size / self.max_size_bytes * 100, 1),
            "by_model": models,
            "numpy_available": NUMPY_AVAILABLE,
        }

    def clear(self) -> int:
        """Limpa todo o cache de embeddings."""
        count = len(self.index)

        for key in list(self.index.keys()):
            cache_file = self._get_cache_path(key)
            if cache_file.exists():
                cache_file.unlink()

        self.index.clear()
        self._save_index()

        logger.info(f"Embedding cache cleared: {count} embeddings removed")
        return count


_embedding_cache: Optional[EmbeddingCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """Return the global embedding cache singleton."""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache
