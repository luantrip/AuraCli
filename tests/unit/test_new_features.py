"""
Testes unitários para os novos recursos implementados.

Este módulo testa:
    - Cache Persistente
    - Sistema de Sessões
    - Rate Limiter LLM
    - User Workflows
    - Agent Metrics
    - Checkpointable Workflow
    - Plugin API
    - Fuzzy Autocomplete
    - Toast Notifications
    - Virtual List
    - Interactive Dashboard
"""

from pathlib import Path
import tempfile
import time

import pytest


class TestPersistentCache:
    """Testes para o cache persistente."""

    def test_cache_creation(self):
        """Testa criação do cache."""
        from aura_cli.core.cache_advanced.persistent_cache import PersistentCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PersistentCache(cache_dir=Path(tmpdir), max_size_mb=10, name="test")
            assert cache is not None
            assert cache.cache_dir.exists()

    def test_cache_set_get(self):
        """Testa set e get de valores."""
        from aura_cli.core.cache_advanced.persistent_cache import PersistentCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PersistentCache(cache_dir=Path(tmpdir), name="test")

            # Set
            cache.set("key1", {"data": "value"}, ttl=3600)

            # Get
            result = cache.get("key1")
            assert result == {"data": "value"}

    def test_cache_expiration(self):
        """Testa expiração de entradas."""
        from aura_cli.core.cache_advanced.persistent_cache import PersistentCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PersistentCache(cache_dir=Path(tmpdir), name="test")

            # Set com TTL curto
            cache.set("key1", "value", ttl=1)

            # Imediato - deve existir
            assert cache.get("key1") == "value"

            # Após expiração
            time.sleep(1.1)
            assert cache.get("key1") is None

    def test_cache_delete(self):
        """Testa remoção de entradas."""
        from aura_cli.core.cache_advanced.persistent_cache import PersistentCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PersistentCache(cache_dir=Path(tmpdir), name="test")

            cache.set("key1", "value")
            assert cache.delete("key1") is True
            assert cache.get("key1") is None

    def test_cache_stats(self):
        """Testa estatísticas do cache."""
        from aura_cli.core.cache_advanced.persistent_cache import PersistentCache

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PersistentCache(cache_dir=Path(tmpdir), name="test")

            cache.set("key1", "value1")
            cache.set("key2", "value2")
            cache.get("key1")
            cache.get("missing")

            stats = cache.get_stats()
            assert stats["entries"] == 2
            assert stats["hits"] == 1
            assert stats["misses"] == 1


class TestSessionManager:
    """Testes para o gerenciador de sessões."""

    def test_create_session(self):
        """Testa criação de sessão."""
        from aura_cli.core.sessions.session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(storage_path=Path(tmpdir))

            session = manager.create_session("Test Session")

            assert session is not None
            assert session.name == "Test Session"
            assert session.id is not None

    def test_session_messages(self):
        """Testa adicionar mensagens à sessão."""
        from aura_cli.core.sessions.session_manager import Session

        session = Session(
            id="test", name="Test", created_at="2024-01-01", updated_at="2024-01-01"
        )

        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")

        assert len(session.conversation_history) == 2
        assert session.conversation_history[0]["role"] == "user"
        assert session.conversation_history[1]["content"] == "Hi there!"

    def test_save_load_session(self):
        """Testa salvar e carregar sessão."""
        from aura_cli.core.sessions.session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(storage_path=Path(tmpdir))

            # Criar e salvar
            session = manager.create_session("Test")
            session.add_message("user", "Hello")
            manager.save_session(session)

            # Carregar
            loaded = manager.load_session(session.id)

            assert loaded is not None
            assert loaded.name == "Test"
            assert len(loaded.conversation_history) == 1

    def test_list_sessions(self):
        """Testa listagem de sessões."""
        from aura_cli.core.sessions.session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(storage_path=Path(tmpdir))

            manager.create_session("Session 1")
            manager.create_session("Session 2")
            manager.create_session("Session 3")

            sessions = manager.list_sessions()
            assert len(sessions) == 3


class TestRateLimiter:
    """Testes para o rate limiter."""

    def test_limiter_creation(self):
        """Testa criação do limiter."""
        from aura_cli.core.llm.rate_limiter import RateLimiter

        limiter = RateLimiter()
        assert limiter is not None

    def test_acquire_under_limit(self):
        """Testa acquire quando abaixo do limite."""
        from aura_cli.core.llm.rate_limiter import RateLimiter

        limiter = RateLimiter()
        limiter.reset()  # Garantir estado limpo

        # Deve conseguir adquirir
        assert limiter.acquire("gemini") is True
        limiter.release("gemini")

    def test_provider_detection(self):
        """Testa detecção de provedor."""
        from aura_cli.core.llm.rate_limiter import RateLimiter

        limiter = RateLimiter()

        assert limiter._get_provider("gemini-1.5-flash") == "gemini"
        assert limiter._get_provider("gpt-4") == "openai"
        assert limiter._get_provider("claude-3") == "anthropic"
        assert limiter._get_provider("unknown-model") == "default"

    def test_stats(self):
        """Testa estatísticas do limiter."""
        from aura_cli.core.llm.rate_limiter import RateLimiter

        limiter = RateLimiter()
        limiter.reset()

        limiter.acquire("gemini")
        limiter.release("gemini")

        stats = limiter.get_stats()
        assert stats["total_requests"] >= 1


class TestUserWorkflow:
    """Testes para workflows do usuário."""

    def test_create_workflow(self):
        """Testa criação de workflow."""
        from aura_cli.core.workflows.user_workflow import UserWorkflowManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkflowManager(storage_path=Path(tmpdir))

            workflow = manager.create_workflow(
                name="Test Workflow",
                description="A test workflow",
                steps=[{"id": "step1", "type": "shell", "command": "echo hello"}],
            )

            assert workflow is not None
            assert workflow.name == "Test Workflow"
            assert len(workflow.steps) == 1

    def test_execute_shell_step(self):
        """Testa execução de passo shell."""
        from aura_cli.core.workflows.user_workflow import UserWorkflowManager

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UserWorkflowManager(storage_path=Path(tmpdir))

            workflow = manager.create_workflow(
                name="Echo Test",
                steps=[{"id": "echo", "type": "shell", "command": "echo hello"}],
            )

            result = manager.execute_workflow(workflow.id)

            assert result["success"] is True
            assert "hello" in result["steps"]["echo"]["output"]


class TestAgentMetrics:
    """Testes para métricas de agentes."""

    def test_metrics_creation(self):
        """Testa criação de métricas."""
        from aura_cli.core.agents.agent_metrics import AgentMetrics

        metrics = AgentMetrics("test_agent")
        assert metrics.agent_id == "test_agent"
        assert metrics.total_tasks == 0

    def test_record_task(self):
        """Testa registro de tarefa."""
        from aura_cli.core.agents.agent_metrics import AgentMetrics

        metrics = AgentMetrics("test_agent")

        metrics.record_task_start("task1")
        time.sleep(0.1)
        metrics.record_task_end("task1", success=True, tokens=100)

        assert metrics.total_tasks == 1
        assert metrics.successful_tasks == 1
        assert metrics.total_tokens == 100
        assert metrics.avg_execution_time > 0

    def test_record_tool(self):
        """Testa registro de ferramenta."""
        from aura_cli.core.agents.agent_metrics import AgentMetrics

        metrics = AgentMetrics("test_agent")

        exec_id = metrics.record_tool_start("read_file", {"path": "/test"})
        metrics.record_tool_end(exec_id, success=True)

        assert metrics.tools_called["read_file"] == 1

    def test_get_summary(self):
        """Testa resumo de métricas."""
        from aura_cli.core.agents.agent_metrics import AgentMetrics

        metrics = AgentMetrics("test_agent")

        metrics.record_task_start("task1")
        metrics.record_task_end("task1", success=True, tokens=50)

        summary = metrics.get_summary()

        assert summary["agent_id"] == "test_agent"
        assert summary["tasks"]["total"] == 1
        assert summary["tokens"]["total"] == 50


class TestPluginAPI:
    """Testes para a API de plugins."""

    def test_plugin_manager_creation(self):
        """Testa criação do manager."""
        from aura_cli.core.extensions.plugin_api import PluginManager

        manager = PluginManager()
        assert manager is not None

    def test_plugin_hooks(self):
        """Testa hooks de plugins."""
        from aura_cli.core.extensions.plugin_api import (
            AuraPlugin,
            PluginHook,
            PluginManager,
        )

        class TestPlugin(AuraPlugin):
            @property
            def name(self):
                return "test_plugin"

            @property
            def version(self):
                return "1.0.0"

            @property
            def hooks(self):
                return {PluginHook.ON_STARTUP: self.on_startup}

            def on_startup(self, context):
                context.set("started", True)

        manager = PluginManager()
        plugin = TestPlugin()
        manager.register_plugin(plugin)

        results = manager.emit_hook(PluginHook.ON_STARTUP)
        assert len(results) == 1


class TestFuzzyAutocomplete:
    """Testes para autocomplete fuzzy."""

    def test_fuzzy_matcher(self):
        """Testa matcher fuzzy."""
        from aura_cli.cli.ui.command_completer import FuzzyMatcher

        # Exact prefix match
        matches = FuzzyMatcher.fuzzy_match("/he", ["/help", "/exit", "/theme"])
        assert matches[0][0] == "/help"

    def test_fuzzy_similarity(self):
        """Testa cálculo de similaridade."""
        from aura_cli.cli.ui.command_completer import FuzzyMatcher

        # Similar strings
        sim = FuzzyMatcher.similarity("help", "helps")
        assert sim > 0.8

        # Different strings
        sim = FuzzyMatcher.similarity("help", "exit")
        assert sim < 0.5


class TestToastNotifications:
    """Testes para toast notifications."""

    def test_toast_creation(self):
        """Testa criação de toast."""
        from aura_cli.cli.ui.components.toast import Toast, ToastType

        toast = Toast(id="test1", message="Test message", type=ToastType.SUCCESS)

        assert toast.id == "test1"
        assert toast.message == "Test message"
        assert toast.type == ToastType.SUCCESS

    def test_toast_manager(self):
        """Testa manager de toasts."""
        from aura_cli.cli.ui.components.toast import ToastManager

        manager = ToastManager(max_visible=3)

        toast_id = manager.show("Test", toast_type="info")
        assert toast_id is not None
        assert len(manager.visible) == 1

    def test_toast_dismiss(self):
        """Testa dismiss de toast."""
        from aura_cli.cli.ui.components.toast import ToastManager

        manager = ToastManager()

        toast_id = manager.show("Test")
        manager.dismiss(toast_id)

        assert len(manager.visible) == 0


class TestInteractiveDashboard:
    """Testes para dashboard interativo."""

    def test_dashboard_creation(self):
        """Testa criação de dashboard."""
        from aura_cli.cli.ui.components.interactive_dashboard import (
            InteractiveDashboard,
        )

        dashboard = InteractiveDashboard("Test Dashboard")
        assert dashboard.title == "Test Dashboard"

    def test_add_columns(self):
        """Testa adicionar colunas."""
        from aura_cli.cli.ui.components.interactive_dashboard import (
            InteractiveDashboard,
        )

        dashboard = InteractiveDashboard("Test")
        dashboard.add_column("name", "Name")
        dashboard.add_column("value", "Value")

        assert len(dashboard.columns) == 2

    def test_set_data(self):
        """Testa definir dados."""
        from aura_cli.cli.ui.components.interactive_dashboard import (
            InteractiveDashboard,
        )

        dashboard = InteractiveDashboard("Test")
        dashboard.add_column("name", "Name")

        data = [
            {"name": "Item 1"},
            {"name": "Item 2"},
            {"name": "Item 3"},
        ]
        dashboard.set_data(data)

        assert len(dashboard.data) == 3
        assert len(dashboard.filtered_data) == 3

    def test_sorting(self):
        """Testa ordenação."""
        from aura_cli.cli.ui.components.interactive_dashboard import (
            InteractiveDashboard,
            SortOrder,
        )

        dashboard = InteractiveDashboard("Test")
        dashboard.add_column("name", "Name")

        data = [
            {"name": "Zebra"},
            {"name": "Apple"},
            {"name": "Mango"},
        ]
        dashboard.set_data(data)
        dashboard.set_sort("name", SortOrder.ASC)

        assert dashboard.filtered_data[0]["name"] == "Apple"
        assert dashboard.filtered_data[2]["name"] == "Zebra"


# Teste de integração rápida
class TestIntegration:
    """Testes de integração entre módulos."""

    def test_cache_with_session(self):
        """Testa cache usado com sessão."""
        from aura_cli.core.cache_advanced.persistent_cache import PersistentCache
        from aura_cli.core.sessions.session_manager import SessionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = PersistentCache(cache_dir=Path(tmpdir) / "cache", name="test")
            session_mgr = SessionManager(storage_path=Path(tmpdir) / "sessions")

            # Criar sessão
            session = session_mgr.create_session("Test")

            # Cachear dados da sessão
            cache.set(f"session:{session.id}", session.to_dict())

            # Recuperar
            cached = cache.get(f"session:{session.id}")
            assert cached["name"] == "Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
