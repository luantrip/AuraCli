"""Semantic similarity for refactoring — duplicate code detection.

SemanticSimilarityAnalyzer uses code-specialised embeddings (CodeBERTa via
EmbeddingGenerator) and cosine similarity to find duplicate or near-duplicate
code snippets regardless of textual differences. Configurable threshold
(default 0.85). find_duplicate_code_semantic() is the main entry point.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from aura_cli.core.logger import get_logger
from aura_cli.core.semantic.embeddings import EmbeddingGenerator, EmbeddingModel

logger = get_logger(__name__)


@dataclass
class CodeSimilarity:
    """Similarity between code snippets.

    Attributes:
        code1: First snippet
        code2: Second snippet
        similarity_score: Similarity score (0-1)
        file1: File of first snippet
        file2: File of second snippet
        line1: Line of first snippet
        line2: Line of second snippet
    """

    code1: str
    code2: str
    similarity_score: float
    file1: str = ""
    file2: str = ""
    line1: int = 0
    line2: int = 0


class SemanticSimilarityAnalyzer:
    """Finds duplicate or near-duplicate code using embeddings."""

    def __init__(self, similarity_threshold: float = 0.85):
        """Initialise the semantic similarity analyser."""
        self.similarity_threshold = similarity_threshold
        self.embedding_generator = EmbeddingGenerator(
            model=EmbeddingModel.FASTEMBED, dimension=384
        )
        logger.info(
            f"SemanticSimilarityAnalyzer initialized (threshold: {similarity_threshold})"
        )

    def find_duplicate_code(
        self,
        code_snippets: List[Dict[str, Any]],
        min_similarity: Optional[float] = None,
    ) -> List[CodeSimilarity]:
        """Find duplicate code using semantic similarity."""
        threshold = min_similarity or self.similarity_threshold

        if len(code_snippets) < 2:
            return []

        logger.info(f"Analisando {len(code_snippets)} trechos para duplicação")

        import numpy as np

        from aura_cli.core.embeddings.client import get_embedding_client

        codes = [snippet["code"] for snippet in code_snippets]
        client = get_embedding_client()
        batch_embeddings = client.embed_batch(codes)

        if batch_embeddings is not None:
            embeddings = [np.array(emb, dtype="float32") for emb in batch_embeddings]
        else:
            embeddings = self.embedding_generator.generate_batch(codes)  # type: ignore[assignment]

        similarities = []
        for i in range(len(code_snippets)):
            for j in range(i + 1, len(code_snippets)):
                similarity = self._cosine_similarity(embeddings[i], embeddings[j])

                if similarity >= threshold:
                    similarities.append(
                        CodeSimilarity(
                            code1=code_snippets[i]["code"],
                            code2=code_snippets[j]["code"],
                            similarity_score=similarity,
                            file1=code_snippets[i].get("file", ""),
                            file2=code_snippets[j].get("file", ""),
                            line1=code_snippets[i].get("line", 0),
                            line2=code_snippets[j].get("line", 0),
                        )
                    )

        logger.info(
            f"Encontradas {len(similarities)} similaridades acima de {threshold}"
        )

        return similarities

    def find_similar_code(
        self, query_code: str, code_snippets: List[Dict[str, Any]], top_k: int = 5
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Find code similar to a query snippet."""
        if not code_snippets:
            return []

        import numpy as np

        from aura_cli.core.embeddings.client import get_embedding_client

        client = get_embedding_client()
        query_embedding_list = client.embed(query_code)

        if query_embedding_list is not None:
            query_embedding = np.array(query_embedding_list, dtype="float32")
        else:
            query_embedding = self.embedding_generator.generate(query_code)

        codes = [snippet["code"] for snippet in code_snippets]
        batch_embeddings = client.embed_batch(codes)

        if batch_embeddings is not None:
            embeddings = [np.array(emb, dtype="float32") for emb in batch_embeddings]
        else:
            embeddings = self.embedding_generator.generate_batch(codes)  # type: ignore[assignment]

        similarities = []
        for i, snippet in enumerate(code_snippets):
            similarity = self._cosine_similarity(query_embedding, embeddings[i])
            similarities.append((snippet, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def _cosine_similarity(self, vec1: Any, vec2: Any) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np

        if not isinstance(vec1, np.ndarray):
            vec1 = np.array(vec1)
        if not isinstance(vec2, np.ndarray):
            vec2 = np.array(vec2)

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        vec1_norm = vec1 / norm1
        vec2_norm = vec2 / norm2

        similarity = np.dot(vec1_norm, vec2_norm)

        return max(0.0, min(1.0, (similarity + 1) / 2))


def find_duplicate_code_semantic(
    code_snippets: List[Dict[str, Any]], similarity_threshold: float = 0.85
) -> List[CodeSimilarity]:
    """Find semantically duplicate code in a codebase."""
    analyzer = SemanticSimilarityAnalyzer(similarity_threshold=similarity_threshold)
    return analyzer.find_duplicate_code(code_snippets)
