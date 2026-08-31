"""Tests for delegated task application policies and their CLI adapter."""

from pathlib import Path
from unittest.mock import MagicMock

from aura_cli.application.agents.delegation import (
    build_delegate_handoff,
    build_delegate_payload,
    get_supervisor_state,
)
from aura_cli.cli.delegated_tasks import DelegatedTaskManager


class TestGetSupervisorState:
    def test_completed(self):
        assert (
            get_supervisor_state(status="completed", alive=False, fallback_reason=None)
            == "completed"
        )
        assert (
            get_supervisor_state(status="success", alive=False, fallback_reason=None)
            == "completed"
        )

    def test_awaiting_human(self):
        assert (
            get_supervisor_state(
                status="x", alive=False, fallback_reason="human_approval_required"
            )
            == "awaiting_human"
        )

    def test_in_progress(self):
        assert (
            get_supervisor_state(status="running", alive=True, fallback_reason=None)
            == "in_progress"
        )

    def test_returned_to_chat(self):
        assert (
            get_supervisor_state(
                status="error", alive=False, fallback_reason="some_reason"
            )
            == "returned_to_chat"
        )

    def test_delegated(self):
        assert (
            get_supervisor_state(status="unknown", alive=False, fallback_reason=None)
            == "delegated"
        )


class TestDelegatedTaskManager:
    def test_register_and_list(self):
        mgr = DelegatedTaskManager()
        mgr.register_task(
            agent_type="agi",
            task_id="t1",
            thread_name="th1",
            prompt="build api",
            delegation_payload={},
            mode=None,
        )
        assert "t1" in mgr.tasks
        result = mgr.list_tasks()
        assert "t1" in result
        assert "agi" in result

    def test_resolve_by_id(self):
        mgr = DelegatedTaskManager()
        mgr.register_task(
            agent_type="ops",
            task_id="t2",
            thread_name="th2",
            prompt="deploy",
            delegation_payload={},
        )
        task = mgr.resolve_task(task_id="t2")
        assert task["agent_type"] == "ops"

    def test_resolve_latest(self):
        mgr = DelegatedTaskManager()
        mgr.register_task(
            agent_type="agi",
            task_id="old",
            thread_name="a",
            prompt="x",
            delegation_payload={},
        )
        mgr.register_task(
            agent_type="agi",
            task_id="new",
            thread_name="b",
            prompt="y",
            delegation_payload={},
        )
        task = mgr.resolve_task(agent_type="agi")
        assert task["task_id"] == "new"

    def test_empty_list(self):
        mgr = DelegatedTaskManager()
        assert "Nenhuma" in mgr.list_tasks()

    def test_summarize_empty(self):
        mgr = DelegatedTaskManager()
        assert "Nenhuma" in mgr.summarize_tasks()

    def test_persist_callback_called(self):
        cb = MagicMock()
        mgr = DelegatedTaskManager(persist_callback=cb)
        mgr.register_task(
            agent_type="agi",
            task_id="t1",
            thread_name="th",
            prompt="p",
            delegation_payload={},
        )
        cb.assert_called_once()


class TestBuildDelegateHandoff:
    def test_basic(self):
        result = build_delegate_handoff(
            "create api",
            agent_label="AGI",
            conversation_history=[{"role": "user", "content": "hello"}],
            project_root=Path("/tmp/proj"),
            final_model="gemini-2.5-flash",
            constitution=None,
        )
        assert "[CHAT DELEGATION HANDOFF]" in result
        assert "create api" in result
        assert "AGI" in result
        assert "/tmp/proj" in result

    def test_with_mode(self):
        result = build_delegate_handoff(
            "deploy",
            agent_label="Ops",
            conversation_history=[],
            project_root=Path("/tmp"),
            final_model="gpt-4o",
            constitution="rules",
            mode="docker",
        )
        assert "docker" in result
        assert "Constitution active: yes" in result

    def test_with_handoff_context(self):
        result = build_delegate_handoff(
            "task",
            agent_label="AGI",
            conversation_history=[],
            project_root=Path("/tmp"),
            final_model="x",
            constitution=None,
            handoff_context="custom context here",
        )
        assert "custom context here" in result


class TestBuildDelegatePayload:
    def test_basic(self):
        result = build_delegate_payload(
            "refactor module",
            agent_label="AGI",
            conversation_history=[
                {"role": "user", "content": "refactor the auth module"},
                {"role": "assistant", "content": "sure"},
            ],
            project_root=Path("/proj"),
            final_model="claude-3-5-sonnet",
            constitution="my rules",
        )
        assert result["source"] == "general_chat"
        assert result["agent_label"] == "AGI"
        assert result["primary_request"] == "refactor module"
        assert result["constitution_active"] is True
        assert "refactor the auth module" in result["recent_chat_excerpt"]
