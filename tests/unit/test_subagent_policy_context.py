from unittest.mock import Mock

import pytest

from aura_cli.application.tools.execution_policy import get_execution_policy
from aura_cli.cli.subagent import _invoke_subagent_tool_with_policy


def test_subagent_tool_failure_does_not_retry_outside_policy() -> None:
    calls: list[object] = []
    tool_call_count = [0]

    def failing_tool(*, path: str) -> None:
        calls.append(get_execution_policy())
        raise RuntimeError(f"falha local: {path}")

    callback = Mock()
    with pytest.raises(RuntimeError, match="falha local"):
        _invoke_subagent_tool_with_policy(
            "write_file",
            failing_tool,
            {"path": "sentinel.txt"},
            tool_call_count=tool_call_count,
            on_tool_call=callback,
        )

    assert len(calls) == 1
    assert calls[0] is not None
    assert calls[0].task_id == "subagent:write_file"
    assert calls[0].allow_dangerous is False
    assert get_execution_policy() is None
    assert tool_call_count == [1]
    callback.assert_called_once_with("write_file", 1)
