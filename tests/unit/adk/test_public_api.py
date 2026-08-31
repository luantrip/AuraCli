"""Public ADK API identity and lazy-import contracts."""

import threading

import aura_cli.adk as adk
from aura_cli.adk.agent import AgentConfig, AgentResponse
from aura_cli.adk.tools import ToolResult
from aura_cli.application.agents import (
    AgentConfig as ApplicationAgentConfig,
)
from aura_cli.application.agents import (
    AgentResponse as ApplicationAgentResponse,
)
from aura_cli.application.agents import (
    ToolResult as ApplicationToolResult,
)


def test_public_contract_types_preserve_application_identity() -> None:
    assert AgentConfig is ApplicationAgentConfig
    assert AgentResponse is ApplicationAgentResponse
    assert ToolResult is ApplicationToolResult


def test_all_declared_public_names_resolve() -> None:
    assert set(adk.__all__)
    assert all(hasattr(adk, name) for name in adk.__all__)


def test_import_and_non_specialized_public_access_work_in_worker_thread() -> None:
    result: list[tuple[str, str]] = []

    def inspect_api() -> None:
        result.append((adk.Agent.__name__, adk.Workflow.__name__))

    worker = threading.Thread(target=inspect_api)
    worker.start()
    worker.join(timeout=5)

    assert not worker.is_alive()
    assert result == [("Agent", "Workflow")]


def test_deprecated_alias_has_schedule_and_remains_resolvable() -> None:
    schedule = adk.DEPRECATIONS["MemoryStore"]
    assert adk.MemoryStore is adk.PersistentMemory
    assert schedule.replacement == "PersistentMemory"
    assert schedule.deprecated_since == "0.2.0"
    assert schedule.remove_no_earlier_than == "1.0.0"


# ---------------------------------------------------------------------------
# New symbols added to __all__ — verify they are accessible and correct type
# ---------------------------------------------------------------------------

def test_workflow_builder_exported() -> None:
    assert adk.WorkflowBuilder is not None
    assert hasattr(adk.WorkflowBuilder, "add")
    assert hasattr(adk.WorkflowBuilder, "build")


def test_step_state_exported() -> None:
    from aura_cli.application.agents.workflow import StepState as _StepState

    assert adk.StepState is _StepState


def test_create_workflow_is_callable() -> None:
    assert callable(adk.create_workflow)


def test_create_workflow_returns_workflow_instance() -> None:
    async def _noop(task, **kwargs):
        return adk.AgentResponse(content="ok", success=True)

    wf = adk.create_workflow(
        name="test-wf",
        steps=[
            {"id": "step1", "name": "Step 1", "fn": _noop},
        ],
    )
    assert isinstance(wf, adk.Workflow)


def test_composite_agent_exported() -> None:
    assert adk.CompositeAgent is not None
    assert issubclass(adk.CompositeAgent, adk.Agent)


def test_create_agent_returns_none_for_unknown() -> None:
    result = adk.create_agent("__nonexistent_agent__")
    assert result is None


def test_list_agents_returns_list() -> None:
    names = adk.list_agents()
    assert isinstance(names, list)


def test_get_agent_class_returns_none_for_unknown() -> None:
    assert adk.get_agent_class("__nonexistent__") is None


def test_register_agent_decorator() -> None:
    @adk.register_agent
    class _TempAgent(adk.Agent):
        name = "_temp_test_agent_xyzzy"
        description = "Temporary test agent"

        async def execute(self, task: str, **kwargs) -> adk.AgentResponse:
            return adk.AgentResponse(content=task, success=True)

    assert adk.get_agent_class("_temp_test_agent_xyzzy") is _TempAgent
    assert "_temp_test_agent_xyzzy" in adk.list_agents()


def test_tool_category_exported() -> None:
    assert adk.ToolCategory is not None
    assert hasattr(adk.ToolCategory, "FILE_SYSTEM")
    assert hasattr(adk.ToolCategory, "SHELL")


def test_tool_schema_exported() -> None:
    assert adk.ToolSchema is not None
    schema = adk.ToolSchema(name="t", description="d")
    assert schema.name == "t"
    openai = schema.to_openai_schema()
    assert openai["type"] == "function"
    anthropic = schema.to_anthropic_schema()
    assert "input_schema" in anthropic


def test_reset_tool_registry_exported() -> None:
    assert callable(adk.reset_tool_registry)


def test_tool_decorator_registers_in_global_registry() -> None:
    @adk.tool(name="_test_tool_xyzzy", description="Test tool")
    def _my_tool(value: str) -> str:
        return value.upper()

    registry = adk.get_tool_registry()
    assert "_test_tool_xyzzy" in registry
    schema = registry.get_schema("_test_tool_xyzzy")
    assert schema is not None
    assert schema.description == "Test tool"


def test_planning_agent_proxy_accessible() -> None:
    # PlanningAgent is a lazy proxy — verify the proxy object itself is present
    assert adk.PlanningAgent is not None
    assert repr(adk.PlanningAgent).startswith("<LazyProxy")


def test_ops_agent_proxy_accessible() -> None:
    assert adk.OpsAgent is not None
    assert repr(adk.OpsAgent).startswith("<LazyProxy")
