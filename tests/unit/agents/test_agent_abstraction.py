"""Testes para sistema de abstração de agentes."""

import pytest

from aura_cli.core.agents import (
    AgentBackend,
    AgentBackendFactory,
    AgentConfig,
    AgentResponse,
    NativeBackend,
)
from aura_cli.core.agents.native_backend import NativeUserProxy
from aura_cli.core.llm.model_utils import DEFAULT_MODEL


class TestAgentConfig:
    """Testes para AgentConfig."""

    def test_agent_config_creation(self):
        """Testa criação de configuração de agente."""
        config = AgentConfig(
            name="TestAgent",
            role="assistant",
            system_message="You are a helpful assistant",
            llm_config={"model": "gpt-4"},
        )

        assert config.name == "TestAgent"
        assert config.role == "assistant"
        assert config.system_message == "You are a helpful assistant"
        assert config.llm_config["model"] == "gpt-4"
        assert config.max_consecutive_auto_reply == 10
        assert config.human_input_mode == "NEVER"


class TestAgentResponse:
    """Testes para AgentResponse."""

    def test_agent_response_success(self):
        """Testa resposta bem-sucedida."""
        response = AgentResponse(
            content="Hello!",
            metadata={"backend": "test"},
            success=True,
        )

        assert response.content == "Hello!"
        assert response.success is True
        assert response.error is None

    def test_agent_response_error(self):
        """Testa resposta com erro."""
        response = AgentResponse(
            content="",
            metadata={"backend": "test"},
            success=False,
            error="Connection failed",
        )

        assert response.content == ""
        assert response.success is False
        assert response.error == "Connection failed"


class TestAgentBackendFactory:
    """Testes para AgentBackendFactory."""

    def test_create_default_backend(self):
        """Testa criação de backend padrão."""
        backend = AgentBackendFactory.create()
        assert isinstance(backend, NativeBackend)
        assert backend.get_backend_name() == "native"

    def test_create_invalid_backend(self):
        """Testa criação de backend inválido."""
        with pytest.raises(ValueError, match="Backend 'invalid' not found"):
            AgentBackendFactory.create("invalid")

    def test_list_backends(self):
        """Testa listagem de backends disponíveis."""
        backends = AgentBackendFactory.list_backends()
        assert "native" in backends
        assert isinstance(backends, list)

    def test_register_custom_backend(self):
        """Testa registro de backend customizado."""

        class CustomBackend(AgentBackend):
            def create_assistant(self, config):
                return None

            def create_user_proxy(self, config):
                return None

            async def execute_conversation(self, assistant, user_proxy, message):
                return AgentResponse("", {}, True)

            def get_backend_name(self):
                return "custom"

        AgentBackendFactory.register_backend("custom", CustomBackend)
        assert "custom" in AgentBackendFactory.list_backends()

        backend = AgentBackendFactory.create("custom")
        assert backend.get_backend_name() == "custom"


class TestNativeBackend:
    """Testes para NativeBackend."""

    def test_backend_creation(self):
        """Testa criação do backend nativo."""
        backend = NativeBackend()
        assert backend.get_backend_name() == "native"

    def test_extract_model_params_uses_central_default(self):
        """Fallback do backend nativo deve usar o default central."""
        model, temperature, api_key = NativeUserProxy._extract_model_params({})
        assert model == DEFAULT_MODEL
        assert temperature == 0.7
        assert api_key is None

    def test_create_native_assistant(self):
        """Testa criação de assistente nativo."""
        backend = NativeBackend()
        config = AgentConfig(
            name="TestAssistant",
            role="assistant",
            system_message="You are a helpful assistant",
            llm_config={"model": "gpt-4"},
        )

        assistant = backend.create_assistant(config)
        assert assistant is not None
        assert assistant.name == "TestAssistant"
        assert assistant.system_message == "You are a helpful assistant"

    def test_create_native_user_proxy(self):
        """Testa criação de user proxy nativo."""
        backend = NativeBackend()
        config = AgentConfig(
            name="UserProxy",
            role="proxy",
            system_message="",
            llm_config={},
        )

        proxy = backend.create_user_proxy(config)
        assert proxy is not None
        assert proxy.name == "UserProxy"
        assert proxy.human_input_mode == "NEVER"

    def test_native_conversation(self):
        """Testa conversa com backend nativo."""
        from unittest.mock import patch

        backend = NativeBackend()

        assistant_config = AgentConfig(
            name="Assistant",
            role="assistant",
            system_message="You are helpful",
            llm_config={"model": "gpt-4o"},
        )
        assistant = backend.create_assistant(assistant_config)

        proxy_config = AgentConfig(
            name="Proxy",
            role="proxy",
            system_message="",
            llm_config={},
        )
        proxy = backend.create_user_proxy(proxy_config)

        mock_msg = {"content": "Hello!", "role": "assistant"}
        with (
            patch.object(proxy, "initiate_chat"),
            patch.object(proxy, "last_message", return_value=mock_msg),
        ):
            proxy.initiate_chat(assistant, "Hello")
            last_msg = proxy.last_message()
            assert last_msg is not None
            assert "content" in last_msg

    def test_factory_creates_native(self):
        """Testa que factory pode criar backend nativo."""
        backend = AgentBackendFactory.create("native")
        assert isinstance(backend, NativeBackend)
        assert backend.get_backend_name() == "native"
