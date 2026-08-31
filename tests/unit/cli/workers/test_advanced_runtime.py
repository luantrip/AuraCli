from unittest.mock import Mock, patch

from aura_cli.cli.workers.advanced_runtime import initialize_advanced_worker_runtime


def test_advanced_runtime_preserves_injected_components() -> None:
    components = [Mock(name=name) for name in ("orch", "comm", "workflow", "memory")]
    notify = Mock()

    runtime = initialize_advanced_worker_runtime(
        channel_id="main",
        channel_name="Main",
        orchestrator=components[0],
        communication_manager=components[1],
        workflow_executor=components[2],
        agent_memory=components[3],
        on_initialized=notify,
    )

    assert (
        runtime.orchestrator,
        runtime.communication_manager,
        runtime.workflow_executor,
        runtime.agent_memory,
    ) == tuple(components)
    notify.assert_not_called()


@patch("aura_cli.core.agents.agent_memory.AgentMemory")
@patch("aura_cli.core.agents.agent_workflow.WorkflowExecutor")
@patch("aura_cli.core.agents.agent_communication.CommunicationManager")
@patch("aura_cli.core.agents.agent_orchestrator.AgentOrchestrator")
def test_advanced_runtime_creates_and_reports_missing_components(
    orchestrator_factory,
    communication_factory,
    workflow_factory,
    memory_factory,
) -> None:
    notify = Mock()

    runtime = initialize_advanced_worker_runtime(
        channel_id="ops",
        channel_name="Ops",
        memory_storage_path="memory-path",
        on_initialized=notify,
    )

    communication_factory.return_value.create_channel.assert_called_once_with(
        "ops", "Ops"
    )
    workflow_factory.assert_called_once_with(orchestrator_factory.return_value)
    memory_factory.assert_called_once_with(storage_path="memory-path")
    assert runtime.agent_memory is memory_factory.return_value
    assert [call.args[0] for call in notify.call_args_list] == [
        "orchestrator",
        "communication",
        "workflow",
        "memory",
    ]
