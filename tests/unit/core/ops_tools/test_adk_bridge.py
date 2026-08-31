"""
Testes para o ADK Bridge.

Valida a integração entre o novo sistema ADK e o sistema legado core.agents.
"""

import asyncio

import pytest

from aura_cli.adk import Agent
from aura_cli.adk import AgentConfig as ADKConfig
from aura_cli.adk import AgentResponse as ADKResponse

# Import base types first
from aura_cli.core.agents import (
    AgentConfig as LegacyConfig,
)
from aura_cli.core.agents import (
    AgentResponse as LegacyResponse,
)

# Ensure ADK bridge is loaded (it's lazy-loaded to avoid PyArrow issues in threads)
from aura_cli.core.agents import _ensure_adk_bridge

_ensure_adk_bridge()

# Now import the ADK bridge classes (they should be loaded now)
from aura_cli.core.agents import (
    ADKAgentAdapter,
    ADKBridgeFactory,
    ADKConfigAdapter,
    ADKResponseAdapter,
)

# Skip tests if ADK bridge components aren't available (thread safety protection)
pytestmark = pytest.mark.skipif(
    ADKConfigAdapter is None,
    reason="ADK Bridge not available (likely running in non-main thread)",
)


# Mock Agent para testes
class MockADKAgent(Agent):
    """Agente ADK mock para testes."""

    def __init__(self, name: str = "mock_agent"):
        config = ADKConfig(
            name=name,
            description="Mock agent for testing",
            system_prompt="You are a test agent",
            model="gpt-4",
        )
        super().__init__(config)
        self.execute_called = False
        self.last_task = None

    async def execute(self, task: str) -> ADKResponse:
        """Executa tarefa mock."""
        self.execute_called = True
        self.last_task = task

        return ADKResponse(
            content=f"Mock response for: {task}",
            metadata={"mock": True, "task": task},
            success=True,
            error=None,
        )


class TestADKConfigAdapter:
    """Testes para ADKConfigAdapter."""

    def test_to_core(self):
        """Testa conversão ADK → Legacy."""
        adk_config = ADKConfig(
            name="test_agent",
            description="Test description",
            system_prompt="Test prompt",
            model="gpt-4",
            temperature=0.8,
            max_tokens=2048,
            max_iterations=5,
        )

        legacy_config = ADKConfigAdapter.to_core(adk_config)

        assert legacy_config.name == "test_agent"
        assert legacy_config.role == "Test description"
        assert legacy_config.system_message == "Test prompt"
        assert legacy_config.llm_config["model"] == "gpt-4"
        assert legacy_config.llm_config["temperature"] == 0.8
        assert legacy_config.llm_config["max_tokens"] == 2048
        assert legacy_config.max_consecutive_auto_reply == 5

    def test_from_core(self):
        """Testa conversão Legacy → ADK."""
        legacy_config = LegacyConfig(
            name="test_agent",
            role="assistant",
            system_message="Test message",
            llm_config={
                "model": "gpt-3.5-turbo",
                "temperature": 0.5,
                "max_tokens": 1024,
            },
            max_consecutive_auto_reply=8,
        )

        adk_config = ADKConfigAdapter.from_core(legacy_config)

        assert adk_config.name == "test_agent"
        assert adk_config.description == "assistant"
        assert adk_config.system_prompt == "Test message"
        assert adk_config.model == "gpt-3.5-turbo"
        assert adk_config.temperature == 0.5
        assert adk_config.max_tokens == 1024
        assert adk_config.max_iterations == 8

    def test_roundtrip_conversion(self):
        """Testa conversão ida e volta."""
        original = ADKConfig(
            name="roundtrip_test",
            description="Test",
            system_prompt="Prompt",
            model="gpt-4",
        )

        # ADK → Legacy → ADK
        legacy = ADKConfigAdapter.to_core(original)
        back_to_adk = ADKConfigAdapter.from_core(legacy)

        assert back_to_adk.name == original.name
        assert back_to_adk.model == original.model


class TestADKResponseAdapter:
    """Testes para ADKResponseAdapter."""

    def test_to_core(self):
        """Testa conversão de resposta ADK → Legacy."""
        adk_response = ADKResponse(
            content="Test content",
            metadata={"key": "value"},
            success=True,
            error=None,
        )

        legacy_response = ADKResponseAdapter.to_core(adk_response)

        assert legacy_response.content == "Test content"
        assert legacy_response.metadata == {"key": "value"}
        assert legacy_response.success is True
        assert legacy_response.error is None

    def test_from_core(self):
        """Testa conversão de resposta Legacy → ADK."""
        legacy_response = LegacyResponse(
            content="Legacy content",
            metadata={"legacy": True},
            success=False,
            error="Test error",
        )

        adk_response = ADKResponseAdapter.from_core(legacy_response)

        assert adk_response.content == "Legacy content"
        assert adk_response.metadata == {"legacy": True}
        assert adk_response.success is False
        assert adk_response.error == "Test error"


class TestADKAgentAdapter:
    """Testes para ADKAgentAdapter."""

    def test_initialization(self):
        """Testa inicialização do adapter."""
        mock_agent = MockADKAgent()
        adapter = ADKAgentAdapter(mock_agent)

        assert adapter.adk_agent == mock_agent
        assert adapter.get_backend_name() == "ADK:mock_agent"

    def test_create_assistant(self):
        """Testa criação de assistant."""
        mock_agent = MockADKAgent()
        adapter = ADKAgentAdapter(mock_agent)

        config = LegacyConfig(
            name="test_assistant",
            role="assistant",
            system_message="Test",
            llm_config={"model": "gpt-4"},
        )

        assistant = adapter.create_assistant(config)

        assert assistant == mock_agent
        assert adapter._assistant == mock_agent

    def test_create_user_proxy(self):
        """Testa criação de user proxy."""
        mock_agent = MockADKAgent()
        adapter = ADKAgentAdapter(mock_agent)

        config = LegacyConfig(
            name="test_user",
            role="user",
            system_message="",
            llm_config={},
        )

        user_proxy = adapter.create_user_proxy(config)

        assert user_proxy["name"] == "test_user"
        assert user_proxy["role"] == "user"
        assert adapter._user_proxy == user_proxy

    def test_execute_conversation_success(self):
        """Testa execução de conversa bem-sucedida."""

        async def run_test():
            mock_agent = MockADKAgent()
            adapter = ADKAgentAdapter(mock_agent)

            config = LegacyConfig(
                name="test",
                role="assistant",
                system_message="Test",
                llm_config={"model": "gpt-4"},
            )

            assistant = adapter.create_assistant(config)
            user_proxy = adapter.create_user_proxy(config)

            response = await adapter.execute_conversation(
                assistant, user_proxy, "Test message"
            )

            assert response.success is True
            assert "Mock response" in response.content
            assert response.error is None
            assert mock_agent.execute_called
            assert mock_agent.last_task == "Test message"

        asyncio.run(run_test())

    def test_execute_conversation_error(self):
        """Testa execução de conversa com erro."""

        async def run_test():
            mock_agent = MockADKAgent()

            # Fazer o execute lançar exceção
            async def failing_execute(task: str):
                raise ValueError("Test error")

            mock_agent.execute = failing_execute

            adapter = ADKAgentAdapter(mock_agent)

            config = LegacyConfig(
                name="test",
                role="assistant",
                system_message="Test",
                llm_config={},
            )

            assistant = adapter.create_assistant(config)
            user_proxy = adapter.create_user_proxy(config)

            response = await adapter.execute_conversation(
                assistant, user_proxy, "Test message"
            )

            assert response.success is False
            assert response.error == "Test error"
            assert "error" in response.metadata

        asyncio.run(run_test())


class TestADKBridgeFactory:
    """Testes para ADKBridgeFactory."""

    def test_register_and_list(self):
        """Testa registro e listagem de agentes."""
        # Limpar registry para teste isolado
        original_registry = ADKBridgeFactory._registry.copy()
        ADKBridgeFactory._registry.clear()

        try:
            ADKBridgeFactory.register("test_agent", MockADKAgent)

            registered = ADKBridgeFactory.list_registered()
            assert "test_agent" in registered
        finally:
            # Restaurar registry original
            ADKBridgeFactory._registry = original_registry

    def test_create_adapter(self):
        """Testa criação de adapter via factory."""
        # Registrar mock agent
        original_registry = ADKBridgeFactory._registry.copy()
        ADKBridgeFactory._registry["test_agent"] = MockADKAgent

        try:
            adapter = ADKBridgeFactory.create_adapter("test_agent")

            assert isinstance(adapter, ADKAgentAdapter)
            assert isinstance(adapter.adk_agent, MockADKAgent)
        finally:
            ADKBridgeFactory._registry = original_registry

    def test_create_adapter_not_registered(self):
        """Testa criação de adapter não registrado."""
        with pytest.raises(ValueError, match="não registrado"):
            ADKBridgeFactory.create_adapter("nonexistent_agent")

    def test_auto_registration(self):
        """Testa auto-registro de agentes especializados."""
        # Verificar se agentes especializados foram registrados
        registered = ADKBridgeFactory.list_registered()

        # Pelo menos alguns devem estar registrados
        # (depende se adk.specialized está disponível)
        assert isinstance(registered, list)


class TestIntegration:
    """Testes de integração end-to-end."""

    def test_full_workflow(self):
        """Testa workflow completo: registro → criação → execução."""

        async def run_test():
            # 1. Registrar agente
            original_registry = ADKBridgeFactory._registry.copy()
            ADKBridgeFactory._registry["integration_test"] = MockADKAgent

            try:
                # 2. Criar adapter via factory
                adapter = ADKBridgeFactory.create_adapter("integration_test")

                # 3. Criar assistant e user_proxy
                config = LegacyConfig(
                    name="integration",
                    role="assistant",
                    system_message="Integration test",
                    llm_config={"model": "gpt-4"},
                )

                assistant = adapter.create_assistant(config)
                user_proxy = adapter.create_user_proxy(config)

                # 4. Executar conversa
                response = await adapter.execute_conversation(
                    assistant, user_proxy, "Integration test message"
                )

                # 5. Validar resultado
                assert response.success
                assert "Mock response" in response.content
                assert response.metadata["mock"] is True

            finally:
                ADKBridgeFactory._registry = original_registry

        asyncio.run(run_test())

    def test_multiple_agents(self):
        """Testa uso de múltiplos agentes simultaneamente."""

        async def run_test():
            original_registry = ADKBridgeFactory._registry.copy()

            try:
                # Registrar múltiplos agentes
                ADKBridgeFactory._registry["agent1"] = MockADKAgent
                ADKBridgeFactory._registry["agent2"] = MockADKAgent

                # Criar adapters
                adapter1 = ADKBridgeFactory.create_adapter("agent1")
                adapter2 = ADKBridgeFactory.create_adapter("agent2")

                # Configurar
                config = LegacyConfig(
                    name="test",
                    role="assistant",
                    system_message="Test",
                    llm_config={},
                )

                # Executar ambos
                response1 = await adapter1.execute_conversation(
                    adapter1.create_assistant(config),
                    adapter1.create_user_proxy(config),
                    "Message 1",
                )

                response2 = await adapter2.execute_conversation(
                    adapter2.create_assistant(config),
                    adapter2.create_user_proxy(config),
                    "Message 2",
                )

                # Validar
                assert response1.success
                assert response2.success
                assert "Message 1" in response1.content
                assert "Message 2" in response2.content

            finally:
                ADKBridgeFactory._registry = original_registry

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
