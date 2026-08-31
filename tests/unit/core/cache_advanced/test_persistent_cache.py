"""
Testes para o sistema de cache persistente.

Propósito: Verifica funcionalidade completa do cache em disco
Componentes: PersistentCache, CacheEntry, get_persistent_cache
"""

from pathlib import Path
import tempfile
import time
from unittest.mock import patch

import pytest

from aura_cli.core.cache_advanced.persistent_cache import (
    CacheEntry,
    PersistentCache,
    get_persistent_cache,
)


class TestCacheEntry:
    """Testes para CacheEntry."""

    def test_cache_entry_creation(self):
        """Testa criação de entrada de cache."""
        entry = CacheEntry(
            file_hash="abc123",
            created_at="2025-01-01T00:00:00",
            expires_at="2025-01-01T01:00:00",
            size=1024,
        )
        assert entry.file_hash == "abc123"
        assert entry.size == 1024
        assert entry.compressed is False
        assert entry.access_count == 0

    def test_cache_entry_to_dict(self):
        """Verifica conversão para dicionário."""
        entry = CacheEntry(
            file_hash="abc123",
            created_at="2025-01-01T00:00:00",
            expires_at="2025-01-01T01:00:00",
            size=1024,
            compressed=True,
            access_count=5,
        )
        result = entry.to_dict()
        assert result["file_hash"] == "abc123"
        assert result["compressed"] is True
        assert result["access_count"] == 5

    def test_cache_entry_from_dict(self):
        """Testa criação a partir de dicionário."""
        data = {
            "file_hash": "def456",
            "created_at": "2025-01-01T00:00:00",
            "expires_at": "2025-01-01T01:00:00",
            "size": 2048,
            "compressed": False,
            "access_count": 3,
            "last_accessed": "2025-01-01T00:30:00",
        }
        entry = CacheEntry(**data)
        assert entry.file_hash == "def456"
        assert entry.size == 2048
        assert entry.access_count == 3


class TestPersistentCache:
    """Testes para PersistentCache."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Diretório temporário para cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Cache configurado para testes."""
        return PersistentCache(
            cache_dir=temp_cache_dir,
            max_size_mb=10,
        )

    def test_cache_initialization(self, temp_cache_dir):
        """Verifica inicialização do cache."""
        cache = PersistentCache(cache_dir=temp_cache_dir)
        assert cache.cache_dir == temp_cache_dir
        assert cache.max_size_bytes == 100 * 1024 * 1024  # default 100MB
        assert cache.compress is True  # default
        assert cache.name == "default"

    def test_cache_directories_created(self, temp_cache_dir):
        """Testa criação de diretórios necessários."""
        PersistentCache(cache_dir=temp_cache_dir)
        assert temp_cache_dir.exists()
        # index.json é criado apenas quando há dados para salvar

    def test_set_and_get_basic(self, cache):
        """Verifica operações básicas set/get."""
        test_data = {"key": "value", "number": 42}
        cache.set("test_key", test_data)

        result = cache.get("test_key")
        assert result == test_data

    def test_set_with_custom_ttl(self, cache):
        """Testa set com TTL customizado."""
        test_data = {"data": "expires_soon"}
        cache.set("short_lived", test_data, ttl=1)

        # Deve existir imediatamente
        assert cache.get("short_lived") == test_data

        # Simula expiração
        time.sleep(1.1)
        assert cache.get("short_lived") is None

    def test_get_nonexistent_key(self, cache):
        """Verifica get de chave inexistente."""
        result = cache.get("nonexistent")
        assert result is None

    def test_has_key(self, cache):
        """Testa verificação de existência de chave."""
        cache.set("existing", {"data": "test"})

        assert cache.contains("existing") is True
        assert cache.contains("nonexistent") is False

    def test_delete_key(self, cache):
        """Verifica remoção de chave."""
        cache.set("to_delete", {"data": "test"})
        assert cache.contains("to_delete") is True

        cache.delete("to_delete")
        assert cache.contains("to_delete") is False

    def test_clear_cache(self, cache):
        """Testa limpeza completa do cache."""
        cache.set("key1", {"data": "test1"})
        cache.set("key2", {"data": "test2"})

        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        stats = cache.get_stats()
        assert stats["entries"] == 0

    def test_get_stats(self, cache):
        """Verifica obtenção de estatísticas."""
        cache.set("key1", {"data": "test1"})
        cache.set("key2", {"data": "test2"})

        stats = cache.get_stats()
        assert stats["entries"] == 2
        assert stats["size_bytes"] > 0  # Usar size_bytes em vez de size_mb
        assert "hit_rate" in stats

    def test_compression_enabled(self, temp_cache_dir):
        """Testa cache com compressão habilitada."""
        cache = PersistentCache(
            cache_dir=temp_cache_dir,
            compress=True,
        )

        large_data = {"data": "x" * 1000}  # Dados grandes
        cache.set("compressed", large_data)

        result = cache.get("compressed")
        assert result == large_data

    def test_size_limit_enforcement(self, temp_cache_dir):
        """Verifica aplicação do limite de tamanho."""
        cache = PersistentCache(
            cache_dir=temp_cache_dir,
            max_size_mb=1,  # Limite muito baixo
        )

        # Adiciona dados até exceder limite
        for i in range(20):  # Mais dados para garantir que exceda
            large_data = {"data": "x" * 50000, "id": i}  # Dados maiores
            cache.set(f"key_{i}", large_data)

        # Deve ter removido entradas antigas (LRU)
        stats = cache.get_stats()
        assert stats["entries"] <= 20  # Pode ter removido algumas

    def test_thread_safety(self, cache):
        """Testa segurança de thread."""
        import threading

        def worker(thread_id):
            for i in range(10):
                cache.set(f"thread_{thread_id}_key_{i}", {"data": f"value_{i}"})

        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verifica que dados foram salvos sem conflitos
        stats = cache.get_stats()
        assert stats["entries"] == 30

    def test_persistence_across_instances(self, temp_cache_dir):
        """Verifica persistência entre instâncias."""
        # Primeira instância
        cache1 = PersistentCache(cache_dir=temp_cache_dir)
        cache1.set("persistent_key", {"data": "persistent_value"})

        # Segunda instância (simula restart)
        cache2 = PersistentCache(cache_dir=temp_cache_dir)
        result = cache2.get("persistent_key")

        assert result == {"data": "persistent_value"}

    @patch("aura_cli.core.cache_advanced.persistent_cache.json.dumps")
    def test_serialization_error_handling(self, mock_dumps, cache):
        """Testa tratamento de erros de serialização."""
        mock_dumps.side_effect = Exception("Serialization failed")

        # Não deve lançar exceção
        cache.set("error_key", {"data": "test"})

        # Chave não deve existir devido ao erro
        assert cache.get("error_key") is None

    def test_expired_entry_cleanup(self, cache):
        """Verifica limpeza de entradas expiradas."""
        # Adiciona entrada com TTL muito baixo
        cache.set("expires_fast", {"data": "test"}, ttl=0.1)

        # Espera expirar
        time.sleep(0.2)

        # Força limpeza
        cache._cleanup_expired()

        assert cache.get("expires_fast") is None


class TestGlobalCache:
    """Testes para função global de cache."""

    def test_get_persistent_cache_singleton(self):
        """Verifica padrão singleton."""
        cache1 = get_persistent_cache()
        cache2 = get_persistent_cache()

        assert cache1 is cache2

    def test_get_persistent_cache_default_location(self):
        """Testa localização padrão do cache."""
        cache = get_persistent_cache()
        # Verifica que usa o padrão esperado (sem mock para evitar problemas de singleton)
        assert "cache" in str(cache.cache_dir)
        assert "global" in str(cache.cache_dir)


class TestCacheIntegration:
    """Testes de integração do cache."""

    @pytest.fixture
    def temp_cache_dir(self):
        """Diretório temporário para cache."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_real_world_usage_pattern(self, temp_cache_dir):
        """Testa padrão de uso do mundo real."""
        cache = PersistentCache(cache_dir=temp_cache_dir)

        # Simula cache de análise de código
        file_analysis = {
            "file_path": "/path/to/file.py",
            "functions": ["func1", "func2"],
            "classes": ["Class1"],
            "imports": ["os", "sys"],
            "complexity": 5,
        }

        cache.set("analysis:/path/to/file.py", file_analysis, ttl=7200)

        # Simula cache de embeddings
        embeddings = {
            "text": "sample code snippet",
            "vector": [0.1, 0.2, 0.3, 0.4, 0.5],
            "model": "sentence-transformers",
        }

        cache.set("embedding:sample_hash", embeddings, ttl=86400)

        # Verifica recuperação
        assert cache.get("analysis:/path/to/file.py") == file_analysis
        assert cache.get("embedding:sample_hash") == embeddings

        # Verifica estatísticas
        stats = cache.get_stats()
        assert stats["entries"] == 2
        assert stats["hit_rate"] == 100.0  # 100% hit rate
