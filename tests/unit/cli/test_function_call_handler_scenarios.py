"""Scenario tests for function_call_handler runtime behavior."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from aura_cli.cli import function_call_handler as fch
from aura_cli.cli import response_parser
from aura_cli.cli import tool_execution as execution


class TestFunctionCallHandlerScenarios:
    """Covers parsing, confirmation and guarded tool execution paths."""

    def test_parse_tool_calls_prefers_openai_tool_calls(self):
        """When tool_calls exists, parser should return it unchanged."""
        tool_calls = [{"id": "1", "function": {"name": "read_file", "arguments": "{}"}}]
        message = SimpleNamespace(
            tool_calls=tool_calls, function_call=None, content=None
        )

        result = response_parser.parse_tool_calls(message)
        assert result == tool_calls

    def test_execute_tool_call_facade_delegates_to_canonical_engine(self):
        canonical = AsyncMock(return_value=("ok", 0.25))

        with patch("aura_cli.cli.tool_execution.execute_tool_call", canonical):
            result = asyncio.run(
                fch.execute_tool_call(
                    "read_file",
                    {"path": "x.py"},
                    "call_1",
                    {},
                    [],
                    Mock(),
                    Mock(),
                    Mock(),
                    suppress_tool_loading=True,
                )
            )

        assert result == ("ok", 0.25)
        canonical.assert_awaited_once()

    def test_execute_tool_call_facade_forwards_explicit_audit_sink(self):
        canonical = AsyncMock(return_value=("ok", 0.25))
        audit_sink = Mock()

        with patch("aura_cli.cli.tool_execution.execute_tool_call", canonical):
            result = asyncio.run(
                fch.execute_tool_call(
                    "read_file",
                    {"path": "x.py"},
                    "call_2",
                    {},
                    [],
                    Mock(),
                    Mock(),
                    Mock(),
                    capability_audit=audit_sink,
                )
            )

        assert result == ("ok", 0.25)
        assert canonical.await_args.kwargs["capability_audit"] is audit_sink

    def test_handler_does_not_redefine_execution_pipeline_helpers(self):
        """Execution internals belong only to tool_execution."""
        for name in {
            "_resolve_hook_manager",
            "_run_pre_execution_checks",
            "_run_tool_and_heal",
            "_auto_heal_python_write",
            "_record_tool_result",
            "_run_policy_check",
        }:
            assert name not in fch.__dict__

    def test_provider_error_adapter_suppresses_repeated_free_tier_message(self):
        fch._last_error_message = None
        fch._last_error_time = 0.0
        error = RuntimeError("free_tier quota exceeded")

        first = fch._handle_llm_call_error(error)
        second = fch._handle_llm_call_error(error)

        assert first is not None
        assert "Free Tier Quota Exceeded" in first[0]
        assert second == ("__SUPPRESSED__", None)

    def test_provider_error_adapter_revokes_leaked_credential(self):
        with patch.object(fch, "_handle_leaked_key") as revoke:
            result = fch._handle_llm_call_error(RuntimeError("API key leaked"))

        revoke.assert_called_once_with()
        assert result is not None
        assert "deactivated for security" in result[0]

    def test_parse_tool_calls_local_llm_xml_strips_function_tags(self):
        """Local XML format should be converted into a standard tool call."""
        message = SimpleNamespace(
            content=(
                "<function_call>read_file</function_call>"
                '<arguments>{"path":"a.py"}</arguments>\nremaining text'
            )
        )

        result = response_parser.parse_tool_calls(message)
        assert isinstance(result, list)
        assert result[0]["function"]["name"] == "read_file"
        assert "function_call" not in message.content
        assert "arguments" not in message.content

    def test_check_tool_confirmation_blocks_risky_tool_when_feature_unavailable(self):
        """Unavailable intervention must not silently allow a risky tool."""
        console = Mock()
        with (
            patch.object(execution, "INTERVENTION_AVAILABLE", False),
            patch.object(execution, "get_service_registry", return_value=None),
        ):
            allowed = execution._check_tool_requires_confirmation(
                "run_shell_command", {"command": "git status"}, console
            )
        assert allowed is False

    def test_execute_tool_call_cancels_non_write_tool_when_denied(self):
        """Non-write tool should return cancellation message when denied."""
        available_tools = {"read_file": Mock(return_value="content")}
        history = []
        stats = Mock()
        ui = Mock()
        console = Mock()
        console.width = 120

        with (
            patch.object(execution, "get_service_registry", return_value=None),
            patch.object(execution, "get_hook_manager", return_value=None),
            patch.object(execution, "_run_hooks", new=AsyncMock(return_value=None)),
            patch.object(execution, "_run_ops_audit", return_value=True),
            patch.object(
                execution, "_check_tool_requires_confirmation", return_value=False
            ),
        ):
            result, elapsed = asyncio.run(
                fch.execute_tool_call(
                    function_name="read_file",
                    function_args={"path": "x.py"},
                    tool_call_id="call_1",
                    available_tools=available_tools,
                    conversation_history=history,
                    stats=stats,
                    ui=ui,
                    console=console,
                )
            )

        assert "cancelada pelo usuário" in result
        assert elapsed == 0.0
        available_tools["read_file"].assert_not_called()

    def test_execute_tool_call_wraps_write_oserror_as_file_operation_error(self):
        """Write tool filesystem errors should be mapped to FileOperationError."""
        available_tools = {"write_file": Mock(return_value="ok")}
        history = []
        stats = Mock()
        ui = Mock()
        console = Mock()
        console.width = 120

        with (
            patch.object(execution, "get_service_registry", return_value=None),
            patch.object(execution, "get_hook_manager", return_value=None),
            patch.object(execution, "_run_hooks", new=AsyncMock(return_value=None)),
            patch.object(execution, "_run_ops_audit", return_value=True),
            patch.object(execution, "DIFF_CONFIRMATION_ENABLED", False),
            patch.object(
                execution,
                "_run_tool_with_interceptors",
                side_effect=OSError("disk full"),
            ),
        ):
            with pytest.raises(fch.FileOperationError):
                asyncio.run(
                    fch.execute_tool_call(
                        function_name="write_file",
                        function_args={"file_path": "x.py", "content": "abc"},
                        tool_call_id="call_2",
                        available_tools=available_tools,
                        conversation_history=history,
                        stats=stats,
                        ui=ui,
                        console=console,
                        suppress_tool_loading=True,
                    )
                )

    def test_process_function_calls_loop_returns_interrupted_on_shutdown_event(self):
        """Loop should stop immediately when shutdown event is set."""
        shutdown_event = Mock()
        shutdown_event.is_set.return_value = True
        set_workspace = Mock()

        with patch.object(fch.tool_execution, "set_active_workspace", set_workspace):
            result, response = asyncio.run(
                fch.process_function_calls_loop(
                    model="auto",
                    conversation_history=[],
                    tool_schemas=[],
                    available_tools={},
                    stats=Mock(),
                    ui=Mock(),
                    console=Mock(),
                    shutdown_event=shutdown_event,
                )
            )

        assert result == "Execução interrompida pelo usuário."
        assert response is None
        assert set_workspace.call_count == 2
        assert set_workspace.call_args_list[-1].args == (None,)

    def test_process_function_calls_loop_handles_invalid_response_shape(self):
        """Loop should return friendly error when response has no choices."""
        invalid_response = SimpleNamespace(choices=[])

        with patch.object(
            fch, "_llm_call_with_learning", new=AsyncMock(return_value=invalid_response)
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
        assert response is invalid_response

    def test_process_function_calls_loop_returns_limit_exceeded(self):
        """Loop should stop when max function-call budget is exhausted."""
        message = SimpleNamespace(
            tool_calls=[
                {"id": "1", "function": {"name": "read_file", "arguments": "{}"}}
            ],
            content=None,
        )
        llm_response = SimpleNamespace(choices=[SimpleNamespace(message=message)])

        async def _bump_counter(*args, **kwargs):
            return args[-1] + 1

        with (
            patch.object(
                fch, "_llm_call_with_learning", new=AsyncMock(return_value=llm_response)
            ),
            patch.object(
                fch, "_handle_tool_calls", new=AsyncMock(side_effect=_bump_counter)
            ),
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
                    max_calls=2,
                )
            )

        assert result == "Execução interrompida: orçamento do turno esgotado."
        assert response is llm_response
