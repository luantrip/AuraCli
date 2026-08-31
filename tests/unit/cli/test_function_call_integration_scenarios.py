"""Integration-like scenarios across function-calling runtime modules."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from aura_cli.cli import function_call_handler as fch
from aura_cli.cli import tool_execution as execution


class TestFunctionCallIntegrationScenarios:
    """Covers short cross-module flows (handler + registry + fallback)."""

    def test_execute_tool_call_uses_registry_when_tool_not_in_available_tools(self):
        """execute_tool_call should resolve tools via ServiceRegistry fallback."""
        fake_registry = Mock()
        fake_registry.get_tool.return_value = object()
        fake_registry.execute_tool.return_value = "registry_result"

        stats = Mock()
        ui = Mock()
        console = Mock()
        console.width = 120
        history = []

        with (
            patch.object(execution, "get_service_registry", return_value=fake_registry),
            patch.object(execution, "get_hook_manager", return_value=None),
            patch.object(execution, "_run_hooks", new=AsyncMock(return_value=None)),
            patch.object(execution, "_run_ops_audit", return_value=True),
            patch.object(
                execution, "_check_tool_requires_confirmation", return_value=True
            ),
            patch.object(execution, "show_tool_loading") as loading,
        ):
            loading.return_value = Mock()
            result, _ = asyncio.run(
                fch.execute_tool_call(
                    function_name="registry_only_tool",
                    function_args={"x": 1},
                    tool_call_id="call_r1",
                    available_tools={},
                    conversation_history=history,
                    stats=stats,
                    ui=ui,
                    console=console,
                )
            )

        assert result == "registry_result"
        fake_registry.execute_tool.assert_called_once_with(
            "registry_only_tool", {"x": 1}
        )
        stats.increment_tool_calls.assert_called_once_with("registry_only_tool")

    def test_process_loop_retries_without_tools_when_content_is_none(self):
        """When content=None and no tool_calls, loop should retry without tool schemas."""
        first_message = SimpleNamespace(
            tool_calls=None, function_call=None, content=None
        )
        first_response = SimpleNamespace(
            choices=[SimpleNamespace(message=first_message)]
        )
        retry_message = SimpleNamespace(content="final plain answer")
        retry_response = SimpleNamespace(
            choices=[SimpleNamespace(message=retry_message)]
        )

        with (
            patch.object(
                fch,
                "_llm_call_with_learning",
                new=AsyncMock(return_value=first_response),
            ),
            patch.object(fch, "query_with_fallback", return_value=retry_response),
        ):
            result, response = asyncio.run(
                fch.process_function_calls_loop(
                    model="auto",
                    conversation_history=[{"role": "user", "content": "hello"}],
                    tool_schemas=[{"name": "read_file"}],  # forces retry branch
                    available_tools={},
                    stats=Mock(),
                    ui=Mock(),
                    console=Mock(),
                )
            )

        assert result == "final plain answer"
        assert response is retry_response

    def test_process_loop_returns_invalid_message_when_choices_missing(self):
        """Loop should emit friendly invalid-response message for malformed payload."""
        malformed_response = SimpleNamespace()

        with patch.object(
            fch,
            "_llm_call_with_learning",
            new=AsyncMock(return_value=malformed_response),
        ):
            result, response = asyncio.run(
                fch.process_function_calls_loop(
                    model="auto",
                    conversation_history=[],
                    tool_schemas=[],
                    available_tools={},
                    stats=Mock(),
                    ui=Mock(),
                    console=Mock(),
                )
            )

        assert "Resposta inválida do modelo" in result
        assert response is malformed_response
