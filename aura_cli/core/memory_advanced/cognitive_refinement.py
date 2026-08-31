"""
Auxiliary cognitive refinement for the legacy advanced vector stack.

Adds three capabilities on top of VectorStorage:

1. Re-ranking  — boosts results by recency and access frequency
2. Temporal decay — reduces relevance of old, unaccessed memories
3. Consolidation — merges near-duplicate documents (cosine sim > threshold)

These are non-destructive and still useful for explicit advanced semantic
flows, but they do not define the canonical notebook/memory behavior of the
product runtime.

Usage:
    >>> from aura_cli.core.memory_advanced.cognitive_refinement import CognitiveRefinement
    >>> cr = CognitiveRefinement(storage)
    >>> refined = cr.rerank(index_id, raw_results, query_vector)
    >>> cr.apply_decay(index_id)
    >>> merged = cr.consolidate(index_id)
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import List, Optional, Tuple

import numpy as np

from aura_cli.core.logger import get_logger
from aura_cli.core.memory_advanced.vector_storage import VectorDocument, VectorStorage

logger = get_logger(__name__)

# Constants

DECAY_HALF_LIFE_DAYS: float = 7.0  # score halves every 7 days
CONSOLIDATION_THRESHOLD: float = 0.95  # cosine sim above this → merge
RERANK_RECENCY_WEIGHT: float = 0.15  # weight of recency bonus in final score
RERANK_FREQUENCY_WEIGHT: float = 0.10  # weight of access-frequency bonus


# Metadata helpers


def _now() -> float:
    """Return current UTC timestamp as float."""
    return time.time()


def _get_created_at(doc: VectorDocument) -> float:
    """Extract creation timestamp from a memory entry."""
    return float(doc.metadata.get("created_at", _now()))


def _get_accessed_at(doc: VectorDocument) -> float:
    """Extract last access timestamp from a memory entry."""
    return float(doc.metadata.get("accessed_at", _get_created_at(doc)))


def _get_access_count(doc: VectorDocument) -> int:
    """Extract access count from a memory entry."""
    return int(doc.metadata.get("access_count", 0))


def _touch(doc: VectorDocument) -> None:
    """Update access metadata in-place."""
    doc.metadata["accessed_at"] = _now()
    doc.metadata["access_count"] = _get_access_count(doc) + 1


# Core class


@dataclass
class RefinedResult:
    """Search result after cognitive re-ranking."""

    doc: VectorDocument
    raw_score: float
    refined_score: float
    recency_bonus: float = 0.0
    frequency_bonus: float = 0.0


class CognitiveRefinement:
    """
    Applies cognitive refinement to VectorStorage search results.

    Attributes:
        storage: The underlying VectorStorage instance.
        decay_half_life: Days until a memory's relevance halves.
        consolidation_threshold: Cosine similarity above which docs are merged.
    """

    def __init__(
        self,
        storage: VectorStorage,
        decay_half_life: float = DECAY_HALF_LIFE_DAYS,
        consolidation_threshold: float = CONSOLIDATION_THRESHOLD,
    ) -> None:
        """Initialize the instance."""
        self.storage = storage
        self.decay_half_life = decay_half_life
        self.consolidation_threshold = consolidation_threshold

    # 1. Re-ranking

    def rerank(
        self,
        index_id: str,
        raw_results: List[Tuple[VectorDocument, float]],
        *,
        touch: bool = True,
    ) -> List[RefinedResult]:
        """
        Re-rank raw search results by blending similarity with recency and frequency.

        Args:
            index_id: Index the results came from (unused currently, for future use).
            raw_results: List of (VectorDocument, cosine_similarity) pairs.
            touch: If True, update access metadata for returned documents.

        Returns:
            Sorted list of RefinedResult, highest refined_score first.
        """
        if not raw_results:
            return []

        now = _now()
        refined: List[RefinedResult] = []

        for doc, raw_score in raw_results:
            # Recency bonus: exponential decay from last access
            age_days = (now - _get_accessed_at(doc)) / 86400.0
            recency_bonus = RERANK_RECENCY_WEIGHT * (
                2 ** (-age_days / self.decay_half_life)
            )

            # Frequency bonus: log-scaled access count
            freq = _get_access_count(doc)
            frequency_bonus = RERANK_FREQUENCY_WEIGHT * (np.log1p(freq) / np.log1p(100))

            refined_score = raw_score + recency_bonus + frequency_bonus

            if touch:
                _touch(doc)

            refined.append(
                RefinedResult(
                    doc=doc,
                    raw_score=raw_score,
                    refined_score=refined_score,
                    recency_bonus=recency_bonus,
                    frequency_bonus=frequency_bonus,
                )
            )

        refined.sort(key=lambda r: r.refined_score, reverse=True)
        logger.debug(f"Reranked {len(refined)} results for index '{index_id}'")
        return refined

    # 2. Temporal decay

    def apply_decay(self, index_id: str) -> int:
        """
        Apply temporal decay to all documents in an index.

        Adds/updates a `decay_score` metadata field. Documents with
        decay_score < 0.01 are candidates for pruning (not removed here).

        Args:
            index_id: Index to apply decay to.

        Returns:
            Number of documents updated.
        """
        index = self.storage.indices.get(index_id)
        if index is None:
            logger.warning(f"apply_decay: index '{index_id}' not found")
            return 0

        now = _now()
        updated = 0
        for doc in index.documents:
            age_days = (now - _get_accessed_at(doc)) / 86400.0
            decay_score = 2 ** (-age_days / self.decay_half_life)
            doc.metadata["decay_score"] = round(decay_score, 4)
            updated += 1

        logger.info(f"Applied decay to {updated} documents in index '{index_id}'")
        return updated

    def prune_decayed(self, index_id: str, min_decay_score: float = 0.01) -> int:
        """
        Remove documents whose decay_score is below min_decay_score.

        Args:
            index_id: Index to prune.
            min_decay_score: Threshold below which documents are removed.

        Returns:
            Number of documents removed.
        """
        index = self.storage.indices.get(index_id)
        if index is None:
            return 0

        before = len(index.documents)
        surviving = [
            doc
            for doc in index.documents
            if doc.metadata.get("decay_score", 1.0) >= min_decay_score
        ]
        removed = before - len(surviving)

        if removed > 0:
            index.documents = surviving
            # Rebuild vector matrix
            if surviving:
                index.vectors = np.stack([d.vector for d in surviving])
            else:
                index.vectors = None
            logger.info(f"Pruned {removed} decayed documents from index '{index_id}'")

        return removed

    # 3. Consolidation

    def consolidate(self, index_id: str) -> int:
        """
        Merge near-duplicate documents (cosine similarity > threshold).

        The merged document keeps the content of the higher-access document
        and accumulates access counts. The lower-access duplicate is removed.

        Args:
            index_id: Index to consolidate.

        Returns:
            Number of documents removed by consolidation.
        """
        index = self.storage.indices.get(index_id)
        if index is None or not index.documents or index.vectors is None:
            return 0

        n = len(index.documents)
        if n < 2:
            return 0

        # Normalize vectors for cosine similarity
        vecs = index.vectors.astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normed = vecs / norms

        # Find pairs above threshold (upper triangle only)
        sim_matrix = np.dot(normed, normed.T)
        to_remove: set = set()

        for i in range(n):
            if i in to_remove:
                continue
            for j in range(i + 1, n):
                if j in to_remove:
                    continue
                if sim_matrix[i, j] >= self.consolidation_threshold:
                    # Keep the one with higher access count
                    keep, drop = (
                        (i, j)
                        if (
                            _get_access_count(index.documents[i])
                            >= _get_access_count(index.documents[j])
                        )
                        else (j, i)
                    )
                    # Merge access count into keeper
                    index.documents[keep].metadata["access_count"] = _get_access_count(
                        index.documents[keep]
                    ) + _get_access_count(index.documents[drop])
                    to_remove.add(drop)

        if not to_remove:
            return 0

        surviving_idx = [i for i in range(n) if i not in to_remove]
        index.documents = [index.documents[i] for i in surviving_idx]
        index.vectors = vecs[surviving_idx]

        logger.info(
            f"Consolidated index '{index_id}': removed {len(to_remove)} near-duplicates "
            f"(threshold={self.consolidation_threshold})"
        )
        return len(to_remove)

    # Convenience: full refinement pipeline

    def refine_search(
        self,
        index_id: str,
        raw_results: List[Tuple[VectorDocument, float]],
    ) -> List[RefinedResult]:
        """Run rerank on raw results (decay/consolidation are separate batch ops)."""
        return self.rerank(index_id, raw_results)


def get_cognitive_refinement(
    storage: Optional[VectorStorage] = None,
) -> CognitiveRefinement:
    """Create a refinement service around an explicit or fresh vector store."""
    return CognitiveRefinement(storage or VectorStorage())
