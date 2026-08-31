"""
Tests for autonomous delegation tools (delegate_to_agi, delegate_to_ops).

Validates that the general agent can delegate to AGI/Ops via tools
and that edge cases (already running, no API key) are handled.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.runtime_helpers import make_runtime_services


@pytest.fixture
def app_loop_with_mocks():
    """Create AppLoop with minimal mocks for delegation tests."""
    with patch("aura_cli.core.memory.get_persistent_store") as mock_store:
        from aura_cli.cli.app_loop import AppLoop
        from aura_cli.cli.ui.manager import UIManager

        ui = MagicMock(spec=UIManager)
        ui.status_queue = MagicMock()
        stats = MagicMock()
        console = MagicMock()
        persistent_store = MagicMock()
        persistent_store.get_recent_tasks.return_value = []
        mock_store.return_value = persistent_store
        conversation_history = [{"role": "system", "content": "You are Aura."}]
        context_manager = MagicMock()
        available_tools = {}
        app = AppLoop(
            ui=ui,
            stats=stats,
            console=console,
            conversation_history=conversation_history,
            context_manager=context_manager,
            available_tools=available_tools,
            initial_model="gemini/gemini-2.5-flash",
            project_root=Path("/tmp"),
            runtime_services=make_runtime_services(Path("/tmp")),
        )
        app.agi_thread = None
        app.ops_thread = None
        app.final_model = "gemini/gemini-2.5-flash"
        app.project_root = Path("/tmp")
        yield app


class TestDelegationToolsExist:
    """Delegation methods exist and are callable."""

    def test_do_delegate_to_agi_exists(self, app_loop_with_mocks):
        assert hasattr(app_loop_with_mocks, "_do_delegate_to_agi")
        assert callable(app_loop_with_mocks._do_delegate_to_agi)

    def test_do_delegate_to_ops_exists(self, app_loop_with_mocks):
        assert hasattr(app_loop_with_mocks, "_do_delegate_to_ops")
        assert callable(app_loop_with_mocks._do_delegate_to_ops)


class TestDelegationWhenAlreadyRunning:
    """When AGI or Ops is already running, delegation returns a message instead of starting again."""

    def test_agi_already_running_returns_message(self, app_loop_with_mocks):
        app_loop_with_mocks.agi_thread = MagicMock(
            is_alive=MagicMock(return_value=True)
        )
        result = app_loop_with_mocks._do_delegate_to_agi("refatorar módulo X")
        assert isinstance(result, str)
        assert "já está" in result or "já está em execução" in result.lower()

    def test_ops_already_running_returns_message(self, app_loop_with_mocks):
        app_loop_with_mocks.ops_thread = MagicMock(
            is_alive=MagicMock(return_value=True)
        )
        result = app_loop_with_mocks._do_delegate_to_ops("git status", mode="git")
        assert isinstance(result, str)
        assert "já está" in result or "já está em execução" in result.lower()


class TestDelegationNoApiKey:
    """When no API key is configured, delegation returns a helpful message."""

    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_agi_no_api_key_returns_message(self, mock_keys, app_loop_with_mocks):
        mock_keys.return_value = {}
        app_loop_with_mocks.agi_thread = None
        result = app_loop_with_mocks._do_delegate_to_agi("analisar projeto")
        assert "API" in result or "configurar" in result or "settings" in result.lower()

    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_ops_no_api_key_returns_message(self, mock_keys, app_loop_with_mocks):
        mock_keys.return_value = {}
        app_loop_with_mocks.ops_thread = None
        result = app_loop_with_mocks._do_delegate_to_ops("docker ps", mode="docker")
        assert "API" in result or "configurar" in result or "settings" in result.lower()

    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_agi_openrouter_key_is_accepted(self, mock_keys, app_loop_with_mocks):
        mock_keys.return_value = {"OPENROUTER_API_KEY": "test-key"}
        with patch(
            "aura_cli.cli.utils.worker_factory.create_agi_worker_thread"
        ) as mock_create:
            mock_create.return_value = (MagicMock(), MagicMock())
            result = app_loop_with_mocks._do_delegate_to_agi("analisar projeto")

        assert "AGI" in result
        mock_create.assert_called_once()

    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_ops_nvidia_key_is_accepted(self, mock_keys, app_loop_with_mocks):
        mock_keys.return_value = {"NVIDIA_API_KEY": "test-key"}
        with patch(
            "aura_cli.cli.utils.worker_factory.create_ops_worker_thread"
        ) as mock_create:
            mock_create.return_value = (MagicMock(), MagicMock())
            result = app_loop_with_mocks._do_delegate_to_ops("docker ps", mode="docker")

        assert "Ops" in result
        mock_create.assert_called_once()


class TestDelegationSuccessPath:
    """When API key is present and thread is free, delegation starts the worker and returns success message."""

    @patch("aura_cli.cli.utils.worker_factory.create_agi_worker_thread")
    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_agi_success_returns_message_and_sets_thread(
        self, mock_keys, mock_create, app_loop_with_mocks
    ):
        mock_keys.return_value = {"GOOGLE_API_KEY": "test-key"}
        worker = MagicMock(task_id="agi_task_123")
        thread = MagicMock()
        thread.name = "agi_worker_thread"
        mock_create.return_value = (worker, thread)

        result = app_loop_with_mocks._do_delegate_to_agi("implementar login")

        assert "AGI" in result and (
            "acionada" in result or "background" in result.lower()
        )
        assert "agi_task_123" in result
        assert "agi_worker_thread" in result
        assert app_loop_with_mocks.agi_thread is thread
        mock_create.assert_called_once()
        call_kw = mock_create.call_args.kwargs
        assert "implementar login" in call_kw["objective"]
        assert "[CHAT DELEGATION HANDOFF]" in call_kw["objective"]
        assert call_kw["delegation_payload"]["source"] == "general_chat"
        assert call_kw["delegation_payload"]["agent_label"] == "AGI"
        assert call_kw["delegation_payload"]["primary_request"] == "implementar login"
        status = app_loop_with_mocks.get_delegated_task_status("agi_task_123")
        assert "task_id=agi_task_123" in status
        assert "agent_type=agi" in status

    @patch("aura_cli.cli.utils.worker_factory.create_ops_worker_thread")
    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_ops_success_returns_message_and_sets_thread(
        self, mock_keys, mock_create, app_loop_with_mocks
    ):
        mock_keys.return_value = {"GOOGLE_API_KEY": "test-key"}
        worker = MagicMock(task_id="ops_task_456")
        thread = MagicMock()
        thread.name = "ops_worker_thread"
        mock_create.return_value = (worker, thread)

        result = app_loop_with_mocks._do_delegate_to_ops("git status", mode="git")

        assert "Ops" in result and (
            "acionada" in result or "background" in result.lower()
        )
        assert "ops_task_456" in result
        assert "ops_worker_thread" in result
        assert app_loop_with_mocks.ops_thread is thread
        mock_create.assert_called_once()
        call_kw = mock_create.call_args[1]
        assert call_kw.get("mode") == "git"
        assert "git status" in call_kw["task"]
        assert "[CHAT DELEGATION HANDOFF]" in call_kw["task"]
        assert call_kw["delegation_payload"]["source"] == "general_chat"
        assert call_kw["delegation_payload"]["agent_label"] == "Ops"
        assert call_kw["delegation_payload"]["delegation_mode"] == "git"
        status = app_loop_with_mocks.get_delegated_task_status("ops_task_456")
        assert "task_id=ops_task_456" in status
        assert "agent_type=ops" in status

    def test_list_delegated_tasks_empty(self, app_loop_with_mocks):
        assert "Nenhuma tarefa delegada" in app_loop_with_mocks.list_delegated_tasks()
        assert (
            "Nenhuma tarefa delegada" in app_loop_with_mocks.get_delegated_task_status()
        )
        assert (
            "Nenhuma tarefa delegada" in app_loop_with_mocks.summarize_delegated_task()
        )
        assert (
            "Nenhuma tarefa delegada"
            in app_loop_with_mocks.reattach_delegated_task_context()
        )

    def test_loads_persisted_delegated_tasks_for_same_project(self):
        # The lazy import inside _get_persistent_store must be patched at the
        # module level *before* AppLoop.__init__ runs, so we use a context
        # manager and import AppLoop inside it (same pattern as the fixture).
        #
        # On macOS /tmp is a symlink to /private/tmp. AppLoop resolves the
        # canonical path, so the persisted project_root must match it.
        import os

        tmp_real = str(Path(os.path.realpath("/tmp")))

        persistent_store = MagicMock()
        persistent_store.get_recent_tasks.return_value = [
            {
                "task_id": "persisted_agi_1",
                "name": "delegated_agi",
                "status": "stopped",
                "created_at": "2026-04-24T12:00:00",
                "completed_at": None,
                "data": {
                    "kind": "delegated_chat_task",
                    "project_root": tmp_real,
                    "agent_type": "agi",
                    "thread_name": "old_agi_thread",
                    "prompt": "analisar arquitetura",
                    "mode": None,
                    "delegation_payload": {
                        "primary_request": "analisar arquitetura",
                        "source": "general_chat",
                    },
                    "created_at_ts": 123.0,
                },
            },
            {
                "task_id": "persisted_other_project",
                "name": "delegated_ops",
                "status": "running",
                "created_at": "2026-04-24T12:00:01",
                "completed_at": None,
                "data": {
                    "kind": "delegated_chat_task",
                    "project_root": "/different",
                    "agent_type": "ops",
                    "thread_name": "other_thread",
                    "prompt": "git status",
                    "mode": "git",
                    "delegation_payload": {},
                    "created_at_ts": 124.0,
                },
            },
        ]

        with patch("aura_cli.core.memory.get_persistent_store") as mock_store:
            mock_store.return_value = persistent_store

            from aura_cli.cli.app_loop import AppLoop
            from aura_cli.cli.ui.manager import UIManager

            app = AppLoop(
                ui=MagicMock(spec=UIManager),
                stats=MagicMock(),
                console=MagicMock(),
                conversation_history=[{"role": "system", "content": "You are Aura."}],
                context_manager=MagicMock(),
                available_tools={},
                initial_model="gemini/gemini-2.5-flash",
                project_root=Path("/tmp"),
                runtime_services=make_runtime_services(Path("/tmp")),
            )

        summary = app.summarize_delegated_task("persisted_agi_1")
        assert "task_id=persisted_agi_1" in summary
        assert "primary_request=analisar arquitetura" in summary
        assert "persisted_other_project" not in app.list_delegated_tasks()

    @patch("aura_cli.cli.session_lifecycle.get_thread_manager")
    def test_status_falls_back_to_persisted_status_when_thread_is_gone(
        self, mock_thread_manager, app_loop_with_mocks
    ):
        mock_thread_manager.return_value.get_thread_info.return_value = None
        app_loop_with_mocks._task_manager.tasks["persisted_ops_1"] = {
            "task_id": "persisted_ops_1",
            "agent_type": "ops",
            "thread_name": "finished_thread",
            "prompt": "git status",
            "mode": "git",
            "delegation_payload": {"primary_request": "git status"},
            "created_at": 123.0,
            "persisted_status": "stopped",
        }

        status = app_loop_with_mocks.get_delegated_task_status("persisted_ops_1")
        assert "status=stopped" in status
        assert "alive=False" in status

    @patch("aura_cli.cli.session_lifecycle.get_thread_manager")
    def test_status_reconciles_live_worker_final_result(
        self, mock_thread_manager, app_loop_with_mocks
    ):
        mock_thread_manager.return_value.get_thread_info.return_value = None
        worker_ref = MagicMock()
        worker_ref.final_result = {
            "status": "completed",
            "tools_used": ["git_status"],
            "snapshot_path": "/tmp/.aura/notebooks/page_001.txt",
        }
        worker_ref.final_error = None
        worker_ref.last_snapshot_path = "/tmp/.aura/notebooks/page_001.txt"
        worker_ref.completed_at = 321.0
        app_loop_with_mocks._task_manager.tasks["ops_live_1"] = {
            "task_id": "ops_live_1",
            "agent_type": "ops",
            "thread_name": "finished_thread",
            "prompt": "git status",
            "mode": "git",
            "delegation_payload": {"primary_request": "git status"},
            "created_at": 123.0,
            "persisted_status": "running",
            "worker_ref": worker_ref,
            "final_result": None,
            "final_error": None,
            "snapshot_path": None,
        }

        status = app_loop_with_mocks.get_delegated_task_status("ops_live_1")
        summary = app_loop_with_mocks.summarize_delegated_task("ops_live_1")
        assert "status=completed" in status
        assert "supervisor_state=completed" in status
        assert "fallback_reason=" not in status or "fallback_reason=None" not in status
        assert "snapshot_path=/tmp/.aura/notebooks/page_001.txt" in summary
        assert "snapshot_page=page_001.txt" in summary
        assert "supervisor_state=completed" in summary
        assert "fallback_reason=n/a" in summary
        assert "result_summary=" in summary

    @patch("aura_cli.cli.delegated_tasks.notebook_service")
    def test_read_delegated_task_snapshot(
        self, mock_notebook_service, app_loop_with_mocks
    ):
        mock_notebook_service.read_page.return_value = "# Snapshot\nconteudo importante"
        app_loop_with_mocks._task_manager.tasks["agi_snap_1"] = {
            "task_id": "agi_snap_1",
            "agent_type": "agi",
            "thread_name": "done_thread",
            "prompt": "analisar arquitetura",
            "mode": None,
            "delegation_payload": {"primary_request": "analisar arquitetura"},
            "created_at": 100.0,
            "persisted_status": "completed",
            "worker_ref": None,
            "final_result": {"status": "completed"},
            "final_error": None,
            "snapshot_path": "/tmp/.aura/notebooks/page_010.txt",
        }

        result = app_loop_with_mocks.read_delegated_task_snapshot("agi_snap_1")
        assert "[DELEGATED TASK SNAPSHOT]" in result
        assert "snapshot_path: /tmp/.aura/notebooks/page_010.txt" in result
        assert "conteudo importante" in result

    @patch("aura_cli.cli.delegated_tasks.os.path.exists", return_value=True)
    def test_get_delegated_task_artifacts(self, _mock_exists, app_loop_with_mocks):
        app_loop_with_mocks._task_manager.tasks["ops_art_1"] = {
            "task_id": "ops_art_1",
            "agent_type": "ops",
            "thread_name": "done_thread",
            "prompt": "git status",
            "mode": "git",
            "delegation_payload": {"primary_request": "git status"},
            "created_at": 100.0,
            "persisted_status": "completed",
            "worker_ref": None,
            "final_result": {
                "status": "completed",
                "tools_used": ["git_status"],
                "generated_files": ["infra/docker-compose.yml"],
                "edited_files": ["src/app.py"],
                "analyzed_files": ["README.md"],
                "files_touched": [
                    "infra/docker-compose.yml",
                    "src/app.py",
                    "README.md",
                ],
                "workflow_result": {"status": "completed", "iterations": 1},
            },
            "final_error": None,
            "snapshot_path": "/tmp/.aura/notebooks/page_011.txt",
        }

        artifacts = app_loop_with_mocks.get_delegated_task_artifacts("ops_art_1")
        assert "supervisor_state=completed" in artifacts
        assert "fallback_reason=n/a" in artifacts
        assert "snapshot_exists=True" in artifacts
        assert "tools_used=['git_status']" in artifacts
        assert "generated_files=['infra/docker-compose.yml']" in artifacts
        assert "edited_files=['src/app.py']" in artifacts
        assert "analyzed_files=['README.md']" in artifacts
        assert (
            "files_touched=['infra/docker-compose.yml', 'src/app.py', 'README.md']"
            in artifacts
        )
        assert "workflow_result={'status': 'completed', 'iterations': 1}" in artifacts

    @patch("aura_cli.cli.utils.worker_factory.create_agi_worker_thread")
    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_get_latest_delegated_task_by_agent_type(
        self, mock_keys, mock_create, app_loop_with_mocks
    ):
        mock_keys.return_value = {"GOOGLE_API_KEY": "test-key"}
        worker = MagicMock(task_id="agi_task_latest")
        thread = MagicMock()
        thread.name = "agi_thread_latest"
        mock_create.return_value = (worker, thread)

        app_loop_with_mocks._do_delegate_to_agi("implementar login")

        result = app_loop_with_mocks.get_latest_delegated_task("agi")
        assert "task_id=agi_task_latest" in result
        assert "agent_type=agi" in result

    @patch("aura_cli.cli.utils.worker_factory.create_agi_worker_thread")
    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_summarize_delegated_tasks(
        self, mock_keys, mock_create, app_loop_with_mocks
    ):
        mock_keys.return_value = {"GOOGLE_API_KEY": "test-key"}
        agi_worker = MagicMock(task_id="agi_task_latest")
        agi_thread = MagicMock()
        agi_thread.name = "agi_thread_latest"
        mock_create.return_value = (agi_worker, agi_thread)

        app_loop_with_mocks._do_delegate_to_agi("implementar login")

        summary = app_loop_with_mocks.summarize_delegated_tasks()
        assert "delegated_total=1" in summary
        assert "agi=1" in summary
        assert "latest_agi=task_id=agi_task_latest" in summary

    @patch("aura_cli.cli.utils.worker_factory.create_agi_worker_thread")
    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_summarize_single_delegated_task(
        self, mock_keys, mock_create, app_loop_with_mocks
    ):
        mock_keys.return_value = {"GOOGLE_API_KEY": "test-key"}
        worker = MagicMock(task_id="agi_task_detail")
        thread = MagicMock()
        thread.name = "agi_thread_detail"
        mock_create.return_value = (worker, thread)

        app_loop_with_mocks._do_delegate_to_agi(
            "implementar login", handoff_context="arquivo principal: auth.py"
        )

        summary = app_loop_with_mocks.summarize_delegated_task("agi_task_detail")
        assert "task_id=agi_task_detail" in summary
        assert "primary_request=implementar login" in summary
        assert "supporting_context=arquivo principal: auth.py" in summary

    @patch("aura_cli.cli.session_lifecycle.get_thread_manager")
    def test_status_and_summary_expose_fallback_reason(
        self, mock_thread_manager, app_loop_with_mocks
    ):
        mock_thread_manager.return_value.get_thread_info.return_value = None
        worker_ref = MagicMock()
        worker_ref.final_result = None
        worker_ref.final_error = {
            "status": "error",
            "error": "Human approval required before git commit",
            "fallback_reason": "human_approval_required",
        }
        worker_ref.last_snapshot_path = None
        worker_ref.completed_at = 999.0
        app_loop_with_mocks._task_manager.tasks["ops_need_human"] = {
            "task_id": "ops_need_human",
            "agent_type": "ops",
            "thread_name": "finished_thread",
            "prompt": "git commit",
            "mode": "git",
            "delegation_payload": {"primary_request": "git commit"},
            "created_at": 123.0,
            "persisted_status": "running",
            "worker_ref": worker_ref,
            "final_result": None,
            "final_error": None,
            "snapshot_path": None,
            "fallback_reason": None,
        }

        status = app_loop_with_mocks.get_delegated_task_status("ops_need_human")
        summary = app_loop_with_mocks.summarize_delegated_task("ops_need_human")
        artifacts = app_loop_with_mocks.get_delegated_task_artifacts("ops_need_human")

        assert "supervisor_state=awaiting_human" in status
        assert "fallback_reason=human_approval_required" in status
        assert "supervisor_state=awaiting_human" in summary
        assert "fallback_reason=human_approval_required" in summary
        assert "supervisor_state=awaiting_human" in artifacts
        assert "fallback_reason=human_approval_required" in artifacts

    @patch("aura_cli.cli.utils.worker_factory.create_agi_worker_thread")
    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_summarize_latest_delegated_task_without_args(
        self, mock_keys, mock_create, app_loop_with_mocks
    ):
        mock_keys.return_value = {"GOOGLE_API_KEY": "test-key"}
        worker = MagicMock(task_id="agi_task_latest_summary")
        thread = MagicMock()
        thread.name = "agi_thread_latest_summary"
        mock_create.return_value = (worker, thread)

        app_loop_with_mocks._do_delegate_to_agi("investigar regressao no login")

        summary = app_loop_with_mocks.summarize_delegated_task()
        assert "task_id=agi_task_latest_summary" in summary
        assert "primary_request=investigar regressao no login" in summary

    @patch("aura_cli.cli.utils.worker_factory.create_ops_worker_thread")
    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_reattach_delegated_task_context(
        self, mock_keys, mock_create, app_loop_with_mocks
    ):
        mock_keys.return_value = {"GOOGLE_API_KEY": "test-key"}
        worker = MagicMock(task_id="ops_task_context")
        thread = MagicMock()
        thread.name = "ops_thread_context"
        mock_create.return_value = (worker, thread)

        app_loop_with_mocks._do_delegate_to_ops(
            "git status", mode="git", handoff_context="branch principal release/1.0"
        )

        context = app_loop_with_mocks.reattach_delegated_task_context(
            "ops_task_context"
        )
        assert "Contexto da tarefa delegada preparado" in context
        assert "[DELEGATED TASK CONTEXT]" in context
        assert "task_id: ops_task_context" in context
        assert "supporting_context:" in context
        assert "branch principal release/1.0" in context
        assert "[DELEGATED TASK CONTEXT]" in app_loop_with_mocks.stats._pending_context
        assert app_loop_with_mocks.stats._pending_context_files == 1

    @patch("aura_cli.cli.utils.worker_factory.create_ops_worker_thread")
    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    def test_reattach_latest_delegated_task_context_without_args(
        self, mock_keys, mock_create, app_loop_with_mocks
    ):
        mock_keys.return_value = {"GOOGLE_API_KEY": "test-key"}
        worker = MagicMock(task_id="ops_task_latest_context")
        thread = MagicMock()
        thread.name = "ops_thread_latest_context"
        mock_create.return_value = (worker, thread)
        app_loop_with_mocks.stats._pending_context = "FILE CONTEXT"
        app_loop_with_mocks.stats._pending_context_files = 2

        app_loop_with_mocks._do_delegate_to_ops(
            "git diff", mode="git", handoff_context="revisar alteracoes recentes"
        )

        context = app_loop_with_mocks.reattach_delegated_task_context()
        assert "task_id: ops_task_latest_context" in context
        assert "FILE CONTEXT" in app_loop_with_mocks.stats._pending_context
        assert (
            "revisar alteracoes recentes" in app_loop_with_mocks.stats._pending_context
        )
        assert app_loop_with_mocks.stats._pending_context_files == 3
