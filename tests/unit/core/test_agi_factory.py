from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from aura_cli.core.agents.agent_base import AgentContext
from aura_cli.core.agi.factory import AgiAgentFactory


def test_create_agent_uses_adk_wrapper_with_model_and_context():
    context = AgentContext()

    with patch(
        "aura_cli.core.agents.adk_integration.create_adk_wrapper"
    ) as mock_create_wrapper:
        from aura_cli.core.agi import factory as agi_factory_module

        agent = agi_factory_module._create_agent(
            "code",
            "code_agent",
            "unused.module",
            "UnusedClass",
            model="openai/gpt-5.4",
            context=context,
        )

    assert agent is mock_create_wrapper.return_value
    mock_create_wrapper.assert_called_once_with(
        agent_type="code",
        agent_id="code_agent",
        model="openai/gpt-5.4",
        context=context,
        memory_synchronizer=None,
    )


def test_create_agent_skips_adk_completely_when_disabled():
    native_agent = MagicMock()
    native_class = MagicMock(return_value=native_agent)
    fallback_module = SimpleNamespace(NativeAgent=native_class)

    with (
        patch(
            "aura_cli.core.agents.adk_integration.create_adk_wrapper"
        ) as create_adk_wrapper,
        patch(
            "aura_cli.core.agi.factory.importlib.import_module",
            return_value=fallback_module,
        ),
    ):
        from aura_cli.core.agi import factory as agi_factory_module

        agent = agi_factory_module._create_agent(
            "code",
            "code_agent",
            "native.module",
            "NativeAgent",
            use_adk=False,
        )

    assert agent is native_agent
    create_adk_wrapper.assert_not_called()
    native_class.assert_called_once_with(agent_id="code_agent")


def test_factory_initializes_memory_bridge_and_registers_agents():
    orchestrator = MagicMock()
    orchestrator.context = AgentContext()
    orchestrator.agents = {}
    communication_manager = MagicMock()
    event_adapter = MagicMock()
    agent_memory = MagicMock()
    agent_memory.retrieve.return_value = []
    wrapped_agent = MagicMock()
    wrapped_agent.context = orchestrator.context

    synchronizer = MagicMock()
    with patch(
        "aura_cli.core.agi.factory._create_agent", return_value=wrapped_agent
    ) as mock_create_agent:
        factory = AgiAgentFactory(
            orchestrator=orchestrator,
            communication_manager=communication_manager,
            agi_event_adapter=event_adapter,
            model="gemini/gemini-2.5-flash",
            agent_memory=agent_memory,
            memory_synchronizer=synchronizer,
        )

        factory.create_specialized_agents("inspect the codebase")

    synchronizer.set_agent_memory.assert_called_once_with(agent_memory)
    assert mock_create_agent.call_count == 4
    assert all(
        call.kwargs["use_adk"] is True for call in mock_create_agent.call_args_list
    )
    assert all(
        call.kwargs["memory_synchronizer"] is synchronizer
        for call in mock_create_agent.call_args_list
    )
    assert communication_manager.register_agent.call_count == 4
    assert orchestrator.register_agent.call_count == 4
    assert agent_memory.retrieve.call_count == 4
