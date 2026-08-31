"""Contract tests for cooperative subagent cancellation."""

from __future__ import annotations

import threading
import time

import pytest

from aura_cli.cli.subagent import _invoke_subagent_tool_with_policy


def test_subagent_tool_wrapper_rejects_cancelled_execution() -> None:
    calls: list[str] = []
    cancel_event = threading.Event()
    cancel_event.set()

    with pytest.raises(TimeoutError, match="cancellation requested"):
        _invoke_subagent_tool_with_policy(
            "read_file",
            lambda: calls.append("called"),
            {},
            tool_call_count=[0],
            on_tool_call=None,
            task_id="subagent:task",
            cancel_event=cancel_event,
        )

    assert calls == []


def test_subagent_tool_wrapper_sets_cancel_event_after_deadline() -> None:
    cancel_event = threading.Event()

    with pytest.raises(TimeoutError, match="deadline exceeded"):
        _invoke_subagent_tool_with_policy(
            "read_file",
            lambda: "ok",
            {},
            tool_call_count=[0],
            on_tool_call=None,
            task_id="subagent:task",
            cancel_event=cancel_event,
            deadline=time.monotonic() - 0.001,
        )

    assert cancel_event.is_set()
