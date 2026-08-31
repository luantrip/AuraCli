"""
Testes de cenário: Lifecycle de tools no ServiceRegistry.

Valida enable/disable de tools, category filtering, usage statistics
e concurrent execution.
"""

import threading
from unittest.mock import Mock

from aura_cli.core.service_registry import ServiceRegistry, ToolCategory


class TestServiceRegistryLifecycle:
    """Testes de lifecycle de tools."""

    def test_get_tool_returns_descriptor_for_registered_tool(self):
        """get_tool deve retornar descriptor para tool registrada."""
        registry = ServiceRegistry()

        mock_func = Mock(return_value="result")
        registry._register_tool(
            "test_tool", ToolCategory.DEVELOPMENT, "Test", mock_func, {}
        )

        descriptor = registry.get_tool("test_tool")

        assert descriptor is not None
        assert descriptor.name == "test_tool"
        assert descriptor.category == ToolCategory.DEVELOPMENT
        assert descriptor.enabled is True

    def test_get_tool_returns_none_for_unregistered_tool(self):
        """get_tool deve retornar None para tool não registrada."""
        registry = ServiceRegistry()

        descriptor = registry.get_tool("nonexistent_tool")

        assert descriptor is None

    def test_execute_tool_returns_none_when_tool_disabled(self):
        """execute_tool deve retornar None quando tool está desabilitada."""
        registry = ServiceRegistry()

        mock_func = Mock(return_value="result")
        registry._register_tool(
            "test_tool", ToolCategory.DEVELOPMENT, "Test", mock_func, {}
        )

        # Desabilita tool
        tool = registry.get_tool("test_tool")
        tool.enabled = False

        # Tenta executar
        result = registry.execute_tool("test_tool", {})

        assert result is None
        assert mock_func.call_count == 0  # Função não deve ser chamada

    def test_execute_tool_increments_usage_count(self):
        """execute_tool deve incrementar usage_count."""
        registry = ServiceRegistry()

        mock_func = Mock(return_value="result")
        registry._register_tool(
            "test_tool", ToolCategory.DEVELOPMENT, "Test", mock_func, {}
        )

        tool = registry.get_tool("test_tool")
        initial_count = tool.usage_count

        # Executa 3 vezes
        registry.execute_tool("test_tool", {"param": "A"})
        registry.execute_tool("test_tool", {"param": "B"})
        registry.execute_tool("test_tool", {"param": "C"})

        # Usage count deve ter incrementado
        assert tool.usage_count == initial_count + 3

    def test_execute_tool_increments_error_count_on_exception(self):
        """execute_tool deve incrementar error_count em exceção."""
        registry = ServiceRegistry()

        mock_func = Mock(side_effect=RuntimeError("Error"))
        registry._register_tool(
            "test_tool", ToolCategory.DEVELOPMENT, "Test", mock_func, {}
        )

        tool = registry.get_tool("test_tool")
        initial_error_count = tool.error_count

        # Executa (vai falhar)
        result = registry.execute_tool("test_tool", {})

        assert result is None
        assert tool.error_count == initial_error_count + 1

    def test_execute_tool_tracks_average_execution_time(self):
        """execute_tool deve rastrear tempo médio de execução."""
        registry = ServiceRegistry()

        import time

        def slow_func(**kwargs):
            time.sleep(0.1)
            return "result"

        registry._register_tool(
            "test_tool", ToolCategory.DEVELOPMENT, "Test", slow_func, {}
        )

        tool = registry.get_tool("test_tool")

        # Executa
        registry.execute_tool("test_tool", {})

        # Tempo médio deve ser > 0
        assert tool.avg_execution_time > 0
        assert tool.avg_execution_time >= 0.1

    def test_get_tools_by_category_filters_correctly(self):
        """get_tools_by_category deve filtrar por categoria."""
        # Cria registry sem bootstrap automático
        registry = ServiceRegistry.__new__(ServiceRegistry)
        registry.tools = {}
        registry.stats = Mock()
        registry._cache = Mock()

        # Registra tools de categorias diferentes
        registry._register_tool("dev_tool", ToolCategory.DEVELOPMENT, "Dev", Mock(), {})
        registry._register_tool("git_tool", ToolCategory.GIT, "Git", Mock(), {})
        registry._register_tool(
            "dev_tool2", ToolCategory.DEVELOPMENT, "Dev2", Mock(), {}
        )

        # Filtra por DEVELOPMENT
        dev_tools = registry.get_tools_by_category(ToolCategory.DEVELOPMENT)

        assert len(dev_tools) == 2
        assert all(t.category == ToolCategory.DEVELOPMENT for t in dev_tools)

    def test_get_tools_by_category_excludes_disabled_tools(self):
        """get_tools_by_category deve excluir tools desabilitadas."""
        # Cria registry sem bootstrap automático
        registry = ServiceRegistry.__new__(ServiceRegistry)
        registry.tools = {}
        registry.stats = Mock()
        registry._cache = Mock()

        # Registra 2 tools da mesma categoria
        registry._register_tool("tool1", ToolCategory.DEVELOPMENT, "Tool1", Mock(), {})
        registry._register_tool("tool2", ToolCategory.DEVELOPMENT, "Tool2", Mock(), {})

        # Desabilita uma
        tool1 = registry.get_tool("tool1")
        tool1.enabled = False

        # Filtra
        dev_tools = registry.get_tools_by_category(ToolCategory.DEVELOPMENT)

        # Deve retornar apenas a habilitada
        assert len(dev_tools) == 1
        assert dev_tools[0].name == "tool2"

    def test_execute_tool_handles_concurrent_execution(self):
        """execute_tool deve suportar execução concorrente."""
        registry = ServiceRegistry()

        # Tool que simula trabalho
        import time

        call_count = [0]
        lock = threading.Lock()

        def concurrent_func(**kwargs):
            with lock:
                call_count[0] += 1
            time.sleep(0.1)
            return f"result_{kwargs.get('id')}"

        registry._register_tool(
            "test_tool", ToolCategory.DEVELOPMENT, "Test", concurrent_func, {}
        )

        # Executa em threads paralelas
        results = []

        def worker(worker_id):
            result = registry.execute_tool("test_tool", {"id": worker_id})
            results.append(result)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Todas as execuções devem ter completado
        assert len(results) == 5
        assert call_count[0] == 5
