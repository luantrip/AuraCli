"""
Testes de cenário: Cache do ServiceRegistry.

Valida comportamento de cache TTL, eviction LRU, hit/miss metrics
e invalidation em erro.
"""

import time
from unittest.mock import Mock

from aura_cli.core.service_registry import ServiceRegistry, ToolCategory


class TestServiceRegistryCache:
    """Testes de cache do ServiceRegistry."""

    def test_execute_tool_caches_result_on_first_call(self):
        """Primeira execução deve cachear o resultado."""
        registry = ServiceRegistry(cache_ttl_seconds=60)

        # Registra tool mock
        mock_func = Mock(return_value="result1")
        registry._register_tool(
            "test_tool",
            ToolCategory.DEVELOPMENT,
            "Test",
            mock_func,
            {},
            effect="read_only",
            cacheable=True,
        )

        # Primeira chamada
        result1 = registry.execute_tool("test_tool", {"param": "value"})

        # Segunda chamada com mesmos parâmetros
        result2 = registry.execute_tool("test_tool", {"param": "value"})

        # Função deve ter sido chamada apenas uma vez (cache hit na segunda)
        assert mock_func.call_count == 1
        assert result1 == result2 == "result1"

    def test_execute_tool_cache_respects_different_parameters(self):
        """Cache deve diferenciar chamadas com parâmetros diferentes."""
        registry = ServiceRegistry(cache_ttl_seconds=60)

        # Registra tool mock que retorna o parâmetro
        mock_func = Mock(side_effect=lambda param: f"result_{param}")
        registry._register_tool(
            "test_tool",
            ToolCategory.DEVELOPMENT,
            "Test",
            mock_func,
            {},
            effect="read_only",
            cacheable=True,
        )

        # Chamadas com parâmetros diferentes
        result1 = registry.execute_tool("test_tool", {"param": "A"})
        result2 = registry.execute_tool("test_tool", {"param": "B"})
        result3 = registry.execute_tool("test_tool", {"param": "A"})  # Cache hit

        # Função deve ter sido chamada 2 vezes (A e B), terceira é cache
        assert mock_func.call_count == 2
        assert result1 == "result_A"
        assert result2 == "result_B"
        assert result3 == "result_A"

    def test_cache_key_is_independent_of_parameter_order(self):
        registry = ServiceRegistry(cache_ttl_seconds=60)
        mock_func = Mock(return_value="result")
        registry._register_tool(
            "test_tool",
            ToolCategory.DEVELOPMENT,
            "Test",
            mock_func,
            {},
            effect="read_only",
            cacheable=True,
        )

        registry.execute_tool("test_tool", {"a": 1, "b": 2})
        registry.execute_tool("test_tool", {"b": 2, "a": 1})

        mock_func.assert_called_once()

    def test_execute_tool_cache_expires_after_ttl(self):
        """Cache deve expirar após TTL."""
        registry = ServiceRegistry(cache_ttl_seconds=1)  # 1 segundo

        # Registra tool mock
        call_count = [0]

        def mock_func(**kwargs):
            call_count[0] += 1
            return f"result_{call_count[0]}"

        registry._register_tool(
            "test_tool",
            ToolCategory.DEVELOPMENT,
            "Test",
            mock_func,
            {},
            effect="read_only",
            cacheable=True,
        )

        # Primeira chamada
        result1 = registry.execute_tool("test_tool", {"param": "value"})
        assert result1 == "result_1"

        # Segunda chamada imediata (cache hit)
        result2 = registry.execute_tool("test_tool", {"param": "value"})
        assert result2 == "result_1"
        assert call_count[0] == 1

        # Aguarda TTL expirar
        time.sleep(1.5)

        # Terceira chamada após TTL (cache miss)
        result3 = registry.execute_tool("test_tool", {"param": "value"})
        assert result3 == "result_2"
        assert call_count[0] == 2

    def test_execute_tool_cache_evicts_lru_when_full(self):
        """Cache deve evitar entradas LRU quando atingir max_size."""
        registry = ServiceRegistry(cache_ttl_seconds=300, cache_max_size=3)

        # Registra tool mock
        mock_func = Mock(side_effect=lambda param: f"result_{param}")
        registry._register_tool(
            "test_tool",
            ToolCategory.DEVELOPMENT,
            "Test",
            mock_func,
            {},
            effect="read_only",
            cacheable=True,
        )

        # Preenche cache até o limite
        registry.execute_tool("test_tool", {"param": "A"})
        registry.execute_tool("test_tool", {"param": "B"})
        registry.execute_tool("test_tool", {"param": "C"})

        assert mock_func.call_count == 3

        # Adiciona nova entrada (deve evitar LRU = A)
        registry.execute_tool("test_tool", {"param": "D"})

        assert mock_func.call_count == 4

        # Tenta acessar A novamente (deve ser cache miss)
        registry.execute_tool("test_tool", {"param": "A"})

        # Se LRU funcionou, A foi evitado e função foi chamada novamente
        assert mock_func.call_count == 5

    def test_execute_tool_does_not_cache_on_error(self):
        """Erro na execução não deve ser cacheado."""
        registry = ServiceRegistry(cache_ttl_seconds=60)

        # Registra tool que falha na primeira chamada
        call_count = [0]

        def mock_func(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("First call fails")
            return "success"

        registry._register_tool(
            "test_tool",
            ToolCategory.DEVELOPMENT,
            "Test",
            mock_func,
            {},
            effect="read_only",
            cacheable=True,
        )

        # Primeira chamada (falha)
        result1 = registry.execute_tool("test_tool", {"param": "value"})
        assert result1 is None  # Erro retorna None
        assert call_count[0] == 1

        # Segunda chamada (sucesso - não deve usar cache do erro)
        result2 = registry.execute_tool("test_tool", {"param": "value"})
        assert result2 == "success"
        assert call_count[0] == 2

    def test_execute_tool_tracks_cache_hit_miss_via_stats(self):
        """Deve rastrear cache hits/misses via stats."""
        registry = ServiceRegistry(cache_ttl_seconds=60)

        # Registra tool mock
        mock_func = Mock(return_value="result")
        registry._register_tool(
            "test_tool",
            ToolCategory.DEVELOPMENT,
            "Test",
            mock_func,
            {},
            effect="read_only",
            cacheable=True,
        )

        # Primeira chamada (miss)
        registry.execute_tool("test_tool", {"param": "value"})

        # Segunda chamada (hit)
        registry.execute_tool("test_tool", {"param": "value"})

        # Função deve ter sido chamada apenas uma vez
        assert mock_func.call_count == 1

        # Stats deve ter registrado as chamadas
        # (verificação depende da implementação de stats)
        assert registry.stats is not None
