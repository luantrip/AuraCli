"""Tests for function call handler - Tool call processing.

Tests verify proper parsing, validation, and execution of function calls.
"""

from unittest.mock import Mock, patch

import pytest

from aura_cli.application.conversation import build_tool_result_response
from aura_cli.cli.function_call_handler import process_function_calls_loop
from aura_cli.cli.response_parser import extract_tool_call_data, parse_tool_calls


class TestParseToolCalls:
    """Test suite for parse_tool_calls."""

    def test_parse_standard_format(self):
        """Test parsing standard tool_calls format."""
        message = Mock()
        message.tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"path": "test.txt"}'},
            }
        ]

        result = parse_tool_calls(message)

        assert len(result) == 1
        assert result[0]["id"] == "call_1"

    def test_parse_legacy_format(self):
        """Test parsing legacy function_call format."""
        message = Mock()
        message.function_call = {
            "name": "read_file",
            "arguments": '{"path": "test.txt"}',
        }
        message.tool_calls = None

        result = parse_tool_calls(message)

        assert len(result) == 1
        assert result[0]["name"] == "read_file"

    def test_parse_no_tool_calls(self):
        """Test parsing message with no tool calls."""
        # parse_tool_calls returns None when no tool calls, not empty list
        message = Mock()
        message.tool_calls = None
        message.function_call = None
        message.content = "No tool calls here"

        result = parse_tool_calls(message)

        assert result is None


class TestExtractToolCallData:
    """Test suite for extract_tool_call_data."""

    def test_extract_standard_format(self):
        """Test extracting data from standard format."""
        tool_call = {
            "id": "call_1",
            "type": "function",
            "function": {"name": "read_file", "arguments": '{"path": "test.txt"}'},
        }

        function_name, args_str, call_id = extract_tool_call_data(tool_call, 0)

        assert function_name == "read_file"
        assert args_str == '{"path": "test.txt"}'
        assert call_id == "call_1"

    def test_extract_legacy_format(self):
        """Test extracting data from legacy format."""
        tool_call = {
            "name": "write_file",
            "arguments": '{"path": "test.txt", "content": "hello"}',
        }

        function_name, args_str, _call_id = extract_tool_call_data(tool_call, 0)

        assert function_name == "write_file"
        assert "test.txt" in args_str

    def test_extract_missing_name(self):
        """Test extracting with missing function name raises ValueError."""
        tool_call = {"id": "call_1", "function": {"arguments": "{}"}}

        with pytest.raises(ValueError, match="Não foi possível extrair"):
            extract_tool_call_data(tool_call, 0)

    def test_extract_unsupported_format(self):
        """Test extracting from unsupported format raises ValueError."""
        tool_call = "invalid_format"

        with pytest.raises(ValueError, match="Formato de tool call não suportado"):
            extract_tool_call_data(tool_call, 0)


class TestBuildResponseFromToolResults:
    """Test suite for the canonical tool-result response builder."""

    def test_build_response_single_tool(self):
        """Test building response from single tool result."""
        history = [
            {"role": "user", "content": "Read file"},
            {"role": "tool", "name": "read_file", "content": "File contents here"},
        ]

        result = build_tool_result_response(history, "Read file")

        assert "Read file" in result or "Concluí" in result
        assert len(result) > 0

    def test_build_response_multiple_tools(self):
        """Test building response from multiple tool results."""
        history = [
            {"role": "user", "content": "Do multiple things"},
            {"role": "tool", "name": "read_file", "content": "Content 1"},
            {"role": "tool", "name": "write_file", "content": "sucesso"},
            {"role": "tool", "name": "list_directory", "content": "Listou files"},
        ]

        result = build_tool_result_response(history, "Do multiple things")

        assert len(result) > 0
        assert "Concluí" in result or "operacoes" in result.lower()

    def test_build_response_no_tools(self):
        """Test building response with no tool results."""
        history = [{"role": "user", "content": "Simple request"}]

        result = build_tool_result_response(history, "Simple request")

        assert "Concluí" in result or "Operação concluída" in result

    def test_build_response_with_user_request(self):
        """Test building response with user request."""
        history = [{"role": "tool", "name": "read_file", "content": "Content"}]

        result = build_tool_result_response(history, "Read the file")

        assert "Read the file" in result or "Concluí" in result


class TestExecuteToolCall:
    """Test suite for execute_tool_call (async)."""

    @pytest.mark.asyncio
    @patch("aura_cli.cli.tool_execution.show_tool_loading")
    @patch("aura_cli.cli.tool_execution.get_service_registry")
    @patch("aura_cli.cli.tool_execution.get_hook_manager")
    @patch("aura_cli.cli.tool_execution._check_tool_requires_confirmation")
    @patch("aura_cli.cli.tool_execution._show_diff_confirmation")
    async def test_execute_tool_call_success(
        self,
        mock_diff_confirmation,
        mock_check_confirmation,
        mock_hook_manager,
        mock_service_registry,
        mock_loading,
    ):
        """Test successful tool execution."""
        mock_check_confirmation.return_value = True
        mock_diff_confirmation.return_value = (True, None)
        mock_service_registry.return_value = None
        mock_hook_manager.return_value = None

        mock_stats = Mock()
        mock_loading.return_value = Mock()

        mock_tool = Mock(return_value="result")
        available_tools = {"test_tool": mock_tool}

        mock_ui = Mock()
        mock_console = Mock()
        mock_console.width = 80

        from aura_cli.cli.function_call_handler import execute_tool_call

        result, execution_time = await execute_tool_call(
            function_name="test_tool",
            function_args={"arg1": "value1"},
            tool_call_id="call_1",
            available_tools=available_tools,
            conversation_history=[],
            stats=mock_stats,
            ui=mock_ui,
            console=mock_console,
        )

        assert result is not None
        assert execution_time >= 0

    @pytest.mark.asyncio
    @patch("aura_cli.cli.tool_execution.get_service_registry")
    @patch("aura_cli.cli.tool_execution.get_hook_manager")
    async def test_execute_tool_call_not_found(
        self, mock_hook_manager, mock_service_registry
    ):
        """Test tool execution with tool not found."""
        mock_service_registry.return_value = None
        mock_hook_manager.return_value = None
        mock_stats = Mock()

        available_tools = {}
        mock_ui = Mock()
        mock_console = Mock()

        from aura_cli.cli.function_call_handler import execute_tool_call

        with pytest.raises(KeyError, match="não encontrada"):
            await execute_tool_call(
                function_name="nonexistent_tool",
                function_args={},
                tool_call_id="call_1",
                available_tools=available_tools,
                conversation_history=[],
                stats=mock_stats,
                ui=mock_ui,
                console=mock_console,
            )

    @pytest.mark.asyncio
    @patch("aura_cli.cli.tool_execution.get_service_registry")
    @patch("aura_cli.cli.tool_execution.get_hook_manager")
    @patch("aura_cli.cli.tool_execution._get_policy_manager")
    @patch("aura_cli.cli.tool_execution.show_tool_loading")
    async def test_execute_tool_call_policy_denied(
        self,
        mock_show_tool_loading,
        mock_get_policy_manager,
        mock_hook_manager,
        mock_service_registry,
    ):
        """PolicyManager denial should block tool execution."""
        mock_service_registry.return_value = None
        mock_hook_manager.return_value = None
        mock_stats = Mock()

        mock_policy = Mock()
        mock_policy.check_access.return_value = (
            False,
            "ferramenta bloqueada neste contexto",
        )
        mock_get_policy_manager.return_value = mock_policy
        mock_show_tool_loading.return_value = Mock()

        available_tools = {"test_tool": Mock(return_value="should_not_run")}
        mock_ui = Mock()
        mock_console = Mock()

        from aura_cli.cli.function_call_handler import execute_tool_call

        with pytest.raises(Exception, match="Acesso negado pela política"):
            await execute_tool_call(
                function_name="test_tool",
                function_args={"arg1": "value1"},
                tool_call_id="call_1",
                available_tools=available_tools,
                conversation_history=[],
                stats=mock_stats,
                ui=mock_ui,
                console=mock_console,
            )


class TestProcessFunctionCallsLoop:
    """Regression tests for loop-level tool error handling."""

    @pytest.mark.asyncio
    async def test_missing_tool_is_written_back_to_conversation(self):
        first_response = Mock()
        first_message = Mock()
        first_message.function_call = None
        first_message.tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "missing_tool", "arguments": "{}"},
            }
        ]
        first_response.choices = [Mock(message=first_message)]

        second_response = Mock()
        second_message = Mock()
        second_message.function_call = None
        second_message.tool_calls = None
        second_message.content = "fallback answer"
        second_response.choices = [Mock(message=second_message)]

        history = [{"role": "user", "content": "do it"}]

        with patch(
            "aura_cli.cli.function_call_handler.query_with_fallback",
            side_effect=[first_response, second_response],
        ):
            response_text, _ = await process_function_calls_loop(
                model="gpt-4o",
                conversation_history=history,
                tool_schemas=[],
                available_tools={},
                stats=Mock(),
                ui=Mock(),
                console=Mock(),
                max_calls=3,
            )

        assert response_text == "fallback answer"
        tool_messages = [msg for msg in history if msg.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert "não encontrada" in tool_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_tool_execution_failure_is_written_back_to_conversation(self):
        first_response = Mock()
        first_message = Mock()
        first_message.function_call = None
        first_message.tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "broken_tool", "arguments": "{}"},
            }
        ]
        first_response.choices = [Mock(message=first_message)]

        second_response = Mock()
        second_message = Mock()
        second_message.function_call = None
        second_message.tool_calls = None
        second_message.content = "fallback answer"
        second_response.choices = [Mock(message=second_message)]

        history = [{"role": "user", "content": "do it"}]

        with patch(
            "aura_cli.cli.function_call_handler.execute_tool_call",
            side_effect=Exception("boom"),
        ):
            with patch(
                "aura_cli.cli.function_call_handler.query_with_fallback",
                side_effect=[first_response, second_response],
            ):
                response_text, _ = await process_function_calls_loop(
                    model="gpt-4o",
                    conversation_history=history,
                    tool_schemas=[],
                    available_tools={"broken_tool": Mock()},
                    stats=Mock(),
                    ui=Mock(),
                    console=Mock(),
                    max_calls=3,
                )

        assert response_text == "fallback answer"
        tool_messages = [msg for msg in history if msg.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert "Erro inesperado ao executar broken_tool" in tool_messages[0]["content"]
