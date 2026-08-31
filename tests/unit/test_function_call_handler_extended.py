"""
Extended tests for function call handler.

Tests cover:
    - Tool call parsing from different formats
    - Tool execution with error handling
    - Diff confirmation flow
"""

from unittest.mock import Mock

import pytest


class TestToolCallParsing:
    """Tests for parsing tool calls from LLM responses."""

    def test_parse_tool_calls_openai_format(self):
        """Test parsing OpenAI format tool calls."""
        from aura_cli.cli.response_parser import parse_tool_calls

        # Create mock message with tool_calls
        message = Mock()
        mock_function = Mock()
        mock_function.name = "read_file"
        mock_function.arguments = '{"path": "test.py"}'

        mock_tool_call = Mock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function = mock_function

        message.tool_calls = [mock_tool_call]
        message.content = None

        result = parse_tool_calls(message)

        assert result is not None
        assert len(result) == 1
        # parse_tool_calls returns message.tool_calls directly for OpenAI format
        # So result[0] is the Mock tool_call object
        assert result[0].function.name == "read_file"

    def test_parse_tool_calls_legacy_format(self):
        """Test parsing legacy function_call format."""
        from aura_cli.cli.response_parser import parse_tool_calls

        message = Mock()
        message.tool_calls = None
        message.function_call = {
            "name": "write_file",
            "arguments": '{"path": "out.txt", "content": "hello"}',
        }
        message.content = None

        result = parse_tool_calls(message)

        assert result is not None
        assert len(result) == 1

    def test_parse_tool_calls_local_llm_format(self):
        """Test parsing local LLM XML format."""
        from aura_cli.cli.response_parser import parse_tool_calls

        message = Mock()
        message.tool_calls = None
        message.function_call = None
        message.content = """
Here's my response.
<function_call>list_directory</function_call>
<arguments>{"path": "."}</arguments>
Some more text.
"""

        result = parse_tool_calls(message)

        assert result is not None
        assert len(result) == 1
        assert result[0]["function"]["name"] == "list_directory"

    def test_parse_tool_calls_no_calls(self):
        """Test parsing message with no tool calls."""
        from aura_cli.cli.response_parser import parse_tool_calls

        message = Mock()
        message.tool_calls = None
        message.function_call = None
        message.content = "Just a regular message without any tool calls."

        result = parse_tool_calls(message)

        assert result is None


class TestExtractToolCallData:
    """Tests for extracting data from tool calls."""

    def test_extract_from_openai_object(self):
        """Test extraction from OpenAI tool call object."""
        from aura_cli.cli.response_parser import extract_tool_call_data

        tool_call = Mock()
        tool_call.id = "call_abc"
        tool_call.function = Mock()
        tool_call.function.name = "test_tool"
        tool_call.function.arguments = '{"arg1": "value1"}'

        name, args, call_id = extract_tool_call_data(tool_call)

        assert name == "test_tool"
        assert args == '{"arg1": "value1"}'
        assert call_id == "call_abc"

    def test_extract_from_dict(self):
        """Test extraction from dictionary format."""
        from aura_cli.cli.response_parser import extract_tool_call_data

        tool_call = {
            "id": "call_xyz",
            "function": {"name": "another_tool", "arguments": '{"key": "val"}'},
        }

        name, args, call_id = extract_tool_call_data(tool_call)

        assert name == "another_tool"
        assert args == '{"key": "val"}'
        assert call_id == "call_xyz"

    def test_extract_invalid_format_raises(self):
        """Test that invalid format raises ValueError."""
        from aura_cli.cli.response_parser import extract_tool_call_data

        with pytest.raises(ValueError):
            extract_tool_call_data({"invalid": "format"})


class TestBuildResponseFromToolResults:
    """Tests for building responses from tool results."""

    def test_build_response_single_result(self):
        """Test building response from single tool result."""
        from aura_cli.application.conversation import build_tool_result_response

        history = [
            {"role": "user", "content": "Read the file"},
            {"role": "tool", "name": "read_file", "content": "File content here..."},
        ]

        response = build_tool_result_response(history, "Read the file")

        assert response is not None
        assert len(response) > 0

    def test_build_response_multiple_results(self):
        """Test building response from multiple tool results."""
        from aura_cli.application.conversation import build_tool_result_response

        history = [
            {"role": "user", "content": "Do some work"},
            {"role": "tool", "name": "read_file", "content": "Content 1"},
            {"role": "tool", "name": "write_file", "content": "File written"},
            {"role": "tool", "name": "list_directory", "content": "Listou 5 itens"},
        ]

        response = build_tool_result_response(history)

        assert response is not None
        assert "concluída" in response.lower() or "operação" in response.lower()

    def test_build_response_no_results(self):
        """Test building response with no tool results."""
        from aura_cli.application.conversation import build_tool_result_response

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        response = build_tool_result_response(history)

        assert response is not None
        assert "sucesso" in response.lower() or "concluída" in response.lower()


class TestSafeToolExecution:
    """Tests for safe tool execution patterns."""

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """execute_tool_call deve lançar KeyError para ferramenta inexistente."""
        from unittest.mock import MagicMock

        from aura_cli.cli.tool_execution import execute_tool_call

        ui = MagicMock()
        console = MagicMock()
        stats = MagicMock()

        with pytest.raises(KeyError, match="not_a_real_tool_xyz"):
            await execute_tool_call(
                function_name="not_a_real_tool_xyz",
                function_args={},
                tool_call_id="test-id",
                available_tools={},
                conversation_history=[],
                stats=stats,
                ui=ui,
                console=console,
            )

    def test_write_tools_identified(self):
        """Test that write tools are correctly identified."""
        from aura_cli.cli.tool_execution import WRITE_TOOLS

        assert "write_file" in WRITE_TOOLS
        assert "edit_file" in WRITE_TOOLS
        assert "replace_in_file" in WRITE_TOOLS

        # read_file should NOT be a write tool
        assert "read_file" not in WRITE_TOOLS


class TestDiffConfirmation:
    """Tests for diff confirmation flow."""

    @pytest.mark.asyncio
    async def test_show_diff_confirmation_skip(self):
        """Test diff confirmation with skip_confirmations enabled."""
        from aura_cli.cli.tool_execution import _show_diff_confirmation
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        original_skip = stats.skip_confirmations

        try:
            stats.skip_confirmations = True

            ui = Mock()
            console = Mock()

            should_execute, action = await _show_diff_confirmation(
                "write_file",
                {"path": "test.txt", "content": "hello"},
                ui,
                console,
            )

            assert should_execute is True
            assert action == "accept"
        finally:
            stats.skip_confirmations = original_skip
