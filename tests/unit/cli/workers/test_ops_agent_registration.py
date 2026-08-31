from types import SimpleNamespace
from unittest.mock import Mock, patch

from aura_cli.cli.workers.ops_agent_registration import register_ops_agents


@patch("aura_cli.core.agents.adk_integration.create_adk_wrapper")
def test_register_ops_agents_prefers_adk_wrapper(create_wrapper) -> None:
    orchestrator = Mock(context=object())
    communication = Mock()
    memory = Mock()
    memory.retrieve.return_value = []

    outcome = register_ops_agents(
        orchestrator=orchestrator,
        communication_manager=communication,
        agent_memory=memory,
        model="model",
        use_adk=True,
        logger=Mock(),
    )

    assert outcome.backend == "adk"
    assert outcome.agent_ids == ("ops_code_agent",)
    communication.register_agent.assert_called_once_with(
        "ops_code_agent", "ops_channel"
    )
    memory.retrieve.assert_called_once_with("ops_code_agent", limit=10)
    orchestrator.register_agent.assert_called_once_with(create_wrapper.return_value)


@patch("aura_cli.core.agents.specialized_agents.ops_code_agent.OpsCodeAgent")
@patch("aura_cli.core.agents.adk_integration.create_adk_wrapper")
def test_register_ops_agents_falls_back_to_native_team(
    create_wrapper, native_factory
) -> None:
    create_wrapper.side_effect = RuntimeError("ADK unavailable")
    agents = [SimpleNamespace(context=None) for _ in range(3)]
    native_factory.side_effect = agents
    orchestrator = Mock(context=object())
    communication = Mock()
    memory = Mock()
    memory.retrieve.return_value = []

    outcome = register_ops_agents(
        orchestrator=orchestrator,
        communication_manager=communication,
        agent_memory=memory,
        model="model",
        use_adk=True,
        logger=Mock(),
    )

    assert outcome.backend == "native"
    assert outcome.adk_fallback_error == "ADK unavailable"
    assert outcome.agent_ids == (
        "ops_code_agent",
        "ops_git_agent",
        "ops_docker_agent",
    )
    assert [agent.context for agent in agents] == [orchestrator.context] * 3
    assert orchestrator.register_agent.call_count == 3
