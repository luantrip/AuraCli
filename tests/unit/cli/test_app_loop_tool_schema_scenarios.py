"""Scenario tests for AppLoop tool schema sourcing."""

from pathlib import Path
from unittest.mock import Mock, patch

from aura_cli.cli.app_loop import AppLoop
from tests.runtime_helpers import make_runtime_services


def _build_app_loop_with_tools(available_tools):
    """Create an AppLoop with minimal mocked dependencies."""
    return AppLoop(
        ui=Mock(),
        stats=Mock(),
        console=Mock(),
        conversation_history=[],
        context_manager=Mock(),
        available_tools=available_tools,
        initial_model="auto",
        project_root=Path.cwd(),
        runtime_services=make_runtime_services(Path.cwd()),
    )


class TestAppLoopToolSchemaScenarios:
    """Validates schema source priority between local and registry tools."""

    def test_prepare_tool_schemas_prefers_instance_available_tools(self):
        """When app has available_tools, registry fallback should not be used."""
        app_loop = _build_app_loop_with_tools({"tool_a": Mock()})

        with patch(
            "aura_cli.core.llm.tool_schemas.create_tool_schemas"
        ) as create_schemas:
            create_schemas.return_value = [{"name": "tool_a"}]
            result = app_loop._prepare_tool_schemas()

        create_schemas.assert_called_once_with(
            {"tool_a": app_loop.available_tools["tool_a"]}
        )
        assert result == [{"name": "tool_a"}]

    def test_prepare_tool_schemas_falls_back_to_registry_when_empty(self):
        """When no local tools exist, AppLoop should fetch tools from registry."""
        app_loop = _build_app_loop_with_tools({})
        registry_tools = {"tool_b": Mock()}

        with (
            patch(
                "aura_cli.core.service_registry.get_tools_dict",
                return_value=registry_tools,
            ),
            patch(
                "aura_cli.core.llm.tool_schemas.create_tool_schemas"
            ) as create_schemas,
        ):
            create_schemas.return_value = [{"name": "tool_b"}]
            result = app_loop._prepare_tool_schemas()

        create_schemas.assert_called_once_with(registry_tools)
        assert result == [{"name": "tool_b"}]
