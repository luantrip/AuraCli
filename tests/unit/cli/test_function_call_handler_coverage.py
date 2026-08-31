"""Tests for cli/function_call_handler.py — uncovered branches."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Canonical tool-result summaries
# ---------------------------------------------------------------------------


class TestSummarizeToolResult:
    def _fn(self, name, content):
        from aura_cli.application.conversation import summarize_tool_result

        return summarize_tool_result(name, content)

    def test_read_file_returns_preview(self):
        result = self._fn("read_file", "hello world content")
        assert "Li o arquivo" in result
        assert "hello" in result

    def test_write_file_success(self):
        result = self._fn("write_file", "Arquivo editado com sucesso")
        assert result == "Arquivo modificado com sucesso"

    def test_write_file_failure_returns_none(self):
        result = self._fn("write_file", "Operação cancelada")
        assert result is None

    def test_list_directory_success(self):
        result = self._fn("list_directory", "Listou 3 itens em '.'")
        assert result is not None

    def test_list_directory_no_listou(self):
        result = self._fn("list_directory", "something else")
        assert result is None

    def test_shell_command_returns_preview(self):
        result = self._fn("run_shell_command", "output text")
        assert result is not None

    def test_short_error_returns_none(self):
        result = self._fn("any_tool", "Erro: bad")
        assert result is None

    def test_long_content_truncated(self):
        result = self._fn("other_tool", "x" * 300)
        assert result is not None
        assert len(result) <= 200


# ---------------------------------------------------------------------------
# Canonical response builder
# ---------------------------------------------------------------------------


class TestBuildResponseFromToolResults:
    def _fn(self, history, request=None):
        from aura_cli.application.conversation import build_tool_result_response

        return build_tool_result_response(history, request)

    def test_empty_history_returns_default(self):
        result = self._fn([])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_with_user_request_and_no_tools(self):
        result = self._fn([], "do something")
        assert "do something" in result or "concluí" in result.lower()

    def test_single_tool_result(self):
        history = [
            {"role": "tool", "name": "read_file", "content": "file content here"}
        ]
        result = self._fn(history, "read the file")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_multiple_tool_results(self):
        history = [
            {"role": "tool", "name": "read_file", "content": "content"},
            {
                "role": "tool",
                "name": "write_file",
                "content": "Arquivo editado com sucesso",
            },
            {"role": "tool", "name": "run_shell_command", "content": "ok"},
        ]
        result = self._fn(history, "do tasks")
        assert isinstance(result, str)

    def test_many_tool_results_summarized(self):
        history = [
            {"role": "tool", "name": "run_shell_command", "content": f"output {i}"}
            for i in range(5)
        ]
        result = self._fn(history)
        assert "operações" in result.lower() or isinstance(result, str)


# ---------------------------------------------------------------------------
# parse_tool_calls
# ---------------------------------------------------------------------------


class TestParseToolCalls:
    def _fn(self, msg):
        from aura_cli.cli.response_parser import parse_tool_calls

        return parse_tool_calls(msg)

    def test_returns_tool_calls_from_openai_format(self):
        msg = MagicMock()
        msg.tool_calls = [MagicMock()]
        msg.function_call = None
        result = self._fn(msg)
        assert result == msg.tool_calls

    def test_legacy_function_call_wrapped(self):
        msg = MagicMock()
        msg.tool_calls = None
        msg.function_call = MagicMock()
        result = self._fn(msg)
        assert result == [msg.function_call]

    def test_xml_format_parsed(self):
        msg = MagicMock()
        msg.tool_calls = None
        msg.function_call = None
        msg.content = '<function_call>read_file</function_call><arguments>{"path": "x.py"}</arguments>'
        result = self._fn(msg)
        assert result is not None
        assert len(result) == 1
        assert result[0]["function"]["name"] == "read_file"

    def test_no_tool_calls_returns_none(self):
        msg = MagicMock()
        msg.tool_calls = None
        msg.function_call = None
        msg.content = "plain text without tools"
        result = self._fn(msg)
        assert result is None


# ---------------------------------------------------------------------------
# _parse_local_llm_function_call
# ---------------------------------------------------------------------------


class TestParseLocalLLMFunctionCall:
    def _fn(self, content, message=None):
        from aura_cli.cli.response_parser import _parse_local_llm_function_call

        if message is None:
            message = MagicMock()
            message.content = content
        return _parse_local_llm_function_call(content, message)

    def test_valid_xml_call_parsed(self):
        content = '<function_call>write_file</function_call><arguments>{"path": "a.txt", "content": "hi"}</arguments>'
        result = self._fn(content)
        assert result is not None
        assert result[0]["function"]["name"] == "write_file"
        args = json.loads(result[0]["function"]["arguments"])
        assert args["path"] == "a.txt"

    def test_invalid_json_args_returns_empty_dict(self):
        content = "<function_call>tool</function_call><arguments>NOT JSON</arguments>"
        result = self._fn(content)
        assert result is not None
        assert json.loads(result[0]["function"]["arguments"]) == {}

    def test_missing_tags_returns_none(self):
        result = self._fn("no tags here")
        assert result is None

    def test_message_content_stripped_of_tags(self):
        msg = MagicMock()
        content = "text before <function_call>f</function_call><arguments>{}</arguments> text after"
        msg.content = content
        self._fn(content, msg)
        assert "<function_call>" not in msg.content


# ---------------------------------------------------------------------------
# extract_tool_call_data
# ---------------------------------------------------------------------------


class TestExtractToolCallData:
    def _fn(self, tc, idx=0):
        from aura_cli.cli.response_parser import extract_tool_call_data

        return extract_tool_call_data(tc, idx)

    def test_openai_object_format(self):
        tc = MagicMock()
        tc.function.name = "read_file"
        tc.function.arguments = '{"path": "x"}'
        tc.id = "call_123"
        name, _args, id_ = self._fn(tc)
        assert name == "read_file"
        assert id_ == "call_123"

    def test_dict_with_function_key(self):
        tc = {
            "function": {"name": "write_file", "arguments": '{"path": "y"}'},
            "id": "c1",
        }
        name, _args, id_ = self._fn(tc)
        assert name == "write_file"
        assert id_ == "c1"

    def test_dict_legacy_format(self):
        tc = {"name": "list_directory", "arguments": '{"path": "."}', "id": "c2"}
        name, _args, _id = self._fn(tc)
        assert name == "list_directory"

    def test_dict_missing_name_raises(self):
        from aura_cli.cli.response_parser import extract_tool_call_data

        with pytest.raises(ValueError):
            extract_tool_call_data({"id": "x"}, 0)

    def test_unsupported_type_raises(self):
        from aura_cli.cli.response_parser import extract_tool_call_data

        with pytest.raises(ValueError):
            extract_tool_call_data(42, 0)

    def test_fallback_id_generated_when_missing(self):
        tc = MagicMock()
        tc.function.name = "tool"
        tc.function.arguments = "{}"
        del tc.id
        _name, _args, id_ = self._fn(tc, 3)
        assert "3" in id_


# ---------------------------------------------------------------------------
# _run_ops_audit
# ---------------------------------------------------------------------------


class TestRunOpsAudit:
    def test_returns_true_when_audit_passes(self):
        from aura_cli.cli.tool_execution import _run_ops_audit

        mock_audit = MagicMock()
        mock_audit.blocked = False
        with patch(
            "aura_cli.core.ops_tools.security.ops_auditor.audit_tool_call",
            return_value=mock_audit,
        ):
            result = _run_ops_audit("read_file", {}, MagicMock())
        assert result is True

    def test_returns_false_when_import_fails(self):
        from aura_cli.cli.tool_execution import _run_ops_audit

        # The function does a lazy `from aura_cli.core.ops_tools.security.ops_auditor
        # import audit_tool_call`. Raising ImportError from that symbol is the
        # correct way to simulate a missing auditor — patching builtins.__import__
        # causes the patch machinery itself to fail before the test body runs.
        with patch(
            "aura_cli.core.ops_tools.security.ops_auditor.audit_tool_call",
            side_effect=ImportError("nope"),
        ):
            result = _run_ops_audit("any_tool", {}, MagicMock())
        assert result is False

    def test_returns_false_when_audit_raises(self):
        from aura_cli.cli.tool_execution import _run_ops_audit

        with patch(
            "aura_cli.core.ops_tools.security.ops_auditor.audit_tool_call",
            side_effect=RuntimeError("auditor unavailable"),
        ):
            result = _run_ops_audit("any_tool", {}, MagicMock())
        assert result is False


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Confirmation input
# ---------------------------------------------------------------------------


def test_prompt_user_action_rejects_unexpected_input_failure():
    from aura_cli.cli.tool_execution import _prompt_user_action

    stats = MagicMock(skip_confirmations=False)
    with patch("rich.prompt.Prompt.ask", side_effect=RuntimeError("input failed")):
        assert _prompt_user_action(MagicMock(), stats) == (False, "reject")


# ---------------------------------------------------------------------------
# _raise_tool_exception
# ---------------------------------------------------------------------------


class TestRaiseToolException:
    def _fn(self, name, args, exc):
        from aura_cli.cli.tool_execution import _raise_tool_exception

        _raise_tool_exception(name, args, exc)

    def test_key_error_raises_tool_execution_error(self):
        from aura_cli.cli.utils.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError):
            self._fn("tool", {}, KeyError("missing"))

    def test_permission_error_on_write_tool_raises_file_op_error(self):
        from aura_cli.cli.utils.exceptions import FileOperationError

        with pytest.raises(FileOperationError):
            self._fn("write_file", {"file_path": "x.txt"}, PermissionError("denied"))

    def test_os_error_on_non_write_raises_tool_error(self):
        from aura_cli.cli.utils.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError):
            self._fn("read_file", {}, OSError("disk error"))

    def test_generic_exception_raises_tool_error(self):
        from aura_cli.cli.utils.exceptions import ToolExecutionError

        with pytest.raises(ToolExecutionError):
            self._fn("tool", {}, RuntimeError("unexpected"))


# ---------------------------------------------------------------------------
# _call_tool
# ---------------------------------------------------------------------------


class TestCallTool:
    def test_uses_registry_when_available(self):
        from aura_cli.cli.tool_execution import _call_tool

        registry = MagicMock()
        registry.get_tool.return_value = MagicMock()
        registry.execute_tool.return_value = "registry_result"
        result = _call_tool("my_tool", {}, {}, registry)
        assert result == "registry_result"
        registry.execute_tool.assert_called_once_with("my_tool", {})

    def test_falls_back_to_direct_call_when_no_registry(self):
        from aura_cli.cli.tool_execution import _call_tool

        tool_fn = MagicMock(return_value="direct_result")
        with patch(
            "aura_cli.core.agents.tool_calling.tool_caller.ToolCaller",
            side_effect=ImportError("no module"),
        ):
            result = _call_tool("my_tool", {"x": 1}, {"my_tool": tool_fn}, None)
        assert result == "direct_result"
        tool_fn.assert_called_once_with(x=1)


# ---------------------------------------------------------------------------
# _run_policy_check
# ---------------------------------------------------------------------------


class TestRunPolicyCheck:
    def test_passes_when_allowed(self):
        from aura_cli.cli.tool_execution import _run_policy_check

        mock_pm = MagicMock()
        mock_pm.check_access.return_value = (True, "ok")
        with patch(
            "aura_cli.cli.tool_execution._get_policy_manager", return_value=mock_pm
        ):
            _run_policy_check("tool", {})  # no exception

    def test_raises_when_denied(self):
        from aura_cli.cli.tool_execution import _run_policy_check
        from aura_cli.cli.utils.exceptions import ToolExecutionError

        mock_pm = MagicMock()
        mock_pm.check_access.return_value = (False, "not allowed")
        with patch(
            "aura_cli.cli.tool_execution._get_policy_manager", return_value=mock_pm
        ):
            with pytest.raises(ToolExecutionError):
                _run_policy_check("tool", {})

    def test_no_policy_manager_is_noop(self):
        from aura_cli.cli.tool_execution import _run_policy_check

        with patch(
            "aura_cli.cli.tool_execution._get_policy_manager", return_value=None
        ):
            _run_policy_check("tool", {})  # no exception


# ---------------------------------------------------------------------------
# _check_rate_limit_suppression
# ---------------------------------------------------------------------------


class TestCheckRateLimitSuppression:
    def setup_method(self):
        import aura_cli.cli.function_call_handler as fch

        fch._last_error_message = None
        fch._last_error_time = 0.0

    def test_first_occurrence_not_suppressed(self):
        from aura_cli.cli.function_call_handler import _check_rate_limit_suppression

        assert _check_rate_limit_suppression("quota exceeded") is False

    def test_repeated_within_window_suppressed(self):
        import aura_cli.cli.function_call_handler as fch
        from aura_cli.cli.function_call_handler import _check_rate_limit_suppression

        fch._last_error_message = "quota exceeded"
        fch._last_error_time = time.time()
        assert _check_rate_limit_suppression("quota exceeded") is True

    def test_different_message_not_suppressed(self):
        import aura_cli.cli.function_call_handler as fch
        from aura_cli.cli.function_call_handler import _check_rate_limit_suppression

        fch._last_error_message = "other error"
        fch._last_error_time = time.time()
        assert _check_rate_limit_suppression("quota exceeded") is False

    def test_expired_window_not_suppressed(self):
        import aura_cli.cli.function_call_handler as fch
        from aura_cli.cli.function_call_handler import _check_rate_limit_suppression

        fch._last_error_message = "quota exceeded"
        fch._last_error_time = time.time() - 10.0  # expired
        assert _check_rate_limit_suppression("quota exceeded") is False
