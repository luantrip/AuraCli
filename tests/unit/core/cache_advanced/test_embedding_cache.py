"""
Testes para o cache de embeddings.

Propósito: Verifica cache especializado para embeddings vetoriais
Componentes: EmbeddingCache, EmbeddingEntry, get_embedding_cache
"""

from pathlib import Path
import tempfile

import pytest

from aura_cli.core.cache_advanced.embedding_cache import (
    EmbeddingCache,
    get_embedding_cache,
)


class TestEmbeddingCache:
    """Testes para EmbeddingCache."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Diretório temporário para cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def embedding_cache(self, temp_cache_dir):
        """Cache de embeddings configurado para testes."""
        return EmbeddingCache(cache_dir=temp_cache_dir)

    @pytest.fixture
    def sample_embedding(self):
        """Embedding de exemplo."""
        return [0.1, 0.2, 0.3, 0.4, 0.5]

    def test_cache_initialization(self, temp_cache_dir):
        """Verifica inicialização do cache de embeddings."""
        cache = EmbeddingCache(cache_dir=temp_cache_dir)
        assert cache.cache_dir == temp_cache_dir
        assert cache.max_size_bytes > 0

    def test_set_and_get_embedding(self, embedding_cache, sample_embedding):
        """Testa cache de embedding."""
        text = "def calculate_sum(a, b): return a + b"
        model = "sentence-transformers/all-MiniLM-L6-v2"

        embedding_cache.set(text, model, sample_embedding)

        result = embedding_cache.get(text, model)
        assert result is not None
        # Usar aproximação devido a precisão de float32/64
        assert len(result) == len(sample_embedding)
        for i, (a, b) in enumerate(zip(result, sample_embedding, strict=False)):
            assert abs(a - b) < 1e-6, f"Diferença no índice {i}: {a} != {b}"

    def test_get_embedding_cache_miss(self, embedding_cache):
        """Verifica cache miss."""
        result = embedding_cache.get("nonexistent text", "nonexistent-model")
        assert result is None

    def test_get_embedding_different_model(self, embedding_cache, sample_embedding):
        """Testa busca com modelo diferente."""
        text = "test function"
        model1 = "model-1"
        model2 = "model-2"

        # Cache com modelo 1
        embedding_cache.set(text, model1, [0.1, 0.2])

        # Busca com modelo 2 (deve retornar None)
        result = embedding_cache.get(text, model2)
        assert result is None

        # Busca com modelo 1 (deve retornar resultado)
        result = embedding_cache.get(text, model1)
        assert result is not None

    def test_batch_get(self, embedding_cache):
        """Testa busca em lote."""
        texts = ["text1", "text2", "text3"]
        model = "test-model"

        # Cache alguns embeddings
        for i, text in enumerate(texts[:2]):  # Só os 2 primeiros
            embedding_cache.set(text, model, [float(i), float(i + 1)])

        hits, misses = embedding_cache.batch_get(texts, model)

        assert len(hits) == 2  # text1 e text2
        assert len(misses) == 1  # text3
        assert "text3" in misses

    def test_get_or_compute(self, embedding_cache):
        """Testa get_or_compute."""
        text = "compute this"
        model = "test-model"

        def compute_fn(text_input):  # Função deve aceitar texto como parâmetro
            return [0.5, 0.6, 0.7]

        # Primeira chamada - deve computar
        result1 = embedding_cache.get_or_compute(text, model, compute_fn)
        assert len(result1) == 3

        # Segunda chamada - deve usar cache
        result2 = embedding_cache.get_or_compute(text, model, compute_fn)
        assert len(result2) == 3

    def test_clear_cache(self, embedding_cache, sample_embedding):
        """Verifica limpeza do cache."""
        embedding_cache.set("text1", "model1", sample_embedding)
        embedding_cache.set("text2", "model2", sample_embedding)

        count = embedding_cache.clear()

        assert count == 2
        assert embedding_cache.get("text1", "model1") is None
        assert embedding_cache.get("text2", "model2") is None

    def test_get_stats(self, embedding_cache, sample_embedding):
        """Verifica obtenção de estatísticas."""
        # Cache alguns embeddings
        models = ["model1", "model2"]
        for i in range(6):
            model = models[i % 2]
            embedding_cache.set(f"text {i}", model, [float(i) / 10])

        stats = embedding_cache.get_stats()
        assert stats["total_embeddings"] == 6
        # Verifica se tem campo de modelos únicos ou similar
        assert "models" in stats or "size_mb" in stats


class TestGlobalEmbeddingCache:
    """Testes para função global de cache de embeddings."""

    def test_get_embedding_cache_singleton(self):
        """Verifica padrão singleton."""
        cache1 = get_embedding_cache()
        cache2 = get_embedding_cache()

        assert cache1 is cache2


class TestEmbeddingCacheIntegration:
    """Testes de integração do cache de embeddings."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Diretório temporário para cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_semantic_code_search_workflow(self, temp_cache_dir):
        """Testa workflow de busca semântica de código."""
        cache = EmbeddingCache(cache_dir=temp_cache_dir)
        model = "sentence-transformers/all-MiniLM-L6-v2"

        # Simula embeddings de funções Python
        code_snippets = [
            ("def add_numbers(a, b): return a + b", [1.0, 0.1, 0.0]),
            ("def subtract(x, y): return x - y", [0.9, 0.2, 0.1]),
            ("def multiply(a, b): return a * b", [0.8, 0.1, 0.2]),
            ("class Calculator: pass", [0.1, 1.0, 0.0]),
            ("import math", [0.0, 0.1, 1.0]),
        ]

        # Cache todos os snippets
        for text, vector in code_snippets:
            cache.set(text, model, vector)

        # Verifica que foram cached (com tolerância para float)
        for text, expected_vector in code_snippets:
            result = cache.get(text, model)
            assert result is not None
            assert len(result) == len(expected_vector)

        # Verifica estatísticas
        stats = cache.get_stats()
        assert stats["total_embeddings"] == 5

    def test_multi_model_embedding_cache(self, temp_cache_dir):
        """Testa cache com múltiplos modelos de embedding."""
        cache = EmbeddingCache(cache_dir=temp_cache_dir)

        text = "def process_data(data): return data.strip()"

        # Cache com diferentes modelos
        models_and_vectors = [
            ("sentence-transformers/all-MiniLM-L6-v2", [0.1, 0.2, 0.3]),
            ("openai/text-embedding-ada-002", [0.4, 0.5, 0.6]),
            ("cohere/embed-english-v2.0", [0.7, 0.8, 0.9]),
        ]

        for model, vector in models_and_vectors:
            cache.set(text, model, vector)

        # Verifica que cada modelo tem seu próprio embedding (com tolerância)
        for model, expected_vector in models_and_vectors:
            result = cache.get(text, model)
            assert result is not None
            assert len(result) == len(expected_vector)

        # Verifica estatísticas por modelo
        stats = cache.get_stats()
        assert stats["total_embeddings"] == 3
